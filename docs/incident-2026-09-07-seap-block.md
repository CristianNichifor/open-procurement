# 2026-09-07 — SEAP blocked our IP

## Status, 2026-10-14: the hold is lifted

**On the owner's decision, scheduled collection from SEAP resumes**, on one condition:
SEAP's published limits are respected. The hold of 2026-09-08 is over; no answer to the
request of 2026-09-08 has been recorded here, and the decision does not depend on one.

**The limits, as SEAP publishes them.** An IP is blocked if it makes more than **500 HTTP
requests within 5 minutes**, or more than **50 HTTP requests in one second**, whatever the
URLs are.

**How they are enforced** (`src/achizitii/client.py`, `config.py`):

| Ceiling | Published | Enforced | Where |
|---|---|---|---|
| requests in any rolling 5 minutes | 500 | 450 | `SEAP_MAX_PER_WINDOW` |
| requests in any one second | 50 | 2 | `SEAP_MAX_BURST` |
| spacing between requests | — | 1 every 0.67 s (1.5/s) | `MAX_RPS` |

- One `RateLimiter` per process, shared by every `SeapClient`, every worker thread and
  every retry. Only `client.py` names the SEAP host (a test enforces it), so the daily
  ingest, the backfill and any helper all pass through it.
- One SEAP run at a time: `publish-data.yml` and `backfill.yml` share the concurrency
  group `ingest-seap`, never cancelling a run in progress. The limiter is per process, so
  two overlapping runs would each have had the full budget.
- Every run writes to its summary the requests it sent, the most in any rolling 5 minutes
  and the most in any one second, measured when each request went out, next to the
  enforced and published limits. Those numbers are the evidence that the limits held.

**The circuit breaker** (`client.CircuitBreaker`, one per process). It opens on an HTTP
**403** or **429**, on a page that reads as the block notice or a captcha, or on **3
connection failures in a row**. Nothing is retried after that: the request that saw it
is the last one sent, from any thread. The run stops, the day it was collecting is
discarded (written nowhere, so the never-shrink archive cannot freeze half a day), the
days it finished are archived and committed, and the job ends **failed**. A failed run
opens the issue "SEAP collection failed", or comments on it if it is open, with the
reason and the request counts. 5xx answers are still retried with backoff, inside the
same limiter.

A weekday is about 9,700 requests, about 1 h 50 min at the cap; both jobs keep a
300-minute timeout. Before this, the last run (38437561637, 2026-10-13, 9,746 requests
in 1 h 49 min, all HTTP 200) found GitHub's addresses unrestricted.

Note that the schedule only runs the workflow file on `main`, so the scheduled run
collects from the first 04:20 UTC after this change is promoted from `dev` to `main`.

### Backfilling the days missed since 2026-10-12

`backfill.yml` collects **one day per dispatch**. Dispatch a day, wait for the run to
finish, then dispatch the next; each run opens a `data/backfill-<day>` pull request into
`dev`.

```sh
gh workflow run backfill.yml -R CristianNichifor/open-procurement -f day=2026-10-12
gh run watch -R CristianNichifor/open-procurement \
  "$(gh run list -R CristianNichifor/open-procurement -w backfill.yml -L 1 --json databaseId --jq '.[0].databaseId')"
```

Which days: from 2026-10-12 up to the day before the first scheduled run's window (it
collects the three days ending yesterday, Romanian time). 2026-10-10 and 2026-10-11 are
missing too: run 38437561637 collected them but failed at its commit step before
uploading anything. The archive on `dev` holds 2026-07-01 to 2026-07-06 and 2026-09-06;
every other day since 2026-09-07 is absent and can be collected the same way. A day that
has not ended in Romanian time is refused.

**Which days are past SEAP's window.** The repository records no retention window for
`api-pub`, and none is assumed here. What it does record: days 2026-07-01 to 2026-07-06
were collected from a runner on 2026-09-08, more than two months later, and
`docs/sources.md` notes that the history from 2007 to 2018 is served from
`istoric.e-licitatie.ro`. So no day since 2026-10-12 is known to be unrecoverable. The
earlier lines in this document that call held days lost for good were about the bulk
exports, which carry no quantities, not evidence of a window in the API. If a backfill
of a weekday returns no acquisitions, treat that as the first evidence of a window and
record it here.

## Observation, 2026-10-13: GitHub runners reach SEAP

Superseded by the status above; kept as the record of what was known before the decision.

On 2026-10-13 a manual run of the SEAP line-items job,
[run 38437561637](https://github.com/CristianNichifor/open-procurement/actions/runs/38437561637)
(`workflow_dispatch` on `main`), received **HTTP 200** on all 9,746 requests to
`e-licitatie.ro/api-pub` between 17:18 and 19:07 UTC, list and detail endpoints alike. The run is marked failed, but for an unrelated reason: its last step,
"Commit the day", tried to `git add` a path that `.gitignore` excludes
(`data/autoritati.parquet`). Nothing in it suggests the restriction on GitHub's addresses
has returned.

That observation does not lift the hold. The scheduled trigger in
`.github/workflows/publish-data.yml` stays off, guarded by `tests/test_seap_hold.py`,
until an ADR records the decision to resume automated collection, at what rate, and what
the answer to the 2026-09-08 request was. Until then SEAP is contacted only by a person
starting a run by hand. The rate the collector enforces is in the follow-up of 2026-10-14
at the end of this document.

## What happened

At roughly 22:50 UTC on 2026-09-07, `e-licitatie.ro/api-pub` began returning **HTTP 403**
with `server: SICAP` and an HTML notice:

> Accesul de la adresa dumneavoastră IP a fost restricționat. Sistemul a detectat, de la
> adresa IP de pe care accesați platforma, un volum de trafic automat care depășește
> limitele de utilizare normală. […] Pentru deblocare, contactați echipa de suport,
> menționând adresa IP publică și ora la care ați întâmpinat problema.

The restriction is on the **IP address**, not an API key, and affects everything behind
that address.

## Why it happened

We went looking for the maximum sustainable request rate and treated "the server answers
quickly with no errors" as evidence that a rate was acceptable. Over roughly two hours we:

- probed concurrency at 8, 16, 24 and 32 workers
- ran a sustained 400-record burst at 16 workers, measuring 36.9 records/second
- listed a full weekday across 12 CPV categories (8,272 records)
- fetched 400 acquisition details concurrently

`MAX_RPS` had been raised from 3.0 to 40.0 and `DETAIL_WORKERS` set to 16 on the strength
of those measurements.

**The reasoning was wrong.** Latency and error rate measure whether a server *can* absorb
load, not whether its operator is willing to serve it. SICAP's own threshold for "normal
use" is the only measure that mattered, and it is not published.

## What it cost

Access to the only source of line-item quantities and unit prices that exists. The bulk
data.gov.ro exports are unaffected, so 30M rows of procurement metadata, all eight
indicators, company profiles and the whole published site keep working. What stops is the
unit-price archive, which was one day old.

## What changed

- `MAX_RPS` 40.0 → **4.0**, `DETAIL_WORKERS` 16 → **2** (~8 records/second, a little over
  twice the long-standing 3.0 that never drew a complaint)
- schedule every three hours → **once a day**, as it ran for months without incident
- both constants now carry the incident in their docstring, so the next person to find a
  "safe" rate by measurement reads this first

The CPV-category partitioning from #39 is kept: it is 12 list calls a day and was not
what drew the block. It also remains correct — it is the difference between capturing
22% and 93% of a weekday.

## To restore access

Contact SEAP support with:

- **the public IP that was restricted** — deliberately not recorded here; it is a
  residential address, it identifies a person rather than the project, and a public
  incident report is not the place for it. It is in the operator's own logs, and whoever
  sends the request will know their own address.
- **time:** 2026-09-07 ~22:50 UTC (01:50 EEST, 8 September)
- context: automated collection for an open-data project, since corrected to 1.5 req/s —
  within the published limit of 500 requests per 5 minutes

## The rule this establishes

Do not discover a service's tolerance by approaching it. For a public service with no
published rate limit, pick a rate that is obviously modest, and if more is genuinely
needed, ask the operator. A throughput measurement is not permission.

## Follow-up, 2026-09-08: the limit was published all along

The fix above set `MAX_RPS` to 4.0 and called it "far below what drew the block". That was
true and beside the point. SEAP had published its thresholds on 2026-07-15:

| Threshold | Meaning |
|---|---|
| 500 accesses in 5 minutes from one IP | 1.67 requests/second sustained |
| 50 accesses in 1 second | burst ceiling |

4.0 rps is 1,200 requests per 5 minutes — **2.4× the published sustained limit**. The
post-incident configuration was still over the line; it simply ran on GitHub runners,
whose addresses had not yet been blocked. A backfill was cancelled mid-run on 2026-09-08
when this was found.

`MAX_RPS` is now **1.5**, leaving headroom under 1.67 for retries.

### What this costs

At 1.5 rps a weekday of ~8,300 acquisitions takes about 2 hours rather than 45 minutes.
Full history goes from ~100 days of continuous fetching to **~266 days**; the last three
years, from 21 days to **~56**.

### The part that is not a rate question

The same announcement discourages parallel queries, repeated requests at short intervals,
and **continuous automated processes over extended periods**, and directs anyone needing
high-volume or recurring programmatic access to contact support. A multi-month crawl is
what that paragraph describes, at any rate. The next step is a request to SEAP support —
both to lift the block and to ask what bulk or whitelisted access exists
for a public-interest open-data project. Not another round of tuning.

### The lesson, stated plainly

The first mistake was inferring consent from performance: 37 records a second with flat
latency meant the server answered quickly, never that it agreed. The second was fixing
that by picking a smaller number that still felt polite, instead of looking for whether
the operator had said what the number should be. They had, three weeks earlier.

## Request sent, 2026-09-08

A request went to ADR — the authority that operates SEAP — at `contact@adr.gov.ro`, copied
to `contact.companii@e-licitatie.ro`. Those addresses come from adr.gov.ro itself; a search
for "SEAP support" returns mostly private resellers, including a `@yahoo.com` address, and
none of them are official channels.

It asks three things:

1. that the restriction on the affected address be lifted;
2. whether a **bulk export including line items** exists — quantities and unit prices, the
   fields no data.gov.ro export carries — at any price or on request;
3. failing that, whether there is a registration or whitelist procedure for open-data
   reusers, and what collection rate they would consider acceptable.

It states the breach plainly rather than working around it: ~40 requests a second against a
published ceiling of 500 per 5 minutes, with the announcement read only after the block. It
records the correction already shipped — 1.5 rps, with a test that fails if anyone raises
it past the published limit — and offers to stop the historical collection altogether if
they would prefer that.

It does not ask for a higher rate as a favour, and it does not mention distributing traffic
across addresses. Both would turn a legitimate request into a negotiation about how much
can be taken before someone objects.

### What happens while waiting

**Superseded the same day.** This section said "nothing changes — the daily job keeps
running from GitHub runners, which were never blocked, at a rate inside the published
limit; only local development is cut off." That was true when written and is no longer.

Later on 2026-09-08 the decision was taken to **hold all automated collection**, including
the scheduled job that was operating inside the published ceiling. Nothing now contacts
SEAP unless a person starts it by hand. The switch and the reasoning live on the schedule
trigger in `.github/workflows/publish-data.yml`, and `tests/test_seap_hold.py` guards it.

The hold is narrower than it sounds: the same scheduled job still mirrors the RUTI
meetings register, rebuilds the published bundle and uploads to R2, none of which touches
SEAP. Only the ingest is off.

**What it costs, stated once so it is not rediscovered later.** Unit prices cannot be
reconstructed retroactively — no bulk export carries quantities — so the archive only ever
grows forward from the first day collected. Every day held is a day that can never be
added. `2026-09-05` and `2026-09-07` are already gone. That is a deliberate price for
being able to say, truthfully, that nothing automated has touched SEAP since the request
went in.

The answer decides the shape of the project. A bulk export makes the ~266-day figure
irrelevant. No bulk export makes the daily archive the product, growing forward, which the
measurements support anyway: median-bearing product groups grew 21 → 75 → 136 → 253 over
the first four weekdays collected, faster than linearly, because each new day both adds
groups and pushes existing ones past the n=5 threshold.

## Follow-up, 2026-10-14: the limit is enforced, not just configured

The thresholds, restated as SEAP publishes them: an IP that makes **more than 500 HTTP
requests within 5 minutes**, or **more than 50 in one second**, is blocked, whatever the
URLs are. Run 38437561637 made 9,746 requests in 1h49m — about 1.49 a second, or 447 per
5 minutes on average — so it ran at the line, and the limiter that kept it there only
spaced consecutive requests, per client object. A second client, or a retry burst after a
timeout, had a budget of its own.

What the collector enforces now (`src/achizitii/client.py`, `RateLimiter`, one instance
per process shared by every `SeapClient`, every worker thread and every retry):

| Ceiling | Published | Enforced | Setting |
|---|---|---|---|
| requests in any rolling 5 minutes | 500 | 450 | `SEAP_MAX_PER_WINDOW` |
| requests in any one second | 50 | 2 (3 until the status above) | `SEAP_MAX_BURST` |
| sustained spacing | 1.67/s | 1.5/s (one every 0.67 s) | `MAX_RPS` |

- Each call reserves the next free send slot against the three ceilings and sleeps until
  it; the window is rolling, measured over reserved send times, not reset every 5 minutes.
- A retry is a request SEAP sees, so it takes a slot like any other.
- 5xx and connection errors are retried with exponential backoff (5, 10, 20 s) and then
  raised. 403 and 429 were retried too; since the status above they open the circuit
  breaker instead.
- `ACHIZITII_SEAP_MAX_PER_WINDOW`, `ACHIZITII_SEAP_MAX_BURST` and `ACHIZITII_SEAP_MAX_RPS`
  can lower these for a cautious run. Asking for more is clamped to 475 per window, 5 a
  second and the matching sustained rate: the environment can tighten, never cross.

`tests/test_rate_limit.py` proves the caps on a fake clock (1,200 requests never exceed
450 in any 300 s; the third request in a second waits; four threads share one window;
retries count; 404 is not retried) and that the defaults are the safe ones.

Throughput is unchanged, so the workflow's 300-minute timeout still holds: one weekday is
roughly 8,900 detail calls plus 36 list calls, about 1h40m at 1.5 a second. Backfill is
now one day per dispatch (see the status above).
