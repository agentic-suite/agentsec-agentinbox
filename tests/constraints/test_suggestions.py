"""Class-generic suggestions are labelled and never recorded (M27 item 27.2, R88)."""

from __future__ import annotations

from agentinbox.card import build_card
from agentinbox.resolve import resolve
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, approve, ingest_ask
from tests.readiness.conftest import config


def test_suggestions_render_but_leave_no_constraint_when_unpicked() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store, command="psql prod -c 'DROP TABLE customers'")
        rendered = build_card(ask, now=NOW).render("terminal")
        approve(store, ask)
        outcome = resolve(store, ask.ask_id, now=NOW, config=config())
    finally:
        store.close()

    assert "CHOICES" in rendered
    assert "suggestion" in rendered
    assert outcome.decision == "allow"
    assert outcome.constraints == ()
