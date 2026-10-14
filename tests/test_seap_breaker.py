"""OP-30, OP-32, OP-33: the circuit breaker, the run report and the day guard.

On 2026-09-07 SEAP answered a burst with HTTP 403 and an HTML notice that the IP had been
restricted. The client then retried every request four times. A blocked IP that keeps
knocking is the opposite of what the notice asks for, so the first sign of a block now
stops the whole run: no retry, no further request, from any thread.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest

from achizitii import cli, config, pipeline
from achizitii.client import CircuitBreaker, RateLimiter, SeapBlocked, SeapClient

BLOCK_PAGE = (
    "<html><body><h1>Acces restricționat</h1><p>Accesul de la adresa dumneavoastră IP a fost "
    "restricționat. Sistemul a detectat, de la adresa IP de pe care accesați platforma, un "
    "volum de trafic automat care depășește limitele de utilizare normală.</p></body></html>"
)
CAPTCHA_PAGE = '<html><body><div class="g-recaptcha" data-sitekey="x"></div></body></html>'


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class Script(httpx.BaseTransport):
    """Answers from a list of responses (or exceptions), repeating the last one."""

    def __init__(self, answers: list[object]) -> None:
        self.answers = answers
        self.calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        answer = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, httpx.Response)
        return httpx.Response(
            answer.status_code, headers=answer.headers, content=answer.content, request=request
        )


def ok() -> httpx.Response:
    return httpx.Response(200, json={"ok": True})


def html(status: int, body: str) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "text/html"}, content=body.encode())


def make(answers: list[object]) -> tuple[SeapClient, Script, CircuitBreaker]:
    clock = Clock()
    transport = Script(answers)
    breaker = CircuitBreaker()
    limiter = RateLimiter(max_rps=1000.0, clock=clock, sleep=clock.sleep)
    client = SeapClient(limiter=limiter, sleep=clock.sleep, transport=transport, breaker=breaker)
    return client, transport, breaker


@pytest.mark.parametrize("status", [403, 429])
def test_403_and_429_open_the_breaker_without_a_retry(status: int) -> None:
    c, transport, breaker = make([httpx.Response(status, json={}), ok()])
    with c:
        with pytest.raises(SeapBlocked, match=str(status)):
            c.get("/x")
        assert transport.calls == 1
        # Every later request fails before it is sent.
        with pytest.raises(SeapBlocked):
            c.get("/y")
    assert transport.calls == 1
    assert breaker.is_open


@pytest.mark.parametrize("page", [BLOCK_PAGE, CAPTCHA_PAGE])
@pytest.mark.parametrize("status", [200, 503])
def test_a_block_or_captcha_page_opens_the_breaker(page: str, status: int) -> None:
    c, transport, breaker = make([html(status, page), ok()])
    with c, pytest.raises(SeapBlocked):
        c.get("/x")
    assert transport.calls == 1
    assert breaker.is_open


def test_json_that_happens_to_mention_captcha_is_not_a_block() -> None:
    """An item description is free text typed by a buyer. Only a non-JSON page is read
    for the notice."""
    c, _, breaker = make([httpx.Response(200, json={"name": "licenta captcha, trafic automat"})])
    with c:
        assert c.get("/x")["name"].startswith("licenta")
    assert not breaker.is_open


def test_three_consecutive_connection_failures_open_the_breaker() -> None:
    boom = httpx.ConnectError("refused")
    c, transport, breaker = make([boom, boom, boom, ok()])
    with c, pytest.raises(SeapBlocked, match="connection"):
        c.get("/x")
    assert transport.calls == 3
    assert breaker.is_open


def test_the_connection_count_is_shared_across_requests() -> None:
    boom = httpx.ConnectError("refused")
    c, transport, breaker = make([boom, ok(), boom, boom, boom, ok()])
    with c:
        c.get("/a")  # one failure, then success: the count resets
        with pytest.raises(SeapBlocked):
            c.get("/b")  # three in a row
    assert transport.calls == 5
    assert breaker.is_open


def test_two_connection_failures_then_success_do_not_open_it() -> None:
    boom = httpx.ConnectError("refused")
    c, _, breaker = make([boom, boom, ok()])
    with c:
        assert c.get("/x") == {"ok": True}
    assert not breaker.is_open


def test_one_breaker_per_process() -> None:
    from achizitii import client as client_mod

    a, b = SeapClient(), SeapClient()
    try:
        assert a._breaker is b._breaker is client_mod.SEAP_BREAKER
    finally:
        a.close()
        b.close()


# -- the run: completed days kept, the interrupted day discarded --------------------------


class FakeSeap(httpx.BaseTransport):
    """List and detail endpoints for a few days; detail calls for `blocked_day` get 403."""

    def __init__(self, blocked_day: str | None) -> None:
        self.blocked_day = blocked_day
        self.calls = 0
        self.after_block = 0
        self._blocked = False
        self._day_of: dict[int, str] = {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self._blocked:
            self.after_block += 1
        path = request.url.path
        if path.endswith("/GetDirectAcquisitionList/"):
            body = json.loads(request.content)
            day = body["finalizationDateStart"]
            items = []
            if body["cPVCategoryId"] == 1:
                base = int(day.replace("-", "")) * 10
                for n in range(3):
                    self._day_of[base + n] = day
                    items.append({
                        "directAcquisitionId": base + n,
                        "contractingAuthority": "4221306 - PRIMARIA TEST",
                        "supplier": "1234567 - FURNIZOR SRL",
                    })
            return httpx.Response(200, json={"items": items, "total": len(items)}, request=request)
        da_id = int(path.rsplit("/", 1)[1])
        day = self._day_of[da_id]
        if day == self.blocked_day:
            self._blocked = True
            return httpx.Response(403, headers={"content-type": "text/html"},
                                  content=BLOCK_PAGE.encode(), request=request)
        return httpx.Response(200, json={
            "directAcquisitionID": da_id,
            "finalizationDate": f"{day}T10:00:00",
            "directAcquisitionItems": [{
                "directAcquisitionItemID": da_id,
                "catalogItemName": "Hartie copiator A4",
                "cpvCode": "30197630-1 - Hartie pentru imprimare",
                "itemQuantity": 10,
                "itemMeasureUnit": "top",
                "itemClosingPrice": 25.0,
            }],
        }, request=request)


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "RAW", tmp_path / "data" / "raw")
    monkeypatch.setattr(config, "CORE", tmp_path / "data" / "core")
    monkeypatch.setattr(config, "SITE_DATA", tmp_path / "site" / "data")
    monkeypatch.setattr(pipeline, "AUTHORITY_CACHE", tmp_path / "data" / "autoritati.parquet")
    monkeypatch.setattr(pipeline.AuthorityResolver, "prime", lambda self, cuis: 0)
    # One worker makes "nothing after the 403" exact. With two, the other worker's request
    # may already be on the wire when the 403 lands; it is the only one that can be.
    monkeypatch.setattr(config, "DETAIL_WORKERS", 1)
    return tmp_path


def _run_with(monkeypatch: pytest.MonkeyPatch, transport: FakeSeap) -> dict:
    clock = Clock()
    limiter = RateLimiter(max_rps=1000.0, clock=clock, sleep=clock.sleep)

    def client() -> SeapClient:
        return SeapClient(limiter=limiter, sleep=clock.sleep, transport=transport,
                          breaker=CircuitBreaker())

    monkeypatch.setattr(pipeline, "SeapClient", client)
    return pipeline.run(date(2026, 10, 10), date(2026, 10, 12))


def test_a_clean_run_keeps_every_day_and_reports_requests(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeSeap(blocked_day=None)
    report = _run_with(monkeypatch, transport)
    assert report["aborted"] is None
    assert [d["date"] for d in report["days"]] == ["2026-10-10", "2026-10-11", "2026-10-12"]
    assert report["requests"]["requests"] == transport.calls == 3 * (12 + 3)
    assert report["requests"]["max_per_window"] >= 1
    assert report["requests"]["max_per_second"] >= 1


def test_a_block_stops_the_run_and_discards_the_day_it_interrupted(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeSeap(blocked_day="2026-10-11")
    report = _run_with(monkeypatch, transport)

    assert report["aborted"] and "403" in report["aborted"]
    assert report["aborted_day"] == "2026-10-11"
    # The day before the block is complete and kept; the blocked day and the day after
    # are not written at all.
    assert [d["date"] for d in report["days"]] == ["2026-10-10"]
    assert (config.RAW / "da-2026-10-10.jsonl.gz").is_file()
    assert not (config.RAW / "da-2026-10-11.jsonl.gz").exists()
    assert not (config.RAW / "da-2026-10-12.jsonl.gz").exists()
    assert report["items"] == 3
    # No retry storm: the 403 was the last request that reached SEAP.
    assert transport.after_block == 0


# -- the CLI: exit status, report file, step summary, the day guard ----------------------


def _fake_report(aborted: str | None) -> dict:
    return {
        "days": [], "items": 0, "comparable_items": 0, "parquet": None, "parse_version": 2,
        "aborted": aborted, "aborted_day": "2026-10-11" if aborted else None,
        "requests": {"requests": 9746, "max_per_window": 450, "max_per_second": 2},
    }


def test_cli_exits_non_zero_and_writes_the_reason_when_the_breaker_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: _fake_report("HTTP 403"))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    out = tmp_path / "report.json"
    code = cli.main(["seap", "--start", "2026-10-10", "--end", "2026-10-11", "--report", str(out)])
    assert code != 0
    assert json.loads(out.read_text())["aborted"] == "HTTP 403"
    text = summary.read_text()
    assert "HTTP 403" in text
    for figure in ("9746", "450", "500", "| 2 |", "50"):
        assert figure in text.replace(",", "")


def test_cli_summary_on_a_clean_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: _fake_report(None))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert cli.main(["seap", "--start", "2026-10-10"]) == 0
    text = summary.read_text()
    assert "Total requests" in text
    assert "rolling 5 minutes" in text
    assert "one second" in text


def test_cli_writes_the_report_even_when_the_run_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*a: object, **k: object) -> dict:
        raise RuntimeError("list endpoint gave up")

    monkeypatch.setattr(pipeline, "run", explode)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    out = tmp_path / "report.json"
    assert cli.main(["seap", "--start", "2026-10-10", "--report", str(out)]) != 0
    assert "list endpoint gave up" in json.loads(out.read_text())["aborted"]


def test_cli_refuses_a_day_that_has_not_ended(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: called.append(1) or _fake_report(None))
    today = cli.datetime.now(cli.RO_TZ).date()
    with pytest.raises(SystemExit):
        cli.main(["seap", "--start", today.isoformat()])
    with pytest.raises(SystemExit):
        cli.main(["seap", "--start", (today - timedelta(days=1)).isoformat(),
                  "--end", (today + timedelta(days=1)).isoformat()])
    assert not called
