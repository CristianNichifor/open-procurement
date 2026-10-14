# UX and UI guidelines — Achiziții publice din România

Short, enforceable rules for `site/`. They specialise the fleet guideline in civic-ui
(`docs/ux-guidelines.md` on civic-ui `dev`) and [CIVIC_UI.md](CIVIC_UI.md); where this
file is silent, those apply. The interface language is Romanian; this document is in
English like the rest of `docs/`. Romanian strings quoted here are agent-written and need
human review.

## 1. Users and top tasks

| User | Top task |
|---|---|
| Journalist, watchdog | "What did this authority buy, from whom, for how much?" |
| Supplier, competitor | "What does this product usually cost in public purchases?" |
| Official named in the data | Check a figure and use the right of reply (`replica.html`) |
| Researcher | Reproduce a view: shared link, CSV, the SQL that produced it |

**The one job of the first screen:** the search box. A reader types an authority, a
firm, a CUI or a product and gets an answer; everything else on the front door
(panorama, tabs, filters) is secondary and must not push the search below the fold at
390 px.

## 2. Page anatomy

Top to bottom, on every page of `site/`:

1. Family bar linking back to the hub (civic-ui `FamilyBar`). *Not present yet — D-1.*
2. H1 „Achiziții publice din România” and one line of purpose (`#scale`).
3. Provenance line: „Date: sursă, an” and the as-of date (`#la-zi`, footer `#meta`).
4. Primary task: search (`#hero`), then the caveat banner („Cifrele arată tipare, nu
   concluzii.”), which is always visible; only its elaboration folds on a phone.
5. Secondary views: tabs, then the selectors for that tab, then the results.
6. Reproducibility: share link, CSV, the SQL used.
7. Footer: source and licence, method, privacy, source code, contact.

## 3. Content rules

- Romanian diacritics with comma below: ș ț Ș Ț, never ş ţ (cedilla).
- Numbers: `ro-RO` (`1.234.567,8`); amounts in RON carry the unit („lei” in prose, „RON”
  in column headers and tooltips). Large sums in prose: „mil.”, „mld.” with one decimal.
- Dates shown to readers: `ro-RO` long or `zz.ll.aaaa`. ISO dates are for the CSV and the
  URL only. *Tables still show ISO — D-3.*
- Codes are shown as words (procedure types, CPV labels); the code may follow in a
  tooltip. Tested in `tests/browser/ux.spec.js` „codes are shown as words”.
- Tone: factual and neutral. A figure is a pattern, never an accusation; indicators name
  their legal basis (see [METHODOLOGY.md](../METHODOLOGY.md)).
- Natural persons are never listed or searchable (`gdpr.py`, entity index rule OP-9).
- Banned internal terms in the UI: DuckDB, Parquet, bundle, R2, OCDS (except on the
  method page), „bucket”, „release”, `n minim` without explanation, English words in
  Romanian mode.

## 4. Data visualisation

- Colours from the validated categorical palette already in `index.html` (the civic-ui
  viz palette, colour-blind safe). Identity never rests on colour alone: every chart with
  two or more series has a legend, and the table beneath is the text alternative
  (`tests/test_site_charts.py`).
- One y axis per chart; no dual axes. Values on or beside bars where space allows.
- Each chart is drawn from the rows of the table under it, so they cannot disagree.
- Every chart and every table carries its source and as-of date through the page
  provenance line; a view that shows a partial sample (thin groups, `n` below the
  threshold) marks it: cells under 10 purchases are flagged and a note says so
  (`ux.spec.js` „thin groups marked”).
- Nominal amounts unless the reader picks an inflation base year; the selector says so.

## 5. States

- Loading: `#status` (`role="status"`, `aria-live="polite"`) states what is happening;
  anything over 2 s shows staged progress (download size in MB, then the engine). A query
  typed while the engine loads is queued, not lost (`ux.spec.js`).
- Empty: say what was searched and suggest a wider filter; never an empty table.
- Error: say what failed in plain Romanian and offer „Reîncearcă”, which runs the same
  view again (OP-12, `ux.spec.js`).
- A tab change replaces the old table at once (`ux.spec.js`).
- Demo or partial data is labelled where the figure appears, not only on the method page.

## 6. Mobile, accessibility, input

- Works at 390 px and 320 px without horizontal page scroll; wide tables become stacked
  cards; price tables become two-line rows (OP-10, `mobile-prices.spec.js`).
- Touch targets at least 24 × 24 px, 44 px preferred for primary actions.
- WCAG 2.1 AA; axe reports 0 serious or critical issues in light and dark
  (`tests/browser/a11y.spec.js`, `tests/test_site_a11y.py`).
- Everything works by keyboard: tabs, typeahead (arrows, Enter, Escape), clickable rows
  (`controls.spec.js`, `typeahead.spec.js`). Focus is visible.
- `prefers-reduced-motion` removes animation; forced-colours mode keeps borders, focus and
  chart legends visible.

## 7. Status vocabulary

Use exactly one of: **Date reale** (Live data) · **Date demonstrative** (Demo data) ·
**Prototip** (Prototype) · **Arhivat** (Archived). The site publishes live data from
data.gov.ro exports; while the SEAP collection is on hold the as-of line says how old the
newest data is instead of claiming freshness.

## 8. Conformance checklist

| Rule | Test |
|---|---|
| Search first, works before the engine loads | `tests/browser/typeahead.spec.js`, `ux.spec.js` |
| Data date shown on the front door | `ux.spec.js` „data date shown” |
| Footer links source, method, privacy, code, contact | `tests/test_site_links.py` |
| Codes shown as words | `ux.spec.js` „codes are shown as words” |
| Charts: legend + table alternative | `tests/test_site_charts.py` |
| ro-RO number formatting | `tests/test_site_numbers.py` |
| Phone layout, no horizontal scroll | `tests/test_site_mobile.py`, `mobile-prices.spec.js`, `controls.spec.js` |
| axe 0 serious, light and dark | `tests/browser/a11y.spec.js` |
| RO/EN toggle sets the document language | `tests/browser/pages.spec.js` |
| Failed query offers a retry | `tests/browser/ux.spec.js` |
| Every view has a URL | `tests/test_site_links.py` |
| No IP or personal data leaks | `tests/test_no_ip_leaks.py` |

`tests/test_ux_guidelines.py` fails when a test named here no longer exists.

## 9. Known deviations backlog

From the live review (2026-10-14) and a code audit of `site/index.html`; screenshots at
1440 and 390 px were not taken in this pass.

- **D-1** No family bar back to the hub; the name differs between the hub ("Open
  Procurement") and the site („Achiziții publice din România”). Needs the hub URL and a
  naming decision from the owner.
- **D-2** No status badge from the vocabulary in §7.
- **D-3** Table date columns show ISO dates (`toISOString`) to readers; switch the displayed form to `ro-RO`, keep ISO in CSV and URL.
- ~~**D-4** Error states have no retry action.~~ Fixed by OP-12.
- ~~**D-5** Thin-sample warnings are not yet shown on every view that ranks by median.~~ Fixed by OP-17.
- **D-6** The provenance line is split between `#la-zi` and the footer `#meta`; merge
  into one „Date: …” line under the H1.
- ~~**D-7** The `n minim` control label is jargon.~~ Now „Minimum de achiziții pe grup” (OP-13).
