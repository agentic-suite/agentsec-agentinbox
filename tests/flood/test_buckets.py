"""Token buckets: burst, refill, per-key isolation, class overrides (M12 item 12.2)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.config import ClassConfig, Config, ThrottleConfig
from agentinbox.flood import FloodGuard, TokenBucket
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def config(*, burst: int | None = None, rate: int | None = None) -> Config:
    ask_class = ClassConfig(
        ttl_seconds=300,
        flood_burst=burst,
        flood_rate_per_min=rate,
    )
    return Config(classes={"irreversible": ask_class})


def ingest_one(  # type: ignore[no-untyped-def]
    store,
    guard,
    *,
    index: int,
    agent: str = "agent://ops-agent/7f31",
    principal=None,
    session: str = "sess_burst",
):
    producer = (
        ProducerIdentity(adapter="agentpolicy", authenticated=True, principal=principal)
        if principal
        else ProducerIdentity.unauthenticated()
    )
    return ingest(
        payload(
            arguments={"command": f"echo {index}"},
            agent_id=agent,
            session_id=session,
        ),
        store=store,
        config=config(),
        producer=producer,
        now=NOW,
        flood_guard=guard,
    )


def test_bucket_trips_at_capacity_and_refills(store) -> None:  # type: ignore[no-untyped-def]
    bucket = TokenBucket(capacity=3, rate_per_second=1 / 60)
    assert all(bucket.take(NOW) for _ in range(3))
    assert bucket.take(NOW) is False

    assert bucket.take(NOW + timedelta(seconds=60)) is True
    assert bucket.take(NOW + timedelta(seconds=60)) is False


def test_the_twenty_first_ask_in_a_burst_is_denied(store) -> None:  # type: ignore[no-untyped-def]
    guard = FloodGuard(store, config(), now=lambda: NOW)

    results = [ingest_one(store, guard, index=index) for index in range(21)]

    assert [result.ask.status for result in results[:20]] == [AskStatus.PENDING] * 20
    assert results[20].ask.status is AskStatus.FLOOD_DENIED


def test_buckets_are_isolated_per_agent(store) -> None:  # type: ignore[no-untyped-def]
    guard = FloodGuard(store, config(), now=lambda: NOW)

    for index in range(20):
        assert ingest_one(store, guard, index=index).ask.status is AskStatus.PENDING
    assert ingest_one(store, guard, index=99).ask.status is AskStatus.FLOOD_DENIED

    other = ingest_one(store, guard, index=100, agent="agent://other/1")
    assert other.ask.status is AskStatus.PENDING


def test_producer_uid_is_part_of_the_bucket_key(store) -> None:  # type: ignore[no-untyped-def]
    guard = FloodGuard(store, config(), now=lambda: NOW)

    for index in range(20):
        assert ingest_one(store, guard, index=index).ask.status is AskStatus.PENDING
    assert ingest_one(store, guard, index=21).ask.status is AskStatus.FLOOD_DENIED

    # A different authenticated producer uid gets its own bucket.
    assert (
        ingest_one(store, guard, index=22, principal="uid:1001").ask.status
        is AskStatus.PENDING
    )


def test_a_class_can_lower_the_burst_threshold(store) -> None:  # type: ignore[no-untyped-def]
    tight = config(burst=2, rate=1)
    guard = FloodGuard(store, tight, now=lambda: NOW)

    first = ingest_one(store, guard, index=1)
    second = ingest_one(store, guard, index=2)
    third = ingest_one(store, guard, index=3)

    assert first.ask.status is AskStatus.PENDING
    assert second.ask.status is AskStatus.PENDING
    assert third.ask.status is AskStatus.FLOOD_DENIED


def test_global_throttle_is_used_without_a_class_override(store) -> None:  # type: ignore[no-untyped-def]
    throttled = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        throttle=ThrottleConfig(per_agent_burst=1, per_agent_rate_per_min=1),
    )
    guard = FloodGuard(store, throttled, now=lambda: NOW)

    assert ingest_one(store, guard, index=1).ask.status is AskStatus.PENDING
    assert ingest_one(store, guard, index=2).ask.status is AskStatus.FLOOD_DENIED
