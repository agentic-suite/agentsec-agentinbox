"""Repair recall on resubmission (M27 item 27.5, R92)."""

from __future__ import annotations

from agentinbox.alternatives import prior_objections
from agentinbox.card import build_card
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, deny, ingest_ask


def test_a_resubmission_shows_the_prior_denial_and_repair() -> None:
    store = MemoryStore()
    try:
        first = ingest_ask(store, session="s1")
        deny(store, first, reason="missing the migration diff")
        second = ingest_ask(store, session="s2")
        objections = prior_objections(store, second)
        rendered = build_card(second, now=NOW, prior_objections=objections).render("terminal")
    finally:
        store.close()

    assert [item["ask_id"] for item in objections] == [first.ask_id]
    assert "prior objection" in rendered
    assert first.ask_id in rendered
    assert "denied once" in rendered
