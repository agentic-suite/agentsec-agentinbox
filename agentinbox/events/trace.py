"""Derive the agentwatch event stream from the audit chain (M16).

The chain is the evidence; events are a projection of it. One audit entry produces at most one
event, so an integration run has exactly one event per fact (no double-emission from the
delivery/flood transitions that mirror their records).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from agentinbox.events.base import (
    PAYLOAD_REQUIREMENTS,
    BufferedEventSink,
    Event,
    EventSink,
    ListSink,
)
from agentinbox.store import AskRecord, AskStore, AuditEntry, to_iso, utcnow

#: The schema's vocabulary. Internal causes are preserved in ``cause_detail``.
ANSWER_CAUSE_MAP: dict[str, str] = {
    "unknown_claim": "unknown_claim",
    "bad_secret": "bad_signature",
    "expired_token": "expired_claim",
    "used": "used_claim",
    "revoked": "revoked_claim",
    "guessing": "bad_signature",
    "bad_signature": "bad_signature",
    "identity_mismatch": "binding_mismatch",
    "off_roster": "off_roster",
    "self_review": "self_review",
    "late": "late",
    "reason_required": "binding_mismatch",
    "confirmation": "binding_mismatch",
    "unknown_ask": "binding_mismatch",
    "unknown_class": "binding_mismatch",
}

_TRANSITION_TYPES: dict[str, str] = {
    "created": "ask-raised",
    "warned": "ask-warned",
    "ask-escalated": "ask-escalated",
    "answer": "ask-answered",
    "expired": "ask-expired",
    "cancelled": "ask-cancelled",
    "gate-cancelled": "ask-cancelled",
    "answer-rejected": "answer-rejected",
    "late-answer": "answer-rejected",
}

#: Mirrored transitions; their audit records are the event source of truth.
_SKIP_TRANSITIONS = frozenset({"ask-delivered", "delivery-failed", "ask-flood"})


def event_from_entry(store: AskStore, entry: AuditEntry) -> dict[str, Any] | None:
    if entry.kind == "transition":
        kind = str(entry.payload.get("kind", ""))
        if kind in _SKIP_TRANSITIONS:
            return None
        event_type = _TRANSITION_TYPES.get(kind)
        if event_type is None:
            return None
        ask = store.get(entry.ref_id)
        if ask is None:
            return None
        payload = _transition_payload(event_type, entry, ask)
    elif entry.kind == "delivery":
        event_type = (
            "ask-delivered"
            if entry.payload.get("status") == "delivered"
            else "ask-delivery-failed"
        )
        ask = store.get(entry.ref_id)
        if ask is None:
            return None
        payload = {
            "channel": entry.payload.get("channel"),
            "attempt": entry.payload.get("attempt"),
            "error": entry.payload.get("error"),
        }
    elif entry.kind == "flood":
        first_ask_id = entry.payload.get("first_ask_id")
        ask = store.get(str(first_ask_id)) if first_ask_id else None
        if ask is None:
            return None
        event_type = "ask-flood"
        payload = {
            "window": {
                "start": entry.payload.get("window_start"),
                "end": entry.payload.get("window_end"),
            },
            "denied_count": entry.payload.get("denied_count"),
            "first_ask_id": first_ask_id,
        }
    else:  # export / retention markers are evidence, not lifecycle events
        return None

    missing = PAYLOAD_REQUIREMENTS[event_type] - set(payload)
    if missing:  # pragma: no cover - guarded by the builder and schema fixtures
        raise ValueError(f"{event_type} payload is missing {sorted(missing)}")

    event = Event(
        event_type=event_type,
        event_id=f"agentinbox:{entry.seq}",
        at=entry.at,
        ask_id=ask.ask_id,
        session_id=ask.session_id,
        agent_id=ask.agent_id,
        action_identity=ask.action_identity,
        payload=payload,
        traceparent=_traceparent(ask),
    )
    return event.to_dict()


def _transition_payload(
    event_type: str, entry: AuditEntry, ask: AskRecord
) -> dict[str, Any]:
    detail = entry.payload.get("detail") or {}
    if event_type == "ask-raised":
        return {
            "class": str(ask.payload.get("class", "unknown")),
            "criticality": ask.payload.get("criticality"),
            "expires_at": to_iso(ask.expires_at),
            "requested_by": ask.payload.get("requested_by"),
        }
    if event_type == "ask-warned":
        return {"remaining_s": detail.get("remaining_s")}
    if event_type == "ask-escalated":
        return {
            "tier": detail.get("to_tier"),
            "targets_count": detail.get("recipients"),
            "revoked_claims": detail.get("revoked_claims", 0),
        }
    if event_type == "ask-answered":
        return {
            "outcome": detail.get("decision"),
            "principal": entry.payload.get("principal"),
            "channel": entry.payload.get("channel"),
            "reason": entry.payload.get("reason"),
        }
    if event_type == "ask-expired":
        return {
            "ttl_s": int((ask.expires_at - ask.created_at).total_seconds())
        }
    if event_type == "ask-cancelled":
        return {"by": entry.payload.get("principal") or "producer"}
    cause = str(detail.get("cause", "late"))
    return {
        "cause": ANSWER_CAUSE_MAP.get(cause, "binding_mismatch"),
        "cause_detail": cause,
    }


def _traceparent(ask: AskRecord) -> str | None:
    value = ask.payload.get("traceparent")
    return value if isinstance(value, str) else None


class EventTracer:
    """Drain new audit entries to a buffered sink; the decision path never waits on it."""

    def __init__(
        self,
        store: AskStore,
        *,
        sink: EventSink | None = None,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.store = store
        self.sink = (
            sink
            if isinstance(sink, BufferedEventSink)
            else BufferedEventSink(sink or ListSink(), now=now)
        )
        self._last_seq = 0

    def drain(self) -> list[dict[str, Any]]:
        emitted: list[dict[str, Any]] = []
        for entry in self.store.audit_entries():
            if entry.seq <= self._last_seq:
                continue
            self._last_seq = entry.seq
            event = event_from_entry(self.store, entry)
            if event is None:
                continue
            self.sink.write(event)
            emitted.append(event)
        return emitted


__all__ = ["ANSWER_CAUSE_MAP", "EventTracer", "event_from_entry"]
