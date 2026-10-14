"""Typeahead suggestions are touch targets: at least 44 px tall.

Design screen 01 Home (docs/design/README.md, acceptance): „suggestion items ≥ 44 px
tall”. Source-text assertion on the CSS rule, like `test_site_numbers`; the browser suite
exercises the listbox itself.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX = Path("site/index.html")


def test_suggestion_items_are_at_least_44px_tall() -> None:
    source = INDEX.read_text(encoding="utf-8")
    rule = re.search(r"#sugestii li \{([^}]*)\}", source)
    assert rule, "no rule for the suggestion items"
    assert re.search(r"min-height:\s*44px", rule.group(1)), rule.group(1)
    assert "align-items:center" in rule.group(1).replace(" ", ""), (
        "text should centre in the taller row"
    )
