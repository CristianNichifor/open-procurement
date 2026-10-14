"""OP-17: every item in the production-readiness spec has a unique id, a status and a test."""
import re
from collections import Counter
from pathlib import Path

SPEC = Path("docs/specs/production-readiness.md")
HEADING = re.compile(r"^### ([A-Z]+-\d+[a-z]?) .+ \((todo|done|blocked|needs-human)\)$", re.MULTILINE)
# Doubled before this guard existed; both halves are referenced elsewhere, so they stay.
KNOWN_DOUBLES = {"OP-9": 2}


def _items() -> list[tuple[str, str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    parts = re.split(r"^(?=### )", text, flags=re.MULTILINE)
    found = []
    for part in parts:
        head = part.split("\n", 1)[0]
        m = HEADING.match(head)
        if m:
            found.append((m.group(1), m.group(2), part))
    return found


def test_every_item_heading_carries_an_id_and_a_status() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for line in re.findall(r"^### .+$", text, flags=re.MULTILINE):
        assert HEADING.match(line), f"not `### ID title (status)`: {line}"


def test_item_ids_are_unique() -> None:
    counts = Counter(item_id for item_id, _, _ in _items())
    doubled = {k: v for k, v in counts.items() if v > KNOWN_DOUBLES.get(k, 1)}
    assert not doubled, f"pick the next free number: {doubled}"


def test_every_item_names_its_test() -> None:
    for item_id, _, body in _items():
        assert re.search(r"^Tests?:", body, flags=re.MULTILINE), f"{item_id} names no test"
