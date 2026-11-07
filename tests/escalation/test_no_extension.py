"""Escalation never extends the deadline; exhaustion denies at the original T (M11 item 11.2)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.escalation import Escalator
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStatus
from tests.ask.conftest import NOW
from tests.escalation.conftest import Clock, make_ask, make_config


def test_escalation_never_changes_expires_at(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config(
        tiers=("tier-1", "on-call", "incident-commander"),
        delays=(0, 300, 900),
        roster={
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
            "incident-commander": {"terminal": ("carol",)},
        },
    )
    ask = make_ask(store, config=config)
    original = ask.expires_at  # type: ignore[attr-defined]
    clock = Clock(NOW + timedelta(seconds=300))
    escalator = Escalator(store, config, now=clock)

    assert escalator.tick().escalated == 1
    assert store.get(ask.ask_id).expires_at == original  # type: ignore[union-attr]

    clock.moment = NOW + timedelta(seconds=900)
    assert escalator.tick().escalated == 1
    assert store.get(ask.ask_id).expires_at == original  # type: ignore[union-attr]


def test_ladder_exhaustion_denies_at_the_original_expiry(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config(
        tiers=("tier-1", "on-call", "incident-commander"),
        delays=(0, 300, 900),
        roster={
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
            "incident-commander": {"terminal": ("carol",)},
        },
    )
    ask = make_ask(store, config=config)
    original = ask.expires_at  # type: ignore[attr-defined]
    clock = Clock(NOW + timedelta(seconds=300))
    escalator = Escalator(store, config, now=clock)
    scheduler = Scheduler(store, now=clock, escalator=escalator)

    assert scheduler.tick().expired == 0
    clock.moment = NOW + timedelta(seconds=900)
    assert scheduler.tick().expired == 0

    # The last tier has no successor; the ask expires at the original T, not later.
    clock.moment = original
    assert scheduler.tick().expired == 1
    stored = store.get(ask.ask_id)
    assert stored.status is AskStatus.EXPIRED  # type: ignore[union-attr]
    assert stored.expires_at == original  # type: ignore[union-attr]

    events = [item for item in store.transitions_for(ask.ask_id) if item.kind == "ask-escalated"]
    assert len(events) == 2  # tiers - 1


def test_last_tier_renders_the_remaining_time(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.card import build_card

    config = make_config()
    ask = make_ask(store, config=config)
    clock = Clock(NOW + timedelta(seconds=300))
    Escalator(store, config, now=clock).tick()

    stored = store.get(ask.ask_id)
    card = build_card(stored, now=clock(), transitions=store.transitions_for(ask.ask_id))  # type: ignore[arg-type]
    rendered = card.render("terminal")

    assert "tier-1 → on-call" in rendered
    assert card.ttl_seconds == 3300
