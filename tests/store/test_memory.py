"""Memory driver parity (M1 item 1.3).

Same seven semantics as SQLite, no disk — used by tests and embedded ephemeral callers. The
full conformance suite (1.4) runs against both; this file pins the driver's own edges.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from agentinbox.store import (
    AskRecord,
    AskStatus,
    ClaimRecord,
    StoreError,
    TransitionRecord,
)
from agentinbox.store.memory import MemoryStore

T0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def ask(index: int = 0, *, created_at: datetime = T0, identity: str | None = None) -> AskRecord:
    return AskRecord(
        ask_id=f"ask_{index:016x}",
        action_identity=identity or "sha256:" + "a" * 64,
        session_id="sess_1",
        agent_id="agent://ops/1",
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
        payload={"tool": "shell"},
    )


def move(record: AskRecord, kind: str, to: AskStatus) -> TransitionRecord:
    return TransitionRecord(ask_id=record.ask_id, at=record.created_at, kind=kind, to_status=to)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


def test_create_and_get(store: MemoryStore) -> None:
    created = store.create_or_get_by_identity(ask())

    assert created.created is True
    loaded = store.get(ask().ask_id)
    assert loaded is not None
    assert loaded.payload == {"tool": "shell"}
    assert store.get("ask_nope") is None


def test_dedupe_window(store: MemoryStore) -> None:
    store.create_or_get_by_identity(ask())

    duplicate = store.create_or_get_by_identity(ask(1))
    later = store.create_or_get_by_identity(ask(2, created_at=T0 + timedelta(hours=1)))

    assert duplicate.created is False
    assert duplicate.ask.ask_id == ask().ask_id
    assert later.created is True
    assert later.ask.ask_id == ask(2).ask_id
    assert [item.kind for item in store.export_session("sess_1").transitions] == [
        "created",
        "deduplicated",
        "created",
    ]


def test_cas_race_single_winner(store: MemoryStore) -> None:
    record = ask()
    store.create_or_get_by_identity(record)
    barrier = threading.Barrier(6)
    wins: list[bool] = []
    lock = threading.Lock()

    def race() -> None:
        barrier.wait()
        won = store.cas_status(
            record.ask_id,
            expected=AskStatus.PENDING,
            new=AskStatus.APPROVED,
            transition=move(record, "answer", AskStatus.APPROVED),
        )
        with lock:
            wins.append(won)

    threads = [threading.Thread(target=race) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert wins.count(True) == 1
    loaded = store.get(record.ask_id)
    assert loaded is not None
    assert loaded.status is AskStatus.APPROVED


def test_claim_single_use_and_expiry(store: MemoryStore) -> None:
    record = ask()
    store.create_or_get_by_identity(record)
    claim = ClaimRecord(
        claim_id="claim_1",
        ask_id=record.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(minutes=1),
    )
    store.issue_claim(claim)

    assert store.consume_claim("claim_1", ask_id=record.ask_id, at=T0) is True
    assert store.consume_claim("claim_1", ask_id=record.ask_id, at=T0) is False

    late = ClaimRecord(
        claim_id="claim_2",
        ask_id=record.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0,
    )
    store.issue_claim(late)
    assert (
        store.consume_claim("claim_2", ask_id=record.ask_id, at=T0 + timedelta(seconds=1))
        is False
    )


def test_duplicate_claim_rejected(store: MemoryStore) -> None:
    record = ask()
    store.create_or_get_by_identity(record)
    claim = ClaimRecord(
        claim_id="claim_dup",
        ask_id=record.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(minutes=1),
    )
    store.issue_claim(claim)

    with pytest.raises(StoreError):
        store.issue_claim(claim)


def test_cas_wrong_transition_ask_rejected(store: MemoryStore) -> None:
    record = ask()
    store.create_or_get_by_identity(record)
    foreign = TransitionRecord(
        ask_id="ask_other", at=T0, kind="answer", to_status=AskStatus.DENIED
    )

    with pytest.raises(StoreError):
        store.cas_status(
            record.ask_id,
            expected=AskStatus.PENDING,
            new=AskStatus.DENIED,
            transition=foreign,
        )


def test_gapless_audit_seq_under_threads(store: MemoryStore) -> None:
    record = ask()
    store.create_or_get_by_identity(record)
    barrier = threading.Barrier(6)

    def append(index: int) -> None:
        barrier.wait()
        store.append_event(
            TransitionRecord(
                ask_id=record.ask_id,
                at=T0,
                kind=f"event-{index}",
                to_status=AskStatus.PENDING,
            )
        )

    threads = [threading.Thread(target=append, args=(index,)) for index in range(30)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    entries = store.audit_entries()
    assert [entry.seq for entry in entries] == list(range(1, len(entries) + 1))
    store.verify_chain()


def test_pending_ordering_and_resolution(store: MemoryStore) -> None:
    early = ask(1)
    overdue = ask(2, created_at=T0 - timedelta(hours=1), identity="sha256:" + "b" * 64)
    store.create_or_get_by_identity(early)
    store.create_or_get_by_identity(overdue)

    assert [item.ask_id for item in store.list_pending(now=T0)] == [
        overdue.ask_id,
        early.ask_id,
    ]

    store.cas_status(
        early.ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.CANCELLED,
        transition=move(early, "cancelled", AskStatus.CANCELLED),
    )
    assert [item.ask_id for item in store.list_pending(now=T0)] == [overdue.ask_id]


def test_close_is_idempotent(store: MemoryStore) -> None:
    store.close()
    store.close()
