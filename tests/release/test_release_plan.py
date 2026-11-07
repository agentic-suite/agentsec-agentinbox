"""M33 33.D0 — the release plan must exist and stay complete.

``docs/release/v0.1.0/RELEASE_PLAN.md`` is the reviewed-before-release design
for M33. These checks fail if the plan is missing or drops a section that the
release gates depend on. They also pin the M32 honesty caveats: the plan must
not promote the harness or study claims beyond the evidence.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs" / "release" / "v0.1.0" / "RELEASE_PLAN.md"

REQUIRED_SECTIONS = [
    "versioning",
    "artifact",
    "evidence",
    "compatibility",
    "security",
    "tag",
    "release steps",
    "rollback",
    "known issues",
    "definition of done",
]


class TestReleasePlan:
    def test_plan_exists(self) -> None:
        assert PLAN.is_file(), f"missing release plan: {PLAN}"

    def test_plan_has_required_sections(self) -> None:
        text = PLAN.read_text(encoding="utf-8").lower()
        missing = [section for section in REQUIRED_SECTIONS if section not in text]
        assert not missing, f"release plan missing sections: {missing}"

    def test_plan_names_the_artifact_set(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        for token in (
            "CycloneDX",
            "SBOM",
            "SHA256SUMS",
            "SLSA",
            "Sigstore",
            "Scorecard",
        ):
            assert token in text, f"release plan must name the artifact {token!r}"

    def test_plan_keeps_m32_caveats_honest(self) -> None:
        text = PLAN.read_text(encoding="utf-8").lower()
        # No human cohort ran; the study is not proven.
        assert "study" in text
        assert "not run" in text or "by design" in text
        # The harness suite was removed; do not claim field-tested rows.
        assert "harness" in text
        assert "field-tested" in text
        assert "not field-tested" in text or "not field tested" in text

    def test_plan_names_the_release_target(self) -> None:
        text = PLAN.read_text(encoding="utf-8")
        assert "v0.1.0" in text
        assert "agentsec-agentinbox" in text

    def test_tag_is_conditional_on_gates(self) -> None:
        text = PLAN.read_text(encoding="utf-8").lower()
        assert "claims lint" in text
        assert "evidence scanner" in text
        assert "tag" in text
        assert "gate" in text
