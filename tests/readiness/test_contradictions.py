"""Contradiction corpus: 12 labelled cases, zero silent delivery (M26 item 26.3, R80)."""

from __future__ import annotations

import pytest

from agentinbox.readiness import detect_contradictions
from tests.readiness.conftest import good_body


def _detect(body: dict, *, authenticated: bool = True) -> tuple[str, ...]:
    context = body.get("context") or {}
    return detect_contradictions(
        body,
        context=context,
        arguments=body.get("arguments") or {},
        producer_authenticated=authenticated,
    )


CASES = [
    # none
    ("clean", good_body(), True, set()),
    ("clean-unsigned", good_body(), False, set()),
    ("clean-staging-prod-ok", good_body(environment="production"), True, set()),
    ("clean-low-criticality-reversible", None, True, set()),
    # staging vs prod
    ("staging-resource-prod", good_body(environment="staging"), True, {"staging_vs_prod"}),
    ("dev-resource-production", None, True, {"staging_vs_prod"}),
    # read-only vs destructive
    ("readonly-drop", None, True, {"readonly_vs_destructive"}),
    ("dry-run-delete", None, True, {"readonly_vs_destructive"}),
    # low criticality vs irreversible
    ("low-vs-irreversible", None, True, {"low_criticality_vs_irreversible"}),
    ("info-vs-irreversible", None, True, {"low_criticality_vs_irreversible"}),
    # unverified trust claim
    ("unsigned-claims-verified", None, False, {"unverified_trust_claim"}),
    ("signed-claims-verified", None, True, set()),
]


def build(name: str, body: dict | None) -> dict:
    if body is not None:
        return body
    if name == "clean-low-criticality-reversible":
        body = good_body(criticality="low")
        body["class"] = "readonly"
        body["context"]["blast_radius"]["reversibility"] = "reversible"
        return body
    if name == "dev-resource-production":
        body = good_body(environment="dev")
        body["context"]["blast_radius"]["resource"] = "db:production/app"
        return body
    if name in {"readonly-drop", "dry-run-delete"}:
        body = good_body()
        body["context"]["read_only"] = True
        body["arguments"] = {"command": "psql -c 'DROP TABLE customers'"}
        return body
    if name in {"low-vs-irreversible", "info-vs-irreversible"}:
        return good_body(criticality="low" if name.startswith("low") else "info")
    if name in {"unsigned-claims-verified", "signed-claims-verified"}:
        body = good_body()
        body["context"] = {**body["context"], "trust": "verified"}
        return body
    return good_body()


@pytest.mark.parametrize(("name", "body", "authenticated", "expected"), CASES)
def test_contradiction_corpus_labels_every_case(
    name: str, body: dict | None, authenticated: bool, expected: set[str]
) -> None:
    found = set(_detect(build(name, body), authenticated=authenticated))

    assert found == expected, name
