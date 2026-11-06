"""Timer engine: warn once at T-60, expire exactly at T (M4 item 4.1/4.5)."""

from __future__ import annotations

from datetime import timedelta

from tests.ask.conftest import NOW, config, payload

from agentinbox.ingest import ingest
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity


def make_scheduler(store, now):  # type: ignore[no-untyped-def]
    return Scheduler(store, now=lambda: now[0])


def make_ask(store) -> str:  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id


def test_nothing_fires_before_due(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    clock = [NOW + timedelta(seconds=30)]
    scheduler = make_scheduler(store, clock)

    stats = scheduler.tick()

    assert stats.expired == 0
    assert stats.warned == 0
    ask = store.get(ask_id)
    assert ask is not None
    assert ask.status is AskStatus.PENDING


def test_warning_fires_at_warn_at_and_only_once(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    clock = [NOW + timedelta(seconds=240)]  # T-60 for a 300 s TTL
    scheduler = make_scheduler(store, clock)

    stats = scheduler.tick()
    again = scheduler.tick()

    assert stats.warned == 1
    assert again.warned == 0
    warned = [item for item in store.transitions_for(ask_id) if item.kind == "warned"]
    assert len(warned) == 1
    assert warned[0].detail["remaining_s"] == 60


def test_expiry_fires_exactly_at_expires_at(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    clock = [ask.expires_at]
    scheduler = make_scheduler(store, clock)

    stats = scheduler.tick()

    assert stats.expired == 1
    stored = store.get(ask_id)
    assert stored is not None
    assert stored.status is AskStatus.EXPIRED
    assert stored.decided_at == ask.expires_at
    assert [item.kind for item in store.transitions_for(ask_id)][-1] == "expired"


def test_expiry_does_not_fire_one_microsecond_early(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    scheduler = make_scheduler(store, [ask.expires_at - timedelta(microseconds=1)])

    assert scheduler.tick().expired == 0
    stored = store.get(ask_id)
    assert stored is not None
    assert stored.status is AskStatus.PENDING


def test_scheduler_never_extends_the_deadline(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    before = store.get(ask_id)
    assert before is not None
    scheduler = make_scheduler(store, [before.expires_at + timedelta(hours=1)])

    scheduler.tick()

    after = store.get(ask_id)
    assert after is not None
    assert after.expires_at == before.expires_at
