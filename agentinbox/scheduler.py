"""Crash-safe scheduler: timeout = deny (M4).

Design: ``docs/design/v0.1.0/scheduler.md``. Timers are derived from persisted absolute UTC
instants; every firing is a CAS/append through the store, so restarts and concurrent schedulers
expire an ask exactly once. The scheduler can never allow: expiry resolves deny and the
``allows_on_expiry`` counter stays zero by construction.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from agentinbox.escalation import Escalator
from agentinbox.lifecycle import IllegalTransition, observe
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    TransitionRecord,
    utcnow,
)

DEFAULT_TICK_SECONDS = 1.0
BATCH_LIMIT = 1000


@dataclass(frozen=True, slots=True)
class TickStats:
    expired: int = 0
    warned: int = 0


class Scheduler:
    """Single-process scheduler; safe to run alongside another instance."""

    def __init__(
        self,
        store: AskStore,
        *,
        now: Callable[[], datetime] = utcnow,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
        escalator: Escalator | None = None,
    ) -> None:
        self.store = store
        self._now = now
        self.tick_seconds = tick_seconds
        self.escalator = escalator
        self._last_seen: datetime | None = None
        #: Proof for tests/reviews: expiry must never produce an allow.
        self.allows_on_expiry = 0
        self.expired_total = 0
        self.warned_total = 0

    # ------------------------------------------------------------------ clock

    def effective_now(self) -> datetime:
        """Wall clock, guarded against backwards jumps (a TTL can only shrink)."""
        wall = self._now()
        if self._last_seen is None or wall > self._last_seen:
            self._last_seen = wall
        return self._last_seen

    # ------------------------------------------------------------------ ticking

    def tick(self, *, recovered: bool = False) -> TickStats:
        now = self.effective_now()
        expired = 0
        warned = 0

        for pending in self.store.list_pending(now=now, limit=BATCH_LIMIT):
            ask = self.store.get(pending.ask_id)
            if ask is None or ask.status is not AskStatus.PENDING:
                continue

            is_due = ask.expires_at <= now
            warning_due = (
                not is_due
                and ask.warn_at is not None
                and ask.warn_at <= now
                and not _already_warned(self.store, ask.ask_id)
            )

            if recovered and (is_due or warning_due):
                self._mark_recovered(ask, now=now, expired=is_due, warned=warning_due)

            if is_due:
                if self._expire(ask, now=now):
                    expired += 1
            elif warning_due and self._warn(ask, now=now):
                warned += 1

        self.expired_total += expired
        self.warned_total += warned
        if self.escalator is not None:
            self.escalator.tick()
        return TickStats(expired=expired, warned=warned)

    def recover(self) -> TickStats:
        """Boot pass: recompute every timer from the store, fire overdue work once."""
        return self.tick(recovered=True)

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.tick()
            stop.wait(self.tick_seconds)

    def start(self) -> tuple[threading.Thread, threading.Event]:
        stop = threading.Event()
        thread = threading.Thread(target=self.run, args=(stop,), daemon=True)
        thread.start()
        return thread, stop

    # ------------------------------------------------------------------ firing

    def _expire(self, ask: AskRecord, *, now: datetime) -> bool:
        won = self.store.cas_status(
            ask.ask_id,
            expected=AskStatus.PENDING,
            new=AskStatus.EXPIRED,
            transition=TransitionRecord(
                ask_id=ask.ask_id,
                at=now,
                kind="expired",
                from_status=AskStatus.PENDING,
                to_status=AskStatus.EXPIRED,
                detail={"reason": "ttl", "retryable": False},
            ),
        )
        # Deliberately no allow path here: expiry resolves deny (D-1).
        return won

    def _warn(self, ask: AskRecord, *, now: datetime) -> bool:
        remaining = int((ask.expires_at - now).total_seconds())
        try:
            observe(
                self.store,
                ask.ask_id,
                kind="warned",
                at=now,
                detail={"remaining_s": remaining, "channel_reread": True},
            )
        except IllegalTransition:  # the ask resolved between the read and the write
            return False
        return True

    def _mark_recovered(
        self, ask: AskRecord, *, now: datetime, expired: bool, warned: bool
    ) -> None:
        self.store.append_event(
            TransitionRecord(
                ask_id=ask.ask_id,
                at=now,
                kind="scheduler-recovered",
                from_status=ask.status,
                to_status=ask.status,
                detail={"expired": expired, "warned": warned},
            )
        )


def _already_warned(store: AskStore, ask_id: str) -> bool:
    return any(item.kind == "warned" for item in store.transitions_for(ask_id))


__all__ = ["BATCH_LIMIT", "DEFAULT_TICK_SECONDS", "Scheduler", "TickStats"]
