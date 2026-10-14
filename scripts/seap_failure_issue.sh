#!/usr/bin/env bash
# Open the issue "SEAP collection failed", or comment on it if it is already open.
#
# Called by the "Report the failure" step of publish-data.yml and backfill.yml. One open
# issue collects every failure, so a run of bad days is one thread rather than a pile.
# The reason comes from the ingest report (`achizitii seap --report`) when there is one:
# its `aborted` field says why the run stopped, and `requests` what it sent.
#
#   GH_TOKEN, GITHUB_REPOSITORY, GITHUB_WORKFLOW, RUN_URL, EVENT    from the step
#   $1  path of the ingest report (optional; may not exist)

set -euo pipefail

REPORT="${1:-}"
REASON=""
SENT="no ingest report was written"
if [ -n "$REPORT" ] && [ -f "$REPORT" ]; then
  REASON=$(jq -r '.aborted // empty' "$REPORT")
  SENT=$(jq -r '"\(.requests.requests // 0) requests sent; at most \(.requests.max_per_window // 0) in any 5 minutes and \(.requests.max_per_second // 0) in any one second"' "$REPORT")
fi
[ -n "$REASON" ] || REASON="a step other than the SEAP ingest failed; see the run log"

TITLE="SEAP collection failed"
BODY=$(printf '%s (%s) failed: %s\n\n**Reason:** %s\n\n%s.\n\nA day the run did not collect can be collected with backfill.yml, one day per dispatch; see docs/incident-2026-09-07-seap-block.md.' \
  "$GITHUB_WORKFLOW" "${EVENT:-unknown event}" "$RUN_URL" "$REASON" "$SENT")

NUM=$(gh issue list -R "$GITHUB_REPOSITORY" --state open --search "\"$TITLE\" in:title" \
  --json number,title --jq "map(select(.title == \"$TITLE\")) | .[0].number // empty")
if [ -n "$NUM" ]; then
  gh issue comment "$NUM" -R "$GITHUB_REPOSITORY" --body "$BODY"
else
  gh issue create -R "$GITHUB_REPOSITORY" --title "$TITLE" --body "$BODY"
fi
