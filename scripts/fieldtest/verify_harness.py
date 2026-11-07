#!/usr/bin/env python3
"""Verify the verifier: the deep-validation gates must reject bad input.

If these gates cannot fail, a green field-test run is meaningless. This checks:

  1. an ungrounded PASS is rejected,
  2. a PASS with a failed assertion is rejected,
  3. a PASS whose counts disagree with assertions.ndjson is rejected,
  4. a grounded, all-green PASS is accepted,
  5. a BLOCKED case without limitation/gate is rejected,
  6. the leak gate catches a planted AWS key.

Usage:
    python3 verify_harness.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _verdict(case_dir: Path, verdict: dict[str, object], rows: list[dict[str, object]]) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "verdict.json").write_text(json.dumps(verdict), encoding="utf-8")
    (case_dir / "assertions.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _run(script: str, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HERE / script), str(root)],
        capture_output=True,
        text=True,
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ft-verify-") as temp:
        root = Path(temp)
        case = root / "suite" / "cases" / "FT-FAKE"

        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": False,
                "assertions_total": 1,
                "assertions_grounded": 0,
            },
            [{"name": "a", "ok": True, "grounded": False}],
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted an ungrounded PASS")

        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": True,
                "assertions_total": 1,
                "assertions_grounded": 1,
            },
            [{"name": "a", "ok": False, "grounded": True}],
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted a PASS with a failed assertion")

        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": True,
                "assertions_total": 2,
                "assertions_grounded": 2,
            },
            [{"name": "a", "ok": True, "grounded": True}],
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted a count mismatch")

        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": True,
                "assertions_total": 1,
                "assertions_grounded": 1,
            },
            [{"name": "a", "ok": True, "grounded": True}],
        )
        if _run("check_grounding.py", root).returncode != 0:
            failures.append("check_grounding rejected a grounded, all-green PASS")

        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": True,
                "assertions_total": 1,
                "assertions_grounded": 1,
                "llm_required": True,
                "llm_captured": False,
            },
            [{"name": "a", "ok": True, "grounded": True}],
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted an LLM PASS with no capture")

        # 7) LLM-required PASS with a balanced 2xx capture is accepted.
        llm = case / "artifacts" / "llm"
        llm.mkdir(parents=True)
        (llm / "call-0001-request.json").write_text(
            json.dumps({"url": "/v1/messages", "body": {"model": "test"}}), encoding="utf-8"
        )
        (llm / "call-0001-response.json").write_text(
            json.dumps({"status_code": 200, "body": {"ok": True}}), encoding="utf-8"
        )
        _verdict(
            case,
            {
                "id": "FT-FAKE",
                "status": "pass",
                "grounded": True,
                "assertions_total": 1,
                "assertions_grounded": 1,
                "llm_required": True,
                "llm_captured": True,
            },
            [{"name": "a", "ok": True, "grounded": True}],
        )
        if _run("check_grounding.py", root).returncode != 0:
            failures.append("check_grounding rejected a balanced 2xx LLM capture")

        # 8) Unbalanced capture is rejected.
        (llm / "call-0002-request.json").write_text("{}", encoding="utf-8")
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted an unbalanced LLM capture")
        (llm / "call-0002-request.json").unlink()

        # 9) A secret in the capture is rejected.
        (llm / "call-0001-request.json").write_text(
            json.dumps({"body": {"token": "AKIA" + "A" * 16}}), encoding="utf-8"
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted a secret in LLM capture")
        (llm / "call-0001-request.json").write_text(
            json.dumps({"url": "/v1/messages", "body": {"model": "test"}}), encoding="utf-8"
        )

        # 10) A non-2xx response is rejected.
        (llm / "call-0001-response.json").write_text(
            json.dumps({"status_code": 500, "body": {"error": "no"}}), encoding="utf-8"
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted a non-2xx LLM response")
        (llm / "call-0001-response.json").write_text(
            json.dumps({"status_code": 200, "body": {"ok": True}}), encoding="utf-8"
        )

        _verdict(
            case,
            {"id": "FT-FAKE", "status": "blocked", "class": "P/F|B"},
            [{"name": "blocked", "ok": True, "blocked": True}],
        )
        if _run("check_grounding.py", root).returncode == 0:
            failures.append("check_grounding accepted BLOCKED without limitation/gate")

        (root / "leak.txt").write_text("token=AKIA" + "A" * 16 + "\n", encoding="utf-8")
        if _run("scan_results.py", root).returncode == 0:
            failures.append("scan_results missed a planted AWS key")

    if failures:
        for failure in failures:
            print(f"verify-harness: FAIL — {failure}", file=sys.stderr)
        return 1
    print("verify-harness: OK (grounding, assertion, blocked and leak gates all reject bad input)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
