"""Six-dimension readiness scorer (M26 item 26.1, R78)."""

from __future__ import annotations

from agentinbox.readiness import DIMENSIONS, band_for, evaluate
from tests.readiness.conftest import NOW, config, good_body, weak_body


def test_a_complete_signed_ask_scores_green() -> None:
    readiness = evaluate(
        good_body(), config=config(), producer_authenticated=True, now=NOW
    )

    assert readiness.score == 1.0
    assert readiness.band == "green"
    assert set(readiness.dimensions) == set(DIMENSIONS)
    assert readiness.contradictions == ()
    assert readiness.missing == ()
    assert readiness.repairs == ()


def test_an_unsigned_ask_loses_trust_provenance_only() -> None:
    readiness = evaluate(
        good_body(), config=config(), producer_authenticated=False, now=NOW
    )

    assert readiness.dimensions["trust_provenance"] == 0.5
    assert readiness.band == "green"  # 5/6 dimensions are perfect
    assert "trust_provenance" in readiness.missing
    assert any(item["name"] == "trust_provenance" for item in readiness.repairs)


def test_a_weak_ask_names_each_failing_dimension_and_fix() -> None:
    readiness = evaluate(
        weak_body(), config=config(), producer_authenticated=True, now=NOW
    )

    assert readiness.band == "yellow"
    assert {"target_specificity", "reversibility_clarity", "evidence_presence"} <= set(
        readiness.missing
    )
    fixes = {str(item["name"]): str(item["fix"]) for item in readiness.repairs}
    assert "name the exact resource" in fixes["target_specificity"]
    assert "state reversibility" in fixes["reversibility_clarity"]
    assert "attach: diff, logs" in fixes["evidence_presence"]


def test_bands_are_deterministic() -> None:
    assert band_for(0.8) == "green"
    assert band_for(0.79) == "yellow"
    assert band_for(0.5) == "yellow"
    assert band_for(0.49) == "red"


def test_malformed_shapes_are_treated_as_empty_not_crashing() -> None:
    from agentinbox.readiness import evaluate as score

    body = good_body()
    body["context"] = "not-a-mapping"
    body["policy_ref"] = "not-a-mapping"
    readiness = score(body, config=config(), producer_authenticated=True, now=NOW)

    assert readiness.dimensions["completeness"] < 1.0
    assert readiness.dimensions["target_specificity"] == 0.0


def test_completeness_lists_the_fields_to_fill() -> None:
    body = good_body()
    body["policy_ref"] = {"rule_id": "", "policy_version": "v1", "clause": ""}
    body["requested_by"] = ""
    readiness = evaluate(body, config=config(), producer_authenticated=True, now=NOW)

    fixes = " ".join(str(item["fix"]) for item in readiness.repairs)
    assert "fill policy_ref.rule_id" in fixes
    assert "fill requested_by" in fixes
