"""resolve/1.0 read path, including derived expiry (M3 item 3.5)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.resolve import (
    REASON_ALLOW,
    REASON_DENIED,
    REASON_FLOOD,
    REASON_PENDING,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    derived_status,
    resolve,
)
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload


def make_ask(store) -> str:  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id


def test_pending_read(store) -> None:  # type: ignore[no-untyped-def]
    result = resolve(store, make_ask(store), now=NOW)

    assert result.status == "pending"
    assert result.reason_code == REASON_PENDING
    assert result.retryable is True


def test_expiry_is_derived_on_read_without_a_write(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)

    result = resolve(store, ask_id, now=NOW + timedelta(minutes=10))

    assert result.status == "deny"
    assert result.reason_code == REASON_TIMEOUT
    assert result.retryable is False
    assert result.rescope_hint is not None
    stored = store.get(ask_id)
    assert stored is not None
    assert stored.status is AskStatus.PENDING, "a read must never write the expiry"


def test_expiry_boundary_is_inclusive(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    stored = store.get(ask_id)
    assert stored is not None

    assert derived_status(stored, now=stored.expires_at) is AskStatus.EXPIRED


def test_approved_read(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(
        store,
        ask_id,
        AskStatus.APPROVED,
        kind="answer",
        at=NOW,
        principal="alice",
        channel="terminal",
    )

    result = resolve(store, ask_id, now=NOW)

    assert result.status == "allow"
    assert result.reason_code == REASON_ALLOW
    assert result.answered_by == "alice"


def test_denied_read(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(
        store,
        ask_id,
        AskStatus.DENIED,
        kind="answer",
        at=NOW,
        principal="bob",
        channel="desktop",
    )

    result = resolve(store, ask_id, now=NOW)

    assert result.status == "deny"
    assert result.reason_code == REASON_DENIED
    assert result.answered_by == "bob"


def test_stored_expiry_read(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.EXPIRED, kind="expired", at=NOW)

    result = resolve(store, ask_id, now=NOW)

    assert result.status == "deny"
    assert result.reason_code == REASON_TIMEOUT


def test_cancelled_read(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.CANCELLED, kind="cancelled", at=NOW)

    result = resolve(store, ask_id, now=NOW)

    assert result.status == "deny"
    assert result.reason_code == REASON_DENIED
    assert "cancelled" in result.explanation


def test_flood_denied_read(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.FLOOD_DENIED, kind="flood", at=NOW)

    result = resolve(store, ask_id, now=NOW)

    assert result.status == "deny"
    assert result.reason_code == REASON_FLOOD


def test_unknown_ask_read(store) -> None:  # type: ignore[no-untyped-def]
    result = resolve(store, "ask_missing", now=NOW)

    assert result.status == "deny"
    assert result.reason_code == REASON_UNKNOWN
    assert result.action_identity is None


def test_resolve_dict_shape(store) -> None:  # type: ignore[no-untyped-def]
    result = resolve(store, make_ask(store), now=NOW).to_dict()

    assert result["contract"] == "resolve/1.0"
    assert {"ask_id", "status", "reason_code", "retryable", "answered_by"} <= set(result)
