"""The front door carries one status badge from the vocabulary in the UX guidelines.

D-2 in docs/ux-guidelines.md §7: exactly one of „Date reale”, „Date demonstrative”,
„Prototip”, „Arhivat”. The site publishes data.gov.ro exports, so it says „Date reale”.
Source-text assertions, like `test_site_numbers`.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX = Path("site/index.html")
VOCABULARY = ("Date reale", "Date demonstrative", "Prototip", "Arhivat")


def test_one_status_badge_from_the_vocabulary() -> None:
    source = INDEX.read_text(encoding="utf-8")
    badges = re.findall(r'<span class="status-badge"[^>]*>(.*?)</span>', source)
    assert len(badges) == 1, badges
    assert badges[0] in VOCABULARY, badges[0]
    # One status, not several competing ones.
    assert sum(source.count(word) for word in VOCABULARY) == 1


def test_badge_sits_in_the_family_bar() -> None:
    # OP-27 moved it from under the H1 into the family bar, as design screen 01 draws it.
    source = INDEX.read_text(encoding="utf-8")
    bar = source.index('<header class="family-bar">')
    badge = source.index('class="status-badge"')
    assert bar < badge < source.index("</header>", bar) < source.index("<h1>")
