"""The front-door signals are a labelled bar chart whose rows are also a table.

Design screen 01 Home (docs/design/README.md, acceptance): „the signals chart has a
legend and the same rows in a table”. The list of buttons becomes one table: name, count,
and a bar proportional to the count, with a legend line saying what the bar measures.
Source-text assertions, like `test_site_numbers`.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")


def _signals_block(source: str) -> str:
    start = source.index("const semnale = manifest.indicatori || [];")
    end = source.index("// ---- 3. who buys", start)
    return source[start:end]


def test_signals_are_a_table_with_bars_and_a_legend() -> None:
    block = _signals_block(INDEX.read_text(encoding="utf-8"))
    assert "semnale-tbl" in block, "no table for the signals"
    assert "semnal-bar" in block, "no bar per row"
    assert "legend" in block and "Lungimea barei" in block, "no legend saying what the bar is"
    assert "selectTab('indicatori', ind)" in block, "rows must still open the signal"
    assert "'Temei legal'" in block and "ind.temei" in block, "every row carries its legal basis"


def test_bar_width_is_proportional_to_the_count() -> None:
    block = _signals_block(INDEX.read_text(encoding="utf-8"))
    assert "Math.max(" in block and "ind.rows" in block
    assert "width:" in block or "width =" in block
