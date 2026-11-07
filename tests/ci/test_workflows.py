"""CI quality-gate contract (M0 item 0.5).

There is no local way to execute GitHub Actions, so the workflow files themselves are the
artifact under test: they must run the four milestone gates on every PR, on the supported
Python versions, with read-only permissions and no ``pull_request_target``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


@pytest.fixture(scope="module")
def ci() -> str:
    return (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


def test_ci_workflow_exists() -> None:
    assert (WORKFLOWS / "ci.yml").is_file()


def test_ci_runs_on_pull_request_and_push_to_main(ci: str) -> None:
    assert "pull_request:" in ci
    assert "push:" in ci
    assert "branches: [main]" in ci


def test_ci_uses_read_only_permissions(ci: str) -> None:
    assert "permissions:" in ci
    assert "contents: read" in ci


def test_ci_never_uses_pull_request_target(ci: str) -> None:
    assert "pull_request_target" not in ci


def test_ci_runs_every_gate(ci: str) -> None:
    for gate in ("ruff", "mypy", "pytest", "--cov-fail-under=95"):
        assert gate in ci, f"CI does not run {gate}"


def test_ci_covers_supported_python_versions(ci: str) -> None:
    for version in ('"3.11"', '"3.12"', '"3.13"'):
        assert version in ci, f"CI does not test Python {version}"


def test_ci_installs_the_project_itself(ci: str) -> None:
    assert 'pip install -e ".[dev]"' in ci


def test_dco_workflow_exists_and_checks_signoff() -> None:
    dco = (WORKFLOWS / "dco.yml").read_text(encoding="utf-8")

    assert "Signed-off-by" in dco
    assert "pull_request" in dco


def test_scorecard_workflow_is_present() -> None:
    assert (WORKFLOWS / "scorecard.yml").is_file()


def test_ci_runs_the_release_blocking_security_gates(ci: str) -> None:
    assert "python -m agentinbox.packs" in ci
    assert "python -m agentinbox.scanner --self-test" in ci
    assert "python -m pytest tests/security" in ci
    assert "python -m agentinbox.posture manifest" in ci


def test_ci_runs_claims_lint_and_release_evidence_scan(ci: str) -> None:
    assert "python -m agentinbox.claimslint" in ci
    assert "python -m agentinbox.scanner --path docs/release/v0.1.0" in ci
    assert "python -m agentinbox.scanner --path field-test/v0.1.0/results" in ci
