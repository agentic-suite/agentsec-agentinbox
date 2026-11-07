"""Additive resolve/1.0 vocabulary (M27 item 27.5, R92)."""

from __future__ import annotations

from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, approve, ingest_ask
from tests.readiness.conftest import config


def test_status_stays_compatible_while_decision_is_additive() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        approve(store, ask)
        outcome = resolve(store, ask.ask_id, now=NOW, config=config()).to_dict()
    finally:
        store.close()

    assert outcome["status"] == "allow"
    assert outcome["decision"] == "allow"
    assert outcome["constraints"] == []
    assert outcome["edits"] is None
    assert outcome["repair"] is None
