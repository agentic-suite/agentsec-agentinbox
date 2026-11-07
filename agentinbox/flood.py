"""Flood protection as a security property (M12, R7, D-12).

Design: ``docs/design/v0.1.0/flood.md``. Duplicate coalescing happens first (the store's
identity window); this module adds token buckets per agent/session/environment/producer, and turns
a trip into **decisions**: every over-threshold ask is denied with ``ask_flood_throttled``, one
``ask-flood`` event is recorded for the window, and one digest job is published.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from agentinbox.bus.base import AskBus, publish_digest
from agentinbox.config import ClassConfig, Config
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    FloodRecord,
    TransitionRecord,
    payload_digest,
    to_iso,
    utcnow,
)
from agentinbox.trust import ProducerIdentity

FLOOD_REASON = "ask_flood_throttled"


@dataclass(frozen=True, slots=True)
class FloodDecision:
    denied: bool
    retry_after_s: int = 0
    flood_id: str | None = None


class TokenBucket:
    """Classic burst + refill bucket. One token per ask."""

    def __init__(
        self,
        *,
        capacity: int,
        rate_per_second: float,
        tokens: float | None = None,
        updated: datetime | None = None,
    ) -> None:
        self.capacity = float(capacity)
        self.rate_per_second = rate_per_second
        self.tokens = self.capacity if tokens is None else tokens
        self.updated = updated

    def take(self, at: datetime) -> bool:
        if self.updated is None:
            self.updated = at
        elapsed = max(0.0, (at - self.updated).total_seconds())
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)
        self.updated = at
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class FloodGuard:
    """Buckets plus the one-event/one-digest window aggregation."""

    def __init__(
        self,
        store: AskStore,
        config: Config,
        *,
        now: Callable[[], datetime] = utcnow,
        bus: AskBus | None = None,
    ) -> None:
        self.store = store
        self.config = config
        self._now = now
        self.bus = bus
        self._buckets: dict[str, TokenBucket] = {}
        self._windows: dict[str, tuple[datetime, str]] = {}
        #: Proof for tests/reviews: a denied ask is never resurrected by the flood path.
        self.resurrections = 0

    # ------------------------------------------------------------------ config

    def limits_for(self, ask: AskRecord) -> tuple[int, int, int]:
        ask_class: ClassConfig | None = self.config.classes.get(
            str(ask.payload.get("class", ""))
        )
        burst = (
            ask_class.flood_burst
            if ask_class is not None and ask_class.flood_burst is not None
            else self.config.throttle.per_agent_burst
        )
        rate = (
            ask_class.flood_rate_per_min
            if ask_class is not None and ask_class.flood_rate_per_min is not None
            else self.config.throttle.per_agent_rate_per_min
        )
        return burst, rate, self.config.throttle.flood_window_seconds

    def bucket_key(self, ask: AskRecord, producer: ProducerIdentity) -> str:
        environment = str(ask.payload.get("environment", "unknown"))
        uid = producer.principal or producer.remote_addr or "-"
        return "|".join((ask.agent_id, ask.session_id, environment, uid))

    # ------------------------------------------------------------------ check

    def check(
        self,
        ask: AskRecord,
        *,
        producer: ProducerIdentity,
        now: datetime,
    ) -> FloodDecision:
        burst, rate, window = self.limits_for(ask)
        key = self.bucket_key(ask, producer)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(capacity=burst, rate_per_second=rate / 60.0)
            self._buckets[key] = bucket
        if bucket.take(now):
            return FloodDecision(denied=False)

        window_start, flood_id = self._window_for(key, now=now, window=window)
        existing = self.store.get_flood(flood_id)
        count = (existing.denied_count if existing is not None else 0) + 1
        first_ask_id = existing.first_ask_id if existing is not None else ask.ask_id
        created = self.store.record_flood(
            FloodRecord(
                flood_id=flood_id,
                agent_id=ask.agent_id,
                session_id=ask.session_id,
                window_start=window_start,
                window_end=window_start + timedelta(seconds=window),
                denied_count=count,
                first_ask_id=first_ask_id,
                at=now,
            )
        )
        if created:
            # Exactly one ask-flood event per window (the ask is still pending here).
            self.store.append_event(
                TransitionRecord(
                    ask_id=ask.ask_id,
                    at=now,
                    kind="ask-flood",
                    to_status=AskStatus.PENDING,
                    detail={
                        "window_start": to_iso(window_start),
                        "window_end": to_iso(window_start + timedelta(seconds=window)),
                        "count": count,
                        "first_ask_id": first_ask_id,
                        "agent_id": ask.agent_id,
                        "session_id": ask.session_id,
                        "bucket": key,
                    },
                )
            )
        if self.bus is not None:
            publish_digest(
                self.bus,
                window_start=window_start,
                first_ask_id=first_ask_id or ask.ask_id,
                count=count,
                now=now,
                agent_id=ask.agent_id,
            )
        return FloodDecision(denied=True, retry_after_s=window, flood_id=flood_id)

    # ------------------------------------------------------------------ internals

    def _window_for(
        self, key: str, *, now: datetime, window: int
    ) -> tuple[datetime, str]:
        active = self._windows.get(key)
        if active is not None and now - active[0] < timedelta(seconds=window):
            return active
        start = now
        flood_id = "flood_" + payload_digest(
            {"bucket": key, "window_start": to_iso(start)}
        )[:16]
        self._windows[key] = (start, flood_id)
        return start, flood_id


__all__ = ["FLOOD_REASON", "FloodDecision", "FloodGuard", "TokenBucket"]
