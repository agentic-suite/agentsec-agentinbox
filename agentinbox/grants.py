"""Repeated-ask compression and bounded approval windows/grants (M30).

Design: ``docs/design/v0.1.0/grants.md``. Compression is a view; each ask keeps its record. Grants
are audited, bounded, and revocable — a spent or revoked grant never yields a silent allow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from agentinbox.config import Config
from agentinbox.lifecycle import transition
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    canonical_json,
    to_iso,
    utcnow,
)

GRANT_SCOPES = frozenset({"class", "session"})
DEFAULT_COMPRESSION_WINDOW_SECONDS = 300


class GrantError(Exception):
    """A grant request refused (shape, scope, or an existing active session grant)."""


@dataclass(frozen=True, slots=True)
class GrantState:
    grant_id: str
    scope: str
    class_name: str
    session_id: str | None
    owner: str
    reason: str
    issued_by: str
    issued_at: datetime
    expires_at: datetime
    max_uses: int
    max_per_minute: int
    uses: int
    revoked_at: datetime | None
    expired_at: datetime | None

    @property
    def status(self) -> str:
        if self.revoked_at is not None:
            return "revoked"
        if self.expired_at is not None:
            return "expired"
        if self.uses >= self.max_uses:
            return "spent"
        return "active"

    def burndown(self, *, now: datetime) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "scope": self.scope,
            "class": self.class_name,
            "session_id": self.session_id,
            "owner": self.owner,
            "reason": self.reason,
            "issued_by": self.issued_by,
            "uses": self.uses,
            "max_uses": self.max_uses,
            "max_per_minute": self.max_per_minute,
            "remaining_uses": max(0, self.max_uses - self.uses),
            "expires_at": to_iso(self.expires_at),
            "remaining_s": max(0, int((self.expires_at - now).total_seconds())),
            "status": self.status,
        }


def _parse_at(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _states(store: AskStore) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    revoked: dict[str, datetime] = {}
    expired: dict[str, datetime] = {}
    uses: dict[str, list[datetime]] = {}
    for entry in store.audit_entries():
        if entry.payload is None:
            continue
        if entry.kind == "grant-issued":
            raw[str(entry.payload.get("grant_id"))] = dict(entry.payload)
        elif entry.kind == "grant-used":
            uses.setdefault(str(entry.payload.get("grant_id")), []).append(entry.at)
        elif entry.kind == "grant-revoked":
            revoked[str(entry.payload.get("grant_id"))] = entry.at
        elif entry.kind == "grant-expired":
            expired[str(entry.payload.get("grant_id"))] = entry.at
    states: dict[str, dict[str, Any]] = {}
    for grant_id, data in raw.items():
        data["uses_list"] = sorted(uses.get(grant_id, []))
        data["revoked_at"] = revoked.get(grant_id)
        data["expired_at"] = expired.get(grant_id)
        states[grant_id] = data
    return states


def grants(store: AskStore) -> tuple[GrantState, ...]:
    result: list[GrantState] = []
    for grant_id, data in _states(store).items():
        result.append(
            GrantState(
                grant_id=grant_id,
                scope=str(data.get("scope")),
                class_name=str(data.get("class")),
                session_id=None if data.get("session_id") is None else str(data["session_id"]),
                owner=str(data.get("owner")),
                reason=str(data.get("reason")),
                issued_by=str(data.get("issued_by")),
                issued_at=_parse_at(data.get("issued_at")),
                expires_at=_parse_at(data.get("expires_at")),
                max_uses=int(data.get("max_uses") or 0),
                max_per_minute=int(data.get("max_per_minute") or 0),
                uses=len(data["uses_list"]),
                revoked_at=data.get("revoked_at"),
                expired_at=data.get("expired_at"),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.issued_at, item.grant_id)))


def issue_grant(
    store: AskStore,
    config: Config,
    *,
    scope: str,
    class_name: str,
    owner: str,
    reason: str,
    issued_by: str,
    ttl_seconds: int,
    max_uses: int,
    max_per_minute: int,
    session_id: str | None = None,
    at: datetime | None = None,
) -> GrantState:
    if scope not in GRANT_SCOPES:
        raise GrantError(f"unknown grant scope: {scope}")
    if class_name not in config.classes:
        raise GrantError(f"unknown class: {class_name}")
    if not owner.strip() or not reason.strip() or not issued_by.strip():
        raise GrantError("owner, reason, and issued_by are required")
    if ttl_seconds < 1 or max_uses < 1 or max_per_minute < 1:
        raise GrantError("ttl_seconds, max_uses, and max_per_minute must be positive")
    if scope == "session" and not session_id:
        raise GrantError("a session grant requires session_id")
    moment = at or utcnow()
    for existing in active_grants(store, now=moment):
        if (
            scope == "session"
            and existing.scope == "session"
            and existing.session_id == session_id
        ):
            raise GrantError(f"session {session_id} already has an active grant")
    grant_id = f"grant_{len(_states(store)) + 1:04d}"
    payload = {
        "grant_id": grant_id,
        "scope": scope,
        "class": class_name,
        "session_id": session_id,
        "owner": owner,
        "reason": reason,
        "issued_by": issued_by,
        "issued_at": to_iso(moment),
        "expires_at": to_iso(moment + timedelta(seconds=ttl_seconds)),
        "max_uses": max_uses,
        "max_per_minute": max_per_minute,
    }
    store.append_audit(kind="grant-issued", ref_id=grant_id, at=moment, payload=payload)
    return next(item for item in grants(store) if item.grant_id == grant_id)


def active_grants(store: AskStore, *, now: datetime | None = None) -> tuple[GrantState, ...]:
    moment = now or utcnow()
    active: list[GrantState] = []
    for grant in grants(store):
        if grant.revoked_at is not None or grant.expired_at is not None:
            continue
        if grant.expires_at <= moment or grant.uses >= grant.max_uses:
            continue
        active.append(grant)
    return tuple(active)


def grant_covering(
    store: AskStore, ask: AskRecord, *, now: datetime | None = None
) -> GrantState | None:
    moment = now or utcnow()
    for grant in active_grants(store, now=moment):
        if grant.class_name != str(ask.payload.get("class")):
            continue
        if grant.scope == "session" and grant.session_id != ask.session_id:
            continue
        return grant
    return None


def _rate_ok(store: AskStore, grant: GrantState, *, now: datetime) -> bool:
    since = now - timedelta(seconds=60)
    recent = 0
    for entry in store.audit_entries():
        if entry.kind != "grant-used" or entry.payload is None:
            continue
        if entry.payload.get("grant_id") == grant.grant_id and entry.at >= since:
            recent += 1
    return recent < grant.max_per_minute


def consume_grant(
    store: AskStore, ask: AskRecord, *, now: datetime | None = None
) -> Mapping[str, Any] | None:
    moment = now or utcnow()
    grant = grant_covering(store, ask, now=moment)
    if grant is None or not _rate_ok(store, grant, now=moment):
        return None
    store.append_audit(
        kind="grant-used",
        ref_id=grant.grant_id,
        at=moment,
        payload={
            "grant_id": grant.grant_id,
            "ask_id": ask.ask_id,
            "principal": grant.owner,
        },
    )
    refreshed = next(item for item in grants(store) if item.grant_id == grant.grant_id)
    authorization = {
        "source": "window-grant",
        "grant_id": grant.grant_id,
        "owner": grant.owner,
        "scope": grant.scope,
        "burndown": refreshed.burndown(now=moment),
    }
    if not transition(
        store,
        ask.ask_id,
        AskStatus.APPROVED,
        kind="answer",
        at=moment,
        principal=grant.owner,
        channel="grant",
        reason="window-grant",
        detail={"decision": "approve", "authorization": authorization},
    ):
        return None
    return authorization


def revoke_grant(
    store: AskStore, grant_id: str, *, by: str, reason: str, at: datetime | None = None
) -> None:
    if not reason.strip():
        raise GrantError("a revocation reason is required")
    store.append_audit(
        kind="grant-revoked",
        ref_id=grant_id,
        at=at or utcnow(),
        payload={"grant_id": grant_id, "by": by, "reason": reason},
    )


def end_session(
    store: AskStore, session_id: str, *, at: datetime | None = None
) -> tuple[str, ...]:
    moment = at or utcnow()
    expired: list[str] = []
    for grant in active_grants(store, now=moment):
        if grant.scope == "session" and grant.session_id == session_id:
            store.append_audit(
                kind="grant-expired",
                ref_id=grant.grant_id,
                at=moment,
                payload={"grant_id": grant.grant_id, "reason": "session-ended"},
            )
            expired.append(grant.grant_id)
    return tuple(expired)


def expire_due_grants(store: AskStore, *, at: datetime | None = None) -> tuple[str, ...]:
    moment = at or utcnow()
    expired: list[str] = []
    for grant in grants(store):
        if grant.expired_at is not None or grant.revoked_at is not None:
            continue
        if grant.expires_at <= moment:
            store.append_audit(
                kind="grant-expired",
                ref_id=grant.grant_id,
                at=moment,
                payload={"grant_id": grant.grant_id, "reason": "time"},
            )
            expired.append(grant.grant_id)
    return tuple(expired)


@dataclass(frozen=True, slots=True)
class Compression:
    group_key: str
    asks: tuple[AskRecord, ...]

    @property
    def count(self) -> int:
        return len(self.asks)

    def render(self) -> str:
        lines = [f"COMPRESSED x{self.count} (view only — each row answers itself)"]
        for ask in self.asks:
            lines.append(f"  {ask.ask_id}  {ask.status.value}  {ask.payload.get('action')}")
        return "\n".join(lines)


def compression_key(ask: AskRecord, *, ignore: Sequence[str] = ()) -> str:
    arguments = {
        key: value
        for key, value in (ask.payload.get("arguments") or {}).items()
        if key not in ignore
    }
    return canonical_json(
        {
            "class": ask.payload.get("class"),
            "tool": ask.payload.get("tool"),
            "action": ask.payload.get("action"),
            "arguments": arguments,
        }
    )


def compress(
    store: AskStore,
    ask: AskRecord,
    *,
    window_seconds: int = DEFAULT_COMPRESSION_WINDOW_SECONDS,
    ignore: Sequence[str] = (),
) -> Compression:
    key = compression_key(ask, ignore=ignore)
    matches: list[AskRecord] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "created":
            continue
        candidate = store.get(entry.ref_id)
        if candidate is None:
            continue
        if abs((candidate.created_at - ask.created_at).total_seconds()) > window_seconds:
            continue
        if compression_key(candidate, ignore=ignore) == key:
            matches.append(candidate)
    matches.sort(key=lambda item: (item.created_at, item.ask_id))
    return Compression(group_key=key, asks=tuple(matches))


def repeated_denials(
    store: AskStore, *, threshold: int = 5, ignore: Sequence[str] = ()
) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "answer":
            continue
        if entry.payload.get("to_status") != AskStatus.DENIED.value:
            continue
        ask = store.get(entry.ref_id)
        if ask is None:
            continue
        key = compression_key(ask, ignore=ignore)
        bucket = counts.setdefault(
            key,
            {
                "class": ask.payload.get("class"),
                "tool": ask.payload.get("tool"),
                "action": ask.payload.get("action"),
                "ask_ids": [],
                "count": 0,
            },
        )
        bucket["ask_ids"].append(ask.ask_id)
        bucket["count"] += 1
    return [item for item in counts.values() if item["count"] >= threshold]


def grant_for_card(
    store: AskStore, ask: AskRecord, *, now: datetime | None = None
) -> dict[str, Any] | None:
    moment = now or utcnow()
    covering = grant_covering(store, ask, now=moment)
    if covering is not None:
        return covering.burndown(now=moment)
    for grant in reversed(grants(store)):
        if grant.class_name != str(ask.payload.get("class")):
            continue
        if grant.scope == "session" and grant.session_id != ask.session_id:
            continue
        if grant.issued_at <= ask.created_at <= grant.expires_at:
            return grant.burndown(now=moment)
    return None


__all__ = [
    "GRANT_SCOPES",
    "Compression",
    "GrantError",
    "GrantState",
    "active_grants",
    "compress",
    "compression_key",
    "consume_grant",
    "end_session",
    "expire_due_grants",
    "grant_covering",
    "grant_for_card",
    "grants",
    "issue_grant",
    "repeated_denials",
    "revoke_grant",
]
