"""M33 33.1 — the compatibility matrix is generated and honest.

Every row carries one of the four PRD 19 labels and evidence. The harness rows
must not claim `field-tested`: the s15 suite was removed and only LLM captures
exist.
"""

from __future__ import annotations

from pathlib import Path

from agentinbox.compatmatrix import LABELS, ROWS, main, render

REPO = Path(__file__).resolve().parents[2]
MATRIX = REPO / "docs" / "release" / "v0.1.0" / "COMPATIBILITY.md"


def test_every_row_has_a_valid_label_and_evidence() -> None:
    assert ROWS
    for row in ROWS:
        assert row.label in LABELS, row
        assert row.evidence.strip(), row
        assert row.layer.strip(), row


def test_harness_rows_are_documented_not_field_tested() -> None:
    harness = {row.surface: row for row in ROWS if row.surface in {"Claude Code", "Codex CLI"}}
    assert harness["Claude Code"].label == "documented"
    assert harness["Codex CLI"].label == "documented"
    assert "evidence/harness" in harness["Claude Code"].evidence
    assert "evidence/harness" in harness["Codex CLI"].evidence


def test_generated_matrix_matches_the_committed_file() -> None:
    assert MATRIX.is_file(), f"missing generated matrix: {MATRIX}"
    assert MATRIX.read_text(encoding="utf-8") == render()


def test_check_mode_is_green_on_the_committed_file() -> None:
    assert main(["--check"]) == 0
