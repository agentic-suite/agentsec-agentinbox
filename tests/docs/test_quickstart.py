"""Replay the quickstart exactly and prove first approval < 5 minutes (M23 item 23.1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_quickstart_step_test_records_an_approval_under_five_minutes() -> None:
    script = ROOT / "scripts" / "quickstart_step_test.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "quickstart ok" in result.stdout
