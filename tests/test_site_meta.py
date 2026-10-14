"""What a crawler or a chat app sees before anyone opens the page.

A link to the site pasted into a chat showed a bare URL: no description, no title card,
no image. Search engines had two addresses for one page (the pages.dev host and the
project path) and nothing saying which one is real.
"""

from __future__ import annotations

import base64
import hashlib
import re
import struct
from html.parser import HTMLParser
from pathlib import Path

import pytest

SITE = Path("site")
CANONICAL = "https://projects.cristian-nichifor.com/open-procurement/"


class _Head(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "meta":
            key = a.get("name") or a.get("property") or a.get("http-equiv")
            if key:
                self.meta[key.lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel"):
            self.links[a["rel"]] = a.get("href", "")


@pytest.fixture(scope="module")
def head() -> _Head:
    parser = _Head()
    source = (SITE / "index.html").read_text(encoding="utf-8")
    parser.feed(source.split("</head>")[0])
    return parser


def test_the_page_describes_itself(head: _Head) -> None:
    description = head.meta.get("description", "")
    assert 50 <= len(description) <= 200, "a search snippet is cut at about 160 characters"
    assert head.meta.get("og:description")
    assert head.meta.get("og:title")
    assert head.meta.get("og:type") == "website"
    assert head.meta.get("og:locale") == "ro_RO"


def test_there_is_one_address(head: _Head) -> None:
    assert head.links.get("canonical") == CANONICAL
    assert head.meta.get("og:url") == CANONICAL


def test_the_preview_image_exists_and_is_the_card_size(head: _Head) -> None:
    image = head.meta.get("og:image", "")
    assert image.startswith(CANONICAL), "og:image must be absolute: scrapers do not resolve"
    local = SITE / image.removeprefix(CANONICAL)
    assert local.is_file(), f"{local} is referenced but missing"
    data = local.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1200, 630)
    assert head.meta.get("og:image:width") == "1200"
    assert head.meta.get("og:image:height") == "630"
    assert head.meta.get("og:image:alt")
    assert head.meta.get("twitter:card") == "summary_large_image"


def test_the_preview_image_is_drawn_by_a_script_in_the_repo() -> None:
    """Regenerable, and so provably free of third-party marks: the source is right here."""
    script = Path("scripts/make_og_image.mjs")
    assert script.is_file()
    assert re.search(r"og-image\.png", script.read_text(encoding="utf-8"))


# --- Content Security Policy -----------------------------------------------------------
#
# Served as plain static files, so the policy travels in a <meta> tag. The inline module
# is allowed by its hash rather than by 'unsafe-inline': an injected script tag would not
# match it. scripts/build_pages.py rewrites the hash after the script changes.

def _build():
    """scripts/build_pages.py, which extracts inline scripts with an HTML parser."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_pages", "scripts/build_pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PAGES = ("index.html", "privacy.html", "metodologie.html", "replica.html")


def _csp(page: str) -> dict[str, list[str]]:
    parser = _Head()
    parser.feed((SITE / page).read_text(encoding="utf-8").split("</head>")[0])
    policy = parser.meta.get("content-security-policy", "")
    assert policy, f"{page} has no Content-Security-Policy meta tag"
    out: dict[str, list[str]] = {}
    for directive in filter(None, (d.strip() for d in policy.split(";"))):
        name, *values = directive.split()
        out[name] = values
    return out


@pytest.mark.parametrize("page", PAGES)
def test_every_page_has_a_restrictive_policy(page: str) -> None:
    csp = _csp(page)
    assert csp["default-src"] == ["'self'"]
    assert csp["object-src"] == ["'none'"]
    assert csp["base-uri"] == ["'self'"]
    assert "'unsafe-inline'" not in csp["script-src"]
    assert "'unsafe-eval'" not in csp["script-src"]


@pytest.mark.parametrize("page", PAGES[1:])
def test_static_pages_run_only_their_own_script(page: str) -> None:
    assert _csp(page)["script-src"] == ["'self'"]


def test_the_inline_module_is_allowed_by_its_hash() -> None:
    source = (SITE / "index.html").read_text(encoding="utf-8")
    scripts = _build().inline_scripts(source)
    assert len(scripts) == 1, "one inline script, one hash"
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    assert f"'sha256-{digest}'" in _csp("index.html")["script-src"], (
        "the inline script changed: run `python scripts/build_pages.py` to update the hash"
    )


def test_the_engine_hosts_are_the_only_third_parties() -> None:
    csp = _csp("index.html")
    hosts = {v for d in csp.values() for v in d if v.startswith("https://")}
    assert hosts == {"https://cdn.jsdelivr.net", "https://extensions.duckdb.org"}
    assert "'wasm-unsafe-eval'" in csp["script-src"], "DuckDB-Wasm compiles WebAssembly"
    assert "blob:" in csp["worker-src"], "DuckDB-Wasm starts its worker from a blob URL"


def test_no_inline_event_handlers() -> None:
    """A hash covers <script> elements, not onclick="" attributes; the policy blocks them."""
    for page in PAGES:
        text = (SITE / page).read_text(encoding="utf-8")
        assert not re.search(r"\son[a-z]+=\"", text), f"{page} has an inline handler"
