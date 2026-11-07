"""Generated compatibility matrix (M33 33.1).

The matrix is output, not aspiration: every row carries one of the four PRD 19
labels and a concrete evidence citation. ``render()`` is the source of truth;
``COMPATIBILITY.md`` is generated from it and checked in CI so it cannot drift.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

LABELS = frozenset({"field-tested", "conformance-tested", "documented", "not-supported"})

_OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "release" / "v0.1.0" / "COMPATIBILITY.md"


@dataclass(frozen=True, slots=True)
class CompatRow:
    layer: str
    surface: str
    label: str
    evidence: str
    note: str = ""


#: Runtime rows. Keep every evidence string concrete; no row may be unlabeled.
ROWS: tuple[CompatRow, ...] = (
    CompatRow(
        "Coding agent",
        "Claude Code",
        "documented",
        "docs/adapters/harness-recipes.md; docs/release/v0.1.0/evidence/harness/FT-T1-CLAUDE/",
        "11/11 LLM pairs captured; end-to-end s15 field run removed, so not field-tested",
    ),
    CompatRow(
        "Coding agent",
        "Codex CLI",
        "documented",
        "docs/adapters/harness-recipes.md; docs/release/v0.1.0/evidence/harness/FT-T1-CODEX/",
        "11/11 LLM pairs captured; end-to-end s15 field run removed, so not field-tested",
    ),
    CompatRow(
        "Producer",
        "agentpolicy reference adapter",
        "conformance-tested",
        "tests/adapters/test_agentpolicy.py; docs/adapters/producer-guide.md",
        "Wave-0 demo (#116) will add field evidence; label upgrades only after it runs",
    ),
    CompatRow(
        "Coding agent",
        "GitHub Copilot agent mode",
        "documented",
        "docs/adapters/producer-guide.md",
        "Reached through lower-layer agentgate/agentseatbelt; no dedicated adapter",
    ),
    CompatRow(
        "Coding agent",
        "Cursor",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "No headless evidence-capturing hook on the v0.1.0 field box",
    ),
    CompatRow(
        "Coding agent",
        "Gemini CLI",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Approval modes exist but the field surface is unstable; v0.1.x target",
    ),
    CompatRow(
        "Framework",
        "LangGraph",
        "conformance-tested",
        "tests/adapters/test_langgraph.py; docs/adapters/langgraph/README.md",
        "Reference interrupt adapter; crash-resume conformance fixture",
    ),
    CompatRow(
        "Framework",
        "OpenAI Agents SDK",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Pattern is identical to the reference adapter; adapter planned for v0.1.x",
    ),
    CompatRow(
        "Framework",
        "CrewAI",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Planned v0.1.x; no shipped adapter",
    ),
    CompatRow(
        "Framework",
        "AutoGen / AG2",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Planned v0.1.x; no shipped adapter",
    ),
    CompatRow(
        "Framework",
        "PydanticAI",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Target v0.2.0; no shipped adapter",
    ),
    CompatRow(
        "Framework",
        "Temporal",
        "documented",
        "docs/adapters/temporal.md",
        "Signal/query recipe; not field-tested",
    ),
    CompatRow(
        "Protocol",
        "Generic MCP ask-gating tool",
        "documented",
        "docs/adapters/mcp.md",
        "Tool-wrapping recipe; no elicitation bridge",
    ),
    CompatRow(
        "Protocol",
        "MCP elicitation bridge",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Design only; implementation target v0.2.0",
    ),
    CompatRow(
        "CI/CD",
        "GitHub Actions",
        "documented",
        "docs/adapters/ci-recipes.md",
        "Gate-step recipe; no live field run",
    ),
    CompatRow(
        "CI/CD",
        "GitLab CI",
        "documented",
        "docs/adapters/ci-recipes.md",
        "Gate-step recipe; no live field run",
    ),
    CompatRow(
        "CI/CD",
        "Jenkins",
        "documented",
        "docs/adapters/ci-recipes.md",
        "Gate-step recipe; no live field run",
    ),
    CompatRow(
        "CI/CD",
        "Argo Workflows",
        "documented",
        "docs/adapters/ci-recipes.md",
        "Suspend/resume recipe; no live field run",
    ),
    CompatRow(
        "Producer",
        "Generic CLI/HTTP producer",
        "conformance-tested",
        "tests/ask/test_api.py; tests/fixtures/conformance/",
        "ask/1.0 and resolve/1.0 contract fixtures",
    ),
    CompatRow(
        "Channel",
        "Terminal, desktop, webhook, CI",
        "conformance-tested",
        "tests/channels/; tests/parity/",
        "M32 LIVE cases exercised the surfaces; not a harness field-test label",
    ),
    CompatRow(
        "Chat",
        "Matrix, Slack, Teams",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Matrix target v0.1.x; Slack/Teams optional community adapters",
    ),
    CompatRow(
        "Enterprise",
        "Copilot Studio, Agentforce, Bedrock agents",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Reached via standards only; target v2.x",
    ),
    CompatRow(
        "Protocol",
        "A2A / CHAP-class",
        "not-supported",
        "docs/prd/19-harness-compatibility.md",
        "Watchlist; target v0.3.0+",
    ),
)


def render() -> str:
    lines = [
        "# agentinbox v0.1.0 — Compatibility Matrix",
        "",
        "<!-- GENERATED by agentinbox.compatmatrix — do not hand-edit.",
        "     Check with: python -m agentinbox.compatmatrix --check -->",
        "",
        "Every row carries exactly one PRD 19 label: **field-tested**, "
        "**conformance-tested**, **documented**, or **not-supported**. A label "
        "without its evidence is not allowed.",
        "",
        "**v0.1.0 honesty note:** the M32 s15 harness suite was removed; Claude "
        "Code and Codex CLI have captured LLM pairs but **no end-to-end field "
        "run**. They are therefore **documented**, not field-tested. The study "
        "was not run, so no study claim is made.",
        "",
        "| Layer | Surface | v0.1.0 label | Evidence | Note |",
        "|---|---|---|---|---|",
    ]
    for row in ROWS:
        lines.append(
            f"| {row.layer} | {row.surface} | **{row.label}** | {row.evidence} | {row.note} |"
        )
    lines.extend(
        [
            "",
            "## Label meanings",
            "",
            "- **field-tested** — a run journal with harness/tool version, date, "
            "OS/user, transcript, gate outcome, and a field-test verdict.",
            "- **conformance-tested** — a green CI fixture/conformance suite names "
            "the tested surface.",
            "- **documented** — a recipe or reference exists; no live field run.",
            "- **not-supported** — a stated reason; never an implied absence.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentinbox-compatmatrix",
        description="check or write the generated v0.1.0 compatibility matrix",
    )
    parser.add_argument("--write", action="store_true", help="write the generated file")
    parser.add_argument("--check", action="store_true", help="fail if the file differs")
    args = parser.parse_args(argv)
    expected = render()
    if args.write:
        _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT.write_text(expected, encoding="utf-8")
        print(f"wrote {_OUTPUT}")
        return 0
    if not _OUTPUT.is_file():
        print(f"compatibility matrix missing: {_OUTPUT}", file=sys.stderr)
        return 1
    actual = _OUTPUT.read_text(encoding="utf-8")
    if actual != expected:
        print("compatibility matrix is stale; run --write", file=sys.stderr)
        return 1
    print(f"compatibility matrix ok: {len(ROWS)} rows")
    return 0


__all__ = ["LABELS", "ROWS", "CompatRow", "main", "render"]


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
