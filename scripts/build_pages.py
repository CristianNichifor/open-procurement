"""Render the reader-facing documents into static pages under site/.

The methodology, the right of reply and the privacy notice live in Markdown, where they
are reviewed like code. The site is plain static files with no build step, so the
rendered pages are committed too, and tests/test_site_pages.py fails when they drift.

Each page has a Romanian and an English half, shown one at a time by site/lang.js.

Usage:
    python scripts/build_pages.py
"""

from __future__ import annotations

import base64
import hashlib
import html
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CANONICAL = "https://projects.cristian-nichifor.com/open-procurement/"
REPO = "https://github.com/CristianNichifor/open-procurement"

# Same-repo Markdown files that have a page on the site. Anything else would 404.
LINKS = {
    "METHODOLOGY.md": "metodologie.html",
    "CORRECTIONS.md": "replica.html",
}

# Served as static files, so the policy travels in a <meta> tag (frame-ancestors cannot).
STATIC_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'none'"
)
# The front page: the inline module by its hash; DuckDB-Wasm from cdn.jsdelivr.net (module,
# worker, wasm), its parquet and httpfs extensions from extensions.duckdb.org, compiled
# as WebAssembly, with the worker started from a blob: URL. Host-wide rather than pinned
# paths, because the +esm build resolves its own dependencies' versions server side.
INDEX_CSP = (
    "default-src 'self'; script-src 'self' {hash} 'wasm-unsafe-eval' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "connect-src 'self' https://cdn.jsdelivr.net https://extensions.duckdb.org; "
    "worker-src 'self' blob:; font-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'"
)
CSP_META = re.compile(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">')

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E"
    "%3Crect width='16' height='16' rx='3' fill='%23123a6b'/%3E%3Crect x='3.5' y='8.5' "
    "width='2.5' height='4.5' fill='%23fff'/%3E%3Crect x='6.75' y='5.5' width='2.5' "
    "height='7.5' fill='%23fff'/%3E%3Crect x='10' y='3' width='2.5' height='10' "
    "fill='%23fff'/%3E%3C/svg%3E"
)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _split_corrections() -> tuple[str, str]:
    """CORRECTIONS.md is one bilingual file: a shared title, then `## Română` and
    `## English`. Each half becomes a page of its own, with its own title."""
    text = _read("CORRECTIONS.md")
    ro = text.split("## Română", 1)[1].split("## English", 1)[0].rstrip().rstrip("-")
    en = text.split("## English", 1)[1]
    return "# Corectări și drept la replică\n" + ro, "# Corrections and right of reply\n" + en


def _md(text: str) -> str:
    # Bare URLs are links on GitHub; python-markdown needs them in angle brackets.
    text = re.sub(r"(?<![(<\[])(https://[^\s)>\]]+)", r"<\1>", text)
    out = markdown.markdown(text, extensions=["tables", "fenced_code"])
    for source, page in LINKS.items():
        out = out.replace(f'href="{source}"', f'href="{page}"')
    return out


PAGES = {
    "metodologie.html": {
        "title": ("Metodologia", "Methodology"),
        "description": "Cum sunt calculate prețurile unitare, agregatele și indicatorii "
                       "publicați de Open Procurement.",
        "sources": lambda: (_read("docs/site/metodologie.ro.md"), _read("METHODOLOGY.md")),
    },
    "replica.html": {
        "title": ("Drept la replică", "Right of reply"),
        "description": "Cum cereți o corectare a datelor sau publicarea unui răspuns la o "
                       "înregistrare din Open Procurement.",
        "sources": _split_corrections,
    },
    "privacy.html": {
        "title": ("Confidențialitate", "Privacy"),
        "description": "Ce face site-ul Open Procurement cu vizitatorii: fără cookie-uri, "
                       "fără analiză de trafic.",
        "sources": lambda: (_read("docs/site/privacy.ro.md"), _read("docs/site/privacy.en.md")),
    },
}

NAV = [
    ("./", "Date", "Data"),
    ("metodologie.html", "Metodologie", "Methodology"),
    ("replica.html", "Drept la replică", "Right of reply"),
    ("privacy.html", "Confidențialitate", "Privacy"),
    (REPO, "Cod sursă", "Source code"),
]


def _bilingual(ro: str, en: str) -> str:
    return (f'<span data-lang="ro" lang="ro">{html.escape(ro)}</span>'
            f'<span data-lang="en" lang="en">{html.escape(en)}</span>')


def render(name: str) -> str:
    page = PAGES[name]
    title_ro, title_en = page["title"]
    ro, en = page["sources"]()
    current = ' aria-current="page"'
    nav = " · ".join(
        f'<a href="{href}"{current if href == name else ""}>{_bilingual(r, e)}</a>'
        for href, r, e in NAV
    )
    return f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{STATIC_CSP}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title_ro)} — Open Procurement</title>
<meta name="description" content="{html.escape(page["description"])}">
<link rel="canonical" href="{CANONICAL}{name}">
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="vendor/civic-ui/native.css">
<link rel="stylesheet" href="pages.css">
<script src="lang.js" defer></script>
<noscript><style>[data-lang] {{ display: revert !important; }}</style></noscript>
</head>
<body data-title-ro="{html.escape(title_ro)} — Open Procurement" \
data-title-en="{html.escape(title_en)} — Open Procurement">
<header class="page-head">
  <a class="home" href="./">Open Procurement</a>
  <div class="lang-toggle" role="group" aria-label="Limba / Language">
    <button type="button" data-set-lang="ro" lang="ro" aria-pressed="true">RO</button>
    <button type="button" data-set-lang="en" lang="en" aria-pressed="false">EN</button>
  </div>
</header>
<main>
<article data-lang="ro" lang="ro">
{_md(ro)}
</article>
<article data-lang="en" lang="en">
{_md(en)}
</article>
</main>
<footer>
  <nav aria-label="Pagini / Pages">{nav}</nav>
</footer>
</body>
</html>
"""


def render_all() -> dict[str, str]:
    return {name: render(name) for name in PAGES}


def index_with_csp(source: str) -> str:
    """The front page with its policy naming the current hash of its inline module."""
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", source, flags=re.DOTALL)
    hashes = " ".join(
        "'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'"
        for s in scripts
    )
    meta = f'<meta http-equiv="Content-Security-Policy" content="{INDEX_CSP.format(hash=hashes)}">'
    return CSP_META.sub(lambda _: meta, source, count=1)


def main() -> None:
    for name, text in render_all().items():
        (SITE / name).write_text(text, encoding="utf-8")
        print(f"wrote site/{name}")
    index = SITE / "index.html"
    index.write_text(index_with_csp(index.read_text(encoding="utf-8")), encoding="utf-8")
    print("updated the script hash in site/index.html")


if __name__ == "__main__":
    main()
