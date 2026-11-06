"""Timeout = deny: the security property (M4 item 4.2)."""

from __future__ import annotations

from datetime import timedelta

from tests.ask.conftest import NOW, config, payload

from agentinbox.ingest import ingest
from agentinbox.resolve import resolve
from agentinbox.scheduler import Scheduler
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity


def test_expiry_resolves_deny_with_timeout_and_rescope(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id
    ask = store.get(ask_id)
    assert ask is not None
    scheduler = Scheduler(store, now=lambda: ask.expires_at)

    scheduler.tick()
    result = resolve(store, ask_id, now=ask.expires_at)

    assert result.status == "deny"
    assert result.reason_code == "human_gate_timeout"
    assert result.retryable is False
    assert result.rescope_hint is not None
    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]


def test_zero_allow_counter_survives_every_expiry(store) -> None:  # type: ignore[no-untyped-def]
    scheduler = Scheduler(store, now=lambda: NOW + timedelta(minutes=10))
    for index in range(5):
        ingest(
            payload(arguments={"index": index}),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )

    scheduler.tick()

    assert scheduler.allows_on_expiry == 0
    assert scheduler.expired_total == 5


def test_expired_ask_cannot_be_approved_afterwards(store) -> None:  # type: ignore[no-untyped-def]
    import pytest

    from agentinbox.lifecycle import IllegalTransition, transition

    ask_id = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id
    ask = store.get(ask_id)
    assert ask is not None
    Scheduler(store, now=lambda: ask.expires_at).tick()

    with pytest.raises(IllegalTransition):
        transition(store, ask_id, AskStatus.APPROVED, kind="answer", at=ask.expires_at)

    assert store.get(ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]
