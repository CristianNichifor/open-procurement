"""Dates shown to readers are Romanian; dates in the CSV and the URL stay ISO.

D-3 in docs/ux-guidelines.md: table cells rendered `toISOString().slice(0, 10)`, so a
reader saw 2026-10-14 where a Romanian page says 14.10.2026. The CSV export and the URL
keep ISO on purpose: they are read by software and compared, not read aloud.

Source-text assertions, like `test_site_numbers`; the browser suite exercises the table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

INDEX = Path("site/index.html")


@pytest.fixture(scope="module")
def source() -> str:
    return INDEX.read_text(encoding="utf-8")


def test_table_dates_are_shown_in_romanian(source: str) -> None:
    assert "const ziRo = " in source, "no shared Romanian date formatter"
    assert "toLocaleDateString('ro-RO'" in source
    # The table cell branch for date columns goes through it, not through ISO.
    cell = re.search(r"dates\.has\(c\) \? (\S+)", source)
    assert cell and cell.group(1).startswith("ziRo("), cell.group(0) if cell else None


def test_csv_and_url_dates_stay_iso(source: str) -> None:
    csv = re.search(r"if \(isDate\) return (.+);", source)
    assert csv and "toISOString().slice(0, 10)" in csv.group(1)
    assert source.count("toISOString().slice(0, 10)") == 2, "dayOf and csvCell only"
