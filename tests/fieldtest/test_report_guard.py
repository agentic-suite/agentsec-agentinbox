"""Guard: automation must never clobber a hand-maintained field-test report.

The canonical ``docs/field-test/<version>/FIELD_TEST_REPORT.md`` is hand-edited;
a lossy automated rewrite destroyed notes in this project's history. These tests
lock the guard in: the marker is present, the helper refuses, and a simulated
writer cannot overwrite the canonical file.
"""

from __future__ import annotations

from pathlib import Path

from agentinbox.report_guard import (
    HAND_MAINTAINED_MARKER,
    is_hand_maintained,
    refuse_overwrite,
)

REPO = Path(__file__).resolve().parents[2]
CANONICAL = REPO / "docs" / "field-test" / "v0.1.0" / "FIELD_TEST_REPORT.md"


def test_the_canonical_report_carries_the_hand_maintained_marker() -> None:
    assert CANONICAL.is_file()
    assert HAND_MAINTAINED_MARKER in CANONICAL.read_text(encoding="utf-8")


def test_marker_blocks_every_overwrite() -> None:
    assert is_hand_maintained(CANONICAL)
    assert refuse_overwrite(CANONICAL) is True
    # No force exception: the canonical report is never written by automation.
    assert refuse_overwrite(CANONICAL) is True


def test_a_simulated_writer_refuses_and_preserves_the_report(tmp_path: Path) -> None:
    original = CANONICAL.read_bytes()

    class Writer:
        def write(self, path: Path) -> None:
            if refuse_overwrite(path):
                raise RuntimeError("refusing to overwrite a hand-maintained report")
            path.write_text("generated", encoding="utf-8")

    try:
        Writer().write(CANONICAL)
    except RuntimeError:
        pass
    else:  # pragma: no cover - the guard must refuse
        raise AssertionError("writer was allowed to overwrite the canonical report")

    assert CANONICAL.read_bytes() == original


def test_missing_and_plain_files_are_writable(tmp_path: Path) -> None:
    assert not is_hand_maintained(tmp_path / "missing.md")
    plain = tmp_path / "FIELD_TEST_REPORT.generated.md"
    plain.write_text("# generated draft\n", encoding="utf-8")
    assert not refuse_overwrite(plain)
