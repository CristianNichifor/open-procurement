"""OP-28: the entity file's figures say which years they cover and that the lei are nominal.

Design screen 02 puts an as-of line under each tile („2016–2026”, „nominal, fără ajustare la
inflație”). Source-text assertions, like `test_site_dosar`.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")


def _facts(source: str) -> str:
    start = source.index("const dl = document.createElement('dl');")
    return source[start:source.index("cap.append(dl);", start)]


def test_the_period_comes_from_the_rows_shown() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert "const perioada = (t) =>" in source
    rule = source.split("const perioada = (t) =>", 1)[1][:400]
    assert "r.an" in rule and "Math.min" in rule and "Math.max" in rule


def test_both_sides_say_their_period_and_nominal_lei() -> None:
    facts = _facts(INDEX.read_text(encoding="utf-8"))
    assert facts.count("perioada(by.") == 2, "both sides need their own years"
    assert "lei nominali" in facts
