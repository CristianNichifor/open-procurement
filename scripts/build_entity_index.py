"""Add the search box's suggestion index to an already built bundle.

`achizitii publish` writes it as part of every build. This is for a bundle that predates
it, such as one fetched with scripts/fetch_bundle.sh, without rebuilding the rest.

Usage:
    python scripts/build_entity_index.py [site/data]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from achizitii.entitati import write_index

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str]) -> int:
    data = Path(argv[1]) if len(argv) > 1 else ROOT / "site" / "data"
    meta = write_index(data)
    if meta is None:
        print(f"no autoritati_an/furnizori_an Parquet in {data}", file=sys.stderr)
        return 1
    manifest_path = data / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["entitati"] = meta
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"{meta['file']}: {meta['n']} names, {meta['bytes']} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
