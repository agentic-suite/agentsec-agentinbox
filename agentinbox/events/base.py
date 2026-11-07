"""agentwatch security events: types, sinks, and buffering (M16).

Design: ``docs/design/v0.1.0/events.md``. Events are facts derived from the audit chain — no
inference, no enrichment, and no untrusted text. A downed sink buffers; overflow is marked, never
silent; the decision path never waits on the sink.
"""

from __future__ import annotations

import os
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from agentinbox.store import canonical_json, to_iso, utcnow

EVENT_VERSION = "0.2.0"
EMITTER = "agentinbox"

EVENT_TYPES = frozenset(
    {
        "ask-raised",
        "ask-delivered",
        "ask-delivery-failed",
        "ask-warned",
        "ask-escalated",
        "ask-answered",
        "ask-expired",
        "ask-cancelled",
        "ask-flood",
        "answer-rejected",
    }
)

#: Payload keys the published schema requires per event type (fixture truth).
PAYLOAD_REQUIREMENTS: dict[str, frozenset[str]] = {
    "ask-raised": frozenset({"class", "criticality", "expires_at", "requested_by"}),
    "ask-delivered": frozenset({"channel", "attempt"}),
    "ask-delivery-failed": frozenset({"channel", "attempt", "error"}),
    "ask-warned": frozenset({"remaining_s"}),
    "ask-escalated": frozenset({"tier", "targets_count", "revoked_claims"}),
    "ask-answered": frozenset({"outcome", "principal", "channel"}),
    "ask-expired": frozenset({"ttl_s"}),
    "ask-cancelled": frozenset({"by"}),
    "ask-flood": frozenset({"window", "denied_count", "first_ask_id"}),
    "answer-rejected": frozenset({"cause"}),
}


@dataclass(frozen=True, slots=True)
class Event:
    event_type: str
    event_id: str
    at: datetime
    ask_id: str
    session_id: str
    agent_id: str
    action_identity: str
    payload: dict[str, Any] = field(default_factory=dict)
    traceparent: str | None = None
    event_version: str = EVENT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_version": self.event_version,
            "event_type": self.event_type,
            "emitter": EMITTER,
            "event_id": self.event_id,
            "at": to_iso(self.at),
            "ask_id": self.ask_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "action_identity": self.action_identity,
            "traceparent": self.traceparent,
            "payload": self.payload,
        }


class EventSink(Protocol):
    def write(self, record: dict[str, Any]) -> None: ...


class JsonlEventSink:
    """Append-only JSONL sink (mode 0600)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def write(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
        )
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")


class ListSink:
    """In-memory sink for tests and embedding."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def write(self, record: dict[str, Any]) -> None:
        self.records.append(record)


class BufferedEventSink:
    """Bounded buffer in front of a sink; owns recovery and gap markers."""

    def __init__(
        self,
        inner: EventSink,
        *,
        capacity: int = 1000,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.inner = inner
        self.capacity = capacity
        self._buffer: deque[dict[str, Any]] = deque()
        self._now = now
        self.dropped = 0
        self.gaps = 0

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def write(self, record: dict[str, Any]) -> None:
        try:
            self.inner.write(record)
            return
        except Exception:
            # The sink is down: buffer, never block and never raise into the decision path.
            if len(self._buffer) >= self.capacity:
                self._buffer.popleft()
                self.dropped += 1
            self._buffer.append(record)

    def flush(self) -> int:
        sent = 0
        while self._buffer:
            record = self._buffer[0]
            try:
                self.inner.write(record)
            except Exception:
                break
            self._buffer.popleft()
            sent += 1
        if not self._buffer and self.dropped:
            marker = {
                "event_version": EVENT_VERSION,
                "event_type": "event-gap",
                "emitter": EMITTER,
                "event_id": f"gap:{to_iso(self._now())}",
                "at": to_iso(self._now()),
                "payload": {"dropped": self.dropped},
            }
            try:
                self.inner.write(marker)
            except Exception:
                return sent
            self.gaps += 1
            self.dropped = 0
        return sent


__all__ = [
    "EMITTER",
    "EVENT_TYPES",
    "EVENT_VERSION",
    "PAYLOAD_REQUIREMENTS",
    "BufferedEventSink",
    "Event",
    "EventSink",
    "JsonlEventSink",
    "ListSink",
]
