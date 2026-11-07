#!/usr/bin/env python3
"""Deep verification: every PASS must be grounded from disk.

This is not "did the command exit 0". For every verdict it re-reads the case's
``assertions.ndjson`` and requires:

  * the case id matches its directory,
  * a PASS has >=1 assertion, every assertion is ``ok``, and >=1 assertion is
    marked ``grounded`` (the counts in verdict.json must match the file),
  * a PASS cannot be marked blocked,
  * a BLOCKED case is P/F|B and carries a limitation + release-gate item,
  * an unknown status is a failure.

A verdict that says ``pass`` but fails any of these is an over-claim and fails
the run. run-suite.sh / run-all.sh invoke this automatically.

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
STATUSES = {"pass", "fail", "blocked"}


def _assertions(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"bad assertion JSON: {exc}") from None
    return rows


def check_verdict(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        verdict = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: unreadable verdict ({exc})"]

    case_id = str(verdict.get("id", ""))
    if case_id != path.parent.name:
        problems.append(f"{path}: id {case_id!r} does not match directory {path.parent.name!r}")

    status = str(verdict.get("status", ""))
    if status not in STATUSES:
        problems.append(f"{case_id}: unknown status {status!r}")
        return problems

    try:
        rows = _assertions(path.parent / "assertions.ndjson")
    except ValueError as exc:
        problems.append(f"{case_id}: {exc}")
        return problems

    if status == "pass":
        if verdict.get("blocked") is True:
            problems.append(f"{case_id}: PASS is marked blocked")
        total = int(verdict.get("assertions_total", 0) or 0)
        grounded = int(verdict.get("assertions_grounded", 0) or 0)
        actual_grounded = sum(1 for row in rows if row.get("grounded") is True)
        if not rows:
            problems.append(f"{case_id}: PASS has no assertions")
        if total != len(rows):
            problems.append(
                f"{case_id}: assertions_total={total} but assertions.ndjson has {len(rows)}"
            )
        if grounded != actual_grounded:
            problems.append(
                f"{case_id}: assertions_grounded={grounded} but ndjson has {actual_grounded}"
            )
        if verdict.get("grounded") is not True or grounded < 1 or actual_grounded < 1:
            problems.append(f"{case_id}: PASS is not grounded")
        if any(row.get("ok") is not True for row in rows):
            problems.append(f"{case_id}: PASS contains a failed assertion")
    elif status == "blocked":
        if verdict.get("class") != "P/F|B":
            problems.append(f"{case_id}: BLOCKED is only valid for P/F|B")
        if not str(verdict.get("limitation") or "").strip():
            problems.append(f"{case_id}: BLOCKED without a limitation")
        if not str(verdict.get("release_gate_item") or "").strip():
            problems.append(f"{case_id}: BLOCKED without a release_gate_item")
        if not any(row.get("blocked") is True for row in rows):
            problems.append(f"{case_id}: BLOCKED without a blocked assertion")
    return problems


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
        checked += 1
        case_problems = check_verdict(path)
        problems.extend(case_problems)
        try:
            verdict = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if verdict.get("status") == "pass":
            if case_problems:
                overclaimed += 1
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
