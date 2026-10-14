"""The entity file's head renders from the prebuilt index before the engine is ready.

Design screen 02 Entity file (docs/design/README.md, acceptance): „the head renders from
the entity index before the engine is ready”. runDosar() asks the suggestions index for
an exact match (CUI or folded name) and draws the H2 and CUI line at once; the queried
head replaces it later. Source-text assertions, like `test_site_numbers`.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")


def test_head_is_drawn_from_the_index_before_the_first_query() -> None:
    source = INDEX.read_text(encoding="utf-8")
    start = source.index("async function runDosar() {")
    head = source.index("sugestii.lookup(term)", start)
    first_query = source.index("await disambiguate(term)", start)
    assert head < first_query, "the index head must come before the first query"
    assert "cap.hidden = false" in source[head : head + 700]


def test_the_suggestions_module_exposes_an_exact_lookup() -> None:
    source = INDEX.read_text(encoding="utf-8")
    module = source[source.index("const sugestii = (() => {") :]
    module = module[: module.index("})();")]
    assert "lookup" in module[module.rindex("return {") :], "lookup is not exported"
    assert "index.find(" in module, "an exact match, not the eight-row suggestion filter"
