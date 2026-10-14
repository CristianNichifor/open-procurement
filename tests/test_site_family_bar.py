"""OP-27: the front page opens with the same family bar as the static pages (D-1, front half).

Source-text assertions, like `test_site_status`: the bar sits before <main>, links back to the
hub, names the tool, and carries the page's one status badge instead of a second copy.
"""

from __future__ import annotations

from pathlib import Path

INDEX = Path("site/index.html")
HUB = "https://projects.cristian-nichifor.com/"


def _bar(source: str) -> str:
    body = source.split("<body>", 1)[1]
    assert body.lstrip().startswith('<header class="family-bar">'), "the family bar is not first"
    return body.split("</header>", 1)[0]


def test_the_family_bar_comes_before_the_page() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert source.index('<header class="family-bar">') < source.index("<main")


def test_it_links_back_to_the_hub_and_names_the_tool() -> None:
    bar = _bar(INDEX.read_text(encoding="utf-8"))
    assert f'<a class="hub" href="{HUB}">← Proiecte civice</a>' in bar
    assert '<span class="home">Achiziții publice din România</span>' in bar


def test_it_carries_the_one_status_badge() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert 'class="status-badge"' in _bar(source)
    assert source.count('class="status-badge"') == 1


def test_its_links_are_touch_targets() -> None:
    source = INDEX.read_text(encoding="utf-8")
    rule = source.split(".family-bar a {", 1)[1].split("}", 1)[0]
    assert "min-height:44px" in rule.replace(" ", "")
