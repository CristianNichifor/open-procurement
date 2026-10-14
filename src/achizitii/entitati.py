"""The entity-name index behind the search box's suggestions.

A small JSON file of the buyers and suppliers with the largest totals, so the front page
can suggest names while DuckDB-Wasm is still downloading — the same reason the front door
is JSON (see `publish._panorama`). Suggestions are a shortcut, not the search: anything
not in the index is still found once the engine is up.

Organisations only. A supplier that is a natural person — a sole trader (PFA, II, IF) or
anyone registered under a CNP — is named in the source data, but a list built to be typed
into is a directory of people, and `gdpr.py` keeps people out of what is published.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

FILE = "entitati.json"
PER_KIND = 2500

# The forms under which a natural person trades, written with or without dots.
_SOLE_TRADER = re.compile(
    r"(?i)(?<![\w.])(?:P\.?F\.?A\.?|I\.?I\.?|I\.?F\.?)(?![\w.])"
    r"|persoan[aă]\s+fizic[aă]|cabinet\s+individual|[iî]ntreprindere\s+(?:individual|familial)"
)
# A CNP is 13 digits; a company's fiscal code is at most 10.
_CNP = re.compile(r"^\d{13}$")


def is_natural_person(name: str, cui: str) -> bool:
    return bool(_CNP.match(cui.strip())) or bool(_SOLE_TRADER.search(name))


def _ranked(con: duckdb.DuckDBPyConnection, src: Path, cui: str, name: str) -> list:
    # The newest name, because organisations rename and the reader types today's.
    return con.execute(
        f"""SELECT max_by({name}, an), {cui}, sum(valoare_totala_ron) AS v
            FROM read_parquet(?)
            WHERE {cui} IS NOT NULL AND {cui} <> '' AND {name} IS NOT NULL
            GROUP BY {cui}
            ORDER BY v DESC NULLS LAST, {cui}""",
        [str(src)],
    ).fetchall()


def write_index(data_dir: Path, *, per_kind: int = PER_KIND) -> dict[str, object] | None:
    """Write `entitati.json` into a built bundle and return its manifest entry."""
    data_dir = Path(data_dir)
    sources = {
        "a": (data_dir / "autoritati_an.parquet", "autoritate_cui", "autoritate"),
        "f": (data_dir / "furnizori_an.parquet", "furnizor_cui", "furnizor"),
    }
    if not all(src.is_file() for src, _, _ in sources.values()):
        return None
    con = duckdb.connect()
    picked: dict[str, tuple[str, str, float]] = {}
    for kind, (src, cui, name) in sources.items():
        kept = 0
        for den, code, value in _ranked(con, src, cui, name):
            if kept == per_kind:
                break
            if code in picked:
                continue   # a buyer that also sells stays listed once, as a buyer
            # Only suppliers: a buyer is a public body, and "Colegiul Carol II" is a school.
            if kind == "f" and is_natural_person(den, code):
                continue
            picked[code] = (den.strip(), kind, value or 0.0)
            kept += 1
    con.close()
    rows = sorted(picked.items(), key=lambda kv: (-kv[1][2], kv[0]))
    target = data_dir / FILE
    target.write_text(
        json.dumps({"entitati": [[den, code, kind] for code, (den, kind, _) in rows]},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return {"file": FILE, "bytes": target.stat().st_size, "n": len(rows)}
