"""Crash-safe recovery + exactly-once firing (M4 item 4.3)."""

from __future__ import annotations

import threading
from datetime import timedelta

from tests.ask.conftest import NOW, config, payload

from agentinbox.ingest import ingest
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity


def make_ask(store) -> str:  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id


def test_recovery_fires_overdue_expiry_once_with_marker(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    # Simulate the process being down past the deadline: a brand-new scheduler boots late.
    restarted = Scheduler(store, now=lambda: NOW + timedelta(minutes=10))

    first = restarted.recover()
    second = restarted.recover()

    assert first.expired == 1
    assert second.expired == 0
    kinds = [item.kind for item in store.transitions_for(ask_id)]
    assert "scheduler-recovered" in kinds
    assert kinds.count("expired") == 1
    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]


def test_recovery_fires_a_missed_warning_once(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    restarted = Scheduler(store, now=lambda: NOW + timedelta(seconds=250))

    first = restarted.recover()
    second = restarted.recover()

    assert first.warned == 1
    assert second.warned == 0
    kinds = [item.kind for item in store.transitions_for(ask_id)]
    assert kinds.count("warned") == 1
    assert "scheduler-recovered" in kinds
    assert store.get(ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_concurrent_schedulers_expire_exactly_once(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    moment = ask.expires_at + timedelta(seconds=1)
    barriers = threading.Barrier(4)
    results: list[int] = []
    lock = threading.Lock()

    def run() -> None:
        scheduler = Scheduler(store, now=lambda: moment)
        barriers.wait()
        stats = scheduler.tick()
        with lock:
            results.append(stats.expired)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(results) == 1
    assert [
        item.kind for item in store.transitions_for(ask_id)
    ].count("expired") == 1


def test_adopted_pending_ask_is_recovered(store) -> None:  # type: ignore[no-untyped-def]
    # A CLI-created ask is just a pending row — no separate adoption path.
    ask_id = make_ask(store)
    ask = store.get(ask_id)
    assert ask is not None
    scheduler = Scheduler(store, now=lambda: ask.expires_at + timedelta(seconds=30))

    assert scheduler.recover().expired == 1
