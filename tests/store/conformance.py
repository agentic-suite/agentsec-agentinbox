"""The AskStore conformance suite (M1 item 1.4) — the admission gate for every driver.

Every function here is a semantic requirement from PRD 16 §D. A driver that fails any of them
is **not** an AskStore, regardless of what it declares (E11: refused at load, never at runtime).
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from agentinbox.store import (
    AskRecord,
    AskStatus,
    AuditEntry,
    ClaimRecord,
    StoreError,
    TransitionRecord,
    chain_hash,
    require_capability,
    to_iso,
)

T0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)
WINDOW = 900


def sample_ask(index: int = 0, *, created_at: datetime = T0) -> AskRecord:
    return AskRecord(
        ask_id=f"ask_{index:016x}",
        action_identity="sha256:" + format(index, "064x"),
        session_id=f"sess_{index}",
        agent_id="agent://conformance/1",
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
        payload={"contract": "ask/1.0", "index": index},
    )


def transition(
    ask: AskRecord, kind: str, to: AskStatus = AskStatus.PENDING
) -> TransitionRecord:
    return TransitionRecord(ask_id=ask.ask_id, at=ask.created_at, kind=kind, to_status=to)


# --------------------------------------------------------------------------- 1. idempotent create


def check_idempotent_create(store) -> None:  # type: ignore[no-untyped-def]
    first = store.create_or_get_by_identity(sample_ask())
    second = store.create_or_get_by_identity(sample_ask())
    third = store.create_or_get_by_identity(sample_ask())

    assert first.created is True
    assert second.created is False
    assert third.created is False
    assert second.ask.ask_id == first.ask.ask_id == third.ask.ask_id

    export = store.export_session("sess_0")
    assert len(export.asks) == 1
    assert [item.kind for item in export.transitions] == [
        "created",
        "deduplicated",
        "deduplicated",
    ]


def check_dedupe_window_expires(store) -> None:  # type: ignore[no-untyped-def]
    store.create_or_get_by_identity(sample_ask())

    later = sample_ask(1, created_at=T0 + timedelta(seconds=WINDOW + 1))
    result = store.create_or_get_by_identity(later, dedupe_window_s=WINDOW)

    assert result.created is True


# --------------------------------------------------------------------------- 2. CAS


def check_cas_single_winner(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    barrier = threading.Barrier(8)
    wins: list[bool] = []
    lock = threading.Lock()

    def race() -> None:
        barrier.wait()
        won = store.cas_status(
            ask.ask_id,
            expected=AskStatus.PENDING,
            new=AskStatus.APPROVED,
            transition=transition(ask, "answer", AskStatus.APPROVED),
        )
        with lock:
            wins.append(won)

    threads = [threading.Thread(target=race) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert wins.count(True) == 1
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.APPROVED
    assert stored.decided_at is not None


# --------------------------------------------------------------------------- 3. claims


def check_claim_single_use(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    claim = ClaimRecord(
        claim_id=f"claim_{ask.ask_id}",
        ask_id=ask.ask_id,
        channel="terminal",
        tier="tier-1",
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0 + timedelta(minutes=1),
    )
    store.issue_claim(claim)

    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=T0) is True
    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=T0) is False
    assert (
        store.consume_claim(claim.claim_id, ask_id="ask_someone_else", at=T0) is False
    )


def check_expired_claim_rejected(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    claim = ClaimRecord(
        claim_id=f"claim_exp_{ask.ask_id}",
        ask_id=ask.ask_id,
        channel="terminal",
        tier=None,
        secret_hash="h" * 64,
        issued_at=T0,
        expires_at=T0,
    )
    store.issue_claim(claim)

    assert store.consume_claim(claim.claim_id, ask_id=ask.ask_id, at=T0) is False


# --------------------------------------------------------------------------- 4. audit seq


def check_gapless_audit_seq(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    barrier = threading.Barrier(6)
    entries: list[AuditEntry] = []
    lock = threading.Lock()

    def append(index: int) -> None:
        barrier.wait()
        entry = store.append_event(transition(ask, f"event-{index}"))
        with lock:
            entries.append(entry)

    threads = [threading.Thread(target=append, args=(index,)) for index in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    ordered = sorted(entries, key=lambda entry: entry.seq)
    seqs = [entry.seq for entry in ordered]
    assert seqs == list(range(seqs[0], seqs[0] + len(seqs)))

    for earlier, later in itertools.pairwise(ordered):
        assert later.prev_hash == earlier.entry_hash
    for entry in ordered:
        assert entry.entry_hash == chain_hash(
            prev_hash=entry.prev_hash,
            seq=entry.seq,
            kind=entry.kind,
            ref_id=entry.ref_id,
            at=to_iso(entry.at),
            digest=entry.payload_digest,
        )


# --------------------------------------------------------------------------- 5. pending read


def check_pending_read_is_deterministic(store) -> None:  # type: ignore[no-untyped-def]
    early = sample_ask(1)
    overdue = sample_ask(2, created_at=T0 - timedelta(hours=1))
    store.create_or_get_by_identity(early)
    store.create_or_get_by_identity(overdue)

    first = [item.ask_id for item in store.list_pending(now=T0)]
    second = [item.ask_id for item in store.list_pending(now=T0)]

    assert first == second == [overdue.ask_id, early.ask_id]


def check_resolved_asks_leave_pending(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    store.cas_status(
        ask.ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.DENIED,
        transition=transition(ask, "answer", AskStatus.DENIED),
    )

    assert store.list_pending(now=T0) == []


# --------------------------------------------------------------------------- 6. entities


def check_delivery_accounting(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.store import DeliveryRecord

    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    delivery = DeliveryRecord(
        delivery_id="delivery_conformance",
        ask_id=ask.ask_id,
        channel="terminal",
        attempt=1,
        status="delivered",
        at=T0,
        target="alice",
    )
    store.record_delivery(delivery)

    assert store.list_deliveries(ask.ask_id) == [delivery]
    try:
        store.record_delivery(delivery)
    except StoreError:
        pass
    else:
        raise AssertionError("duplicate delivery id was accepted")


def check_transition_read(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    store.append_event(transition(ask, "observed"))

    transitions = store.transitions_for(ask.ask_id)

    assert [item.kind for item in transitions] == ["created", "observed"]
    assert [item.seq for item in transitions] == [1, 2]


def check_claim_revocation(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    for index, tier in enumerate(("tier-1", "on-call")):
        store.issue_claim(
            ClaimRecord(
                claim_id=f"claim_revoke_{index}",
                ask_id=ask.ask_id,
                channel="terminal",
                tier=tier,
                secret_hash="h" * 64,
                issued_at=T0,
                expires_at=T0 + timedelta(minutes=5),
            )
        )

    assert store.revoke_claims(ask.ask_id, at=T0, tier="tier-1") == 1
    assert store.revoke_claims(ask.ask_id, at=T0, tier="tier-1") == 0
    assert store.consume_claim("claim_revoke_0", ask_id=ask.ask_id, at=T0) is False
    assert store.consume_claim("claim_revoke_1", ask_id=ask.ask_id, at=T0) is True


# --------------------------------------------------------------------------- 7. capabilities


def check_escalation_cas(store) -> None:  # type: ignore[no-untyped-def]
    ask = sample_ask()
    store.create_or_get_by_identity(ask)
    for index, tier in enumerate(("tier-1", "on-call")):
        store.issue_claim(
            ClaimRecord(
                claim_id=f"claim_esc_{index}",
                ask_id=ask.ask_id,
                channel="terminal",
                tier=tier,
                secret_hash="h" * 64,
                issued_at=T0,
                expires_at=T0 + timedelta(minutes=5),
            )
        )

    event = TransitionRecord(
        ask_id=ask.ask_id,
        at=T0,
        kind="ask-escalated",
        to_status=AskStatus.PENDING,
        detail={"to_tier": "tier-1"},
    )
    revoked = store.escalate(
        ask.ask_id,
        expected_tier=None,
        new_tier="tier-1",
        escalate_at=T0 + timedelta(seconds=60),
        revoke_tiers=("tier-1",),
        transition=event,
    )
    assert revoked == 1
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.tier == "tier-1"
    assert stored.escalate_at == T0 + timedelta(seconds=60)
    assert stored.expires_at == ask.expires_at  # never extended

    # A stale expected tier loses the CAS and writes nothing.
    assert (
        store.escalate(
            ask.ask_id,
            expected_tier=None,
            new_tier="on-call",
            escalate_at=None,
            revoke_tiers=(),
            transition=event,
        )
        == -1
    )

    store.cas_status(
        ask.ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.DENIED,
        transition=transition(ask, "answer", AskStatus.DENIED),
    )
    assert (
        store.escalate(
            ask.ask_id,
            expected_tier="tier-1",
            new_tier="on-call",
            escalate_at=None,
            revoke_tiers=(),
            transition=event,
        )
        == -1
    )


def check_flood_accounting(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.store import FloodRecord

    flood = FloodRecord(
        flood_id="flood_1",
        agent_id="agent://conformance/1",
        session_id="sess_0",
        window_start=T0,
        window_end=T0 + timedelta(seconds=30),
        denied_count=1,
        first_ask_id="ask_0000000000000000",
        at=T0,
    )
    assert store.record_flood(flood) is True
    assert store.get_flood(flood.flood_id) == flood

    updated = replace(flood, denied_count=7)
    assert store.record_flood(updated) is False
    stored = store.get_flood(flood.flood_id)
    assert stored is not None
    assert stored.denied_count == 7
    assert store.get_flood("flood_missing") is None


def check_capabilities_fail_closed(store) -> None:  # type: ignore[no-untyped-def]
    require_capability(store, "single_writer")
    for capability in ("multi_writer", "cluster_safe"):
        try:
            require_capability(store, capability)
        except StoreError:
            continue
        raise AssertionError(f"driver wrongly claims capability {capability}")
