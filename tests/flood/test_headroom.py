"""Legitimate burst headroom survives alongside SC-13 (M12 item 12.5)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.bus import InProcBus
from agentinbox.config import ClassConfig, Config
from agentinbox.flood import FloodGuard
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def config() -> Config:
    return Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})


def ask(store, guard, bus, *, index: int, agent: str, now):  # type: ignore[no-untyped-def]
    return ingest(
        payload(
            arguments={"command": f"migrate step {index}"},
            agent_id=agent,
            session_id=f"sess_{agent}",
        ),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=now,
        flood_guard=guard,
        bus=bus,
    )


def test_a_twenty_action_migration_is_fully_answerable(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)

    results = [
        ask(
            store,
            guard,
            bus,
            index=index,
            agent="agent://migration/1",
            now=NOW + timedelta(milliseconds=100 * index),
        )
        for index in range(20)
    ]

    assert [result.ask.status for result in results] == [AskStatus.PENDING] * 20
    assert store.get_flood("flood_missing") is None


def test_the_migration_survives_while_the_flood_is_denied(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)

    migration = [
        ask(
            store,
            guard,
            bus,
            index=index,
            agent="agent://migration/1",
            now=NOW + timedelta(milliseconds=100 * index),
        )
        for index in range(20)
    ]
    flood = [
        ask(
            store,
            guard,
            bus,
            index=index + 1000,
            agent="agent://attacker/1",
            now=NOW + timedelta(seconds=2, milliseconds=10 * index),
        )
        for index in range(200)
    ]

    assert all(result.ask.status is AskStatus.PENDING for result in migration)
    assert sum(result.ask.status is AskStatus.FLOOD_DENIED for result in flood) == 180
