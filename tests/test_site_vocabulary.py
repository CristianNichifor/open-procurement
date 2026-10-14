"""OP-16: the UI never shows the internal terms banned by docs/ux-guidelines.md §3."""
import re
from pathlib import Path

SITE = Path("site")
BANNED = ("DuckDB", "Parquet", "bundle", "R2", "OCDS", "bucket", "release", "n minim")
# Pages whose job is to name the plumbing: the privacy notice (third-party requests) and
# the methodology (the OCDS mapping) may use the words.
PLUMBING_PAGES = {"privacy.html", "metodologie.html"}
# Ceilings for strings still on the front page, kept until site/index.html is free to
# edit (other open pull requests touch it). Lower an entry once its string is gone.
KNOWN = {
    "index.html": {
        "Parquet": 2,  # "fișierele Parquet" in the data-coverage section (D-8)
        "n minim": 1,  # the control label, replaced by "cel puțin … achiziții" (D-7)
    },
}


def _visible(name: str) -> str:
    """Markup text plus the string literals of the inline script, minus styles."""
    html = (SITE / name).read_text(encoding="utf-8")
    body = html.split("<body", 1)[1]
    flags = re.DOTALL | re.IGNORECASE
    scripts = re.findall(r"<script\b.*?</script[^>]*>", body, flags=flags)
    body = re.sub(r"<script\b.*?</script[^>]*>|<style\b.*?</style[^>]*>", "", body, flags=flags)
    text = re.sub(r"<[^>]+>", " ", body)
    literals = re.findall(r"""['"`]([^'"`\n]{4,})['"`]""", "\n".join(scripts))
    romanian = [s for s in literals if re.search(r"[ăâîșț]| de | și ", s)]
    return text + "\n" + "\n".join(romanian)


def _count(term: str, text: str) -> int:
    return len(re.findall(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", text))


def test_the_ui_avoids_internal_terms() -> None:
    pages = [p.name for p in SITE.glob("*.html")]
    assert "index.html" in pages
    for name in pages:
        if name in PLUMBING_PAGES:
            continue
        text = _visible(name)
        for term in BANNED:
            allowed = KNOWN.get(name, {}).get(term, 0)
            found = _count(term, text)
            assert found <= allowed, f"{name} shows {term!r} {found}x (allowed {allowed})"

