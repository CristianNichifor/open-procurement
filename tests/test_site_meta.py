"""What a crawler or a chat app sees before anyone opens the page.

A link to the site pasted into a chat showed a bare URL: no description, no title card,
no image. Search engines had two addresses for one page (the pages.dev host and the
project path) and nothing saying which one is real.
"""

from __future__ import annotations

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
