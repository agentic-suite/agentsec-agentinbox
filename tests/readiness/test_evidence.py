"""Evidence sufficiency + freshness labels differ per class (M26 item 26.4, R81/R82, SC-70)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.readiness import evaluate
from tests.readiness.conftest import NOW, config, good_body


def test_the_same_weak_evidence_scores_differently_per_class() -> None:
    body = good_body()
    body["context"]["evidence"] = {}
    strict = evaluate(body, config=config(), producer_authenticated=True, now=NOW)
    relaxed = evaluate(
        {**body, "class": "readonly"}, config=config(), producer_authenticated=True, now=NOW
    )

    assert strict.dimensions["evidence_presence"] == 0.0
    assert strict.evidence_label == "absent"
    assert "evidence_presence" in strict.missing
    assert relaxed.dimensions["evidence_presence"] == 1.0
    assert relaxed.evidence_label == "strong"


def test_partial_evidence_names_the_missing_dimension() -> None:
    body = good_body()
    body["context"]["evidence"] = {
        "diff": {"at": "2026-11-07T11:55:00.000000Z"}
    }
    readiness = evaluate(body, config=config(), producer_authenticated=True, now=NOW)

    assert readiness.evidence_label == "partial"
    assert any("attach: logs" in str(item["fix"]) for item in readiness.repairs)


def test_freshness_is_stale_when_old_and_unknown_when_absent() -> None:
    stale = good_body()
    old = (NOW - timedelta(days=2)).isoformat(timespec="microseconds").replace("+00:00", "Z")
    stale["context"]["evidence"] = {"diff": {"at": old}, "logs": {"at": old}}
    readiness = evaluate(stale, config=config(), producer_authenticated=True, now=NOW)
    assert readiness.freshness == "stale"

    unknown = good_body()
    unknown["context"]["evidence"] = {"diff": {}, "logs": {}}
    readiness = evaluate(unknown, config=config(), producer_authenticated=True, now=NOW)
    assert readiness.freshness == "unknown freshness"


def test_evidence_lists_and_weak_labels_are_supported() -> None:
    from agentinbox.readiness import evaluate as score

    body = good_body()
    body["context"]["evidence"] = [{"kind": "diff"}]
    readiness = score(
        body,
        config=config(required_evidence=("diff", "logs", "trace")),
        producer_authenticated=True,
        now=NOW,
    )
    assert readiness.evidence_label == "weak"
    assert any("attach: logs, trace" in str(item["fix"]) for item in readiness.repairs)

    body["context"]["evidence"] = "not-evidence"
    readiness = score(body, config=config(), producer_authenticated=True, now=NOW)
    assert readiness.evidence_label == "absent"


def test_mixed_and_invalid_freshness_are_explicit() -> None:
    from agentinbox.readiness import evaluate as score

    mixed = good_body()
    new = "2026-11-07T11:59:00.000000Z"
    old = "2026-11-01T00:00:00.000000Z"
    mixed["context"]["evidence"] = {"diff": {"at": new}, "logs": {"at": old}}
    assert score(mixed, config=config(), producer_authenticated=True, now=NOW).freshness == "mixed"

    invalid = good_body()
    invalid["context"]["evidence"] = {"diff": {"at": "yesterday"}, "logs": {"fetched_at": new}}
    assert (
        score(invalid, config=config(), producer_authenticated=True, now=NOW).freshness
        == "unknown freshness"
    )
