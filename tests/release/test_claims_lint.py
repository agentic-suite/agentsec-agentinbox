"""M33 33.2 — the claims lint must catch over-claims, not prose that rejects them."""

from __future__ import annotations

from pathlib import Path

from agentinbox.claimslint import (
    ClaimFinding,
    default_targets,
    lint_paths,
    lint_text,
)

REPO = Path(__file__).resolve().parents[2]


def test_forbidden_claim_is_rejected() -> None:
    findings = lint_text("agentinbox is enterprise-ready.", path="README.md")
    assert findings
    assert any(finding.rule == "ENTERPRISE_READY" for finding in findings)


def test_negated_or_forbidden_context_is_allowed() -> None:
    text = (
        "Forbidden: enterprise-ready. We do not claim to prevent prompt injection.\n"
        "No ML in any decision path. No chat-bot decision surface.\n"
    )
    assert lint_text(text, path="README.md") == []


def test_code_fences_and_inline_examples_are_not_claims() -> None:
    text = "```\nagentinbox is enterprise-ready\n```\n"
    assert lint_text(text, path="README.md") == []


def test_unforgable_approvals_require_their_sc22_context() -> None:
    assert lint_text("Unforgeable approvals.", path="README.md")
    assert (
        lint_text(
            "Unforgeable approvals are restricted to the SC-22 spoof/replay claim.",
            path="README.md",
        )
        == []
    )


def test_default_public_docs_are_clean() -> None:
    findings = lint_paths(default_targets(REPO))
    assert findings == [], "\n".join(
        f"{finding.path}:{finding.line}: {finding.rule}" for finding in findings
    )


def test_finding_shape_names_the_file_and_line() -> None:
    findings = lint_text("ok\nagentinbox is enterprise-ready.\n", path="README.md")
    assert isinstance(findings[0], ClaimFinding)
    assert findings[0].path == "README.md"
    assert findings[0].line == 2
