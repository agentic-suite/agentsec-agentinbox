"""AskStore contract and records — the single state path (E11).

Design of record: ``docs/design/v0.1.0/store.md``. Drivers implement :class:`AskStore` and are
admitted only by passing the in-repo conformance suite (``tests/store/conformance.py``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Protocol

#: Version of the conformance suite a driver must declare to be admitted.
CONFORMANCE_VERSION: Final = "7"


class StoreError(Exception):
    """Base class for store failures."""


class CapabilityError(StoreError):
    """The configured driver cannot guarantee a required capability."""


class SchemaVersionError(StoreError):
    """The store schema is newer than this build — downgrade is refused loudly."""


class DriverNotAdmittedError(StoreError):
    """The driver is unknown or has not passed this conformance suite."""


class ChainHashMismatch(StoreError):
    """The audit chain does not verify (tampering or corruption)."""


class AskStatus(StrEnum):
    """The v0.1.0 status vocabulary (PRD 15)."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FLOOD_DENIED = "flood_denied"

    @classmethod
    def terminal(cls) -> frozenset[AskStatus]:
        return frozenset(
            {cls.APPROVED, cls.DENIED, cls.EXPIRED, cls.CANCELLED, cls.FLOOD_DENIED}
        )


@dataclass(frozen=True, slots=True)
class StoreCapabilities:
    """What a driver can honestly guarantee."""

    single_writer: bool
    multi_writer: bool = False
    cluster_safe: bool = False


@dataclass(frozen=True, slots=True)
class DriverSpec:
    """What an ``agentinbox.store`` entry point must expose (admission gate)."""

    name: str
    conformance_version: str
    capabilities: StoreCapabilities
    factory: Callable[[Path], AskStore]


@dataclass(frozen=True, slots=True)
class AskRecord:
    """The approval object (PRD 15). Payload is already redacted (M2)."""

    ask_id: str
    action_identity: str
    session_id: str
    agent_id: str
    created_at: datetime
    expires_at: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)
    status: AskStatus = AskStatus.PENDING
    decided_at: datetime | None = None
    warn_at: datetime | None = None
    escalate_at: datetime | None = None
    tier: str | None = None


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    """Append-only lifecycle event. ``seq`` is assigned by the store (caller passes 0)."""

    ask_id: str
    at: datetime
    kind: str
    to_status: AskStatus
    from_status: AskStatus | None = None
    detail: Mapping[str, Any] = field(default_factory=dict)
    principal: str | None = None
    channel: str | None = None
    claim_id: str | None = None
    reason: str | None = None
    seq: int = 0


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    """A single-use answer token. Only the hash is ever stored (E3)."""

    claim_id: str
    ask_id: str
    channel: str
    tier: str | None
    secret_hash: str
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None
    #: The action identity the claim is bound to (PRD 18 binding step).
    action_identity: str | None = None

    def state(self, at: datetime) -> str:
        """Derived claim state: used > revoked > expired > issued."""
        if self.consumed_at is not None:
            return "used"
        if self.revoked_at is not None:
            return "revoked"
        if self.expires_at <= at:
            return "expired"
        return "issued"


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    """One delivery attempt on one channel (E7 accounting)."""

    delivery_id: str
    ask_id: str
    channel: str
    attempt: int
    status: str
    at: datetime
    target: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class FloodRecord:
    """One aggregated flood window (one event, one digest, N denials)."""

    flood_id: str
    agent_id: str
    session_id: str | None
    window_start: datetime
    window_end: datetime
    denied_count: int
    first_ask_id: str | None
    at: datetime


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """The hash-chained evidence row.

    ``payload`` is the canonical evidence body when this build wrote it (``None`` for rows
    migrated from schema v3, whose body cannot be reconstructed). Verification re-hashes a
    present body, so editing it is detected even if the stored digest is left untouched.
    """

    seq: int
    prev_hash: str
    entry_hash: str
    kind: str
    ref_id: str
    at: datetime
    payload_digest: str
    payload: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CreateResult:
    ask: AskRecord
    created: bool


@dataclass(frozen=True, slots=True)
class SessionExport:
    session_id: str
    asks: tuple[AskRecord, ...]
    transitions: tuple[TransitionRecord, ...]
    claims: tuple[ClaimRecord, ...]


class AskStore(Protocol):
    """The contract every driver implements."""

    capabilities: StoreCapabilities

    def create_or_get_by_identity(
        self, ask: AskRecord, *, dedupe_window_s: int = 900
    ) -> CreateResult: ...

    def get(self, ask_id: str) -> AskRecord | None: ...

    def cas_status(
        self,
        ask_id: str,
        *,
        expected: AskStatus,
        new: AskStatus,
        transition: TransitionRecord,
    ) -> bool: ...

    def issue_claim(self, claim: ClaimRecord) -> None: ...

    def get_claim(self, claim_id: str) -> ClaimRecord | None: ...

    def consume_claim(self, claim_id: str, *, ask_id: str, at: datetime) -> bool: ...

    def list_pending(self, *, now: datetime, limit: int = 100) -> list[AskRecord]: ...

    def append_event(self, transition: TransitionRecord) -> AuditEntry: ...

    def transitions_for(self, ask_id: str) -> list[TransitionRecord]: ...

    def record_delivery(self, delivery: DeliveryRecord) -> None: ...

    def revoke_claims(
        self, ask_id: str, *, at: datetime, tier: str | None = None
    ) -> int: ...

    def escalate(
        self,
        ask_id: str,
        *,
        expected_tier: str | None,
        new_tier: str,
        escalate_at: datetime | None,
        revoke_tiers: Sequence[str],
        transition: TransitionRecord,
    ) -> int:
        """Advance the tier and revoke prior-tier claims atomically.

        Returns the number of revoked claims, or ``-1`` when the CAS lost (another writer
        changed the tier or the ask resolved). Never changes ``expires_at``.
        """
        ...

    def list_deliveries(self, ask_id: str) -> list[DeliveryRecord]: ...

    def record_flood(self, flood: FloodRecord) -> bool:
        """Insert or update a flood window; ``True`` only for the creating call."""
        ...

    def get_flood(self, flood_id: str) -> FloodRecord | None: ...

    def audit_entries(self) -> list[AuditEntry]: ...

    def verify_chain(self) -> None: ...

    def append_audit(
        self, *, kind: str, ref_id: str, at: datetime, payload: Mapping[str, Any]
    ) -> AuditEntry: ...

    def prune_evidence(self, before: datetime, *, at: datetime) -> tuple[int, int]:
        """Delete transitions/deliveries older than ``before`` and append a chain marker."""
        ...

    def export_session(self, session_id: str) -> SessionExport: ...

    def close(self) -> None: ...


def require_capability(store: AskStore, capability: str) -> None:
    """Fail closed when a driver cannot guarantee the configuration being enabled."""
    if capability not in {"single_writer", "multi_writer", "cluster_safe"}:
        raise ValueError(f"unknown capability: {capability!r}")
    if not getattr(store.capabilities, capability):
        raise CapabilityError(
            f"store driver cannot guarantee {capability!r}; refuse to start rather than "
            "promise semantics it does not provide"
        )


# --------------------------------------------------------------------------- time & hashing


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_iso(moment: datetime) -> str:
    """UTC ISO-8601 with a ``Z`` suffix; naive datetimes are a bug, not a guess."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    return moment.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_iso(text: str) -> datetime:
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"timestamp is not timezone-aware: {text!r}")
    return moment.astimezone(UTC)


def canonical_json(value: Any) -> str:
    """One canonical JSON form for hashing and storage (sorted keys, no whitespace)."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def transition_payload(transition: TransitionRecord) -> dict[str, Any]:
    """The canonical audit/event payload for a transition (no untrusted text)."""
    return {
        "kind": transition.kind,
        "from_status": (
            None if transition.from_status is None else transition.from_status.value
        ),
        "to_status": transition.to_status.value,
        "principal": transition.principal,
        "channel": transition.channel,
        "claim_id": transition.claim_id,
        "reason": transition.reason,
        "detail": dict(transition.detail),
    }


def payload_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def chain_hash(*, prev_hash: str, seq: int, kind: str, ref_id: str, at: str, digest: str) -> str:
    material = f"{prev_hash}|{seq}|{kind}|{ref_id}|{at}|{digest}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


GENESIS_HASH: Final = "0" * 64


def verify_audit_chain(entries: Sequence[AuditEntry]) -> None:
    """Recompute the chain; raise on the first bad entry. Driver-independent (E11)."""
    previous = GENESIS_HASH
    for expected_seq, entry in enumerate(entries, start=1):
        if entry.seq != expected_seq:
            raise ChainHashMismatch(
                f"audit seq gap: expected {expected_seq}, found {entry.seq}"
            )
        if entry.prev_hash != previous:
            raise ChainHashMismatch(f"audit seq {entry.seq}: prev_hash does not link")
        if entry.payload is not None and payload_digest(entry.payload) != entry.payload_digest:
            raise ChainHashMismatch(
                f"audit seq {entry.seq}: payload_digest does not match the body"
            )
        recomputed = chain_hash(
            prev_hash=entry.prev_hash,
            seq=entry.seq,
            kind=entry.kind,
            ref_id=entry.ref_id,
            at=to_iso(entry.at),
            digest=entry.payload_digest,
        )
        if recomputed != entry.entry_hash:
            raise ChainHashMismatch(f"audit seq {entry.seq}: entry_hash does not verify")
        previous = entry.entry_hash
