"""A natural-person search gets the rule, never a file.

Design screen 02 Entity file (docs/design/README.md, acceptance): „a natural-person
search shows the §3 message and never a file”. The published data excludes natural
persons (gdpr.py, the privacy page), so a CNP-shaped code or a sole-trader marker is
answered in the status line before any query runs. Source-text assertions, like
`test_site_numbers`.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")


def test_natural_persons_are_answered_before_any_query() -> None:
    source = INDEX.read_text(encoding="utf-8")
    start = source.index("async function runDosar() {")
    guard = source.index("Persoanele fizice nu au fișă aici", start)
    first_query = source.index("await disambiguate(term)", start)
    assert guard < first_query, "the message must come before the first query"
    head = source[start:guard]
    assert "[0-9]{13}" in head, "a CNP-shaped code is thirteen digits"
    assert "persoan" in head and "cabinet individual" in head and "PFA" in head
    assert "return;" in source[guard : guard + 200], "and never a file"
