"""In-memory AskStore driver (E11) — same semantics, no disk.

Tests and embedded ephemeral callers use this driver; the conformance suite is what keeps it
honest against the SQLite reference.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime, timedelta

from agentinbox.store.base import (
    CONFORMANCE_VERSION,
    GENESIS_HASH,
    AskRecord,
    AskStatus,
    AuditEntry,
    ClaimRecord,
    CreateResult,
    DriverSpec,
    SessionExport,
    StoreCapabilities,
    StoreError,
    TransitionRecord,
    chain_hash,
    payload_digest,
    to_iso,
    verify_audit_chain,
)


class MemoryStore:
    """Single-writer in-process driver."""

    capabilities = StoreCapabilities(single_writer=True)
    CONFORMANCE_VERSION = CONFORMANCE_VERSION

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._asks: dict[str, AskRecord] = {}
        self._dedupe: dict[str, str] = {}
        self._transitions: dict[str, list[TransitionRecord]] = {}
        self._claims: dict[str, ClaimRecord] = {}
        self._audit: list[AuditEntry] = []
        self._closed = False

    # ------------------------------------------------------------------ contract

    def create_or_get_by_identity(
        self, ask: AskRecord, *, dedupe_window_s: int = 900
    ) -> CreateResult:
        key = f"{ask.action_identity}\n{ask.session_id}"
        with self._lock:
            self._require_open()
            existing_id = self._dedupe.get(key)
            if existing_id is not None:
                existing = self._asks[existing_id]
                if ask.created_at - existing.created_at <= timedelta(seconds=dedupe_window_s):
                    self._append_transition(
                        TransitionRecord(
                            ask_id=existing.ask_id,
                            at=ask.created_at,
                            kind="deduplicated",
                            from_status=existing.status,
                            to_status=existing.status,
                            detail={"why": "deduplicated"},
                        )
                    )
                    return CreateResult(ask=existing, created=False)

            if ask.ask_id in self._asks:
                raise StoreError(f"ask already exists: {ask.ask_id}")
            self._asks[ask.ask_id] = ask
            self._dedupe[key] = ask.ask_id
            self._append_transition(
                TransitionRecord(
                    ask_id=ask.ask_id,
                    at=ask.created_at,
                    kind="created",
                    to_status=ask.status,
                    detail={"why": "created"},
                )
            )
            return CreateResult(ask=ask, created=True)

    def get(self, ask_id: str) -> AskRecord | None:
        with self._lock:
            self._require_open()
            return self._asks.get(ask_id)

    def cas_status(
        self,
        ask_id: str,
        *,
        expected: AskStatus,
        new: AskStatus,
        transition: TransitionRecord,
    ) -> bool:
        if transition.ask_id != ask_id:
            raise StoreError("transition does not belong to the ask being updated")
        with self._lock:
            self._require_open()
            current = self._asks.get(ask_id)
            if current is None or current.status is not expected:
                return False
            decided = transition.at if new in AskStatus.terminal() else current.decided_at
            self._asks[ask_id] = replace(current, status=new, decided_at=decided)
            self._append_transition(
                replace(
                    transition,
                    from_status=expected,
                    to_status=new,
                    seq=0,
                )
            )
            return True

    def issue_claim(self, claim: ClaimRecord) -> None:
        with self._lock:
            self._require_open()
            if claim.claim_id in self._claims:
                raise StoreError(f"claim already exists: {claim.claim_id}")
            self._claims[claim.claim_id] = claim

    def consume_claim(self, claim_id: str, *, ask_id: str, at: datetime) -> bool:
        with self._lock:
            self._require_open()
            claim = self._claims.get(claim_id)
            if claim is None or claim.ask_id != ask_id:
                return False
            if claim.consumed_at is not None or claim.revoked_at is not None:
                return False
            if claim.expires_at <= at:
                return False
            self._claims[claim_id] = replace(claim, consumed_at=at)
            return True

    def list_pending(self, *, now: datetime, limit: int = 100) -> list[AskRecord]:
        del now  # persisted absolute instants are the scheduler's input (M3/M4)
        with self._lock:
            self._require_open()
            pending = [item for item in self._asks.values() if item.status is AskStatus.PENDING]
        pending.sort(key=lambda item: item.expires_at)
        return pending[:limit]

    def append_event(self, transition: TransitionRecord) -> AuditEntry:
        with self._lock:
            self._require_open()
            return self._append_transition(transition)

    def export_session(self, session_id: str) -> SessionExport:
        with self._lock:
            self._require_open()
            asks = sorted(
                (item for item in self._asks.values() if item.session_id == session_id),
                key=lambda item: item.created_at,
            )
            ask_ids = {item.ask_id for item in asks}
            transitions = tuple(
                transition
                for ask_id in sorted(ask_ids)
                for transition in self._transitions.get(ask_id, [])
            )
            claims = tuple(
                sorted(
                    (claim for claim in self._claims.values() if claim.ask_id in ask_ids),
                    key=lambda claim: claim.issued_at,
                )
            )
        return SessionExport(
            session_id=session_id, asks=tuple(asks), transitions=transitions, claims=claims
        )

    def close(self) -> None:
        with self._lock:
            self._closed = True

    # ------------------------------------------------------------------ audit

    def audit_entries(self) -> list[AuditEntry]:
        with self._lock:
            self._require_open()
            return list(self._audit)

    def verify_chain(self) -> None:
        verify_audit_chain(self.audit_entries())

    # ------------------------------------------------------------------ internals

    def _require_open(self) -> None:
        if self._closed:
            raise StoreError("store is closed")

    def _append_transition(self, transition: TransitionRecord) -> AuditEntry:
        existing = self._transitions.setdefault(transition.ask_id, [])
        seq = len(existing) + 1
        stored = replace(transition, seq=seq)
        existing.append(stored)

        detail = dict(stored.detail)
        prev_hash = self._audit[-1].entry_hash if self._audit else GENESIS_HASH
        audit_seq = len(self._audit) + 1
        at = to_iso(stored.at)
        digest = payload_digest(detail)
        entry = AuditEntry(
            seq=audit_seq,
            prev_hash=prev_hash,
            entry_hash=chain_hash(
                prev_hash=prev_hash,
                seq=audit_seq,
                kind="transition",
                ref_id=stored.ask_id,
                at=at,
                digest=digest,
            ),
            kind="transition",
            ref_id=stored.ask_id,
            at=stored.at,
            payload_digest=digest,
        )
        self._audit.append(entry)
        return entry


DRIVER = DriverSpec(
    name="memory",
    conformance_version=CONFORMANCE_VERSION,
    capabilities=MemoryStore.capabilities,
    factory=lambda _home: MemoryStore(),
)


__all__ = ["DRIVER", "MemoryStore"]
