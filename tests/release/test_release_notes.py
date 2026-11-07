"""M33 release notes — every shipped capability, the gaps, and the honest evidence."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTES = REPO / "docs" / "release" / "v0.1.0" / "RELEASE_NOTES.md"


def test_release_notes_exist_and_name_the_release() -> None:
    assert NOTES.is_file()
    text = NOTES.read_text(encoding="utf-8")
    assert "v0.1.0" in text
    assert "agentsec-agentinbox" in text
    assert "pip install agentsec-agentinbox" in text


def test_notes_name_r1_r7_and_e1_e12() -> None:
    text = NOTES.read_text(encoding="utf-8")
    for requirement in [f"R{i}" for i in range(1, 8)]:
        assert requirement in text, f"missing {requirement}"
    for requirement in [f"E{i}" for i in range(1, 13)]:
        assert requirement in text, f"missing {requirement}"


def test_notes_state_the_field_verdict_and_caveats() -> None:
    text = NOTES.read_text(encoding="utf-8")
    assert "47" in text
    assert "6" in text
    assert "study" in text.lower()
    assert "not run" in text.lower() or "no human cohort" in text.lower()
    assert "not field-tested" in text.lower()
    for case in ("FT-SC-20", "FT-SC-21", "FT-SC-24", "FT-SC-26"):
        assert case in text


def test_notes_list_the_gaps_and_links_the_evidence() -> None:
    text = NOTES.read_text(encoding="utf-8")
    for gap in ("SSO", "quorum", "standing approvals", "mobile push"):
        assert gap in text, f"missing gap {gap}"
    for link in ("COMPATIBILITY.md", "SECURITY_AUDIT.md", "demo/transcript.txt"):
        assert link in text, f"missing evidence link {link}"
    assert "Benchmarks" in text
    assert "N-1" in text
