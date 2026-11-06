"""Ask, Transition, Claim, and Delivery entities (M3 items 3.1, 3.2, 3.4)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import ClaimRecord, DeliveryRecord, StoreError, TransitionRecord
from agentinbox.store.memory import MemoryStore
from agentinbox.store.sqlite import SqliteStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


@pytest.fixture(params=["memory", "sqlite"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[MemoryStore | SqliteStore]:
    if request.param == "memory":
        driver: MemoryStore | SqliteStore = MemoryStore()
        yield driver
        return
    sqlite = SqliteStore(tmp_path / "home" / "inbox.db")
    try:
        yield sqlite
    finally:
        sqlite.close()


def ladder_config() -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300, warn_seconds=60, ladder=("tier-1", "on-call")
            )
        }
    )


def test_ask_round_trips_scheduling_fields(store) -> None:  # type: ignore[no-untyped-def]
    result = ingest(
        payload(),
        store=store,
        config=ladder_config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    loaded = store.get(result.ask.ask_id)
    assert loaded is not None
    assert loaded.warn_at == result.ask.expires_at - timedelta(seconds=60)
    assert loaded.escalate_at is None
    assert loaded.tier == "tier-1"
    assert loaded.created_at == NOW
    assert loaded.expires_at == result.ask.expires_at


def test_transitions_are_append_only_and_ordered(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = ingest(
        payload(),
        store=store,
        config=ladder_config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id
    for index in range(3):
        current = store.get(ask_id)
        assert current is not None
        store.append_event(
            TransitionRecord(
                ask_id=ask_id,
                at=NOW,
                kind=f"observation-{index}",
                to_status=current.status,
            )
        )

    transitions = store.transitions_for(ask_id)

    assert [item.seq for item in transitions] == [1, 2, 3, 4]
    assert [item.kind for item in transitions] == [
        "created",
        "observation-0",
        "observation-1",
        "observation-2",
    ]
    assert not hasattr(store, "update_transition")


def test_delivery_accounting(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = ingest(
        payload(),
        store=store,
        config=ladder_config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id
    delivery = DeliveryRecord(
        delivery_id="delivery_1",
        ask_id=ask_id,
        channel="terminal",
        attempt=1,
        status="delivered",
        at=NOW,
        target="alice",
    )
    store.record_delivery(delivery)

    assert store.list_deliveries(ask_id) == [delivery]
    with pytest.raises(StoreError):
        store.record_delivery(delivery)


def test_claim_state_is_derived() -> None:
    base = ClaimRecord(
        claim_id="claim_1",
        ask_id="ask_1",
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
    )

    assert base.state(NOW) == "issued"
    assert base.state(NOW + timedelta(minutes=2)) == "expired"
    assert replace(base, consumed_at=NOW).state(NOW) == "used"
    assert replace(base, revoked_at=NOW).state(NOW) == "revoked"
