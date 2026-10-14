"""Control labels on the front page are plain Romanian, not jargon.

D-7 in docs/ux-guidelines.md: the `n minim` label named a statistic ("n") to readers who
came for prices. The label now says what the control does in words a reader uses.
"""

from __future__ import annotations

import re
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "site" / "index.html"


def _label(for_id: str) -> str:
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(rf'<label for="{for_id}">(.*?)</label>', html)
    assert m, f"no label for #{for_id}"
    return m.group(1)


def test_min_group_label_is_plain_romanian() -> None:
    label = _label("minn")
    assert label.startswith("Cel puțin"), label
    assert "achiziții" in label, label
    assert "minim" not in label.lower(), "jargon label still present"
    assert "ş" not in label and "ţ" not in label, "cedilla diacritics"
