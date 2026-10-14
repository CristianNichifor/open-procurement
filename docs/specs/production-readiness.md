# Production readiness

Each item has an ID, its acceptance criteria and the test that proves it. Status is one
of: todo, done, blocked, needs-human. Text written in a language the maintainer did not
write it in is marked **needs human review**.

Canonical address of the site: `https://projects.cristian-nichifor.com/open-procurement/`.

## Theme A: discoverability and trust

### OP-3 Link previews and canonical address (done)

- Given the published `site/index.html`, when a crawler or a chat app reads its `<head>`,
  then it finds a `meta name="description"`, `og:title`, `og:description`, `og:type`,
  `og:url`, `link rel="canonical"` (both equal to the canonical address) and an absolute
  `og:image` pointing at a file under `site/`.
- Given the `og:image` file, when its PNG header is read, then it is 1200 x 630 and was
  drawn from the site's own motif (no third-party marks).

Test: `tests/test_site_meta.py`.

### OP-6 Privacy page (done)

- Given `site/privacy.html`, when it is read in Romanian or English, then it states that
  the site sets no cookies and runs no analytics, names the hosting (Cloudflare Pages,
  and GitHub Pages for the older github.io address) and the third-party requests (the
  DuckDB-Wasm engine from cdn.jsdelivr.net, its parquet and httpfs extensions from
  extensions.duckdb.org, both measured in a browser), names the operator Cristian Nichifor
  and gives the repository's GitHub issues as the contact.
- Given the front page footer, then it links to `privacy.html`.
- Given the site source, then no script sets `document.cookie` or loads an analytics
  service, so the page's claim stays true.

Test: `tests/test_site_links.py` (privacy section). English and Romanian text written by
an agent: **needs human review**.

### OP-5 Methodology and right of reply on the site (done)

- Given the front page caveat, when a reader follows "metodologia" or "dreptul la
  replică", then they land on same-origin pages (`metodologie.html`, `replica.html`),
  not on GitHub.
- Given any file under `site/`, then it contains no `github.com/.../blob/` link.
- Given `METHODOLOGY.md` and `CORRECTIONS.md`, when `scripts/build_pages.py` renders them,
  then the output equals the committed pages, so the site cannot drift from the docs.
- Given any of the static pages (privacy, methodology, right of reply), when the reader
  presses the RO/EN toggle, then `<html lang>` changes to the chosen language and only
  that language's text is shown; the choice survives a reload through the address
  (`?lang=en`; the site keeps nothing in browser storage).

Tests: `tests/test_site_links.py`, `tests/test_site_pages.py`,
`tests/browser/pages.spec.js`. The Romanian summary of the methodology (the source is
English only) is agent-written: **needs human review**.

## Theme B: resilience and quality

### OP-4 The front page survives a blocked CDN (done)

- Given cdn.jsdelivr.net is unreachable, when the front page loads, then the panorama
  still renders from JSON, and the status line names cdn.jsdelivr.net as the thing that
  failed instead of the old "serve over HTTP (not file://)" hint.
- Self-hosting the engine was assessed: the DuckDB-Wasm 1.29.0 EH module is 35.7 MB
  (MVP 40.6 MB), over Cloudflare Pages' 25 MiB per-file limit (enforced in the deploy
  workflow) and over half of `scripts/check_repo_size.py`'s 60 MB derived budget. It stays on the CDN, imported
  dynamically so that a failure cannot take the rest of the page down with it.

Test: `tests/browser/cdn-fallback.spec.js` (route `**/cdn.jsdelivr.net/**` aborted).

### OP-24 Spec items have unique ids and a named test (done)

- Given `docs/specs/production-readiness.md`, when its `###` headings are read, then each
  is `ID title (status)` with a status from the list above, no id is used twice (the
  doubled `OP-9` from before this guard is the one tolerated exception) and every item
  has a `Test:` line, so parallel sessions cannot land the same number twice as happened
  with OP-12 on 2026-10-14.

Test: `tests/test_spec_ids.py`.

### OP-7 Content Security Policy and accessibility scan (done)

- Given each page, then a `<meta http-equiv="Content-Security-Policy">` allows only self,
  cdn.jsdelivr.net and extensions.duckdb.org where the engine needs them, and
  `data:`/`blob:` where needed. The inline module is allowed by its sha256 hash, which
  `scripts/build_pages.py` keeps current; inline event handlers are gone.
- Given the real engine boot and queries, when the policy is applied, then no
  `securitypolicyviolation` event fires (`tests/browser/csp.spec.js`).
- SRI is not applied to the engine (blocked): DuckDB-Wasm fetches its own worker, wasm and
  extensions, none of which can carry an integrity attribute, and jsDelivr's `+esm` build
  resolves its dependency versions server side, so a pinned hash could break the page
  without any change here.
- Given the front page and the static pages, when axe-core scans them, then there are no
  serious or critical violations.

Tests: `tests/test_site_meta.py` (CSP), `tests/browser/csp.spec.js`,
`tests/browser/a11y.spec.js` (axe-core 4.13 via `@axe-core/playwright`, both colour
schemes). The scan found no serious or critical violations, so nothing needed fixing.

### OP-23 No internal terms in the interface (done)

- Given every page under `site/` except the privacy notice and the methodology (which
  name the plumbing on purpose), when its visible text and the Romanian string literals
  of its script are read, then none of the terms banned by `docs/ux-guidelines.md` §3
  appears: DuckDB, Parquet, bundle, R2, OCDS, bucket, release, `n minim`.
- Given a string that still violates the rule, then it is listed in the test as a
  ceiling with the deviation it belongs to, so no new violation can land. Today: „fișierele Parquet” twice on the
  front page (new deviation D-8, to add to the guideline once `docs/ux-guidelines.md`
  is free to edit) and `n minim` once (D-7, being replaced).

Test: `tests/test_site_vocabulary.py`.

### DOC-1 SEAP incident status (done)

- Given `docs/incident-2026-09-07-seap-block.md`, then it carries a dated Status section
  citing run 38437561637 (GitHub runners got HTTP 200 on 2026-10-13) and saying the
  schedule stays held pending an ADR. No workflow changes.

Test: review only (documentation).

### OP-9 SEAP request rate: one global rolling window (done)

SEAP blocks an IP that makes more than 500 HTTP requests in 5 minutes, or more than 50 in
one second, whatever the URL. Run 38437561637 made 9,746 requests in 1h49m. The previous
limiter only spaced consecutive requests, per client instance.

- Given any number of `SeapClient` instances and worker threads in one process, when they
  send requests (retries included), then every request passes through one shared limiter.
- Given 450 requests in any rolling 300-second window, when the next request is due, then
  it waits until the oldest of the 450 is older than 300 seconds (`config.SEAP_MAX_PER_WINDOW`,
  default 450 of the published 500).
- Given `config.SEAP_MAX_BURST` requests (default 3) in any one second, then the next waits
  for the start of that second to be a full second ago; consecutive requests are also at
  least `1 / config.MAX_RPS` apart (default 1.5 per second).
- Given a 429, 403 or 5xx answer, when the client retries, then it waits
  `config.BACKOFF_BASE * 2^attempt` seconds first and the retry is counted by the limiter.
- Given the `ACHIZITII_SEAP_MAX_PER_WINDOW`, `ACHIZITII_SEAP_MAX_BURST` or
  `ACHIZITII_SEAP_MAX_RPS` environment variables, then they override the defaults but are
  clamped under the published ceilings (500 per 5 minutes, 50 per second).

Tests: `tests/test_rate_limit.py` (fake clock: the 5-minute cap, the per-second cap, the
minimum spacing, retries counted, backoff on 429/403/5xx, env clamp).

## Theme C: first-visit experience (UX review of the live site, 2026-10-14)

Measured on the live site: "Caută" stayed disabled for ~29 s on a cold load, a search for
"Fundeni" took 49 s with only "Se interoghează…" on screen.

### UX-1 The engine starts at once and a search can be queued (done)

- Given a cold load, when the page starts, then the engine download is requested before
  the front-door JSON, not after it.
- Given the engine is still loading, when the reader types a search and presses Caută or
  Enter, then the button is already enabled, the status says the search will run as soon
  as the engine is ready, and it does run then, landing on the entity file.
- Given the engine is downloading, then the status shows staged progress with megabytes
  ("Motor: 2,1 / 4 MB"), and a query that runs long shows how long it has been running.

Tests: `tests/browser/ux.spec.js` (queued search with a delayed wasm, request order),
`tests/test_site_boot.py`.

### UX-2 A tab change never shows the previous table (done)

- Given a results table on screen, when another table view is selected, then in the same
  task the old rows are replaced by skeleton rows, and the old chart is cleared.

Test: `tests/browser/ux.spec.js`.

### UX-3 Codes are shown as words (done)

- Given the contracts view, then `natura` reads "contract subsecvent", "plafon
  acord-cadru", not `contract_subsecvent`, `plafon_acord_cadru`.
- Given a signal table, then the `indicator` column shows the signal's name from the
  manifest, not its id (`dependenta-01`). CSV exports keep the raw codes.

Test: `tests/browser/ux.spec.js`.

### UX-4 Clickable rows look clickable (done)

- Given a row that opens something (`tr.drillable`), then its last cell shows a visible
  "Fișă →" (organisations) or "Detalii →" (price groups) cue.

Test: `tests/browser/ux.spec.js`.

### UX-5 The phone tab bar shows that it scrolls (done)

- Given a 390 px screen, when the tab bar overflows, then its edge fades, it snaps to tabs,
  and the selected tab is scrolled into view.

Test: `tests/browser/ux.spec.js`.

### UX-6 The front-door signal list has no stray bullets (done)

- Given the front door, then `.pan ul.legend` has no list bullets, so wrapped lines align.

Test: `tests/browser/ux.spec.js`.

### UX-7 Thin price groups are marked (done)

- Given a front-door price row with n < 10, then its spread ratio is greyed and a note
  explains that the ratio rests on fewer than 10 prices.

Test: `tests/browser/ux.spec.js`.

### UX-8 The data says how recent it is (done)

- Given the manifest's latest `pana_la`, then the header and the footer show "date până
  la <data>".

Test: `tests/browser/ux.spec.js`.

## Theme D: search and phone layout

### OP-9 Entity typeahead before the engine loads (done)

- Given a published bundle, when `achizitii publish` runs or
  `python scripts/build_entity_index.py` is run on an existing `site/data`, then
  `site/data/entitati.json` holds the buyers and suppliers with the largest totals as
  compact `[denumire, cui, tip]` rows, at most 2 500 of each and under 300 kB.
- Given a supplier that is a natural person (a fiscal code shaped like a CNP, or a name
  marking a sole trader: PFA, II, IF, „persoană fizică”, „cabinet individual”), then it is
  left out, in line with `gdpr.py`: the index lists organisations, never people.
- Given the front page before DuckDB-Wasm has loaded, when a reader types two or more
  letters into the search box, then up to eight matching names appear in a listbox,
  matched without regard to case or diacritics; arrow keys move through them, Enter or a
  click opens that organisation's file by its CUI, and Escape closes the list.
- Given a bundle without `entitati.json`, then the search box works as before.

Test: `tests/test_entity_index.py`, `tests/browser/typeahead.spec.js`.

### OP-10 Two-line price rows on a phone (done)

- Given a price table (product, median, p10, p90) at 480 px or narrower, then each row
  shows two lines: the product with its median, then a bar spanning p10–p90 with the
  median marked and both values beside it, instead of a card of seven labelled lines. The
  row's "Detalii →" cue stays on the second line.
- Given a wider screen, then the table is unchanged and the bar cell is hidden.

Test: `tests/browser/mobile-prices.spec.js` at 390 px and 1440 px.

## Theme E: UX guidelines

### OP-11 UX guidelines with a conformance checklist (done)

- Given `docs/ux-guidelines.md`, then it states the users and top tasks, page anatomy,
  content, data-viz, state, mobile and accessibility rules, the status vocabulary, a
  conformance checklist mapped to tests and a backlog of known deviations, in line with the
  civic-ui fleet guideline.
- Given the checklist, when a test file it names is renamed or deleted, then
  `tests/test_ux_guidelines.py` fails.
- Given the front-door footer, then it links the method page and a contact (the issue
  tracker) beside source, licence, privacy and code.
- Romanian labels in the guideline and the footer („Metodologie”, „Contact”, the status
  vocabulary) are agent-written: needs human review.

Test: `tests/test_ux_guidelines.py`, `tests/test_site_links.py`.

### OP-12 A retry on every failed query (done)

- Given a view whose query fails (a dropped connection, a blocked file), then the status line
  says „Eroare: …” followed by a „Reîncearcă” button; clicking it runs the same view again,
  and on success the button is gone.
- Given the engine fails to start, then the existing explanation is followed by a
  „Reîncearcă” button that reloads the page.
- Closes deviation D-4 in `docs/ux-guidelines.md`. „Reîncearcă” is agent-written: needs human
  review.

Test: `tests/browser/ux.spec.js` › "a failed query offers a retry that runs it again".
### OP-14 Design screens for the five main views (done)

- Given `docs/design/screens/`, when it is read, then it holds self-contained HTML
  mockups for the home (search-first, typeahead), entity file, unit prices (desktop and
  phone rows), signals and methodology screens, each with a 390 px layout and the
  loading, empty, error-with-retry and stale-data states, and no script or external
  request.
- Given `docs/design/README.md`, then every screen names the user task, the guideline
  sections it follows, what changes versus the live site and acceptance criteria.
- Given any mockup, then Romanian text uses comma-below ș ț and every figure is either
  copied from the live site on 2026-10-14 or shown as „—”.

Test: `tests/test_design_screens.py` (no `<script`, no `http` other than the hub link,
no cedilla diacritics, the five files and the README exist). Romanian copy in the
mockups is agent-written: **needs human review**.

### OP-13 A plain label for the group-size filter (done)

- Given the filter row, then the minimum-group-size control is labelled „Minimum de achiziții
  pe grup” instead of „n minim”. Closes D-7. Agent-written: needs human review.

Test: `tests/test_ux_guidelines.py` › `test_the_group_size_filter_has_a_plain_label`.
### OP-18 Family bar on the static pages (done)

- Given `metodologie.html`, `replica.html` and `privacy.html`, when the page is read, then
  the first thing in the `<header>` is a family bar (civic-ui `FamilyBar`, native markup):
  a link „Proiecte civice” to `https://projects.cristian-nichifor.com/`, the tool name
  „Achiziții publice din România” linking to `./`, the status badge „Date reale” from the
  §7 vocabulary and the RO/EN toggle, with every target at least 44 px tall.
- Given `scripts/build_pages.py`, when it runs, then the committed pages equal its output
  (OP-5 still holds) and `site/index.html` is left unchanged.
- The front page's family bar (the other half of D-1) is a separate item: `site/index.html`
  is being edited by other open PRs. Hub address and names come from the civic-ui naming
  registry (`docs/ux-guidelines.md` §9 on civic-ui `dev`).

Test: `tests/test_site_pages.py` („family bar”). Romanian strings agent-written: **needs
human review**.

### OP-15 Provenance line and contents on the static pages (done)

- Given `metodologie.html`, `replica.html` and `privacy.html`, when either language is
  shown, then directly under the H1 there is one provenance line „Date: data.gov.ro,
  exporturile trimestriale ANAP/ADR, 2016–2026” followed by links to the data, the
  methodology and the right of reply (the current page marked `aria-current`), as the
  page anatomy in `docs/ux-guidelines.md` §2 and the methodology screen in
  `docs/design/README.md` require.
- Given `metodologie.html`, then each language's article has a table of contents
  („Cuprins” / „Contents”) whose links point at ids that exist on the page's `h2`s.
- Given `scripts/build_pages.py`, then the committed pages equal its output and
  `site/index.html` is unchanged.

Test: `tests/test_site_pages.py` („provenance”, „contents”). Romanian strings
agent-written: **needs human review**.

### OP-26 Status badge from the vocabulary (done)

- Given the front door, then exactly one badge under the H1 carries one of „Date reale”,
  „Date demonstrative”, „Prototip”, „Arhivat” (UX guidelines §7); it says „Date reale”,
  and the as-of line below it keeps saying how old the newest data is.

Test: `tests/test_site_status.py`. Romanian badge title is agent-written: **needs human
review**. Closes D-2 in `docs/ux-guidelines.md`.

### OP-16 One provenance line under the title (done)

- Given the front door after the bundle loads, then `#la-zi` is one line: „Date:
  data.gov.ro, exporturile ANAP/ADR · date până la <day> · Metodologie”, with the
  methodology as a link; its title lists each source's newest day.
- Given the footer, then `#meta` carries the count of direct acquisitions only; the date
  is said once.
- Given a newest collected day more than seven days old, then the line adds „(acum N de
  zile)” (design screen 03: the stale collection says its age); fresher data adds nothing.

Test: `tests/test_site_provenance.py`; `tests/browser/ux.spec.js` („data date shown”).
Closes D-6 in `docs/ux-guidelines.md`.

### OP-17 Thin groups marked on every median view (done)

- Given any table whose rows carry a product, a median and the percentiles, when a group
  rests on fewer than 10 prices, then its median cell is greyed (`td.slab`) and one note
  under the table says the greyed figures are only indicative; the threshold is one
  module-level constant shared with the front door; the product cell carries a `*`
  (design screen 03), and the note begins with `*` so the mark is explained once.
- Given a re-render of the same table (paging, sorting), then the note appears once.

Test: `tests/test_site_thin.py`; `tests/browser/ux.spec.js` („thin groups marked”).
Closes D-5 in `docs/ux-guidelines.md`.

### OP-25 Suggestions are touch targets (done)

- Given the typeahead listbox, then each suggestion row is at least 44 px tall with its
  text vertically centred (design screen 01 Home, acceptance), so a thumb can hit one
  row on a phone.

Test: `tests/test_site_touch.py`; `tests/browser/typeahead.spec.js` drives the listbox.

### OP-19 Signals as labelled bars, same rows as a table (done)

- Given the front door's „Ce merită verificat” block, then the signals are one table:
  the signal (a button that opens it), its legal basis (design screen 04; a dash when
  the manifest carries none), its count, and a bar whose width is the count relative to
  the largest; a legend line under it says what the bar measures.

Test: `tests/test_site_signals.py`; `tests/browser/ux.spec.js` (front door) in CI.
Romanian legend text is agent-written: **needs human review**.

### OP-20 Empty year offers every year (done)

- Given a view filtered to one year, when the query returns no rows, then the status line
  says so and offers a „Toți anii” button that clears the year and runs again; without a
  year filter the advice stays as it was.

Test: `tests/test_site_empty_year.py`; browser suite in CI.

### OP-21 A natural person never gets a file (done)

- Given the entity file, when the search term is a 13-digit code (CNP-shaped) or carries a
  sole-trader marker (PFA, „persoană fizică”, „cabinet individual”, „întreprindere
  individuală”), then the status line says natural persons have no file here and points
  to the privacy page, and no query runs.

Test: `tests/test_site_natural_person.py`; browser suite in CI. Romanian message is
agent-written: **needs human review**.

### OP-22 Entity head before the engine (done)

- Given a search term that matches one entry of `site/data/entitati.json` exactly (its
  CUI, or its name without regard to case or diacritics), when the entity file opens, then
  the H2 and CUI line are drawn from the index at once, before the engine answers; the
  queried head replaces them.
- Given no exact match, then nothing is drawn early and the file proceeds as before.

Test: `tests/test_site_entity_head.py`; browser suite in CI.

## Workflow-only (diff in the PR body for the maintainer)

- OP-8 retire `pages.yml`, leaving Cloudflare Pages as the single deploy path.

## Needs human

- Lifting the SEAP collection hold (needs an ADR).
- R2 line items, OCDS/Zenodo publication.
- Promotion PR #98 (dev to main), which stops the daily data loss on main.
