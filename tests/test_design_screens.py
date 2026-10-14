"""OP-14: the design mockups are static, self-contained and use comma-below diacritics."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "docs" / "design" / "screens"
EXPECTED = [
    "01-home.html",
    "02-entity-file.html",
    "03-unit-prices.html",
    "04-signals.html",
    "05-methodology.html",
]
HUB = "https://projects.cristian-nichifor.com/"


def test_screens_and_readme_exist():
    for name in EXPECTED:
        assert (SCREENS / name).is_file(), name
    assert (ROOT / "docs" / "design" / "README.md").is_file()


def test_mockups_are_static_and_self_contained():
    for name in EXPECTED:
        text = (SCREENS / name).read_text(encoding="utf-8")
        assert "<script" not in text.lower(), name
        assert text.replace(HUB, "").count("http") == 0, name
        assert 'lang="ro"' in text, name


def test_mockups_use_comma_below_diacritics():
    for name in EXPECTED:
        text = (SCREENS / name).read_text(encoding="utf-8")
        assert not set("şţŞŢ") & set(text), name


def test_mockups_avoid_internal_terms():
    """docs/ux-guidelines.md §3: no plumbing words in the interface, mockups included."""
    for name in EXPECTED:
        text = (SCREENS / name).read_text(encoding="utf-8").split("<body>", 1)[1]
        for term in ("DuckDB", "Parquet", "bundle", "R2", "OCDS", "bucket", "n minim"):
            assert term not in text, (name, term)
