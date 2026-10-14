"""Rate-limited HTTP client for the SEAP `api-pub` endpoints.

The endpoints are undocumented but public. They are the same ones the e-licitatie.ro
Angular front-end calls, so no browser automation is needed — only a Referer header.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any, Self

import httpx

from . import config

log = logging.getLogger(__name__)


def _limits_from_config() -> tuple[float, int, float, int]:
    per_window, burst, rps = config.seap_limits()
    return rps, per_window, config.SEAP_WINDOW, burst


class RateLimiter:
    """Thread-safe limiter with three ceilings, all measured over reserved send times.

    - a minimum interval between consecutive requests (`max_rps`),
    - at most `max_burst` requests in any one second,
    - at most `max_per_window` requests in any rolling `window` seconds.

    Every caller reserves the next free slot under the lock, then sleeps until it. The
    reservations are kept in a deque bounded by `max_per_window`, so a retry, a second
    worker or a second client all draw from the same budget. `clock` and `sleep` are
    injectable so the tests can prove the caps without waiting five minutes.
    """

    def __init__(
        self,
        max_rps: float = config.MAX_RPS,
        max_per_window: int = config.SEAP_MAX_PER_WINDOW,
        window: float = config.SEAP_WINDOW,
        max_burst: int = config.SEAP_MAX_BURST,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_rps <= 0 or max_per_window < 1 or max_burst < 1 or window <= 0:
            raise ValueError("rate limits must be positive")
        self._interval = 1.0 / max_rps
        self._max_per_window = max_per_window
        self._window = window
        self._max_burst = max_burst
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next = 0.0
        self._sent: deque[float] = deque()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            t = max(now, self._next)
            while True:
                # Rolling window: the oldest reservation must have aged out before the
                # count can drop below the cap.
                while self._sent and self._sent[0] <= t - self._window:
                    self._sent.popleft()
                if len(self._sent) >= self._max_per_window:
                    t = self._sent[0] + self._window
                    continue
                # Burst: the reservations are sorted, so the last `max_burst` tell whether
                # this second is already full.
                if len(self._sent) >= self._max_burst:
                    earliest_in_second = self._sent[-self._max_burst]
                    if earliest_in_second > t - 1.0:
                        t = earliest_in_second + 1.0
                        continue
                break
            self._sent.append(t)
            self._next = t + self._interval
        if t > now:
            self._sleep(t - now)


SEAP_LIMITER = RateLimiter(*_limits_from_config())
"""The one limiter every SeapClient shares. SEAP counts per IP, not per client object."""


class SeapClient:
    """Thin wrapper with retries, backoff and rate limiting.

    Retries on connection errors, 403, 429 and 5xx, with exponential backoff
    (config.BACKOFF_BASE). Does NOT retry other 4xx — those mean we sent something wrong
    and repeating it is just rude. All instances share SEAP_LIMITER unless given another.
    """

    def __init__(
        self,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._limiter = limiter if limiter is not None else SEAP_LIMITER
        self._sleep = sleep
        self._client = httpx.Client(
            http2=transport is None,
            timeout=config.TIMEOUT,
            headers=config.HEADERS,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        url = f"{config.API}{path}"
        last: Exception | None = None
        for attempt in range(config.RETRIES):
            # Every attempt, retries included, takes a slot: SEAP counts them all.
            self._limiter.wait()
            try:
                r = self._client.request(method, url, **kw)
            except httpx.HTTPError as exc:  # connect/read/protocol errors
                last = exc
                log.warning("%s %s failed (%s), attempt %d", method, path, exc, attempt + 1)
            else:
                if r.status_code == 200:
                    return r
                if r.status_code in (403, 429) or r.status_code >= 500:
                    last = httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )
                    log.warning("%s %s -> %d, attempt %d", method, path, r.status_code, attempt + 1)
                else:
                    r.raise_for_status()
            if attempt + 1 < config.RETRIES:
                self._sleep(config.BACKOFF_BASE * 2**attempt)
        assert last is not None
        raise last

    def get(self, path: str) -> Any:
        return self._request("GET", path).json()

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, json=payload).json()

    # -- endpoints -------------------------------------------------------------

    def direct_acquisition_list(
        self,
        finalization_date: str,
        page_index: int = 0,
        page_size: int | None = None,
        cpv_category_id: int | None = None,
    ) -> dict[str, Any]:
        """One page of direct acquisitions finalized on `finalization_date` (YYYY-MM-DD).

        `cpv_category_id` is the only filter that meaningfully narrows a day. Measured
        against the endpoint: `publicationDate*`, `sortProperties`, a time component on
        the date, `showOngoingDa` and `cpvCode` are all ignored; `contractingAuthorityId`
        and `supplierId` expect SEAP's internal ids, not fiscal codes. Category and
        acquisition state are the two that work.
        """
        return self.post(
            "/DirectAcquisitionCommon/GetDirectAcquisitionList/",
            {
                "pageSize": page_size or config.LIST_PAGE_SIZE,
                "showOngoingDa": False,
                "cookieContext": None,
                "pageIndex": page_index,
                "cPVCategoryId": cpv_category_id,
                "sysDirectAcquisitionStateId": None,
                "publicationDateStart": None,
                "publicationDateEnd": None,
                "finalizationDateStart": finalization_date,
                "finalizationDateEnd": finalization_date,
            },
        )

    def direct_acquisition(self, da_id: int) -> dict[str, Any]:
        """Full detail including `directAcquisitionItems[]` (the line items)."""
        return self.get(f"/PublicDirectAcquisition/getView/{da_id}")

    def notice_list(
        self, start_date: str, end_date: str, page_index: int = 0, page_size: int | None = None
    ) -> dict[str, Any]:
        """Tender notices published in a date window."""
        return self.post(
            "/NoticeCommon/GetCANoticeList/",
            {
                "sysNoticeTypeIds": [3, 13, 18, 16, 8],
                "sortProperties": [],
                "pageSize": page_size or config.LIST_PAGE_SIZE,
                "sysNoticeStateId": None,
                "contractingAuthorityId": None,
                "winnerId": None,
                "cPVCategoryId": None,
                "sysContractAssigmentTypeId": None,
                "cPVId": None,
                "assignedUserId": None,
                "sysAcquisitionContractTypeId": None,
                "pageIndex": page_index,
                "startPublicationDate": start_date,
                "endPublicationDate": end_date,
            },
        )
