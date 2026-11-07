#!/usr/bin/env python3
"""Deep verification: every PASS must be grounded from disk.

A verdict that says ``pass`` but has no grounded assertion (or no assertions at
all) is an over-claim and is reported as a failure. This is the gate that makes
a green run meaningful; it is run automatically by run-suite.sh / run-all.sh.

Usage:
    python3 check_grounding.py [RESULTS_ROOT] [--strict]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path(
    os.environ.get("FT_RESULTS_ROOT")
    or (REPO_ROOT / "field-test" / os.environ.get("FT_VERSION", "v0.1.0") / "results")
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    strict = "--strict" in args
    args = [arg for arg in args if arg != "--strict"]
    root = Path(args[0]) if args else DEFAULT_ROOT
    if not root.exists():
        print(f"check-grounding: no results at {root}")
        return 0 if not strict else 1

    checked = grounded = overclaimed = 0
    problems: list[str] = []
    for path in sorted(root.glob("*/cases/*/verdict.json")):
        try:
            verdict = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{path}: unreadable verdict ({exc})")
            continue
        checked += 1
        if verdict.get("status") != "pass":
            continue
        total = int(verdict.get("assertions_total", 0) or 0)
        good = int(verdict.get("assertions_grounded", 0) or 0)
        if verdict.get("grounded") is not True or total < 1 or good < 1:
            overclaimed += 1
            problems.append(
                f"{verdict.get('id')}: PASS is not grounded "
                f"(assertions={total}, grounded={good})"
            )
        else:
            grounded += 1

    if problems:
        print(f"check-grounding: {len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(
        f"check-grounding: {checked} verdict(s), {grounded} grounded PASS, "
        f"{overclaimed} over-claimed"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
