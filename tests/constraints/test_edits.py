"""Human edits re-fingerprint and record provenance (M27 item 27.4, R90/R91, SC-73)."""

from __future__ import annotations

import pytest

from agentinbox.answers import AnswerRejected
from agentinbox.contract import compute_action_identity
from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, approve, ingest_ask
from tests.readiness.conftest import config


def test_an_edited_allow_recomputes_the_action_identity_and_records_provenance() -> None:
    from dataclasses import replace

    store = MemoryStore()
    cfg = replace(
        config(),
        classes={
            **config().classes,
            "irreversible": replace(
                config().classes["irreversible"], edit_schema=("command",)
            ),
        },
    )
    try:
        ask = ingest_ask(store)
        approve(
            store,
            ask,
            cfg=cfg,
            edits={"command": "psql prod -c 'select 1 limit 10'"},
        )
        outcome = resolve(store, ask.ask_id, now=NOW, config=cfg)
        winner = [
            item for item in store.transitions_for(ask.ask_id) if item.kind == "answer"
        ][-1]
    finally:
        store.close()

    edited = compute_action_identity(
        tool="shell",
        action="run_command",
        arguments={"command": "psql prod -c 'select 1 limit 10'"},
    )
    assert outcome.decision == "allow_with_edits"
    assert outcome.edits == {"command": "psql prod -c 'select 1 limit 10'"}
    assert winner.detail["original_action_identity"] == ask.action_identity
    assert winner.detail["edited_action_identity"] == edited
    assert winner.principal == "alice"


def test_an_out_of_schema_edit_is_refused_with_the_field_named() -> None:
    from dataclasses import replace

    store = MemoryStore()
    cfg = replace(
        config(),
        classes={
            **config().classes,
            "irreversible": replace(
                config().classes["irreversible"], edit_schema=("command",)
            ),
        },
    )
    try:
        ask = ingest_ask(store)
        from agentinbox.answers import AnswerVerifier
        from agentinbox.claims import mint_claim

        minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW, secret="q" * 32)
        verifier = AnswerVerifier(store, cfg, now=lambda: NOW)
        with pytest.raises(AnswerRejected) as rejected:
            verifier.submit(
                __import__("agentinbox.answers", fromlist=["AnswerRequest"]).AnswerRequest(
                    ask_id=ask.ask_id,
                    claim_id=minted.claim.claim_id,
                    secret=minted.secret,
                    principal="alice",
                    channel="terminal",
                    decision="approve",
                    typed_confirmation="run_command",
                    edits={"environment": "staging"},
                ),
                channel_authenticated=True,
            )
        stored = store.get(ask.ask_id)
    finally:
        store.close()

    assert rejected.value.cause == "edit_schema"
    assert "environment" in str(rejected.value.message)
    assert stored is not None
    assert stored.status.value == "pending"
