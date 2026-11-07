"""Duplicate coalescing is the first flood defense (M12 item 12.1)."""

from __future__ import annotations

from agentinbox.bus import InProcBus, JobKind
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def config() -> Config:
    return Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})


def test_three_retries_create_one_ask_and_one_delivery(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    results = [
        ingest(
            payload(),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
            bus=bus,
        )
        for _ in range(3)
    ]

    assert [result.created for result in results] == [True, False, False]
    assert len(results[0].ask.ask_id) > 0
    assert len({result.ask.ask_id for result in results}) == 1
    assert store.get(results[0].ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]

    jobs = []
    assert bus.consume(jobs.append) == 1
    assert jobs[0].kind is JobKind.DELIVER
    assert jobs[0].ask_id == results[0].ask.ask_id

    kinds = [item.kind for item in store.transitions_for(results[0].ask.ask_id)]
    assert kinds.count("created") == 1
    assert kinds.count("deduplicated") == 2


def test_distinct_action_identities_are_not_coalesced(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    first = ingest(
        payload(arguments={"command": "psql -c 'select 1'"}),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
        bus=bus,
    )
    second = ingest(
        payload(arguments={"command": "psql -c 'select 2'"}),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
        bus=bus,
    )

    assert first.ask.ask_id != second.ask.ask_id
    jobs = []
    assert bus.consume(jobs.append) == 2
