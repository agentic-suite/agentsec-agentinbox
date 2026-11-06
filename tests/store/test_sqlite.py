"""SQLite reference driver semantics (M1 item 1.2)."""

from __future__ import annotations

import stat
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agentinbox.store import (
    AskRecord,
    AskStatus,
    AuditEntry,
    ChainHashMismatch,
    ClaimRecord,
    StoreError,
    TransitionRecord,
    chain_hash,
    parse_iso,
    payload_digest,
    to_iso,
)
from agentinbox.store.sqlite import SqliteStore

T0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def make_store(tmp_path: Path) -> SqliteStore:
    return SqliteStore(tmp_path / "home" / "inbox.db")


def make_ask(
    index: int = 0, *, created_at: datetime = T0, identity: str | None = None
) -> AskRecord:
    return AskRecord(
        ask_id=f"ask_{index:016x}",
        action_identity=identity or "sha256:" + "a" * 64,
        session_id="sess_1",
        agent_id="agent://ops/1",
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
        payload={"contract": "ask/1.0", "tool": "shell"},
    )


def transition(
    ask: AskRecord, kind: str = "created", to: AskStatus = AskStatus.PENDING
) -> TransitionRecord:
    return TransitionRecord(
        ask_id=ask.ask_id, at=ask.created_at, kind=kind, to_status=to, detail={"why": kind}
    )


@pytest.fixture
def store(tmp_path: Path):
    store = make_store(tmp_path)
    yield store
    store.close()


def test_create_and_get_round_trip(store: SqliteStore) -> None:
    ask = make_ask()

    result = store.create_or_get_by_identity(ask)

    assert result.created is True
    loaded = store.get(ask.ask_id)
    assert loaded is not None
    assert loaded.action_identity == ask.action_identity
    assert loaded.payload == ask.payload
    assert loaded.status is AskStatus.PENDING
    assert loaded.created_at == ask.created_at


def test_duplicate_inside_window_returns_one_ask(store: SqliteStore) -> None:
    ask = make_ask()

    first = store.create_or_get_by_identity(ask)
    duplicate = store.create_or_get_by_identity(make_ask(1))

    assert first.created is True
    assert duplicate.created is False
    assert duplicate.ask.ask_id == first.ask.ask_id
    kinds = [item.kind for item in store.export_session("sess_1").transitions]
    assert kinds == ["created", "deduplicated"]


def test_duplicate_outside_window_is_a_new_ask(store: SqliteStore) -> None:
    store.create_or_get_by_identity(make_ask())

    later = store.create_or_get_by_identity(
        make_ask(2, created_at=T0 + timedelta(hours=1)), dedupe_window_s=900
    )

    assert later.created is True
    assert later.ask.ask_id != make_ask().ask_id


def test_cas_race_has_exactly_one_winner(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    barrier = threading.Barrier(8)
    wins: list[bool] = []
    lock = threading.Lock()

    def answer() -> None:
        barrier.wait()
        won = store.cas_status(
            ask.ask_id,
            expected=AskStatus.PENDING,
            new=AskStatus.APPROVED,
            transition=transition(ask, "answer", AskStatus.APPROVED),
        )
        with lock:
            wins.append(won)

    threads = [threading.Thread(target=answer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert wins.count(True) == 1
    loaded = store.get(ask.ask_id)
    assert loaded is not None
    assert loaded.status is AskStatus.APPROVED
    assert loaded.decided_at is not None


def test_cas_with_wrong_expected_writes_nothing(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    before = store.export_session("sess_1")

    won = store.cas_status(
        ask.ask_id,
        expected=AskStatus.DENIED,
        new=AskStatus.APPROVED,
        transition=transition(ask, "answer", AskStatus.APPROVED),
    )

    assert won is False
    assert store.export_session("sess_1").transitions == before.transitions


def test_claim_is_single_use(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    claim = ClaimRecord(
        claim_id="claim_1",
        ask_id=ask.ask_id,
        channel="terminal",
        tier="tier-1",
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(minutes=5),
    )
    store.issue_claim(claim)

    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=T0) is True
    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=T0) is False
    assert store.consume_claim(claim.claim_id, ask_id="ask_other", at=T0) is False


def test_expired_claim_cannot_be_consumed(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    claim = ClaimRecord(
        claim_id="claim_expired",
        ask_id=ask.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(seconds=1),
    )
    store.issue_claim(claim)

    late = T0 + timedelta(seconds=2)
    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=late) is False


def test_duplicate_claim_id_is_rejected(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    claim = ClaimRecord(
        claim_id="claim_dup",
        ask_id=ask.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(minutes=1),
    )
    store.issue_claim(claim)

    with pytest.raises(StoreError):
        store.issue_claim(claim)


def test_audit_sequence_is_gapless_under_concurrency(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    barrier = threading.Barrier(8)
    errors: list[BaseException] = []

    def append(index: int) -> None:
        barrier.wait()
        try:
            store.append_event(transition(ask, f"event-{index}"))
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=append, args=(index,)) for index in range(40)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    entries = store.audit_entries()
    assert [entry.seq for entry in entries] == list(range(1, len(entries) + 1))
    previous = "0" * 64
    for entry in entries:
        assert entry.prev_hash == previous
        previous = entry.entry_hash


def test_audit_hash_recomputes(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    entry = store.append_event(transition(ask, "custom"))

    assert entry.entry_hash == chain_hash(
        prev_hash=entry.prev_hash,
        seq=entry.seq,
        kind=entry.kind,
        ref_id=entry.ref_id,
        at=to_iso(entry.at),
        digest=entry.payload_digest,
    )


def test_list_pending_includes_overdue_and_orders_by_expiry(store: SqliteStore) -> None:
    early = make_ask(1, created_at=T0)
    overdue = make_ask(2, created_at=T0 - timedelta(hours=1), identity="sha256:" + "b" * 64)
    store.create_or_get_by_identity(early)
    store.create_or_get_by_identity(overdue)

    pending = store.list_pending(now=T0)

    assert [item.ask_id for item in pending] == [overdue.ask_id, early.ask_id]


def test_pending_excludes_resolved(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    store.cas_status(
        ask.ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.DENIED,
        transition=transition(ask, "answer", AskStatus.DENIED),
    )

    assert store.list_pending(now=T0) == []


def test_export_session_returns_asks_transitions_and_claims(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)
    store.issue_claim(
        ClaimRecord(
            claim_id="claim_export",
            ask_id=ask.ask_id,
            channel="terminal",
            tier=None,
            secret_hash="h" * 64,
            issued_at=T0,
            expires_at=T0 + timedelta(minutes=1),
        )
    )

    export = store.export_session("sess_1")

    assert [item.ask_id for item in export.asks] == [ask.ask_id]
    assert [item.kind for item in export.transitions] == ["created"]
    assert [item.claim_id for item in export.claims] == ["claim_export"]


def test_store_file_and_directory_permissions(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.close()
    home = tmp_path / "home"

    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE((home / "inbox.db").stat().st_mode) == 0o600


def test_reopen_preserves_state_and_continues_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    first = SqliteStore(path)
    ask = make_ask()
    first.create_or_get_by_identity(ask)
    first.append_event(transition(ask, "note"))
    last_entry = first.audit_entries()[-1]
    first.close()

    second = SqliteStore(path)
    try:
        reloaded = second.get(ask.ask_id)
        assert reloaded is not None
        assert reloaded.action_identity == ask.action_identity
        assert [item.ask_id for item in second.list_pending(now=T0)] == [ask.ask_id]
        appended = second.append_event(transition(ask, "after-restart"))
        assert appended.seq == last_entry.seq + 1
        assert appended.prev_hash == last_entry.entry_hash
    finally:
        second.close()


def test_missing_ask_is_none(store: SqliteStore) -> None:
    assert store.get("ask_missing") is None


def test_transition_seq_is_per_ask(store: SqliteStore) -> None:
    one = make_ask(1)
    two = make_ask(2, identity="sha256:" + "b" * 64)
    store.create_or_get_by_identity(one)
    store.create_or_get_by_identity(two)
    store.append_event(transition(one, "second"))

    export = store.export_session("sess_1")
    sequences = [(item.ask_id, item.seq) for item in export.transitions]

    assert (one.ask_id, 1) in sequences
    assert (one.ask_id, 2) in sequences
    assert (two.ask_id, 1) in sequences


def test_audit_entry_time_is_utc(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)

    entry: AuditEntry = store.audit_entries()[-1]

    assert entry.at.tzinfo is not None
    assert parse_iso(to_iso(entry.at)) == entry.at
    assert entry.payload_digest == payload_digest({"why": "created"})


def test_chain_verification_helper_detects_tampering(store: SqliteStore) -> None:
    ask = make_ask()
    store.create_or_get_by_identity(ask)

    store.verify_chain()
    store._conn.execute("UPDATE audit SET entry_hash = ? WHERE seq = 1", ("f" * 64,))
    with pytest.raises(ChainHashMismatch):
        store.verify_chain()
