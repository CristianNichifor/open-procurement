"""OP-31, OP-33: scheduled SEAP collection, resumed on the owner's decision of 2026-10-14.

This replaces `test_seap_hold.py`, which guarded the hold of 2026-09-08 and asked to be
deleted when it was lifted. What it guards now is the shape of a safe resume: the schedule
collects, two runs that reach SEAP never overlap, the job has the time a weekday takes at
the enforced rate, and a failure is reported where someone will see it.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(".github/workflows")
SEAP_STEP = re.compile(r"^[^#\n]*\bachizitii seap\b", re.MULTILINE)


def _load(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(flow: dict[str, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the bare key `on` as the boolean True.
    return flow.get("on", flow.get(True)) or {}


def _steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    (job,) = flow["jobs"].values()
    return job["steps"]


def _step(flow: dict[str, Any], name: str) -> dict[str, Any]:
    for step in _steps(flow):
        if step.get("name") == name:
            return step
    raise AssertionError(f"no step named {name!r}")


@pytest.fixture(scope="module")
def daily() -> dict[str, Any]:
    return _load("publish-data.yml")


@pytest.fixture(scope="module")
def backfill() -> dict[str, Any]:
    return _load("backfill.yml")


def test_only_the_two_seap_workflows_reach_seap() -> None:
    reaching = sorted(
        p.name for p in WORKFLOWS.glob("*.yml") if SEAP_STEP.search(p.read_text("utf-8"))
    )
    assert reaching == ["backfill.yml", "publish-data.yml"]


def test_the_schedule_collects_and_a_push_does_not(daily: dict[str, Any]) -> None:
    triggers = _triggers(daily)
    assert triggers["schedule"] and "workflow_dispatch" in triggers and "push" in triggers
    ingest = _step(daily, "Ingest")
    # True for schedule and workflow_dispatch; a merge to main only rebuilds the bundle.
    assert ingest["if"] == "github.event_name != 'push'"
    assert "achizitii seap" in ingest["run"]


def test_the_job_has_time_for_a_weekday_at_the_cap(daily: dict[str, Any],
                                                   backfill: dict[str, Any]) -> None:
    """A weekday is about 9,700 requests, about 1 h 50 min at 1.5 a second."""
    for flow in (daily, backfill):
        (job,) = flow["jobs"].values()
        assert job["timeout-minutes"] >= 300


def test_seap_runs_never_overlap(daily: dict[str, Any], backfill: dict[str, Any]) -> None:
    groups = []
    for flow in (daily, backfill):
        concurrency = flow["concurrency"]
        assert concurrency["cancel-in-progress"] is False, "never kill a run mid-collection"
        groups.append(concurrency["group"])
    assert groups[0] == groups[1] == "ingest-seap", groups
    # Workflow-level, so schedule, dispatch, push and backfill all queue on it; a job-level
    # group would leave the workflow-level one free.
    for flow in (daily, backfill):
        (job,) = flow["jobs"].values()
        assert "concurrency" not in job


@pytest.mark.parametrize("name", ["publish-data.yml", "backfill.yml"])
def test_a_failure_opens_or_updates_the_issue(name: str) -> None:
    flow = _load(name)
    assert flow["permissions"].get("issues") == "write"
    step = _step(flow, "Report the failure")
    assert step["if"] == "failure()"
    assert step["run"].startswith("./scripts/seap_failure_issue.sh")
    assert "seap-report.json" in step["run"]
    script = Path("scripts/seap_failure_issue.sh").read_text(encoding="utf-8")
    assert 'TITLE="SEAP collection failed"' in script
    assert "gh issue comment" in script and "gh issue create" in script
    assert ".aborted" in script, "the reason comes from the ingest report"


@pytest.mark.parametrize("name", ["publish-data.yml", "backfill.yml"])
def test_the_ingest_writes_a_report(name: str) -> None:
    flow = _load(name)
    ingest = next(s for s in _steps(flow) if "achizitii seap" in str(s.get("run", "")))
    assert "--report" in ingest["run"]
    assert ingest.get("id") == "ingest"


def test_completed_days_are_kept_when_the_ingest_fails(daily: dict[str, Any]) -> None:
    """The ingest exits non-zero when the breaker opens, after writing the days it finished.
    The steps that archive and commit them must still run; the job still ends failed."""
    for name in ("Archive prices and rebuild the published bundle", "Commit the day"):
        condition = _step(daily, name)["if"]
        assert "!cancelled()" in condition and "steps.test.outcome == 'success'" in condition


def test_backfill_takes_one_day(backfill: dict[str, Any]) -> None:
    inputs = _triggers(backfill)["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"day"}
    assert inputs["day"]["required"] is True
    assert "schedule" not in _triggers(backfill)
    ingest = _step(backfill, "Collect the day")
    assert '--start "$DAY" --end "$DAY"' in ingest["run"]
    assert "while" not in ingest["run"], "one day per dispatch, no loop"


def test_backfill_fetches_the_bundle_before_publishing(backfill: dict[str, Any]) -> None:
    """`achizitii publish --only preturi` merges into an existing manifest."""
    names = [s.get("name") for s in _steps(backfill)]
    assert names.index("Fetch the bundle") < names.index("Archive and commit the day")


@pytest.mark.parametrize("open_issue", ["", "41"])
def test_the_failure_script_comments_on_an_open_issue_or_creates_one(
    tmp_path: Path, open_issue: str
) -> None:
    import json
    import os
    import shutil
    import subprocess

    if not shutil.which("jq"):
        pytest.skip("jq is not installed")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$CALLS"\n'
        f'if [ "$1 $2" = "issue list" ]; then printf "%s" "{open_issue}"; fi\n'
    )
    gh.chmod(0o755)
    report = tmp_path / "report.json"
    report.write_text(json.dumps({
        "aborted": "circuit breaker: HTTP 403 on GET /x",
        "requests": {"requests": 120, "max_per_window": 120, "max_per_second": 2},
    }))
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALLS": str(calls),
           "GITHUB_REPOSITORY": "o/r", "GITHUB_WORKFLOW": "SEAP line items",
           "RUN_URL": "https://example.invalid/run/1", "EVENT": "schedule"}
    subprocess.run(["bash", "scripts/seap_failure_issue.sh", str(report)], env=env, check=True)
    log = calls.read_text()
    if open_issue:
        assert "issue comment 41" in log and "issue create" not in log
    else:
        assert "issue create" in log and "--title SEAP collection failed" in log
    assert "HTTP 403" in log and "120 requests sent" in log
