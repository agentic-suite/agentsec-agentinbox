#!/usr/bin/env python3
"""Run a pytest selection as a *grounded* field-test assertion.

A field-test pass must not rest on "pytest exited 0" when tests were skipped or
none ran. This driver fails (exit 1) if pytest exits non-zero, any test was
skipped, or no test ran.

Usage:
    python3 run_pytest.py tests/... [MORE ...]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    env = os.environ.get("FT_REPO_ROOT")
    if env:
        return Path(env)
    if Path("/work/tests").exists():
        return Path("/work")
    return Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    files: list[str] = []
    extra: list[str] = []
    allow_skip = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--allow-skip":
            allow_skip = True
            i += 1
            continue
        if arg == "-k":
            extra += ["-k", argv[i + 1]]
            i += 2
            continue
        files.append(arg)
        i += 1
    if not files:
        print("run_pytest: no test files given", file=sys.stderr)
        return 2

    root = _repo_root()
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *files,
        "-q",
        "-rs",
        "-p",
        "no:cacheprovider",
        "--no-header",
        *extra,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    out = proc.stdout + proc.stderr
    sys.stdout.write(out)
    if proc.returncode != 0:
        print(f"fail: pytest exited {proc.returncode}", file=sys.stderr)
        return 1

    def _count(kind: str) -> int:
        match = re.search(rf"(\d+) {kind}", out)
        return int(match.group(1)) if match else 0

    passed = _count("passed")
    skipped = _count("skipped")
    failed = _count("failed")
    errors = _count("error")
    if failed or errors:
        print(f"fail: {failed} failed, {errors} error", file=sys.stderr)
        return 1
    if passed == 0:
        print("fail: no tests ran", file=sys.stderr)
        return 1
    if skipped and not allow_skip:
        print(f"fail: {skipped} test(s) skipped (a skip is a failure)", file=sys.stderr)
        return 1
    print(f"ok: {passed} passed, {skipped} skipped, 0 failed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
