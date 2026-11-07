#!/usr/bin/env python3
"""Verify the verifier: the grounding gate must catch a shallow pass and the
leak gate must catch a planted secret. A run whose gate cannot fail is not green.

Usage:
    python3 verify_harness.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ft-verify-") as temp:
        root = Path(temp)

        # 1) An ungrounded PASS must be rejected.
        case_dir = root / "suite" / "cases" / "FT-FAKE"
        case_dir.mkdir(parents=True)
        (case_dir / "verdict.json").write_text(
            json.dumps(
                {
                    "id": "FT-FAKE",
                    "status": "pass",
                    "grounded": False,
                    "assertions_total": 1,
                    "assertions_grounded": 0,
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(HERE / "check_grounding.py"), str(root)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            failures.append("check_grounding accepted an ungrounded PASS")

        # 2) A grounded PASS must be accepted.
        (case_dir / "verdict.json").write_text(
            json.dumps(
                {
                    "id": "FT-FAKE",
                    "status": "pass",
                    "grounded": True,
                    "assertions_total": 1,
                    "assertions_grounded": 1,
                }
            ),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(HERE / "check_grounding.py"), str(root)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append("check_grounding rejected a grounded PASS")

        # 3) The leak gate must catch a planted secret.
        (root / "leak.txt").write_text(
            "token=AKIA" + "A" * 16 + "\n", encoding="utf-8"
        )
        proc = subprocess.run(
            [sys.executable, str(HERE / "scan_results.py"), str(root), "--quiet"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            failures.append("scan_results missed a planted AWS key")

    if failures:
        for failure in failures:
            print(f"verify-harness: FAIL — {failure}", file=sys.stderr)
        return 1
    print("verify-harness: OK (grounding + leak gates both reject a bad input)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
