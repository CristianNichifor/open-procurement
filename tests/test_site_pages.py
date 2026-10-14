"""The methodology and the right of reply are published on the site, rendered from the
Markdown files that are their source. The rendered pages are committed, because the
site is plain static files with no build step, so this test is what keeps them equal."""

from __future__ import annotations

import importlib.util
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
