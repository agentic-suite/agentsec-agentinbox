"""Outcome closure, receipts, comparison, divergence, packets, SLA (M29)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from agentinbox.card import build_card
from agentinbox.operations import narrative
from agentinbox.outcomes import (
    OutcomeError,
    acknowledge_divergence,
    compare_execution,
    decision_packet,
    divergence_ack,
    latest_outcome,
    outcome_sla_pending,
    packet_json,
    record_outcome,
    trace,
    verify_packet,
)
from agentinbox.store import ChainHashMismatch
from agentinbox.store.memory import MemoryStore
from tests.bundles.conftest import ingest_ask
from tests.constraints.conftest import approve
from tests.readiness.conftest import NOW, config


def test_an_approved_ask_closes_without_changing_its_decision() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        before = latest_outcome(store.transitions_for(ask.ask_id))
        detail = record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci-bot",
            receipt={"run_url": "https://ci.example/runs/7", "digest": "sha256:" + "b" * 64},
            manifest={
                "fingerprint": ask.action_identity,
                "resources": ["db:prod/customers"],
                "environment": "production",
            },
            at=NOW,
        )
        after = store.get(ask.ask_id)
        transitions = store.transitions_for(ask.ask_id)
        card = build_card(ask, now=NOW, transitions=transitions).render("terminal")
        story = narrative(ask, transitions)
        latest = latest_outcome(transitions)
    finally:
        store.close()

    assert before is None
    assert detail["comparison"]["status"] == "match"
    assert after is not None
    assert after.status.value == "approved"
    assert latest is not None
    assert latest["state"] == "executed"
    assert "OUTCOME" in card
    assert "executed" in card
    assert "match" in card
    assert "Execution: executed (comparison=match)" in story
    assert "https://ci.example/runs/7" in card


def test_unclosed_asks_stay_unknown_and_illegal_closures_are_refused() -> None:
    store = MemoryStore()
    try:
        pending = ingest_ask(store)
        with pytest.raises(OutcomeError):
            record_outcome(store, pending.ask_id, state="executed", principal="ci")
        approved = ingest_ask(store, session="s2")
        approve(store, approved)
        with pytest.raises(OutcomeError):
            record_outcome(store, approved.ask_id, state="weird", principal="ci")
        with pytest.raises(KeyError):
            record_outcome(store, "ask_0000000000000000", state="executed", principal="ci")
        assert latest_outcome(store.transitions_for(pending.ask_id)) is None
    finally:
        store.close()


def test_a_receipt_with_a_credential_is_refused() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        with pytest.raises(OutcomeError) as rejected:
            record_outcome(
                store,
                ask.ask_id,
                state="executed",
                principal="ci",
                receipt={"job_id": "AKIA" + "A" * 16},
            )
        stored = store.get(ask.ask_id)
    finally:
        store.close()
    assert "credential" in str(rejected.value)
    assert stored is not None
    assert stored.status.value == "approved"


def test_receipts_are_capped_not_unbounded() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        detail = record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci",
            receipt={"resources": [f"db:prod/table-{index}" for index in range(100)]},
        )
    finally:
        store.close()
    assert len(detail["receipt"]["resources"]) == 50


@pytest.mark.parametrize(
    ("manifest", "expected"),
    [
        ({"fingerprint": None, "resources": ["db:prod/customers"]}, "partial"),
        ({"resources": ["db:prod/customers", "db:prod/audit"]}, "exceeded"),
        ({"fingerprint": "sha256:" + "0" * 64, "resources": ["db:prod/customers"]}, "divergent"),
        ({}, "unknown"),
    ],
)
def test_approved_vs_executed_comparison(manifest, expected) -> None:  # type: ignore[no-untyped-def]
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        compare = compare_execution(ask, store.transitions_for(ask.ask_id), manifest)
    finally:
        store.close()
    assert compare["status"] == expected
    if expected == "exceeded":
        assert compare["exceeding"] == ["db:prod/audit"]


def test_exceeded_emits_a_chained_divergence_and_acknowledgement() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci",
            manifest={"resources": ["db:prod/customers", "db:prod/audit"]},
        )
        events = [entry for entry in store.audit_entries() if entry.kind == "outcome-divergence"]
        transitions = store.transitions_for(ask.ask_id)
        card = build_card(ask, now=NOW, transitions=transitions).render("terminal")
        ack = acknowledge_divergence(store, ask.ask_id, principal="alice", at=NOW)
        acked = build_card(
            ask, now=NOW, transitions=store.transitions_for(ask.ask_id)
        ).render("terminal")
        ack_record = divergence_ack(store.transitions_for(ask.ask_id))
    finally:
        store.close()

    assert len(events) == 1
    assert events[0].payload is not None
    assert "db:prod/audit" in events[0].payload["exceeding"]
    assert "UNACKNOWLEDGED" in card
    assert ack["principal"] == "alice"
    assert ack_record is not None
    assert "acknowledged" in acked
    assert "UNACKNOWLEDGED" not in acked


def test_no_divergence_means_nothing_to_acknowledge() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        with pytest.raises(OutcomeError):
            acknowledge_divergence(store, ask.ask_id, principal="alice")
    finally:
        store.close()


def test_a_packet_is_self_contained_and_verifiable_offline() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        record_outcome(store, ask.ask_id, state="executed", principal="ci")
        packet = decision_packet(store, ask.ask_id)
    finally:
        store.close()

    verify_packet(packet)
    assert packet["contract"] == "decision-packet/1.0"
    assert packet["decision"]["status"] == "allow"
    assert packet["outcome"]["state"] == "executed"
    assert "Execution: executed" in packet["narrative"]
    assert packet["trace"]["ask"] == ask.ask_id
    assert packet["verification"]["instructions"]
    assert "decision-packet" in packet_json(packet)

    tampered = {**packet, "chain_segment": [dict(item) for item in packet["chain_segment"]]}
    tampered["chain_segment"][-1]["payload"] = {"evil": True}
    with pytest.raises(ChainHashMismatch):
        verify_packet(tampered)


def test_trace_walks_ask_decision_execution_divergence() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci",
            manifest={"resources": ["db:prod/other"]},
        )
        walked = trace(store, ask.ask_id)
    finally:
        store.close()

    assert walked["ask"] == ask.ask_id
    assert walked["decision"]["status"] == "allow"
    assert walked["outcome"]["state"] == "executed"
    assert walked["outcome"]["comparison"]["status"] == "exceeded"
    assert walked["divergence"]


def test_closure_sla_surfaces_only_unclosed_approved_asks() -> None:
    cfg = replace(
        config(),
        classes={
            **config().classes,
            "irreversible": replace(
                config().classes["irreversible"], closure_sla_seconds=60
            ),
        },
    )
    store = MemoryStore()
    try:
        open_ask = ingest_ask(store, session="open")
        closed_ask = ingest_ask(store, session="closed")
        approve(store, open_ask)
        approve(store, closed_ask)
        record_outcome(store, closed_ask.ask_id, state="executed", principal="ci")
        pending = outcome_sla_pending(store, cfg, now=NOW + timedelta(minutes=2))
        fresh = outcome_sla_pending(store, cfg, now=NOW)
    finally:
        store.close()

    assert [item["ask_id"] for item in pending] == [open_ask.ask_id]
    assert pending[0]["reason"] == "outcome-pending-past-sla"
    assert fresh == []


def test_receipt_and_manifest_shape_edges() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        detail = record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci",
            receipt={"unknown": "ignored", "job_id": "7"},
        )
        assert detail["receipt"] == {"job_id": "7"}
        for receipt in ({"resources": "not-a-list"}, {"url": "x" * 2049}):
            with pytest.raises(OutcomeError):
                record_outcome(
                    store, ask.ask_id, state="executed", principal="ci", receipt=receipt
                )
        for manifest in ({"resources": "x"}, {"constraints": "x"}):
            with pytest.raises(OutcomeError):
                record_outcome(
                    store, ask.ask_id, state="executed", principal="ci", manifest=manifest
                )
        with pytest.raises(KeyError):
            trace(store, "ask_0000000000000000")
        with pytest.raises(KeyError):
            decision_packet(store, "ask_0000000000000000")
    finally:
        store.close()


def test_an_edited_approval_is_the_compared_identity_and_extra_resources_count() -> None:
    cfg = replace(
        config(),
        classes={
            **config().classes,
            "irreversible": replace(
                config().classes["irreversible"], edit_schema=("command",)
            ),
        },
    )
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask, cfg=cfg, edits={"command": "echo safe"})
        transitions = store.transitions_for(ask.ask_id)
        edited_identity = transitions[-1].detail["edited_action_identity"]
        detail = record_outcome(
            store,
            ask.ask_id,
            state="executed",
            principal="ci",
            manifest={
                "fingerprint": edited_identity,
                "resources": ["db:prod/customers"],
            },
        )
    finally:
        store.close()
    assert detail["comparison"]["status"] == "match"
    assert detail["comparison"]["approved_fingerprint"] == edited_identity


def test_export_packet_cli_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from argparse import Namespace

    from agentinbox import cli
    from agentinbox.outcomes import record_outcome as close

    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        close(store, ask.ask_id, state="executed", principal="ci")
        monkeypatch.setattr(cli, "_runtime", lambda args: (config(), store))
        # _export now closes the store on every exit path; give it a fresh
        # store per call so the fixture's store is never closed under it.
        monkeypatch.setattr(cli, "_close_store", lambda _store: None)
        args = Namespace(
            ask=ask.ask_id, packet=True, out=None, format="jsonl", session=None
        )
        assert cli._export(args) == 0
        output = capsys.readouterr().out
        assert "decision-packet/1.0" in output

        missing = Namespace(ask=None, packet=True, out=None, format="jsonl", session="s")
        assert cli._export(missing) == 1

        unknown = Namespace(
            ask="ask_0000000000000000", packet=True, out=None, format="jsonl", session=None
        )
        assert cli._export(unknown) == 4
    finally:
        store.close()
