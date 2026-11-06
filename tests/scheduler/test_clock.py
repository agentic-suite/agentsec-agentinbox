"""Clock jumps are fail-closed (M4 item 4.4, E8)."""

from __future__ import annotations

from datetime import timedelta

from tests.ask.conftest import NOW, config, payload

from agentinbox.ingest import ingest
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity


def make_ask(store):  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id


def test_backwards_jump_cannot_extend_a_ttl(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    clock = [ask.expires_at + timedelta(seconds=1), ask.expires_at - timedelta(hours=1)]
    scheduler = Scheduler(store, now=lambda: clock.pop(0) if len(clock) > 1 else clock[0])

    scheduler.tick()  # at/after the deadline: expires
    scheduler.tick()  # clock jumped backwards: must not resurrect

    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]
    assert [item.kind for item in store.transitions_for(ask_id)].count("expired") == 1


def test_backwards_jump_before_firing_does_not_postpone(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    seen = [NOW + timedelta(minutes=6), NOW - timedelta(hours=2)]
    scheduler = Scheduler(store, now=lambda: seen.pop(0) if seen else NOW + timedelta(minutes=6))

    first = scheduler.tick()  # 6 minutes: past the 5-minute deadline
    second = scheduler.tick()  # clock says 2 hours earlier

    assert first.expired == 1
    assert second.expired == 0
    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]


def test_forwards_jump_cannot_resurrect_an_expired_ask(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    scheduler = Scheduler(store, now=lambda: ask.expires_at + timedelta(days=1))

    scheduler.tick()

    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]
    scheduler.tick()
    assert [item.kind for item in store.transitions_for(ask_id)].count("expired") == 1
