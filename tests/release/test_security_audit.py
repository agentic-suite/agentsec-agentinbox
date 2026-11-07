"""M33 33.6 — the security audit cites every invariant and dispositions M32 findings."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "docs" / "release" / "v0.1.0" / "SECURITY_AUDIT.md"


def test_audit_is_published() -> None:
    assert AUDIT.is_file(), f"missing security audit: {AUDIT}"


def test_every_security_invariant_has_a_fixture_and_field_evidence() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for invariant in ("I-1", "I-2", "I-3", "I-4", "I-5"):
        assert invariant in text, f"missing invariant {invariant}"
    assert "tests/security" in text
    assert "tests/scheduler" in text
    assert "FIELD_TEST_REPORT" in text


def test_m32_findings_are_all_dispositioned() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for token in (
        "Defect #5",
        "fixed",
        "FT-SC-20",
        "FT-SC-21",
        "FT-SC-24",
        "FT-SC-26",
        "study",
        "harness",
    ):
        assert token in text, f"audit missing M32 finding: {token}"
    assert "accepted" in text.lower()
    assert "by design" in text.lower()


def test_audit_keeps_the_non_claims_and_risk_re_grade() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert "Non-claims" in text
    assert "Risk re-grade" in text
    for risk in ("R-R1", "R-R2", "R-R3", "R-R10", "R-R14", "R-R15"):
        assert risk in text, f"missing risk {risk}"
    assert "not run" in text.lower() or "no human cohort" in text.lower()
    assert "not field-tested" in text.lower()
