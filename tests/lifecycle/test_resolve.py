"""resolve/1.0 read path, including derived expiry (M3 item 3.5)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.resolve import (
    REASON_ALLOW,
    REASON_DENIED,
    REASON_FLOOD,
    REASON_MISMATCH,
    REASON_PENDING,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    derived_status,
    resolve,
)
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload


def make_ask(store, *, command: str | None = None) -> str:  # type: ignore[no-untyped-def]
    body = payload(arguments={"command": command}) if command else payload()
    return ingest(
        body,
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
    assert {
        "ask_id",
        "status",
        "reason_code",
        "retryable",
        "retry_after",
        "rescope_hint",
        "answered_by",
        "action_identity",
    } <= set(result)


def test_reason_constants_match_the_frozen_registry() -> None:
    from agentinbox import reasons

    assert {
        REASON_ALLOW,
        REASON_DENIED,
        REASON_TIMEOUT,
        REASON_FLOOD,
        REASON_PENDING,
        REASON_UNKNOWN,
        REASON_MISMATCH,
    } == reasons.REASON_CODES


def test_every_terminal_state_maps_to_the_exact_code(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.reasons import (
        ALLOW_ASK_APPROVED,
        ASK_FLOOD_THROTTLED,
        DENY_ASK_DENIED,
        HUMAN_GATE_TIMEOUT,
    )

    for status, expected in (
        (AskStatus.APPROVED, ALLOW_ASK_APPROVED),
        (AskStatus.DENIED, DENY_ASK_DENIED),
        (AskStatus.CANCELLED, DENY_ASK_DENIED),
        (AskStatus.FLOOD_DENIED, ASK_FLOOD_THROTTLED),
        (AskStatus.EXPIRED, HUMAN_GATE_TIMEOUT),
    ):
        ask_id = make_ask(store, command=f"echo {status.value}")
        transition(store, ask_id, status, kind="answer", at=NOW)
        assert resolve(store, ask_id, now=NOW).reason_code == expected

    assert resolve(store, make_ask(store), now=NOW).reason_code == REASON_PENDING
    assert resolve(store, "ask_missing", now=NOW).reason_code == REASON_UNKNOWN


def test_a_different_action_identity_is_denied(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    stored = store.get(ask_id)
    assert stored is not None

    same = resolve(store, ask_id, now=NOW, action_identity=stored.action_identity)
    mismatch = resolve(store, ask_id, now=NOW, action_identity="sha256:" + "b" * 64)

    assert same.status == "pending"
    assert mismatch.status == "deny"
    assert mismatch.reason_code == REASON_MISMATCH
    assert mismatch.action_identity == stored.action_identity


def test_flood_denial_carries_retry_after(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.store import TransitionRecord

    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.FLOOD_DENIED, kind="flood", at=NOW)
    store.append_event(
        TransitionRecord(
            ask_id=ask_id,
            at=NOW,
            kind="flood-denied",
            to_status=AskStatus.FLOOD_DENIED,
            detail={"retry_after_s": 30},
        )
    )

    result = resolve(store, ask_id, now=NOW)

    assert result.reason_code == REASON_FLOOD
    assert result.retryable is True
    assert result.retry_after == 30


def test_expiry_is_not_retryable(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    result = resolve(store, ask_id, now=NOW + timedelta(minutes=10))
    assert result.retryable is False
    assert result.retry_after is None


def test_class_rescope_hint_and_deny_reason(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.config import ClassConfig, Config

    ask_id = make_ask(store)
    transition(
        store,
        ask_id,
        AskStatus.DENIED,
        kind="answer",
        at=NOW,
        principal="bob",
        channel="terminal",
        reason="target is too broad",
    )
    cfg = Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300, rescope_hint="use db:staging/customers"
            )
        }
    )

    result = resolve(store, ask_id, now=NOW, config=cfg)

    assert result.rescope_hint is not None
    assert "use db:staging/customers" in result.rescope_hint
    assert "target is too broad" in result.rescope_hint
    assert "not policy" in result.rescope_hint


def test_hints_are_capped_and_stripped() -> None:
    from agentinbox.hints import HINT_CAP, author_hint

    hint = author_hint(
        "line one\nline two\x00 " + "x" * 1000,
        action_class="irreversible",
        environment="production",
        reason="too broad",
    )
    assert len(hint) <= HINT_CAP
    assert "\n" not in hint
    assert "\x00" not in hint
    assert "not policy" in hint


def test_double_resolve_is_identical(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.APPROVED, kind="answer", at=NOW)

    first = resolve(store, ask_id, now=NOW).to_dict()
    second = resolve(store, ask_id, now=NOW).to_dict()

    assert first == second
