"""Escalation tier engine: timers, events, and ladder reconstruction (M11 item 11.1)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.escalation import Escalator, initial_escalation
from agentinbox.store import AskStatus
from tests.ask.conftest import NOW
from tests.escalation.conftest import Clock, make_ask, make_config


def test_ingest_starts_at_the_first_tier(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)

    assert ask.tier == "tier-1"  # type: ignore[attr-defined]
    assert ask.escalate_at == NOW + timedelta(seconds=300)  # type: ignore[attr-defined]


def test_single_tier_ladder_has_no_escalation(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config(tiers=("tier-1",), delays=(0,))
    ask = make_ask(store, config=config)

    assert ask.tier == "tier-1"  # type: ignore[attr-defined]
    assert ask.escalate_at is None  # type: ignore[attr-defined]
    assert initial_escalation(config.classes["irreversible"], NOW) == ("tier-1", None)


def test_tier_fires_at_the_configured_instant(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    clock = Clock(NOW + timedelta(seconds=299))
    escalator = Escalator(store, config, now=clock)

    assert escalator.tick().escalated == 0
    assert store.get(ask.ask_id).tier == "tier-1"  # type: ignore[union-attr]

    clock.moment = NOW + timedelta(seconds=300)
    assert escalator.tick().escalated == 1

    stored = store.get(ask.ask_id)
    assert stored.tier == "on-call"  # type: ignore[union-attr]
    assert stored.status is AskStatus.PENDING  # type: ignore[union-attr]

    events = [item for item in store.transitions_for(ask.ask_id) if item.kind == "ask-escalated"]
    assert len(events) == 1
    assert events[0].detail["from_tier"] == "tier-1"
    assert events[0].detail["to_tier"] == "on-call"
    assert events[0].detail["recipients"] == 1
    assert events[0].detail["remaining_s"] == 3300


def test_escalation_is_once_per_tier(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    clock = Clock(NOW + timedelta(seconds=300))
    escalator = Escalator(store, config, now=clock)

    assert escalator.tick().escalated == 1
    assert escalator.tick().escalated == 0
    assert escalator.tick().escalated == 0

    events = [item for item in store.transitions_for(ask.ask_id) if item.kind == "ask-escalated"]
    assert len(events) == 1


def test_a_three_tier_ladder_walks_in_order(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config(
        tiers=("tier-1", "on-call", "incident-commander"),
        delays=(0, 300, 900),
        roster={
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
            "incident-commander": {"terminal": ("carol", "dave")},
        },
    )
    ask = make_ask(store, config=config)
    clock = Clock(NOW + timedelta(seconds=300))
    escalator = Escalator(store, config, now=clock)

    assert escalator.tick().escalated == 1
    assert store.get(ask.ask_id).tier == "on-call"  # type: ignore[union-attr]

    clock.moment = NOW + timedelta(seconds=900)
    assert escalator.tick().escalated == 1
    stored = store.get(ask.ask_id)
    assert stored.tier == "incident-commander"  # type: ignore[union-attr]
    assert stored.escalate_at is None  # type: ignore[union-attr]

    events = [item for item in store.transitions_for(ask.ask_id) if item.kind == "ask-escalated"]
    assert [event.detail["to_tier"] for event in events] == ["on-call", "incident-commander"]
    assert events[-1].detail["recipients"] == 2


def test_a_resolved_ask_never_escalates(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.lifecycle import transition

    config = make_config()
    ask = make_ask(store, config=config)
    assert transition(
        store,
        ask.ask_id,
        AskStatus.APPROVED,
        kind="answered",
        at=NOW,
        principal="alice",
        channel="terminal",
    )
    escalator = Escalator(store, config, now=Clock(NOW + timedelta(seconds=1000)))

    assert escalator.tick().escalated == 0
    assert store.get(ask.ask_id).tier == "tier-1"  # type: ignore[union-attr]
