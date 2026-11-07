#!/usr/bin/env python3
"""Aggregate field-test case verdicts into summary.json / summary.md.

Usage:
    python3 collect-results.py [RUN_DIR] [--expect ID ...] [--allow-blocked]

Reads every ``cases/<ID>/verdict.json`` under the run directory and writes
``summary.json`` / ``summary.md`` beside it. A requested case with no verdict is
a failure (no silent skips).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = Path(
    os.environ.get("FT_RESULTS_ROOT")
    or (REPO_ROOT / "field-test" / os.environ.get("FT_VERSION", "v0.1.0") / "results")
)


def _newest_run_dir() -> Path | None:
    if not RESULTS_ROOT.exists():
        return None
    runs = sorted(p for p in RESULTS_ROOT.iterdir() if p.is_dir())
    return runs[-1] if runs else None


def collect(run_dir: Path, expected: list[str] | None = None) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for verdict_path in sorted(run_dir.glob("cases/*/verdict.json")):
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            verdict = {"id": verdict_path.parent.name, "status": "fail", "error": str(exc)}
        verdict.setdefault("id", verdict_path.parent.name)
        verdict.setdefault("status", "fail")
        cases.append(verdict)

    requested = expected if expected is not None else []
    present = {str(case.get("id")) for case in cases}
    for case_id in requested:
        if case_id not in present:
            cases.append(
                {"id": case_id, "status": "fail", "error": "no verdict recorded"}
            )
    cases.sort(key=lambda case: str(case.get("id")))

    totals = {"pass": 0, "fail": 0, "blocked": 0, "over_claimed": 0}
    for case in cases:
        status = str(case.get("status"))
        if status == "pass":
            if (
                case.get("grounded") is not True
                or int(case.get("assertions_grounded", 0) or 0) < 1
                or int(case.get("assertions_total", 0) or 0) < 1
            ):
                case["status"] = "fail"
                case["error"] = "pass not deeply verified (ungrounded)"
                totals["fail"] += 1
                totals["over_claimed"] += 1
            else:
                totals["pass"] += 1
        elif status == "blocked":
            totals["blocked"] += 1
        else:
            case["status"] = "fail"
            totals["fail"] += 1

    env_path = run_dir / "env.json"
    env: dict[str, object] = {}
    if env_path.exists():
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            env = {}

    return {
        "run_id": run_dir.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "env": env,
        "totals": totals,
        "green": totals["fail"] == 0 and cases != [],
        "cases": cases,
    }


def render_markdown(summary: dict[str, object]) -> str:
    totals = summary["totals"]
    lines = [
        f"# Field Test Run {summary['run_id']}",
        "",
        f"**Totals:** {totals['pass']} pass · {totals['fail']} fail · "
        f"{totals['blocked']} blocked",
        "",
        "| Case | Class | Status | Notes |",
        "|---|---|---|---|",
    ]
    for case in summary["cases"]:
        lines.append(
            f"| {case.get('id')} | {case.get('class', 'P/F')} | "
            f"{case.get('status')} | {case.get('error', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    expected: list[str] | None = None
    allow_blocked = False
    if "--allow-blocked" in args:
        allow_blocked = True
        args.remove("--allow-blocked")
    if "--expect" in args:
        index = args.index("--expect")
        expected = args[index + 1 :]
        args = args[:index]
    run_dir = Path(args[0]) if args else _newest_run_dir()
    if run_dir is None or not run_dir.exists():
        print("collect-results: no run directory found", file=sys.stderr)
        return 1
    summary = collect(run_dir, expected)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (run_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    totals = summary["totals"]
    print(
        f"collect-results: {totals['pass']} pass / {totals['fail']} fail / "
        f"{totals['blocked']} blocked -> {run_dir}/summary.{{json,md}}"
    )
    if totals["fail"]:
        return 1
    if totals["blocked"] and not allow_blocked:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
