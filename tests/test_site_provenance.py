"""One provenance line under the title; the footer keeps only the count.

D-6 in docs/ux-guidelines.md: the as-of date was said once in `#la-zi` under the H1 and
again in the footer `#meta`. Now `#la-zi` is the one „Date: …” line: source, newest
collected day, and a link to the methodology. Source-text assertions, like
`test_site_numbers`; `tests/browser/ux.spec.js` checks the rendered date.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX = Path("site/index.html")


def _assignment(source: str, element: str) -> str:
    m = re.search(
        rf"\$\('{element}'\)\.(?:textContent|replaceChildren)\s*=?\s*\(?([\s\S]*?);\n", source
    )
    assert m, f"no assignment to #{element}"
    return m.group(1)


def test_one_date_line_under_the_title() -> None:
    source = INDEX.read_text(encoding="utf-8")
    line = _assignment(source, "la-zi")
    assert "'Date: data.gov.ro, exporturile ANAP/ADR'" in line, line
    assert "laZi" in line, "the newest collected day stays on the line"
    at = source.index("$('la-zi')")
    assert "metodologie.html" in source[at - 400 : at + 400], "no methodology link"


def test_footer_keeps_only_the_count() -> None:
    source = INDEX.read_text(encoding="utf-8")
    meta = _assignment(source, "meta")
    assert "achiziții directe" in meta
    assert "laZi" not in meta, "the date is said once, under the title"


def test_the_line_says_the_age_in_days_when_stale() -> None:
    """Design screen 03: the stale-collection line shows the age in days."""
    source = INDEX.read_text(encoding="utf-8")
    at = source.index("const laZi = newest")
    around = source[at - 600 : at + 300]
    assert "ageDays" in around and "86400000" in around, "no age computed from the newest day"
    assert "acum ${ageDays} de zile" in around, "the age is not said in days"
    assert "ageDays > 7" in around, "a fresh collection should not nag"
