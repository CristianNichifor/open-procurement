"""Thin groups are marked on every view that ranks by median, not only the front door.

D-5 in docs/ux-guidelines.md: the front door greyed groups under ten prices and said why;
the unit-price, product and entity tables showed the same medians unmarked. The shared
table renderer now does both, from one threshold. Source-text assertions, like
`test_site_numbers`; `tests/browser/ux.spec.js` checks the rendered mark.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX = Path("site/index.html")


def test_one_threshold_at_module_scope() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert len(re.findall(r"^const SLAB = 10;", source, re.MULTILINE)) == 1
    assert len(re.findall(r"\bconst SLAB\b", source)) == 1, "a second, local threshold"


def test_the_shared_renderer_marks_and_explains_thin_groups() -> None:
    source = INDEX.read_text(encoding="utf-8")
    start = source.index("function fillTable(")
    end = source.index("return Math.min(table.numRows, maxRows);", start)
    body = source[start:end]
    assert "Number(row.n) < SLAB" in body, "the renderer does not look at the group size"
    assert "'slab'" in body and "mediana_ron" in body
    assert "nota-slab" in body, "the explanation is not rendered with the table"
    panorama = source.index("if (preturi && preturi.numRows)")
    assert "nota-slab" not in source[panorama:], "the front door keeps its own copy"
