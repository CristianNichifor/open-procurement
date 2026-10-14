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

### DOC-1 SEAP incident status (done)

- Given `docs/incident-2026-09-07-seap-block.md`, then it carries a dated Status section
  citing run 38437561637 (GitHub runners got HTTP 200 on 2026-10-13) and saying the
  schedule stays held pending an ADR. No workflow changes.

Test: review only (documentation).

## Workflow-only (diff in the PR body for the maintainer)

- OP-8 retire `pages.yml`, leaving Cloudflare Pages as the single deploy path.

## Needs human

- Lifting the SEAP collection hold (needs an ADR).
- R2 line items, OCDS/Zenodo publication.
- Promotion PR #98 (dev to main), which stops the daily data loss on main.
