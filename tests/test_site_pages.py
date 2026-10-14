"""The methodology and the right of reply are published on the site, rendered from the
Markdown files that are their source. The rendered pages are committed, because the
site is plain static files with no build step, so this test is what keeps them equal."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

SITE = Path("site")


@pytest.fixture(scope="module")
def build():
    spec = importlib.util.spec_from_file_location("build_pages", "scripts/build_pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_rendered_page_matches_its_source(build) -> None:
    stale = [name for name, html in build.render_all().items()
             if (SITE / name).read_text(encoding="utf-8") != html]
    assert not stale, f"run `python scripts/build_pages.py`: {stale} are out of date"


def test_cross_references_point_at_the_rendered_pages(build) -> None:
    pages = build.render_all()
    assert 'href="replica.html"' in pages["metodologie.html"]
    assert 'href="metodologie.html"' in pages["replica.html"]
    for html in pages.values():
        assert ".md\"" not in html, "a link to a Markdown file 404s on the site"


def test_bare_issue_links_are_clickable(build) -> None:
    html = build.render_all()["replica.html"]
    issues = "https://github.com/CristianNichifor/open-procurement/issues/new/choose"
    assert f'href="{issues}"' in html


def test_the_toggle_script_sets_the_document_language() -> None:
    js = (SITE / "lang.js").read_text(encoding="utf-8")
    assert "document.documentElement.lang" in js
    assert "aria-pressed" in js
    assert "lang=en" in js or "'lang'" in js, "the choice must survive a reload"


# OP-18: every static page starts with the family bar back to the hub.
HUB = "https://projects.cristian-nichifor.com/"
STATIC = ("metodologie.html", "replica.html", "privacy.html")


def test_static_pages_carry_the_family_bar() -> None:
    for name in STATIC:
        html = (SITE / name).read_text(encoding="utf-8")
        head = html.split("<main>", 1)[0]
        assert 'class="family-bar"' in head, name
        assert f'href="{HUB}"' in head and "Proiecte civice" in head, name
        assert 'href="./"' in head and "Achiziții publice din România" in head, name
        assert "Date reale" in head, name
        assert "data-set-lang" in head, name


# OP-15: one provenance line under the H1, and a table of contents on the long page.
STATIC_PAGES = ("metodologie.html", "replica.html", "privacy.html")


def _articles(name: str) -> list[str]:
    html = (SITE / name).read_text(encoding="utf-8")
    return re.findall(r"<article [^>]*>(.*?)</article>", html, flags=re.DOTALL)


def test_static_pages_carry_a_provenance_line_under_the_h1() -> None:
    for name in STATIC_PAGES:
        for article in _articles(name):
            after_h1 = article.split("</h1>", 1)[1].lstrip()
            assert after_h1.startswith('<p class="provenance">'), name
            line = after_h1.split("</p>", 1)[0]
            assert "data.gov.ro" in line and "ANAP/ADR" in line, name
            for target in ("./", "metodologie.html", "replica.html"):
                assert f'href="{target}"' in line, (name, target)
            if name != "privacy.html":  # the privacy page is not one of the three links
                assert f'href="{name}" aria-current="page"' in line, name


def test_the_methodology_page_has_a_table_of_contents() -> None:
    for article in _articles("metodologie.html"):
        assert '<nav class="toc"' in article
        targets = re.findall(r'<nav class="toc".*?</nav>', article, flags=re.DOTALL)[0]
        ids = set(re.findall(r'<h2 id="([^"]+)"', article))
        links = re.findall(r'href="#([^"]+)"', targets)
        assert links and set(links) <= ids, set(links) - ids
