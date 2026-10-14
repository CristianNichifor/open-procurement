"""An empty result under a year filter offers „Toți anii” instead of only advice.

Design screen 02 Entity file (docs/design/README.md, acceptance): „the empty-year state
offers „Toți anii””. The empty branch of run() adds a button that clears the year and
re-runs. Source-text assertions, like `test_site_numbers`.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")


def test_empty_result_under_a_year_offers_all_years() -> None:
    source = INDEX.read_text(encoding="utf-8")
    at = source.index("status('Niciun rezultat. Relaxați filtrele.');")
    branch = source[at : at + 900]
    assert "Toți anii" in branch, "no way out of the year filter"
    assert "$('an').value = ''" in branch, "the button must clear the year"
    assert "run()" in branch, "and run again"
    assert "if ($('an').value)" in branch, "offered only when a year is set"
