"""Operation bundles, handoff, incident overlay, narrative, timeline (M28)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.card import build_card
from agentinbox.config import (
    ConfigError,
    IncidentConfig,
    init_home,
    load_config,
    resolve_config_path,
)
from agentinbox.operations import (
    assign_ask,
    bundle_export,
    claim_ask,
    derive_bundle,
    handoff_for,
    incident_banner,
    incident_state,
    narrative,
    record_handoff,
    record_incident,
    timeline,
)
from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.bundles.conftest import ingest_ask
from tests.constraints.conftest import alternative, approve, deny
from tests.readiness.conftest import NOW, config


def test_a_declared_operation_groups_twenty_asks_with_per_ask_truth() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"s{index}", command=f"echo step-{index}")
            for index in range(20)
        ]
        approve(store, asks[0])
        bundle = derive_bundle(store, asks[0])
        rendered = bundle.render()
        exported = bundle_export(store, bundle)
    finally:
        store.close()

    assert bundle.operation_id == "op_deploy_7"
    assert bundle.derived is False
    assert len(bundle.asks) == 20
    assert bundle.counts == {"pending": 19, "approved": 1}
    assert rendered.startswith("OPERATION op_deploy_7")
    assert exported["contract"] == "bundle/1.0"
    assert len(exported["timeline"]) >= 20
    assert not hasattr(bundle, "approve_all")


def test_an_undeclared_operation_is_derived_from_session_and_class() -> None:
    store = MemoryStore()
    try:
        first = ingest_ask(store, session="same", operation=None, command="echo a")
        second = ingest_ask(store, session="same", operation=None, command="echo b")
        other = ingest_ask(store, session="other", operation=None, command="echo c")
        bundle = derive_bundle(store, first)
    finally:
        store.close()

    assert bundle.derived is True
    assert bundle.operation_id is None
    assert {ask.ask_id for ask in bundle.asks} == {first.ask_id, second.ask_id}
    assert other.ask_id not in {ask.ask_id for ask in bundle.asks}


def test_claim_and_assign_are_routing_observations_only() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        claim_ask(store, ask.ask_id, principal="alice", at=NOW)
        assign_ask(store, ask.ask_id, assignee="bob", by="alice", at=NOW)
        after = store.get(ask.ask_id)
        transitions = store.transitions_for(ask.ask_id)
    finally:
        store.close()

    assert after is not None
    assert after.status.value == "pending"
    assert after.expires_at == ask.expires_at
    assert [item.kind for item in transitions if item.kind in {"claimed", "assigned"}] == [
        "claimed",
        "assigned",
    ]
    assert transitions[-1].detail["assignee"] == "bob"


def test_handoff_preserves_remaining_ttl_context_and_questions() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        note = record_handoff(
            store,
            ask.ask_id,
            outgoing="alice",
            incoming="bob",
            note="waiting on the rollback plan",
            open_questions=["is the backup verified?"],
            evidence=["diff"],
            at=NOW + timedelta(minutes=1),
        )
        stored = handoff_for(store.transitions_for(ask.ask_id))
    finally:
        store.close()

    assert stored == note
    assert note["remaining_s"] == 240
    assert note["open_questions"] == ["is the backup verified?"]
    assert note["evidence"] == ["diff"]
    assert note["incoming"] == "bob"


def test_incident_mode_is_bounded_audited_and_changes_no_ttl_or_denial() -> None:
    cfg = replace(
        config(),
        incident=IncidentConfig(
            enabled=True, owner="alice", reason="SEV-1", ttl_scale=0.5, classes=("irreversible",)
        ),
    )
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        assert record_incident(store, cfg, at=NOW) is True
        state = incident_state(cfg)
        deny(store, ask, reason="still unsafe")
        outcome = resolve(store, ask.ask_id, now=NOW, config=cfg)
        events = [entry for entry in store.audit_entries() if entry.kind == "incident-on"]
        after = store.get(ask.ask_id)
    finally:
        store.close()

    assert "INCIDENT MODE: SEV-1" in incident_banner(state)
    assert state["ttl_scale"] == 0.5
    assert after is not None
    assert after.expires_at == ask.expires_at
    assert outcome.status == "deny"
    assert outcome.decision == "deny"
    assert len(events) == 1


@pytest.mark.parametrize(
    "section",
    [
        "[incident]\nenabled = true\nttl_scale = 0.5\n",
        '[incident]\nenabled = true\nowner = "alice"\nreason = "SEV-1"\nttl_scale = 2.0\n',
        '[incident]\nenabled = "yes"\nowner = "alice"\nreason = "SEV-1"\n',
        '[incident]\nenabled = true\nowner = "alice"\nreason = "SEV-1"\nclasses = "irreversible"\n',
    ],
)
def test_invalid_incident_config_is_a_load_error(tmp_path: Path, section: str) -> None:
    home = tmp_path / "home"
    path = resolve_config_path(home)
    init_home(home, path)
    path.write_text(path.read_text(encoding="utf-8") + "\n" + section, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_narrative_reads_the_chain_including_constraints_and_edits() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        deny(store, ask, reason="missing rollback plan")
        text = narrative(ask, store.transitions_for(ask.ask_id))
    finally:
        store.close()

    assert text.startswith(f"Decision narrative — {ask.ask_id}")
    assert "Rule: irreversible-ask-gate" in text
    assert "Evidence:" in text
    assert "Outcome: denied by alice" in text
    assert "Reason: missing rollback plan" in text


def test_narrative_says_pending_before_an_answer() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        text = narrative(ask, store.transitions_for(ask.ask_id))
    finally:
        store.close()
    assert "Outcome: still pending" in text


def test_timeline_is_ordered_and_carries_operation_id() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        deny(store, ask, reason="too broad")
        transitions = store.transitions_for(ask.ask_id)
        rows = timeline((ask,), transitions)
    finally:
        store.close()

    assert [row["seq"] for row in rows] == sorted(row["seq"] for row in rows)
    assert rows[0]["kind"] == "created"
    assert rows[-1]["kind"] == "answer"
    assert all(row["operation_id"] == "op_deploy_7" for row in rows)


def test_handoff_note_renders_before_the_card_and_preserves_ttl() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        record_handoff(
            store,
            ask.ask_id,
            outgoing="alice",
            incoming="bob",
            note="rollback plan missing",
            open_questions=["is the backup verified?"],
            evidence=["diff"],
            at=NOW,
        )
        note = handoff_for(store.transitions_for(ask.ask_id))
        rendered = build_card(ask, now=NOW, handoff=note).render("terminal")
        after = store.get(ask.ask_id)
        approved = approve(store, ask)
    finally:
        store.close()

    assert note is not None
    assert rendered.index("HANDOFF") < rendered.index("ACTION")
    assert "rollback plan missing" in rendered
    assert "is the backup verified?" in rendered
    assert after is not None
    assert after.expires_at == ask.expires_at
    assert approved.winner


def test_incident_on_and_off_are_chained_events_and_valid_config_parses(
    tmp_path: Path,
) -> None:
    off = replace(config(), incident=IncidentConfig())
    on = replace(
        config(),
        incident=IncidentConfig(enabled=True, owner="alice", reason="SEV-1", ttl_scale=0.5),
    )
    store = MemoryStore()
    try:
        assert record_incident(store, on, at=NOW) is True
        assert record_incident(store, off, at=NOW) is True
        kinds = [
            entry.kind
            for entry in store.audit_entries()
            if entry.kind.startswith("incident-")
        ]
    finally:
        store.close()

    assert kinds == ["incident-on", "incident-off"]

    home = tmp_path / "home"
    path = resolve_config_path(home)
    init_home(home, path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[incident]\nenabled = true\nowner = "alice"\nreason = "SEV-1"\n'
        + "ttl_scale = 0.5\nclasses = [\"irreversible\"]\n",
        encoding="utf-8",
    )
    loaded = load_config(path)
    assert loaded.incident.enabled is True
    assert loaded.incident.classes == ("irreversible",)


def test_bundle_phases_and_critical_path_with_nothing_pending() -> None:
    store = MemoryStore()
    try:
        first = ingest_ask(store, session="a", command="echo a", phase=None)
        second = ingest_ask(store, session="b", command="echo b", phase=None)
        approve(store, first)
        bundle = derive_bundle(store, first)
        rendered = bundle.render()
        approve(store, second)
        done = derive_bundle(store, first)
        done_rendered = done.render()
    finally:
        store.close()

    assert set(bundle.phases) == {"review", "decided"}
    assert bundle.critical_path is not None
    assert bundle.critical_path["ask_id"] == second.ask_id
    assert "critical path: ask_" in rendered
    assert done.critical_path is None
    assert "critical path: none" in done_rendered


def test_narrative_includes_constraints_and_edits() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store, alternatives=[alternative("staging")])
        approve(store, ask, alternative_id="staging")
        text = narrative(ask, store.transitions_for(ask.ask_id))
    finally:
        store.close()
    assert "Alternatives offered: staging" in text
    assert "Constraints: environment" in text


def test_bundle_excludes_other_operation_and_non_transition_audit_rows() -> None:
    store = MemoryStore()
    try:
        first = ingest_ask(store, operation="op_a", command="echo a")
        other = ingest_ask(store, session="s2", operation="op_b", command="echo b")
        foreign_class = ingest_ask(
            store, session="s1", operation=None, command="echo c", **{"class": "readonly"}
        )
        store.append_audit(kind="incident-off", ref_id="incident", at=NOW, payload={})
        declared = derive_bundle(store, first)
        derived = derive_bundle(store, first, operation_id=None)
    finally:
        store.close()

    assert other.ask_id not in {ask.ask_id for ask in declared.asks}
    assert foreign_class.ask_id not in {ask.ask_id for ask in derived.asks}


def test_handoff_for_an_unknown_ask_is_an_error() -> None:
    store = MemoryStore()
    try:
        with pytest.raises(KeyError):
            record_handoff(
                store,
                "ask_0000000000000000",
                outgoing="alice",
                incoming="bob",
                note="n",
            )
    finally:
        store.close()


def test_narrative_reports_missing_evidence_and_contradictions() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        marked = replace(
            ask,
            payload={
                **ask.payload,
                "_readiness": {
                    "band": "red",
                    "missing": ["evidence_presence"],
                    "contradictions": ["environment_mismatch"],
                },
            },
        )
        text = narrative(marked, store.transitions_for(ask.ask_id))
    finally:
        store.close()

    assert "Missing: evidence_presence" in text
    assert "Contradictions: environment_mismatch" in text

    from agentinbox.config import _parse_audit, _parse_channels, _parse_incident

    with pytest.raises(ConfigError):
        _parse_channels({"terminal": {"allow_as": "yes", "enabled": True}})
    with pytest.raises(ConfigError):
        _parse_incident({"owner": ""})
    with pytest.raises(ConfigError):
        _parse_audit({"retention": "forever"})
