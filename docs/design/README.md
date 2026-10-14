# Design screens

Target-state mockups for the five screens that matter most, so an implementation
session can build them without a design round trip. Each file under `screens/` is a
self-contained static page (inline CSS copying the civic-ui token values and the site's
own light/dark colours, no scripts, no external requests) with the desktop layout and a
390 px layout through one media query, and a "Stări" section at the bottom showing the
states that matter. Figures are copied from the live front page on 2026-10-14; `—`
marks a placeholder the implementation fills from the bundle. Romanian copy is
agent-written: **needs human review** (marked in `docs/specs/production-readiness.md`,
OP-14).

Inputs: [`docs/ux-guidelines.md`](../ux-guidelines.md), the civic-ui family guideline
(`docs/ux-guidelines.md` on civic-ui `dev`), the live review notes of 2026-10-14 and
`site/index.html`. Before shots of the live site: `screens/00-before-home-1440.png`,
`screens/00-before-home-390.png`. Mockup screenshots were not taken in this pass (no
browser runs were allowed on the fleet laptop); open the HTML files directly, or run
`npx playwright screenshot --viewport-size=1440,900 docs/design/screens/01-home.html out.png`.

## Shared across every screen

What changes versus today, with the guideline section it comes from:

| Change | Guideline | Deviation |
|---|---|---|
| Family bar: „← Proiecte civice”, tool name, status badge „Date reale”, RO/EN | §2.1, civic-ui §2 | D-1, D-2 |
| One provenance line under the H1: „Date: data.gov.ro, exporturile ANAP/ADR, 2016–2026 · prețuri colectate până la zz.ll.aaaa · Metodologie” | §2.3 | D-6 |
| Status badge from the §7 vocabulary; stale data keeps „Date reale” and says the age | §7 | D-2 |
| Error messages name what failed and carry „Reîncearcă” | §5 | D-4 |
| Dates shown as `zz.ll.aaaa`; ISO only in CSV and URL | §3 | D-3 |
| Thin groups (under 10) marked `*` with one note per table | §4 | D-5 |
| „Cel puțin … achiziții” replaces `n minim` | §3 | D-7 |
| Every chart: title, the question it answers, legend with names, source + as-of, „Afișează ca tabel”; one axis, values beside bars | §4 | — |
| Touch targets ≥ 24 px (44 px for search, tabs, suggestions); no horizontal page scroll at 390 px | §6 | — |

Acceptance criteria an implementation session can turn into tests are listed per screen.

## 01 Home — `screens/01-home.html`

- User task: type an authority, firm, CUI or product and get an answer (§1).
- What changes: family bar and provenance line above the search; the typeahead lists
  `autoritate/firmă · CUI` with the match in bold and a footer explaining keys and the
  natural-person rule; staged loading shows MB downloaded then the engine; the signals
  list becomes a labelled bar chart with values and a table alternative; top-spender
  rows stack into cards at 390 px; coverage tiles get an as-of line.
- Acceptance: search box and family bar visible above the fold at 390 × 844; suggestion
  items ≥ 44 px tall; `#status` shows progress text with MB while the engine downloads;
  the error state has a button labelled „Reîncearcă”; the signals chart has a legend and
  the same rows in a table.

## 02 Entity file — `screens/02-entity-file.html`

- User task: „What did this authority buy, from whom, for how much?”
- What changes: an H2 with name, kind, CUI and a right-of-reply link; three stat tiles
  (achiziții, valoare, semnale) with an as-of line; aspect/year/sum selectors with plain
  labels; per-year bar chart framed with source and table; supplier rows open the
  supplier's file; the signals table cites the legal basis; a per-section loading line.
- Acceptance: the head renders from the entity index before the engine is ready; tiles
  use `ro-RO` formatting; the empty-year state offers „Toți anii”; a natural-person
  search shows the §3 message and never a file.

## 03 Unit prices — `screens/03-unit-prices.html`

- User task: „What does this product usually cost?”
- What changes: a range chart (percentile 10 → 90 with the median mark) above the table;
  desktop keeps the seven numeric columns; at 390 px each row becomes two lines
  (product + unit, count; then „mediana … RON · 80% dintre prețuri între … și …”) per
  OP-10; thin rows carry `*`; the empty state says which days are covered.
- Acceptance: no horizontal scroll at 390 px and 320 px; every row still contains the
  median, p10 and p90 text; `*` appears only when count < 10 and exactly one note
  explains it; the stale-collection badge shows the age in days.

## 04 Signals — `screens/04-signals.html`

- User task: see which patterns exist, with their legal basis, and open the contracts.
- What changes: the caveat banner stays above the tab; the table has signal, legal
  basis, count and share, stacked on a phone; the drill-down table shows dates as
  `zz.ll.aaaa` and procedure types as words.
- Acceptance: every signal row has a non-empty legal basis; the counts match the front
  door; selecting a signal replaces the table at once (UX-2).

## 05 Methodology — `screens/05-methodology.html`

- User task: understand how a figure was made and where its limits are.
- What changes: the same family bar and provenance line as the app; a warning that the
  Romanian summary is agent-written; a two-column table of contents; definition lists for
  the aggregation rules; the signal table repeated with its legal basis.
- Acceptance: `?lang=en` switches `<html lang>` and shows only that language;
  `scripts/build_pages.py` output equals the committed page (OP-5).

## Implementation map (2026-10-14)

Where each shared change is being built, so a session picking up a screen does not
duplicate an open pull request. Update the row when a PR lands.

| Change | Screen | PR |
|---|---|---|
| Family bar on the static pages (D-1, static half) | 05 | #115 |
| Provenance line and contents on the static pages | 05 | #117 |
| Status badge under the title (D-2) | 01 | #114 |
| One provenance line under the title (D-6) | 01 | #118 |
| Thin groups marked on every median table (D-5) | 01, 03 | #120 |
| Suggestion rows at least 44 px tall | 01 | #122 |
| Dates as `zz.ll.aaaa` in tables (D-3) | 04 | #112 |
| Plain label for the group-size filter (D-7) | 03 | #110 |
| Retry on every failed query (D-4) | all | #109 (merged) |
| No internal terms in the interface (guard) | all | #119 |
| Family bar on the front page (D-1, front half) | 01–04 | OP-27 |
| Entity file head from the entity index, stat tiles, per-year chart | 02 | open |
| Range chart above the unit-price table | 03 | open |
| Signals table with legal basis and share | 04 | open |
