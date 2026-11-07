"""M33 33.3 — the release docs index, quickstart, and expansion runbooks are linked."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "docs" / "release" / "v0.1.0" / "README.md"
RUNBOOKS = REPO / "docs" / "release" / "v0.1.0" / "RUNBOOKS.md"
README = REPO / "README.md"


def test_release_index_exists_and_links_the_release_artifacts() -> None:
    assert INDEX.is_file()
    text = INDEX.read_text(encoding="utf-8")
    for target in (
        "RELEASE_PLAN.md",
        "COMPATIBILITY.md",
        "../field-test/v0.1.0/FIELD_TEST_REPORT.md",
        "docs/tutorials/quickstart.md",
        "RUNBOOKS.md",
    ):
        assert target in text, f"release index does not link {target}"


def test_expansion_runbooks_cover_the_new_surfaces() -> None:
    assert RUNBOOKS.is_file()
    text = RUNBOOKS.read_text(encoding="utf-8").lower()
    for surface in (
        "readiness",
        "constrained allow",
        "bundle",
        "handoff",
        "outcome",
        "grant",
        "insight",
    ):
        assert surface in text, f"expansion runbooks missing {surface}"


def test_readme_links_the_release_docs_and_names_m33() -> None:
    text = README.read_text(encoding="utf-8")
    assert "docs/release/v0.1.0/README.md" in text
    assert "M33" in text
    assert "34 milestones" in text
