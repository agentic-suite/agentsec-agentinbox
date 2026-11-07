#!/usr/bin/env python3
"""Leak gate over the committed field-test results.

Field-test results are persisted in git, so they must contain no unmasked
secrets. Exits non-zero on any hit.

Usage:
    python3 scan_results.py [RESULTS_ROOT] [--quiet]
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path(
    os.environ.get("FT_RESULTS_ROOT")
    or (REPO_ROOT / "field-test" / os.environ.get("FT_VERSION", "v0.1.0") / "results")
)

_PATTERNS = [
    ("openai-key", re.compile(r"sk-[A-Za-z0-9]{16,}")),
    ("bearer", re.compile(r"bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE)),
    ("github-token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("aws-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
_ALLOW = re.compile(r"omlx-test|local-test|\[REDACTED\]")
_SKIP = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz", ".whl"}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    quiet = "--quiet" in args
    args = [arg for arg in args if arg != "--quiet"]
    root = Path(args[0]) if args else DEFAULT_ROOT
    if not root.exists():
        print(f"scan-results: no results at {root} (nothing to scan)")
        return 0

    hits: list[tuple[str, str, int]] = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in _SKIP:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            line = _ALLOW.sub("", line)
            for name, pattern in _PATTERNS:
                if pattern.search(line):
                    hits.append((name, str(path.relative_to(root)), lineno))

    if hits:
        print(f"scan-results: {len(hits)} potential secret(s) in {root}:", file=sys.stderr)
        for name, rel, lineno in hits[:50]:
            print(f"  {name}: {rel}:{lineno}", file=sys.stderr)
        print("\nRefusing to persist unsanitized results.", file=sys.stderr)
        return 1
    if not quiet:
        print(f"scan-results: clean — {scanned} file(s) scanned under {root}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
