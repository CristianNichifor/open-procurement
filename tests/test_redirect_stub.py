"""The redirect GitHub Pages now serves in place of the site.

It is HTML and JavaScript, so its own node:test file holds the cases; this runs it with the
rest of the suite, as test_preview_gate.py does for the Pages middleware.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RADACINA = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_redirect_stub():
    result = subprocess.run(
        ["node", "--test", "tests/redirect_stub.test.mjs"],
        cwd=RADACINA,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
