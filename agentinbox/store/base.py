"""AskStore contract and records — the single state path (E11).

Design of record: ``docs/design/v0.1.0/store.md``. Drivers implement :class:`AskStore` and are
admitted only by passing the in-repo conformance suite (``tests/store/conformance.py``).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Final, Protocol

#: Version of the conformance suite a driver must declare to be admitted.
CONFORMANCE_VERSION: Final = "1"


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


class AskStatus(str, Enum):
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


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """The hash-chained evidence row."""

    seq: int
    prev_hash: str
    entry_hash: str
    kind: str
    ref_id: str
    at: datetime
    payload_digest: str


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

    def consume_claim(self, claim_id: str, *, ask_id: str, at: datetime) -> bool: ...

    def list_pending(self, *, now: datetime, limit: int = 100) -> list[AskRecord]: ...

    def append_event(self, transition: TransitionRecord) -> AuditEntry: ...

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
