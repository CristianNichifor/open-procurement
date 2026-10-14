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
        # What actually went out, measured after the sleep: the proof that the caps held.
        self._stats_lock = threading.Lock()
        self._out: list[float] = []
        self._out_window: deque[float] = deque()
        self._max_window = 0
        self._max_second = 0

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
        self._record(self._clock())

    def _record(self, sent: float) -> None:
        with self._stats_lock:
            self._out.append(sent)
            win = self._out_window
            win.append(sent)
            while win and win[0] <= sent - self._window:
                win.popleft()
            self._max_window = max(self._max_window, len(win))
            in_second = 0
            for t in reversed(win):
                if t <= sent - 1.0:
                    break
                in_second += 1
            self._max_second = max(self._max_second, in_second)

    def send_times(self) -> list[float]:
        with self._stats_lock:
            return list(self._out)

    def stats(self) -> dict[str, int]:
        """Requests sent, and the most in any rolling window and in any one second."""
        with self._stats_lock:
            return {
                "requests": len(self._out),
                "max_per_window": self._max_window,
                "max_per_second": self._max_second,
            }


SEAP_LIMITER = RateLimiter(*_limits_from_config())
"""The one limiter every SeapClient shares. SEAP counts per IP, not per client object."""


class SeapBlocked(RuntimeError):
    """SEAP is refusing us, or looks about to. The run stops; nothing is retried."""


# Phrases from the notice SEAP served on 2026-09-07, with and without diacritics, and the
# usual captcha markers. Read only in a response that is not JSON: an item description is
# free text and may say anything.
_BLOCK_MARKERS = (
    "a fost restricționat",
    "a fost restrictionat",
    "a fost restricţionat",
    "trafic automat",
    "captcha",
    "recaptcha",
    "hcaptcha",
    "access denied",
)


def looks_blocked(response: httpx.Response) -> bool:
    if "json" in response.headers.get("content-type", "").lower():
        return False
    try:
        body = response.text.lower()
    except Exception:  # noqa: BLE001 - an undecodable body is not evidence either way
        return False
    return any(marker in body for marker in _BLOCK_MARKERS)


class CircuitBreaker:
    """Opens once and stays open for the life of the process.

    It opens on a 403 or 429, on a page that reads as the block notice or a captcha, or on
    `config.SEAP_BREAKER_CONNECTION_FAILURES` connection failures in a row (any HTTP answer
    resets that count). Once open, every request fails before it is sent, from every
    thread. There is no half-open state: a run that was refused is over, and the next
    scheduled run is the retry.
    """

    def __init__(self, max_connection_failures: int | None = None) -> None:
        self._limit = max_connection_failures or config.SEAP_BREAKER_CONNECTION_FAILURES
        self._lock = threading.Lock()
        self._failures = 0
        self.reason: str | None = None

    @property
    def is_open(self) -> bool:
        return self.reason is not None

    def check(self) -> None:
        if self.reason is not None:
            raise SeapBlocked(self.reason)

    def trip(self, reason: str) -> SeapBlocked:
        with self._lock:
            if self.reason is None:
                self.reason = reason
                log.error("SEAP circuit breaker open: %s", reason)
        return SeapBlocked(self.reason)

    def answered(self) -> None:
        with self._lock:
            self._failures = 0

    def connection_failed(self, exc: Exception) -> SeapBlocked | None:
        with self._lock:
            self._failures += 1
            count = self._failures
        if count >= self._limit:
            return self.trip(f"{count} consecutive connection failures (last: {exc})")
        return None


SEAP_BREAKER = CircuitBreaker()
"""The one breaker every SeapClient shares: a block on one thread stops them all."""


class SeapClient:
    """Thin wrapper with retries, backoff, rate limiting and a circuit breaker.

    Retries connection errors and 5xx with exponential backoff (config.BACKOFF_BASE).
    A 403, a 429 or a block/captcha page opens the breaker instead: no retry, and no later
    request. Does NOT retry other 4xx — those mean we sent something wrong and repeating
    it is just rude. All instances share SEAP_LIMITER and SEAP_BREAKER unless given others.
    """

    def __init__(
        self,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._limiter = limiter if limiter is not None else SEAP_LIMITER
        self._breaker = breaker if breaker is not None else SEAP_BREAKER
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

    def request_stats(self) -> dict[str, int]:
        return self._limiter.stats()

    def _request(self, method: str, path: str, **kw: Any) -> httpx.Response:
        url = f"{config.API}{path}"
        last: Exception | None = None
        for attempt in range(config.RETRIES):
            self._breaker.check()
            # Every attempt, retries included, takes a slot: SEAP counts them all.
            self._limiter.wait()
            self._breaker.check()  # another thread may have tripped it while we slept
            try:
                r = self._client.request(method, url, **kw)
            except httpx.RequestError as exc:  # connect/read/protocol errors
                last = exc
                log.warning("%s %s failed (%s), attempt %d", method, path, exc, attempt + 1)
                blocked = self._breaker.connection_failed(exc)
                if blocked is not None:
                    raise blocked from exc
            else:
                self._breaker.answered()
                if r.status_code in (403, 429):
                    raise self._breaker.trip(f"HTTP {r.status_code} on {method} {path}")
                if looks_blocked(r):
                    raise self._breaker.trip(
                        f"block or captcha page (HTTP {r.status_code}) on {method} {path}"
                    )
                if r.status_code == 200:
                    return r
                if r.status_code >= 500:
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
