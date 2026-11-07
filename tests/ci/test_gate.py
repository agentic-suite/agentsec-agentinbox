"""``gate``: the exit-code matrix, waiting, cancellation, and retry idempotency (M10)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from agentinbox.config import ClassConfig, Config
from agentinbox.exit_codes import ExitCode
from agentinbox.gate import gate
from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


class Clock:
    def __init__(self, start: datetime = NOW) -> None:
        self.moment = start

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, seconds: float) -> None:
        self.moment += timedelta(seconds=seconds)


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


def resolve_to(store, ask_id: str, status: AskStatus, *, at: datetime = NOW) -> None:
    assert transition(
        store,
        ask_id,
        status,
        kind="answered",
        at=at,
        principal="alice",
        channel="terminal",
    )


def test_approved_maps_to_zero(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.APPROVED)
    assert gate(store, ask.ask_id, now=Clock()).code is ExitCode.APPROVED


def test_denied_maps_to_two(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.DENIED)
    assert gate(store, ask.ask_id, now=Clock()).code is ExitCode.DENIED


def test_cancelled_maps_to_denied(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.CANCELLED)
    assert gate(store, ask.ask_id, now=Clock()).code is ExitCode.DENIED


def test_flood_denied_maps_to_denied(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.FLOOD_DENIED)
    assert gate(store, ask.ask_id, now=Clock()).code is ExitCode.DENIED


def test_expired_maps_to_three(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    clock = Clock(NOW + timedelta(seconds=301))
    assert gate(store, ask.ask_id, now=clock).code is ExitCode.EXPIRED


def test_pending_without_wait_maps_to_five(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    assert gate(store, ask.ask_id, now=Clock()).code is ExitCode.PENDING


def test_unknown_ask_fails_closed(store) -> None:  # type: ignore[no-untyped-def]
    assert gate(store, "ask_missing", now=Clock()).code is ExitCode.UNAVAILABLE


def test_wait_returns_the_decision(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    clock = Clock()
    slept = {"count": 0}

    def sleep(_seconds: float) -> None:
        slept["count"] += 1
        clock.advance(1)
        resolve_to(store, ask.ask_id, AskStatus.APPROVED, at=clock())

    result = gate(
        store, ask.ask_id, now=clock, wait=True, timeout=10, sleep=sleep
    )

    assert result.code is ExitCode.APPROVED
    assert slept["count"] == 1


def test_wait_budget_lapse_is_three_and_does_not_mutate(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    clock = Clock()

    result = gate(
        store,
        ask.ask_id,
        now=clock,
        wait=True,
        timeout=3,
        sleep=lambda seconds: clock.advance(seconds),
    )

    assert result.code is ExitCode.EXPIRED
    assert "budget" in result.reason
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_wait_uses_the_ask_ttl_when_no_budget_is_given(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    clock = Clock()

    result = gate(
        store,
        ask.ask_id,
        now=clock,
        wait=True,
        sleep=lambda seconds: clock.advance(seconds),
    )

    assert result.code is ExitCode.EXPIRED
    assert store.get(ask.ask_id).expires_at <= clock()  # type: ignore[union-attr]


def test_cancel_transitions_a_pending_ask(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    cancel = threading.Event()
    cancel.set()

    result = gate(store, ask.ask_id, now=Clock(), wait=True, cancel=cancel)

    assert result.code is ExitCode.DENIED
    assert store.get(ask.ask_id).status is AskStatus.CANCELLED  # type: ignore[union-attr]
    kinds = [item.kind for item in store.transitions_for(ask.ask_id)]
    assert "gate-cancelled" in kinds


def test_cancel_never_overrides_a_real_decision(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.APPROVED)
    before = len(store.transitions_for(ask.ask_id))
    cancel = threading.Event()
    cancel.set()

    result = gate(store, ask.ask_id, now=Clock(), wait=True, cancel=cancel)

    assert result.code is ExitCode.APPROVED
    assert store.get(ask.ask_id).status is AskStatus.APPROVED  # type: ignore[union-attr]
    assert len(store.transitions_for(ask.ask_id)) == before


def test_retry_is_idempotent_and_writes_nothing(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    resolve_to(store, ask.ask_id, AskStatus.DENIED)
    before = len(store.transitions_for(ask.ask_id))

    first = gate(store, ask.ask_id, now=Clock())
    second = gate(store, ask.ask_id, now=Clock())

    assert first.code is second.code is ExitCode.DENIED
    assert len(store.transitions_for(ask.ask_id)) == before
    assert store.list_deliveries(ask.ask_id) == []
