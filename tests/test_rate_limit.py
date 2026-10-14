"""The request rate, against the limit SEAP actually published.

SEAP stated its thresholds on 2026-07-15: 500 accesses in 5 minutes from one IP, and 50
in any single second. That is 1.67 requests per second sustained.

This project got IP-blocked on 2026-09-07 after a burst test showed 37 records a second
with flat latency and that was read as permission. The fix set MAX_RPS to 4.0 and called
it conservative. 4.0 rps is 1,200 requests per 5 minutes — still 2.4x the published
limit, and it stayed that way for a day until someone read the announcement.

So the number lives in a test now. A rate limit that exists only as a constant with a
long comment above it is a rate limit that gets raised by whoever is in a hurry.
"""

from __future__ import annotations

from achizitii import config

SEAP_MAX_PER_5_MIN = 500
"""Published: accesses from one IP in a 5-minute window before restriction."""

SEAP_MAX_PER_SECOND = 50
"""Published: burst ceiling in any single second."""


def test_sustained_rate_is_within_the_published_limit() -> None:
    per_window = config.MAX_RPS * 300
    assert per_window <= SEAP_MAX_PER_5_MIN, (
        f"MAX_RPS={config.MAX_RPS} is {per_window:.0f} requests per 5 minutes, over SEAP's "
        f"published {SEAP_MAX_PER_5_MIN}. This is the mistake that caused the 2026-09-07 "
        "block and survived the first fix. If more throughput is needed, ask SEAP support "
        "— see docs/incident-2026-09-07-seap-block.md."
    )


def test_burst_rate_is_within_the_published_limit() -> None:
    """Workers share one limiter, so the worst case is MAX_RPS, not MAX_RPS x workers.

    Asserted anyway: if the limiter ever moves per-worker, the burst ceiling is the first
    thing that breaks and the symptom would be another block, not a test failure.
    """
    worst_case = config.MAX_RPS * config.DETAIL_WORKERS
    assert worst_case <= SEAP_MAX_PER_SECOND, (
        f"{config.DETAIL_WORKERS} workers at {config.MAX_RPS} rps could reach "
        f"{worst_case}/s against a published ceiling of {SEAP_MAX_PER_SECOND}"
    )


def test_headroom_is_left_for_retries() -> None:
    """Running exactly at the line means any retry crosses it.

    RETRIES>0 means a failing request is re-sent, and those re-sends count too.
    """
    assert config.MAX_RPS * 300 <= SEAP_MAX_PER_5_MIN * 0.95, (
        "leave at least 5% headroom under the published limit for retries"
    )


# -- the limiter itself, on a fake clock -------------------------------------------------
#
# The constants above say what the limit is. The tests below prove the code enforces it:
# a sliding 5-minute window and a per-second burst ceiling, shared by every worker and
# every client in the process, with retries counted like any other request.

import threading
from itertools import pairwise

import httpx
import pytest

from achizitii import client as client_mod
from achizitii.client import CircuitBreaker, RateLimiter, SeapClient


class FakeClock:
    """A clock that only moves when the limiter sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        assert seconds >= 0
        self.sleeps.append(seconds)
        self.now += seconds


def _limiter(clock: FakeClock, **kw: float) -> RateLimiter:
    args: dict[str, float] = {
        "max_rps": 1000.0,  # spacing out of the way unless a test sets it
        "max_per_window": 450,
        "window": 300.0,
        "max_burst": 50,
    }
    args.update(kw)
    return RateLimiter(clock=clock, sleep=clock.sleep, **args)  # type: ignore[arg-type]


def _stamps(limiter: RateLimiter, clock: FakeClock, n: int) -> list[float]:
    out = []
    for _ in range(n):
        limiter.wait()
        out.append(clock.now)
    return out


def test_minimum_spacing_between_consecutive_requests() -> None:
    clock = FakeClock()
    stamps = _stamps(_limiter(clock, max_rps=2.0), clock, 4)
    gaps = [b - a for a, b in pairwise(stamps)]
    assert gaps == pytest.approx([0.5, 0.5, 0.5])


def test_at_most_450_requests_in_any_rolling_five_minutes() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, max_per_window=450, window=300.0)
    stamps = _stamps(limiter, clock, 1200)
    for i in range(len(stamps)):
        in_window = [t for t in stamps if stamps[i] - 300.0 < t <= stamps[i]]
        assert len(in_window) <= 450, f"request {i}: {len(in_window)} in the last 5 minutes"
    # And it is a rolling window, not a fixed one: the 451st waits exactly until the first
    # falls out, so the window keeps turning over rather than resetting.
    assert stamps[450] - stamps[0] == pytest.approx(300.0)
    assert stamps[900] - stamps[450] == pytest.approx(300.0)


def test_at_most_max_burst_requests_in_any_one_second() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, max_burst=3)
    stamps = _stamps(limiter, clock, 30)
    for i in range(len(stamps)):
        in_second = [t for t in stamps if stamps[i] - 1.0 < t <= stamps[i]]
        assert len(in_second) <= 3, f"request {i}: {len(in_second)} in one second"
    assert stamps[:4] == pytest.approx([1000.0, 1000.0, 1000.0, 1001.0], abs=0.01)


def test_both_caps_hold_together_at_the_default_settings() -> None:
    clock = FakeClock()
    limiter = _limiter(
        clock,
        max_rps=config.MAX_RPS,
        max_per_window=config.SEAP_MAX_PER_WINDOW,
        window=config.SEAP_WINDOW,
        max_burst=config.SEAP_MAX_BURST,
    )
    stamps = _stamps(limiter, clock, 1000)
    for i in range(len(stamps)):
        assert (
            sum(1 for t in stamps if stamps[i] - 300.0 < t <= stamps[i]) <= SEAP_MAX_PER_5_MIN * 0.9
        )
        assert sum(1 for t in stamps if stamps[i] - 1.0 < t <= stamps[i]) <= 2


def test_the_window_is_shared_across_threads() -> None:
    """Workers do not each get their own 450: the count is per process, like the block."""
    clock = FakeClock()
    limiter = _limiter(clock, max_per_window=10, window=300.0)
    lock = threading.Lock()
    stamps: list[float] = []

    def worker() -> None:
        for _ in range(5):
            limiter.wait()
            with lock:
                stamps.append(clock.now)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(stamps) == 20
    assert sum(1 for t in stamps if t < 1300.0) == 10
    assert sum(1 for t in stamps if 1300.0 <= t < 1600.0) == 10


def test_default_limiter_is_one_per_process() -> None:
    a, b = SeapClient(), SeapClient()
    try:
        assert a._limiter is b._limiter is client_mod.SEAP_LIMITER
    finally:
        a.close()
        b.close()


# -- retries and backoff -----------------------------------------------------------------


class _Transport(httpx.BaseTransport):
    def __init__(self, statuses: list[int]) -> None:
        self.statuses = statuses
        self.calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        status = self.statuses[min(self.calls, len(self.statuses) - 1)]
        self.calls += 1
        return httpx.Response(status, json={"ok": status == 200}, request=request)


def _client(
    clock: FakeClock, statuses: list[int], **limits: float
) -> tuple[SeapClient, _Transport]:
    transport = _Transport(statuses)
    limiter = _limiter(clock, **limits)
    c = SeapClient(
        limiter=limiter, sleep=clock.sleep, transport=transport, breaker=CircuitBreaker()
    )
    return c, transport


@pytest.mark.parametrize("status", [500, 503])
def test_retries_back_off_exponentially_on_server_errors(status: int) -> None:
    clock = FakeClock()
    c, transport = _client(clock, [status, status, 200])
    with c:
        assert c.get("/x") == {"ok": True}
    assert transport.calls == 3
    # One backoff sleep per failed attempt, doubling from the base.
    assert config.BACKOFF_BASE in clock.sleeps and config.BACKOFF_BASE * 2 in clock.sleeps


def test_gives_up_after_retries_and_raises_the_last_status() -> None:
    clock = FakeClock()
    c, transport = _client(clock, [503])
    with c, pytest.raises(httpx.HTTPStatusError):
        c.get("/x")
    assert transport.calls == config.RETRIES


def test_other_4xx_are_not_retried() -> None:
    clock = FakeClock()
    c, transport = _client(clock, [404])
    with c, pytest.raises(httpx.HTTPStatusError):
        c.get("/x")
    assert transport.calls == 1


def test_retries_count_against_the_window() -> None:
    """A retry is a request SEAP sees, so it takes a slot like any other."""
    clock = FakeClock()
    c, transport = _client(clock, [500, 500, 200], max_per_window=3, window=300.0)
    with c:
        first = clock.now
        c.get("/x")  # three requests (two retries): the window is now full
        c.get("/y")  # waits until the first attempt's slot has aged out
    assert transport.calls == 4
    assert clock.now == pytest.approx(first + 300.0)


# -- configuration -----------------------------------------------------------------------


def test_environment_overrides_are_clamped_under_the_published_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_PER_WINDOW", "9000")
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_BURST", "99")
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_RPS", "30")
    per_window, burst, rps = config.seap_limits()
    assert per_window <= SEAP_MAX_PER_5_MIN * 0.95
    assert burst <= 5
    assert rps * 300 <= SEAP_MAX_PER_5_MIN * 0.95


def test_environment_overrides_can_only_tighten(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_PER_WINDOW", "100")
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_BURST", "1")
    monkeypatch.setenv("ACHIZITII_SEAP_MAX_RPS", "0.5")
    assert config.seap_limits() == (100, 1, 0.5)


def test_defaults_are_the_safe_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ACHIZITII_SEAP_MAX_PER_WINDOW",
        "ACHIZITII_SEAP_MAX_BURST",
        "ACHIZITII_SEAP_MAX_RPS",
    ):
        monkeypatch.delenv(name, raising=False)
    assert config.seap_limits() == (450, 2, 1.5)


# -- OP-29: two a second, on one path ----------------------------------------------------


def test_default_per_second_cap_is_two_with_no_bursts() -> None:
    """SEAP's published ceiling is 50 a second; the collector stays at 2, and the burst
    cap and the spacing agree, so there is no moment where three go out together."""
    assert config.SEAP_MAX_BURST <= 2
    assert config.MAX_RPS <= 2
    clock = FakeClock()
    limiter = RateLimiter(clock=clock, sleep=clock.sleep)  # the shipped defaults
    stamps = _stamps(limiter, clock, 600)
    for i in range(len(stamps)):
        assert sum(1 for t in stamps if stamps[i] - 1.0 < t <= stamps[i]) <= 2
        assert sum(1 for t in stamps if stamps[i] - 300.0 < t <= stamps[i]) <= 450


def test_retries_count_against_the_per_second_cap() -> None:
    clock = FakeClock()
    c, transport = _client(clock, [500, 500, 200], max_burst=2, max_rps=1000.0)
    with c:
        c.get("/x")
    stamps = c._limiter.send_times()
    assert transport.calls == 3
    for i in range(len(stamps)):
        assert sum(1 for t in stamps if stamps[i] - 1.0 < t <= stamps[i]) <= 2


def test_only_the_client_names_the_seap_host() -> None:
    """Every SEAP request path (daily ingest, backfill, any helper) goes through SeapClient
    and its one limiter. A second module that builds its own URL would have its own budget."""
    from pathlib import Path

    src = Path(client_mod.__file__).parent
    offenders = [
        p.name
        for p in src.glob("*.py")
        if p.name not in {"client.py", "config.py"}
        and ("e-licitatie" in p.read_text(encoding="utf-8")
             or "config.API" in p.read_text(encoding="utf-8")
             or "config.BASE" in p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"these reach SEAP without SeapClient: {offenders}"


# -- OP-32: what was actually sent -------------------------------------------------------


def test_stats_report_total_and_the_busiest_window_and_second() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, max_rps=1000.0, max_per_window=10, window=300.0, max_burst=2)
    _stamps(limiter, clock, 25)
    stats = limiter.stats()
    assert stats["requests"] == 25
    assert stats["max_per_window"] == 10
    assert stats["max_per_second"] == 2


def test_stats_are_measured_when_the_request_goes_out() -> None:
    """Measured after the sleep, so a late wake-up shows up in the numbers instead of
    hiding behind the reservation it was meant to honour."""
    clock = FakeClock()

    def oversleep(seconds: float) -> None:
        clock.sleep(seconds + 0.25)

    limiter = RateLimiter(
        max_rps=1.0, max_per_window=450, window=300.0, max_burst=2,
        clock=clock, sleep=oversleep,
    )
    limiter.wait()
    limiter.wait()
    assert limiter.send_times() == pytest.approx([1000.0, 1001.25])
    assert limiter.stats()["requests"] == 2
