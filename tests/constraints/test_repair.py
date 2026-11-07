"""Denial repair packets on the resolve and in evidence (M27 item 27.3, R89, SC-72)."""

from __future__ import annotations

from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, deny, ingest_ask
from tests.readiness.conftest import config


def test_a_deny_carries_a_repair_packet() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        deny(store, ask, reason="too broad for production")
        outcome = resolve(store, ask.ask_id, now=NOW, config=config())
        transitions = store.transitions_for(ask.ask_id)
    finally:
        store.close()

    assert outcome.decision == "deny"
    repair = outcome.repair
    assert repair is not None
    assert repair["violated_invariant"] == "too broad for production"
    assert repair["retry_worthiness"] == "conditional"
    assert repair["required_tier"] is None
    assert any(item.detail.get("repair") for item in transitions)


def test_a_pointless_deny_says_so() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        deny(store, ask, reason="wrong and unsafe, never do this")
        outcome = resolve(store, ask.ask_id, now=NOW, config=config())
    finally:
        store.close()
    assert outcome.repair is not None
    assert outcome.repair["retry_worthiness"] == "pointless"
