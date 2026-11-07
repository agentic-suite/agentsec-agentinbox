"""Claims lint (M33 33.2): enforce the PRD 20 §G vocabulary on public docs.

The linter is deliberately small and auditable. It does **not** try to judge
whether a claim is true; it catches the forbidden/restricted phrasings that the
claims register already decided are out of bounds, and it leaves explicit
"forbidden / not claimed / restricted" statements alone so the policy and gap
docs can quote them.

Public targets are README.md and the reference/adapters/compliance/release doc
sets. PRDs, WBS, design, and field-test evidence are not public marketing docs
and may cite the vocabulary normatively.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ClaimFinding:
    path: str
    line: int
    rule: str


#: (rule name, pattern). Case-insensitive, applied line by line.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ENTERPRISE_READY", re.compile(r"\benterprise[- ]ready\b", re.I)),
    (
        "PREVENTS_PROMPT_INJECTION",
        re.compile(r"\bprevents?\s+prompt\s+injection\b", re.I),
    ),
    ("BLOCKS_ALL_INJECTION", re.compile(r"\bblocks?\s+all\s+injection\b", re.I)),
    ("CHATBOT_DECISION", re.compile(r"\bchat[- ]?bot\s+decision\b", re.I)),
    ("ML_ASSISTED_APPROVAL", re.compile(r"\bml[- ]assisted\s+approval\b", re.I)),
    ("SOC2_CERTIFIED", re.compile(r"\bsoc\s*2\s+(certified|compliant)\b", re.I)),
    (
        "ISO_CERTIFIED",
        re.compile(r"\biso(?:/iec)?\s*(27001|42001)\s+(certified|compliant)\b", re.I),
    ),
    (
        "EU_AI_ACT_CONFORMANCE",
        re.compile(r"\beu\s+ai\s+act\s+(compliant|conformant|certified)\b", re.I),
    ),
    ("UNFORGEABLE_APPROVALS", re.compile(r"\bunforgeable\s+approvals?\b", re.I)),
)

#: Lines that explicitly reject, forbid, restrict, or negate a claim are policy
#: text, not a claim. This is intentionally conservative: a public doc that says
#: "we do not claim X" must not fail the linter for naming X.
_ALLOWED_CONTEXT = (
    "forbidden",
    "restricted",
    "not ",
    "no ",
    "never",
    "cannot",
    "can't",
    "don't",
    "do not",
    "does not",
    "without",
    "refuse",
)

_DOC_SUFFIXES = (".md", ".rst", ".txt")
_ROOT = Path(__file__).resolve().parents[1]


def _is_code_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def lint_text(text: str, *, path: str) -> list[ClaimFinding]:
    """Return claim findings for one text body; code fences/examples are skipped."""
    findings: list[ClaimFinding] = []
    in_fence = False
    lines = text.splitlines()
    for index, line in enumerate(lines):
        number = index + 1
        if _is_code_fence(line):
            in_fence = not in_fence
            continue
        if in_fence or "claims-lint: ignore" in line.lower():
            continue
        # A policy paragraph may wrap the forbidden word onto its own line:
        # "Prevents prompt injection", "enterprise-ready", ... (forbidden below).
        # Use the neighbouring lines as context so policy/gap prose is not a claim.
        context = " ".join(lines[max(0, index - 1) : index + 2]).lower()
        if any(token in context for token in _ALLOWED_CONTEXT):
            continue
        for rule, pattern in _RULES:
            if not pattern.search(line):
                continue
            if rule == "UNFORGEABLE_APPROVALS" and "sc-22" in context:
                continue
            findings.append(ClaimFinding(path=path, line=number, rule=rule))
    return findings


def _iter_docs(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in _DOC_SUFFIXES:
                    yield candidate


def lint_paths(paths: Iterable[Path]) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    for path in _iter_docs(paths):
        try:
            text = path.read_text(encoding="utf-8")
            display = str(path.relative_to(_ROOT)) if path.is_relative_to(_ROOT) else str(path)
        except (OSError, ValueError):
            continue
        findings.extend(lint_text(text, path=display))
    return findings


def default_targets(root: Path | None = None) -> list[Path]:
    base = root or _ROOT
    candidates = [base / "README.md"]
    candidates.extend(
        base / part
        for part in ("docs/reference", "docs/adapters", "docs/compliance", "docs/release")
    )
    return [path for path in candidates if path.exists()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentinbox-claimslint",
        description="check public docs against the PRD 20 §G claims vocabulary",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="files/directories to lint (default: README + public docs)",
    )
    args = parser.parse_args(argv)
    targets = [Path(item) for item in args.paths] if args.paths else default_targets()
    findings = lint_paths(targets)
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.rule}", file=sys.stderr)
    print(f"claims lint: {len(findings)} finding(s)")
    return 0 if not findings else 1


__all__ = [
    "ClaimFinding",
    "default_targets",
    "lint_paths",
    "lint_text",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
