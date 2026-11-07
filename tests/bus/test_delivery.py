"""Delivery wiring: every attempt is a record + event; resolved asks are no-ops (M9 item 9.6)."""

from __future__ import annotations

from typing import Any

from agentinbox.bus.base import JobKind, new_job
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.channels.base import ChannelError
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


class Channel:
    def __init__(self, name: str = "recording", *, fail: bool = False) -> None:
        self.name = name
        self.fail = fail
        self.delivered: list[str] = []

    def deliver(self, ask: Any, card: Any) -> None:
        if self.fail:
            raise ChannelError(f"{self.name} is down")
        self.delivered.append(ask.ask_id)

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        del as_name
        return None


def config() -> Config:
    return Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})


def make_ask(store) -> object:  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def wiring(store, *channels: Channel, **kwargs: Any) -> DeliveryWiring:  # type: ignore[no-untyped-def]
    kwargs.setdefault("backoff", lambda _attempt: None)
    kwargs.setdefault("now", lambda: NOW)
    return DeliveryWiring(store, list(channels), **kwargs)


def test_successful_delivery_is_recorded_and_audited(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    channel = Channel("terminal")

    wiring(store, channel).handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

    assert channel.delivered == [ask.ask_id]
    records = store.list_deliveries(ask.ask_id)
    assert [(item.channel, item.attempt, item.status) for item in records] == [
        ("terminal", 1, "delivered")
    ]
    kinds = [item.kind for item in store.transitions_for(ask.ask_id)]
    assert "ask-delivered" in kinds


def test_failed_delivery_retries_and_emits_events(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    channel = Channel("webhook", fail=True)

    wiring(store, channel).handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

    records = store.list_deliveries(ask.ask_id)
    assert [item.status for item in records] == ["failed", "failed", "failed"]
    assert [item.attempt for item in records] == [1, 2, 3]
    kinds = [item.kind for item in store.transitions_for(ask.ask_id)]
    assert kinds.count("delivery-failed") == 3
    # Failure never decides the ask.
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_failover_to_the_next_channel(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    down = Channel("webhook", fail=True)
    up = Channel("terminal")

    wiring(store, down, up).handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

    assert down.delivered == []
    assert up.delivered == [ask.ask_id]
    records = sorted(
        store.list_deliveries(ask.ask_id), key=lambda item: (item.channel, item.attempt)
    )
    assert [(item.channel, item.attempt, item.status) for item in records] == [
        ("terminal", 1, "delivered"),
        ("webhook", 1, "failed"),
        ("webhook", 2, "failed"),
        ("webhook", 3, "failed"),
    ]


def test_resolved_ask_is_a_logged_no_op(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    assert transition(
        store,
        ask.ask_id,
        AskStatus.APPROVED,
        kind="answered",
        at=NOW,
        principal="alice",
        channel="terminal",
    )
    channel = Channel("terminal")

    wiring(store, channel).handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

    assert channel.delivered == []
    assert store.list_deliveries(ask.ask_id) == []
    skipped = [
        item
        for item in store.transitions_for(ask.ask_id)
        if item.kind == "delivery-skipped"
    ]
    assert len(skipped) == 1
    assert skipped[0].detail["reason"] == "not pending"
    assert store.get(ask.ask_id).status is AskStatus.APPROVED  # type: ignore[union-attr]


def test_delivery_errors_are_redacted(store) -> None:  # type: ignore[no-untyped-def]
    class LeakyChannel(Channel):
        def deliver(self, ask: Any, card: Any) -> None:
            raise OSError("https://user:tok-secret@db.example/x")

    ask = make_ask(store)
    wiring(store, LeakyChannel("webhook")).handle(
        new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW)
    )

    records = store.list_deliveries(ask.ask_id)
    assert records
    for record in records:
        assert "tok-secret" not in (record.error or "")
        assert "REDACTED" in (record.error or "")
    failed = [
        item for item in store.transitions_for(ask.ask_id) if item.kind == "delivery-failed"
    ]
    assert all("tok-secret" not in str(item.detail) for item in failed)


def test_unknown_ask_is_a_no_op(store) -> None:  # type: ignore[no-untyped-def]
    channel = Channel("terminal")
    wiring(store, channel).handle(new_job(JobKind.DELIVER, ask_id="ask-missing", now=NOW))
    assert channel.delivered == []


def test_digest_jobs_go_to_the_digest_handler(store) -> None:  # type: ignore[no-untyped-def]
    seen = []
    channel = Channel("terminal")
    wiring(store, channel, on_digest=seen.append).handle(
        new_job(JobKind.DIGEST, ask_id="ask-0", now=NOW, payload={"count": 200})
    )
    assert len(seen) == 1
    assert seen[0].payload["count"] == 200
    assert channel.delivered == []
