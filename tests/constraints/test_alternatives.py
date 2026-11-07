"""Producer alternatives + enforcer binding (M27 item 27.1, R87/R93, SC-71/SC-74)."""

from __future__ import annotations

import pytest

from agentinbox.alternatives import is_selectable
from agentinbox.answers import AnswerRejected
from agentinbox.card import build_card
from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, alternative, approve, ingest_ask
from tests.readiness.conftest import config


def test_a_bindable_alternative_yields_allow_with_constraints() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store, alternatives=[alternative("staging")])
        result = approve(store, ask, alternative_id="staging")
        outcome = resolve(store, ask.ask_id, now=NOW, config=config())
    finally:
        store.close()

    assert result.winner
    assert outcome.status == "allow"  # old clients stay compatible
    assert outcome.decision == "allow_with_constraints"
    assert outcome.constraints[0]["id"] == "environment"
    assert outcome.alternative_fingerprint.startswith("sha256:")


def test_an_unbindable_alternative_is_advice_only_and_cannot_be_picked() -> None:
    store = MemoryStore()
    try:
        item = alternative("staging")
        item["enforcer"] = None
        ask = ingest_ask(store, alternatives=[item])
        assert not is_selectable(item)
        rendered = build_card(ask, now=NOW).render("terminal")
        with pytest.raises(AnswerRejected) as rejected:
            approve(store, ask, alternative_id="staging")
        stored = store.get(ask.ask_id)
    finally:
        store.close()

    assert "advice only" in rendered
    assert rejected.value.cause == "unbindable_alternative"
    assert stored is not None
    assert stored.status.value == "pending"


def test_a_tampered_fingerprint_is_unbindable() -> None:
    store = MemoryStore()
    try:
        item = alternative("staging")
        item["fingerprint"] = "sha256:" + "0" * 64
        ask = ingest_ask(store, alternatives=[item])
        with pytest.raises(AnswerRejected) as rejected:
            approve(store, ask, alternative_id="staging")
    finally:
        store.close()
    assert rejected.value.cause == "unbindable_alternative"
