"""SQLite reference AskStore driver (E11, E2).

WAL + ``synchronous=FULL``, one write transaction per mutation, and the audit chain appended in
the same transaction as the transition it records. File ``0600`` inside a ``0700`` home.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentinbox.store.base import (
    CONFORMANCE_VERSION,
    GENESIS_HASH,
    AskRecord,
    AskStatus,
    AuditEntry,
    ClaimRecord,
    CreateResult,
    DeliveryRecord,
    DriverSpec,
    FloodRecord,
    SchemaVersionError,
    SessionExport,
    StoreCapabilities,
    StoreError,
    TransitionRecord,
    canonical_json,
    chain_hash,
    parse_iso,
    payload_digest,
    to_iso,
    transition_payload,
    verify_audit_chain,
)

SCHEMA_VERSION = 4

#: from_version -> statements that take the store to ``from_version + 1``.
MIGRATIONS: dict[int, tuple[str, ...]] = {
    0: (
        "CREATE TABLE schema_version (version INTEGER NOT NULL)",
        """
        CREATE TABLE asks (
            ask_id TEXT PRIMARY KEY,
            action_identity TEXT NOT NULL,
            session_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            dedupe_key TEXT NOT NULL
        )
        """,
        "CREATE INDEX pending_by_expiry ON asks (status, expires_at)",
        "CREATE INDEX asks_by_session ON asks (session_id)",
        "CREATE INDEX asks_by_agent ON asks (agent_id)",
        """
        CREATE TABLE transitions (
            ask_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            at TEXT NOT NULL,
            kind TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            principal TEXT,
            channel TEXT,
            claim_id TEXT,
            reason TEXT,
            detail TEXT NOT NULL,
            PRIMARY KEY (ask_id, seq)
        )
        """,
        """
        CREATE TABLE claims (
            claim_id TEXT PRIMARY KEY,
            ask_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            tier TEXT,
            secret_hash TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            revoked_at TEXT
        )
        """,
        "CREATE INDEX claims_by_ask ON claims (ask_id)",
        """
        CREATE TABLE deliveries (
            delivery_id TEXT PRIMARY KEY,
            ask_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            target TEXT,
            attempt INTEGER NOT NULL,
            status TEXT NOT NULL,
            at TEXT NOT NULL,
            error TEXT
        )
        """,
        """
        CREATE TABLE floods (
            flood_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            session_id TEXT,
            window_start TEXT NOT NULL,
            window_end TEXT NOT NULL,
            denied_count INTEGER NOT NULL,
            first_ask_id TEXT,
            at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE audit (
            seq INTEGER PRIMARY KEY,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            kind TEXT NOT NULL,
            ref_id TEXT NOT NULL,
            at TEXT NOT NULL,
            payload_digest TEXT NOT NULL
        )
        """,
    ),
    1: (
        "ALTER TABLE asks ADD COLUMN decided_at TEXT",
        "CREATE INDEX asks_by_dedupe ON asks (dedupe_key)",
    ),
    2: (
        "ALTER TABLE asks ADD COLUMN warn_at TEXT",
        "ALTER TABLE asks ADD COLUMN escalate_at TEXT",
        "ALTER TABLE asks ADD COLUMN tier TEXT",
    ),
    3: ("ALTER TABLE audit ADD COLUMN payload TEXT NOT NULL DEFAULT '{}'",),
}


class SqliteStore:
    """Single-writer SQLite driver — the reference implementation."""

    capabilities = StoreCapabilities(single_writer=True)
    CONFORMANCE_VERSION = CONFORMANCE_VERSION

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._closed = False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        _chmod(self.path.parent, 0o700)
        if not self.path.exists():
            descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(descriptor)
        else:
            _chmod(self.path, 0o600)

        self._conn = sqlite3.connect(
            self.path, isolation_level=None, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        with self._lock:
            self._migrate()

    # ------------------------------------------------------------------ schema

    def _migrate(self) -> None:
        current = self._schema_version()
        if current > SCHEMA_VERSION:
            raise SchemaVersionError(
                f"store schema v{current} is newer than this build (v{SCHEMA_VERSION}); "
                "downgrade is refused loudly — use a matching agentinbox release"
            )
        while current < SCHEMA_VERSION:
            statements = MIGRATIONS[current]
            with self._transaction():
                for statement in statements:
                    self._conn.execute(statement)
                self._conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (current + 1,)
                )
            current += 1

    def _schema_version(self) -> int:
        exists = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        if exists is None:
            return 0
        row = self._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return int(row[0]) if row is not None and row[0] is not None else 0

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    # ------------------------------------------------------------------ contract

    def create_or_get_by_identity(
        self, ask: AskRecord, *, dedupe_window_s: int = 900
    ) -> CreateResult:
        dedupe_key = f"{ask.action_identity}\n{ask.session_id}"
        cutoff = to_iso(ask.created_at - timedelta(seconds=dedupe_window_s))

        with self._transaction():
            existing = self._conn.execute(
                "SELECT * FROM asks WHERE dedupe_key = ? AND created_at >= ? "
                "ORDER BY created_at DESC LIMIT 1",
                (dedupe_key, cutoff),
            ).fetchone()

            if existing is not None:
                record = _row_to_ask(existing)
                self._append_transition(
                    TransitionRecord(
                        ask_id=record.ask_id,
                        at=ask.created_at,
                        kind="deduplicated",
                        from_status=record.status,
                        to_status=record.status,
                        detail={"why": "deduplicated"},
                    )
                )
                return CreateResult(ask=record, created=False)

            self._conn.execute(
                "INSERT INTO asks (ask_id, action_identity, session_id, agent_id, status,"
                " created_at, expires_at, payload, dedupe_key, warn_at, escalate_at, tier)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ask.ask_id,
                    ask.action_identity,
                    ask.session_id,
                    ask.agent_id,
                    ask.status.value,
                    to_iso(ask.created_at),
                    to_iso(ask.expires_at),
                    canonical_json(dict(ask.payload)),
                    dedupe_key,
                    None if ask.warn_at is None else to_iso(ask.warn_at),
                    None if ask.escalate_at is None else to_iso(ask.escalate_at),
                    ask.tier,
                ),
            )
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
            row = self._conn.execute(
                "SELECT * FROM asks WHERE ask_id = ?", (ask_id,)
            ).fetchone()
        return None if row is None else _row_to_ask(row)

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

        with self._transaction():
            row = self._conn.execute(
                "SELECT status FROM asks WHERE ask_id = ?", (ask_id,)
            ).fetchone()
            if row is None or row["status"] != expected.value:
                return False

            decided_at = to_iso(transition.at) if new in AskStatus.terminal() else None
            self._conn.execute(
                "UPDATE asks SET status = ?, decided_at = ? WHERE ask_id = ?",
                (new.value, decided_at, ask_id),
            )
            self._append_transition(
                TransitionRecord(
                    ask_id=ask_id,
                    at=transition.at,
                    kind=transition.kind,
                    from_status=expected,
                    to_status=new,
                    detail=transition.detail,
                    principal=transition.principal,
                    channel=transition.channel,
                    claim_id=transition.claim_id,
                    reason=transition.reason,
                )
            )
            return True

    def issue_claim(self, claim: ClaimRecord) -> None:
        with self._transaction():
            try:
                self._conn.execute(
                    "INSERT INTO claims (claim_id, ask_id, channel, tier, secret_hash,"
                    " issued_at, expires_at, consumed_at, revoked_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        claim.claim_id,
                        claim.ask_id,
                        claim.channel,
                        claim.tier,
                        claim.secret_hash,
                        to_iso(claim.issued_at),
                        to_iso(claim.expires_at),
                        None if claim.consumed_at is None else to_iso(claim.consumed_at),
                        None if claim.revoked_at is None else to_iso(claim.revoked_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise StoreError(f"claim already exists: {claim.claim_id}") from exc

    def get_claim(self, claim_id: str) -> ClaimRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
            ).fetchone()
        return None if row is None else _row_to_claim(row)

    def consume_claim(self, claim_id: str, *, ask_id: str, at: datetime) -> bool:
        with self._transaction():
            cursor = self._conn.execute(
                "UPDATE claims SET consumed_at = ? WHERE claim_id = ? AND ask_id = ?"
                " AND consumed_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
                (to_iso(at), claim_id, ask_id, to_iso(at)),
            )
            return cursor.rowcount == 1

    def list_pending(self, *, now: datetime, limit: int = 100) -> list[AskRecord]:
        # ``now`` is part of the contract: expiry derivation happens on read in M3/M4, and the
        # persisted absolute instants are what the scheduler recovers from.
        del now
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM asks WHERE status = ? ORDER BY expires_at ASC LIMIT ?",
                (AskStatus.PENDING.value, limit),
            ).fetchall()
        return [_row_to_ask(row) for row in rows]

    def append_event(self, transition: TransitionRecord) -> AuditEntry:
        with self._transaction():
            return self._append_transition(transition)

    def transitions_for(self, ask_id: str) -> list[TransitionRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM transitions WHERE ask_id = ? ORDER BY seq ASC", (ask_id,)
            ).fetchall()
        return [_row_to_transition(row) for row in rows]

    def record_delivery(self, delivery: DeliveryRecord) -> None:
        with self._transaction():
            try:
                self._conn.execute(
                    "INSERT INTO deliveries (delivery_id, ask_id, channel, target, attempt,"
                    " status, at, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        delivery.delivery_id,
                        delivery.ask_id,
                        delivery.channel,
                        delivery.target,
                        delivery.attempt,
                        delivery.status,
                        to_iso(delivery.at),
                        delivery.error,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise StoreError(f"delivery already recorded: {delivery.delivery_id}") from exc
            self._append_audit(
                "delivery",
                delivery.ask_id,
                delivery.at,
                {
                    "delivery_id": delivery.delivery_id,
                    "channel": delivery.channel,
                    "attempt": delivery.attempt,
                    "status": delivery.status,
                    "target": delivery.target,
                    "error": delivery.error,
                },
            )

    def revoke_claims(
        self, ask_id: str, *, at: datetime, tier: str | None = None
    ) -> int:
        statement = (
            "UPDATE claims SET revoked_at = ? WHERE ask_id = ? AND revoked_at IS NULL"
        )
        parameters: list[object] = [to_iso(at), ask_id]
        if tier is not None:
            statement += " AND tier = ?"
            parameters.append(tier)
        with self._transaction():
            cursor = self._conn.execute(statement, parameters)
            return cursor.rowcount

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
        with self._transaction():
            if expected_tier is None:
                cursor = self._conn.execute(
                    "UPDATE asks SET tier = ?, escalate_at = ? "
                    "WHERE ask_id = ? AND status = ? AND tier IS NULL",
                    (
                        new_tier,
                        None if escalate_at is None else to_iso(escalate_at),
                        ask_id,
                        AskStatus.PENDING.value,
                    ),
                )
            else:
                cursor = self._conn.execute(
                    "UPDATE asks SET tier = ?, escalate_at = ? "
                    "WHERE ask_id = ? AND status = ? AND tier = ?",
                    (
                        new_tier,
                        None if escalate_at is None else to_iso(escalate_at),
                        ask_id,
                        AskStatus.PENDING.value,
                        expected_tier,
                    ),
                )
            if cursor.rowcount != 1:
                return -1

            revoked = 0
            if revoke_tiers:
                placeholders = ",".join("?" for _ in revoke_tiers)
                # Placeholders are generated `?` only; tier names stay bound parameters.
                revoked = self._conn.execute(
                    f"UPDATE claims SET revoked_at = ? WHERE ask_id = ? "  # noqa: S608
                    f"AND revoked_at IS NULL AND tier IN ({placeholders})",
                    (to_iso(transition.at), ask_id, *revoke_tiers),
                ).rowcount

            self._append_transition(
                replace(
                    transition,
                    ask_id=ask_id,
                    from_status=AskStatus.PENDING,
                    to_status=AskStatus.PENDING,
                    detail={**dict(transition.detail), "revoked_claims": revoked},
                    seq=0,
                )
            )
            return revoked

    def record_flood(self, flood: FloodRecord) -> bool:
        with self._transaction():
            existing = self._conn.execute(
                "SELECT 1 FROM floods WHERE flood_id = ?", (flood.flood_id,)
            ).fetchone()
            if existing is not None:
                self._conn.execute(
                    "UPDATE floods SET denied_count = ?, window_end = ?, at = ? "
                    "WHERE flood_id = ?",
                    (
                        flood.denied_count,
                        to_iso(flood.window_end),
                        to_iso(flood.at),
                        flood.flood_id,
                    ),
                )
                return False
            self._conn.execute(
                "INSERT INTO floods (flood_id, agent_id, session_id, window_start,"
                " window_end, denied_count, first_ask_id, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    flood.flood_id,
                    flood.agent_id,
                    flood.session_id,
                    to_iso(flood.window_start),
                    to_iso(flood.window_end),
                    flood.denied_count,
                    flood.first_ask_id,
                    to_iso(flood.at),
                ),
            )
            self._append_audit(
                "flood",
                flood.flood_id,
                flood.at,
                {
                    "agent_id": flood.agent_id,
                    "session_id": flood.session_id,
                    "window_start": to_iso(flood.window_start),
                    "window_end": to_iso(flood.window_end),
                    "denied_count": flood.denied_count,
                    "first_ask_id": flood.first_ask_id,
                },
            )
            return True

    def get_flood(self, flood_id: str) -> FloodRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM floods WHERE flood_id = ?", (flood_id,)
            ).fetchone()
        if row is None:
            return None
        return FloodRecord(
            flood_id=row["flood_id"],
            agent_id=row["agent_id"],
            session_id=row["session_id"],
            window_start=parse_iso(row["window_start"]),
            window_end=parse_iso(row["window_end"]),
            denied_count=int(row["denied_count"]),
            first_ask_id=row["first_ask_id"],
            at=parse_iso(row["at"]),
        )

    def list_deliveries(self, ask_id: str) -> list[DeliveryRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM deliveries WHERE ask_id = ? ORDER BY attempt ASC", (ask_id,)
            ).fetchall()
        return [_row_to_delivery(row) for row in rows]

    def export_session(self, session_id: str) -> SessionExport:
        with self._lock:
            ask_rows = self._conn.execute(
                "SELECT * FROM asks WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            ask_ids = [row["ask_id"] for row in ask_rows]
            transitions: list[sqlite3.Row] = []
            claims: list[sqlite3.Row] = []
            if ask_ids:
                placeholders = ",".join("?" for _ in ask_ids)
                transitions = self._conn.execute(
                    # placeholders are generated "?" only; ids are bound parameters
                    f"SELECT * FROM transitions WHERE ask_id IN ({placeholders})"  # noqa: S608
                    " ORDER BY ask_id, seq",
                    ask_ids,
                ).fetchall()
                claims = self._conn.execute(
                    # same: only "?" placeholders are interpolated
                    f"SELECT * FROM claims WHERE ask_id IN ({placeholders})"  # noqa: S608
                    " ORDER BY issued_at",
                    ask_ids,
                ).fetchall()

        return SessionExport(
            session_id=session_id,
            asks=tuple(_row_to_ask(row) for row in ask_rows),
            transitions=tuple(_row_to_transition(row) for row in transitions),
            claims=tuple(_row_to_claim(row) for row in claims),
        )

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._conn.close()
                self._closed = True

    # ------------------------------------------------------------------ audit

    def audit_entries(self) -> list[AuditEntry]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM audit ORDER BY seq ASC").fetchall()
        return [
            AuditEntry(
                seq=row["seq"],
                prev_hash=row["prev_hash"],
                entry_hash=row["entry_hash"],
                kind=row["kind"],
                ref_id=row["ref_id"],
                at=parse_iso(row["at"]),
                payload_digest=row["payload_digest"],
                payload=json.loads(row["payload"]),
            )
            for row in rows
        ]

    def verify_chain(self) -> None:
        verify_audit_chain(self.audit_entries())

    def append_audit(
        self, *, kind: str, ref_id: str, at: datetime, payload: Mapping[str, Any]
    ) -> AuditEntry:
        with self._transaction():
            return self._append_audit(kind, ref_id, at, payload)

    def prune_evidence(self, before: datetime, *, at: datetime) -> tuple[int, int]:
        with self._transaction():
            transitions = self._conn.execute(
                "DELETE FROM transitions WHERE at < ?", (to_iso(before),)
            ).rowcount
            deliveries = self._conn.execute(
                "DELETE FROM deliveries WHERE at < ?", (to_iso(before),)
            ).rowcount
            self._append_audit(
                "retention-pruned",
                "retention",
                at,
                {
                    "before": to_iso(before),
                    "transitions": transitions,
                    "deliveries": deliveries,
                },
            )
            return transitions, deliveries

    # ------------------------------------------------------------------ internals

    def _append_transition(self, transition: TransitionRecord) -> AuditEntry:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM transitions WHERE ask_id = ?",
            (transition.ask_id,),
        ).fetchone()
        seq = int(row[0])

        detail = transition_payload(transition)
        self._conn.execute(
            "INSERT INTO transitions (ask_id, seq, at, kind, from_status, to_status,"
            " principal, channel, claim_id, reason, detail)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                transition.ask_id,
                seq,
                to_iso(transition.at),
                transition.kind,
                None if transition.from_status is None else transition.from_status.value,
                transition.to_status.value,
                transition.principal,
                transition.channel,
                transition.claim_id,
                transition.reason,
                canonical_json(detail),
            ),
        )

        return self._append_audit("transition", transition.ask_id, transition.at, detail)

    def _append_audit(
        self, kind: str, ref_id: str, at: datetime, payload: Mapping[str, Any]
    ) -> AuditEntry:
        previous = self._conn.execute(
            "SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = GENESIS_HASH if previous is None else str(previous[0])
        row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM audit").fetchone()
        audit_seq = int(row[0])
        at_text = to_iso(at)
        detail = dict(payload)
        digest = payload_digest(detail)
        entry_hash = chain_hash(
            prev_hash=prev_hash,
            seq=audit_seq,
            kind=kind,
            ref_id=ref_id,
            at=at_text,
            digest=digest,
        )
        self._conn.execute(
            "INSERT INTO audit (seq, prev_hash, entry_hash, kind, ref_id, at,"
            " payload_digest, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                audit_seq,
                prev_hash,
                entry_hash,
                kind,
                ref_id,
                at_text,
                digest,
                canonical_json(detail),
            ),
        )
        return AuditEntry(
            seq=audit_seq,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            kind=kind,
            ref_id=ref_id,
            at=at,
            payload_digest=digest,
            payload=detail,
        )


def _chmod(path: Path, mode: int) -> None:
    os.chmod(path, stat.S_IMODE(mode))


def _row_to_ask(row: sqlite3.Row) -> AskRecord:
    return AskRecord(
        ask_id=row["ask_id"],
        action_identity=row["action_identity"],
        session_id=row["session_id"],
        agent_id=row["agent_id"],
        created_at=parse_iso(row["created_at"]),
        expires_at=parse_iso(row["expires_at"]),
        payload=json.loads(row["payload"]),
        status=AskStatus(row["status"]),
        decided_at=None if row["decided_at"] is None else parse_iso(row["decided_at"]),
        warn_at=None if row["warn_at"] is None else parse_iso(row["warn_at"]),
        escalate_at=None if row["escalate_at"] is None else parse_iso(row["escalate_at"]),
        tier=row["tier"],
    )


def _row_to_transition(row: sqlite3.Row) -> TransitionRecord:
    return TransitionRecord(
        ask_id=row["ask_id"],
        seq=row["seq"],
        at=parse_iso(row["at"]),
        kind=row["kind"],
        from_status=None if row["from_status"] is None else AskStatus(row["from_status"]),
        to_status=AskStatus(row["to_status"]),
        detail=json.loads(row["detail"]),
        principal=row["principal"],
        channel=row["channel"],
        claim_id=row["claim_id"],
        reason=row["reason"],
    )


def _row_to_delivery(row: sqlite3.Row) -> DeliveryRecord:
    return DeliveryRecord(
        delivery_id=row["delivery_id"],
        ask_id=row["ask_id"],
        channel=row["channel"],
        target=row["target"],
        attempt=row["attempt"],
        status=row["status"],
        at=parse_iso(row["at"]),
        error=row["error"],
    )


def _row_to_claim(row: sqlite3.Row) -> ClaimRecord:
    return ClaimRecord(
        claim_id=row["claim_id"],
        ask_id=row["ask_id"],
        channel=row["channel"],
        tier=row["tier"],
        secret_hash=row["secret_hash"],
        issued_at=parse_iso(row["issued_at"]),
        expires_at=parse_iso(row["expires_at"]),
        consumed_at=None if row["consumed_at"] is None else parse_iso(row["consumed_at"]),
        revoked_at=None if row["revoked_at"] is None else parse_iso(row["revoked_at"]),
    )


DRIVER = DriverSpec(
    name="sqlite",
    conformance_version=CONFORMANCE_VERSION,
    capabilities=SqliteStore.capabilities,
    factory=lambda home: SqliteStore(home / "inbox.db"),
)


__all__ = ["DRIVER", "MIGRATIONS", "SCHEMA_VERSION", "SqliteStore"]
