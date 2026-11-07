"""Multi-surface decision parity (M14): one record shape, one truth.

Design: ``docs/design/v0.1.0/parity.md``. Every surface reads the same store and renders the same
M5 card; the decision record is built here, once, so no surface can invent a different shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agentinbox.card import build_card
from agentinbox.lifecycle import winning_answer
from agentinbox.store import AskRecord, AskStore, canonical_json, to_iso

#: The only fields a surface may differ on.
VARIANT_FIELDS = frozenset({"channel", "principal"})


def decision_record(store: AskStore, ask_id: str) -> dict[str, Any]:
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    winner = winning_answer(store.transitions_for(ask_id))
    return {
        "ask_id": ask.ask_id,
        "action_identity": ask.action_identity,
        "status": ask.status.value,
        "decided_at": None if ask.decided_at is None else to_iso(ask.decided_at),
        "decision": None if winner is None else winner.detail.get("decision"),
        "reason": None if winner is None else winner.reason,
        "channel": None if winner is None else winner.channel,
        "principal": None if winner is None else winner.principal,
    }


def comparable_decision(record: dict[str, Any]) -> str:
    """Canonical bytes of the record with the surface-variant fields removed."""
    trimmed = {
        key: value for key, value in record.items() if key not in VARIANT_FIELDS
    }
    return canonical_json(trimmed)


def prior_asks(store: AskStore, ask: AskRecord) -> tuple[AskRecord, ...]:
    """The other asks in the same session, oldest first (for the card's context block)."""
    return tuple(
        item
        for item in store.export_session(ask.session_id).asks
        if item.ask_id != ask.ask_id
    )


def surface_outcome(
    store: AskStore, ask_id: str, *, surface: str, now: datetime
) -> str:
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    from agentinbox.readiness import similar_cases

    card = build_card(
        ask,
        now=now,
        transitions=store.transitions_for(ask_id),
        prior_asks=prior_asks(store, ask),
        similar_cases=similar_cases(store, ask),
    )
    return card.render(surface)


__all__ = [
    "VARIANT_FIELDS",
    "comparable_decision",
    "decision_record",
    "prior_asks",
    "surface_outcome",
]
