"""The Pages middleware that keeps preview builds behind the CN Webify preview gate.

It is JavaScript (functions/_middleware.js runs on Cloudflare Pages), so its own node:test file
holds the cases; this runs it with the rest of the suite.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RADACINA = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_preview_gate_middleware():
    result = subprocess.run(
        ["node", "--test", "tests/preview_gate.test.mjs"],
        cwd=RADACINA,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
