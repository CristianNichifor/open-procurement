"""docs/ux-guidelines.md maps each rule to the test that enforces it.

A checklist that points at tests which were renamed or deleted gives false comfort, so
every test file it names must exist.
"""

from __future__ import annotations

import re
from pathlib import Path

GUIDE = Path("docs/ux-guidelines.md")


def _checklist() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    return text.split("## 8. Conformance checklist")[1].split("\n## ")[0]


def test_every_test_named_in_the_checklist_exists() -> None:
    names = set(re.findall(r"`((?:tests/[\w/]+/)?[\w.-]+\.(?:py|spec\.js))`", _checklist()))
    assert names
    missing = []
    for name in names:
        candidates = [Path(name), Path("tests") / name, Path("tests/browser") / name]
        if not any(p.is_file() for p in candidates):
            missing.append(name)
    assert not missing, f"docs/ux-guidelines.md names tests that do not exist: {missing}"


def test_the_guideline_uses_comma_below_diacritics_only() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    cedilla = {c for c in "şţŞŢ" if c in text.replace("never ş ţ (cedilla)", "")}
    assert not cedilla
