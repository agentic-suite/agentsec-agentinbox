"""Policy-learning insights, calibration access, actions, and hygiene (M31)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from agentinbox.config import InsightsConfig
from agentinbox.ingest import ingest
from agentinbox.insights import (
    InsightsError,
    calibration,
    compute_insights,
    export_insights,
    to_action,
)
from agentinbox.lifecycle import transition
from agentinbox.outcomes import record_outcome
from agentinbox.store import AskStatus
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.bundles.conftest import ingest_ask
from tests.constraints.conftest import approve, deny
from tests.readiness.conftest import NOW, config, weak_body


def _approved_batch(store, count=20, command="echo identical"):  # type: ignore[no-untyped-def]
    asks = [
        ingest_ask(store, session=f"batch{index}", command=command)
        for index in range(count)
    ]
    for ask in asks:
        approve(store, ask)
    return asks


def _kind(store, cfg, kind, **kwargs):  # type: ignore[no-untyped-def]
    return [item for item in compute_insights(store, cfg, **kwargs) if item.kind == kind]


def test_twenty_similar_approvals_produce_one_redacted_insight() -> None:
    store = MemoryStore()
    try:
        asks = _approved_batch(store)
        found = _kind(store, config(), "repetitive-approval")
        exported = export_insights(found)
    finally:
        store.close()

    assert len(found) == 1
    insight = found[0]
    assert insight.counts["approvals"] == 20
    assert insight.representative_ask in {ask.ask_id for ask in asks}
    assert "echo identical" not in str(insight.to_dict())
    assert "echo identical" not in str(exported)
    assert exported["contract"] == "insights/1.0"


def test_deny_clusters_name_the_reason_and_offer_tuning() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"deny{index}", command="echo noisy")
            for index in range(10)
        ]
        for ask in asks:
            deny(store, ask, reason="not now")
        found = _kind(store, config(), "deny-cluster")
        before = store.get(asks[0].ask_id)
    finally:
        store.close()

    assert len(found) == 1
    assert found[0].counts["denials"] == 10
    assert found[0].counts["reason_code"] == "human_gate_required"
    assert "TTL" in found[0].recommendation
    assert before is not None
    assert before.status.value == "denied"


def test_escalation_hotspots_name_class_tier_and_hour() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"hot{index}", command=f"echo hot-{index}")
            for index in range(3)
        ]
        for ask in asks:
            transition(
                store,
                ask.ask_id,
                AskStatus.EXPIRED,
                kind="expired",
                at=NOW,
            )
        found = _kind(store, config(), "escalation-hotspot")
    finally:
        store.close()

    assert len(found) == 1
    assert found[0].counts["hour_utc"] == NOW.hour
    assert "UTC" in found[0].recommendation
    assert found[0].counts["events"] == 3


def test_evidence_gaps_come_from_denied_readiness() -> None:
    store = MemoryStore()
    try:
        body = weak_body()
        ask = ingest(
            body,
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        ).ask
        deny(store, ask, reason="missing evidence")
        found = _kind(store, config(), "evidence-gap")
    finally:
        store.close()

    assert found
    assert any(item.counts["missing"] for item in found)
    assert "requiring" in found[0].recommendation


def test_outcome_divergence_proposes_hardening_only() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"out{index}", command=f"echo out-{index}")
            for index in range(2)
        ]
        for ask in asks:
            approve(store, ask)
            record_outcome(
                store,
                ask.ask_id,
                state="executed",
                principal="ci",
                manifest={"resources": ["db:prod/other"]},
            )
        found = _kind(store, config(), "outcome-tuning")
        states = [store.get(ask.ask_id) for ask in asks]
    finally:
        store.close()

    assert len(found) == 1
    assert found[0].proposed_diff["require_typed_confirmation"] is True
    assert all(item is not None and item.status.value == "approved" for item in states)


def test_calibration_is_aggregate_by_default_and_gated_per_principal() -> None:
    store = MemoryStore()
    try:
        approved = ingest_ask(store, session="cal1", command="echo cal")
        denied = ingest_ask(store, session="cal2", command="echo cal")
        approve(store, approved)
        deny(store, denied, reason="no")
        aggregate = calibration(store, config(), now=NOW)
        with pytest.raises(InsightsError):
            calibration(store, config(), principal="auditor", now=NOW)
        governed = replace(
            config(),
            insights=InsightsConfig(governance_principals=("auditor",)),
        )
        gated = calibration(store, governed, principal="auditor", now=NOW)
        access = [
            entry for entry in store.audit_entries() if entry.kind == "insight-calibration-access"
        ]
    finally:
        store.close()

    assert aggregate["aggregate"][0]["approved"] >= 1
    assert "per_principal" not in aggregate
    assert gated["per_principal"]["alice"]["approved"] >= 1
    assert gated["per_principal"]["alice"]["denied"] >= 1
    assert len(access) == 1
    assert access[0].payload["principal"] == "auditor"


def test_insight_to_action_exports_a_reviewable_body_and_records_origin() -> None:
    store = MemoryStore()
    try:
        _approved_batch(store)
        insight = _kind(store, config(), "repetitive-approval")[0]
        diff = to_action(store, insight, kind="config_diff", reviewer="alice", now=NOW)
        runbook = to_action(store, insight, kind="runbook", reviewer="alice", now=NOW)
        grant = to_action(store, insight, kind="grant", reviewer="alice", now=NOW)
        with pytest.raises(InsightsError):
            to_action(store, insight, kind="automatic", reviewer="alice")
        with pytest.raises(InsightsError):
            to_action(store, insight, kind="runbook", reviewer="")
        actions = [entry for entry in store.audit_entries() if entry.kind == "insight-action"]
    finally:
        store.close()

    assert "proposed config change" in diff.body
    assert "Runbook task" in runbook.body
    assert "Grant proposal" in grant.body
    assert len(actions) == 3
    assert actions[0].payload["origin"] == "repetitive-approval"
    assert actions[0].payload["reviewer"] == "alice"


def test_stale_insights_expire_and_export_has_no_raw_arguments() -> None:
    store = MemoryStore()
    try:
        _approved_batch(store)
        cfg = replace(config(), insights=InsightsConfig(stale_after_seconds=1))
        fresh = compute_insights(store, cfg, now=NOW)
        stale = compute_insights(store, cfg, now=NOW + timedelta(seconds=2))
        exported = export_insights(fresh)
    finally:
        store.close()

    assert fresh
    assert stale == []
    assert "echo identical" not in str(exported)
    assert all("arguments" not in item for item in exported["insights"])


def test_insight_render_action_export_and_config_edges(tmp_path) -> None:  # type: ignore[no-untyped-def]

    from agentinbox.config import ConfigError, init_home, load_config, resolve_config_path

    store = MemoryStore()
    try:
        _approved_batch(store)
        insight = _kind(store, config(), "repetitive-approval")[0]
        action = to_action(store, insight, kind="runbook", reviewer="alice", now=NOW)
        rendered = insight.render()
        action_dict = action.to_dict()
    finally:
        store.close()

    assert "recommendation:" in rendered
    assert action_dict["origin"] == "repetitive-approval"
    assert action_dict["kind"] == "runbook"

    for section in (
        "[insights]\ngovernance_principals = \"alice\"\n",
        "[insights]\napproval_threshold = 0\n",
    ):
        home = tmp_path / f"home-{abs(hash(section))}"
        path = resolve_config_path(home)
        init_home(home, path)
        path.write_text(path.read_text(encoding="utf-8") + "\n" + section, encoding="utf-8")
        with pytest.raises(ConfigError):
            load_config(path)
