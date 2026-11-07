"""Non-decisionable rejection + repair contract (M26 items 26.2/26.4, R79/R84, SC-68)."""

from __future__ import annotations

import pytest

from agentinbox.ingest import ingest
from agentinbox.readiness import ReadinessRejection
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.readiness.conftest import NOW, config, good_body, weak_body


def test_a_failing_ask_stores_nothing_and_returns_the_repair_contract() -> None:
    store = MemoryStore()
    try:
        with pytest.raises(ReadinessRejection) as rejected:
            ingest(
                weak_body(),
                store=store,
                config=config(readiness_enforce=True, readiness_min_score=0.9),
                producer=ProducerIdentity.unauthenticated(),
                now=NOW,
            )
        details = rejected.value.details
        assert store.audit_entries() == []
        assert store.list_pending(now=NOW) == []
    finally:
        store.close()

    assert details["reason_code"] == "ask_not_decisionable"
    assert details["retry"] == "after-repair"
    assert details["contradictions"] == []
    names = {item["name"] for item in details["dimensions"]}
    assert {"target_specificity", "reversibility_clarity", "evidence_presence"} <= names


def test_a_repair_loop_turns_a_rejection_into_an_acceptance() -> None:
    store = MemoryStore()
    cfg = config(readiness_enforce=True, readiness_min_score=0.9)
    body = weak_body()
    try:
        with pytest.raises(ReadinessRejection) as rejected:
            ingest(
                body,
                store=store,
                config=cfg,
                producer=ProducerIdentity.unauthenticated(),
                now=NOW,
            )
        for item in rejected.value.details["dimensions"]:
            if item["name"] == "target_specificity":
                body["context"]["blast_radius"]["resource"] = "db:prod/customers"
            if item["name"] == "reversibility_clarity":
                body["context"]["blast_radius"]["reversibility"] = "irreversible"
            if item["name"] == "evidence_presence":
                body["context"]["evidence"] = {
                    "diff": {"at": "2026-11-07T11:55:00.000000Z"},
                    "logs": {"at": "2026-11-07T11:56:00.000000Z"},
                }
        body["context"]["blast_radius"]["affected_estimate"] = "1200 rows"
        result = ingest(
            body,
            store=store,
            config=cfg,
            producer=ProducerIdentity(
                adapter="agentpolicy", authenticated=True, principal="maya@team"
            ),
            now=NOW,
        )
        assert result.created
        assert result.ask.payload["_readiness"]["band"] == "green"
    finally:
        store.close()


def test_a_contradiction_can_be_rejected_by_class_config() -> None:
    store = MemoryStore()
    body = good_body(environment="staging")
    try:
        with pytest.raises(ReadinessRejection) as rejected:
            ingest(
                body,
                store=store,
                config=config(on_contradiction="reject"),
                producer=ProducerIdentity.unauthenticated(),
                now=NOW,
            )
        assert "staging_vs_prod" in rejected.value.details["contradictions"]
        assert store.audit_entries() == []
    finally:
        store.close()


def test_a_contradiction_is_delivered_with_the_flag_by_default() -> None:
    store = MemoryStore()
    try:
        result = ingest(
            good_body(environment="staging"),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )
        readiness = result.ask.payload["_readiness"]
        assert readiness["contradictions"] == ["staging_vs_prod"]
        assert readiness["band"] in {"yellow", "red"}
    finally:
        store.close()


def test_a_producer_cannot_self_assert_readiness() -> None:
    store = MemoryStore()
    body = good_body()
    body["_readiness"] = {"score": 1.0, "band": "green"}
    try:
        result = ingest(
            body,
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )
        assert result.ask.payload["_readiness"]["score"] != 1.0 or result.ask.payload[
            "_readiness"
        ]["dimensions"]["trust_provenance"] == 0.5
    finally:
        store.close()


def test_the_api_returns_the_structured_repair_contract() -> None:
    import json
    import urllib.error
    import urllib.request
    from datetime import timedelta

    from agentinbox.api import start_api
    from agentinbox.store import utcnow

    body = weak_body()
    body["expires_at"] = (utcnow() + timedelta(minutes=5)).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")
    store = MemoryStore()
    api = start_api(
        store=store,
        config=config(readiness_enforce=True, readiness_min_score=0.9),
        token="token",
        port=0,
    )
    try:
        request = urllib.request.Request(
            f"{api.url}/v1/asks",
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=5)
        body = json.loads(error.value.read())
        assert error.value.code == 400
        assert body["error"]["field"] == "readiness"
        assert body["error"]["reason_code"] == "ask_not_decisionable"
        assert body["error"]["dimensions"]
        assert body["error"]["retry"] == "after-repair"
        assert store.audit_entries() == []
    finally:
        api.stop()
        store.close()


def test_rejection_without_a_class_keeps_every_repair() -> None:
    from agentinbox.readiness import evaluate, rejection_for

    readiness = evaluate(
        weak_body(), config=config(), producer_authenticated=True, now=NOW
    )
    assert rejection_for(readiness, None) is readiness
