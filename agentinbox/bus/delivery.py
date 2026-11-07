"""Delivery wiring: channels subscribe to jobs; every attempt is evidence (M9 item 9.6)."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from agentinbox.bus.base import Job, JobKind
from agentinbox.card import build_card
from agentinbox.lifecycle import IllegalTransition, UnknownAsk, observe
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    DeliveryRecord,
    utcnow,
)

DEFAULT_MAX_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class DeliveryWiring:
    """Consume delivery jobs: record every attempt, fail over, never decide."""

    store: AskStore
    channels: Sequence[object]
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    now: Callable[[], datetime] = utcnow
    backoff: Callable[[int], None] = time.sleep
    on_digest: Callable[[Job], None] | None = None
    _seen: set[str] = field(default_factory=set, compare=False)

    def handle(self, job: Job) -> None:
        if job.kind is JobKind.DIGEST:
            if self.on_digest is not None:
                self.on_digest(job)
            return

        ask = self.store.get(job.ask_id)
        if ask is None:
            self._observe(job, "delivery-skipped", {"reason": "unknown ask"})
            return
        if ask.status is not AskStatus.PENDING or ask.expires_at <= self.now():
            self._observe(
                job,
                "delivery-skipped",
                {"reason": "not pending", "status": ask.status.value},
            )
            return
        if job.job_id in self._seen:
            return

        card = build_card(
            ask, now=self.now(), transitions=self.store.transitions_for(ask.ask_id)
        )
        for channel in self.channels:
            if self._attempt(job, ask, channel, card):
                self._seen.add(job.job_id)
                return

    # ------------------------------------------------------------------ internals

    def _attempt(
        self, job: Job, ask: AskRecord, channel: object, card: object
    ) -> bool:
        name = str(getattr(channel, "name", "unknown"))
        for attempt in range(1, self.max_attempts + 1):
            moment = self.now()
            try:
                channel.deliver(ask, card)  # type: ignore[attr-defined]
            except Exception as exc:  # every failure is accounted for
                self.store.record_delivery(
                    DeliveryRecord(
                        delivery_id=f"{job.job_id}:{name}:{attempt}",
                        ask_id=ask.ask_id,
                        channel=name,
                        attempt=attempt,
                        status="failed",
                        at=moment,
                        target=name,
                        error=str(exc)[:500],
                    )
                )
                self._observe(
                    job,
                    "delivery-failed",
                    {"channel": name, "attempt": attempt, "error": str(exc)[:200]},
                )
                if attempt < self.max_attempts:
                    self.backoff(attempt)
                continue

            self.store.record_delivery(
                DeliveryRecord(
                    delivery_id=f"{job.job_id}:{name}:{attempt}",
                    ask_id=ask.ask_id,
                    channel=name,
                    attempt=attempt,
                    status="delivered",
                    at=moment,
                    target=name,
                )
            )
            self._observe(job, "ask-delivered", {"channel": name, "attempt": attempt})
            return True
        return False

    def _observe(self, job: Job, kind: str, detail: dict[str, object]) -> None:
        try:
            observe(
                self.store,
                job.ask_id,
                kind=kind,
                at=self.now(),
                detail={"job": job.job_id, "kind": job.kind.value, **detail},
            )
        except (IllegalTransition, UnknownAsk):
            # The ask resolved (or vanished) while we were delivering: evidence may not
            # rewrite truth, and there is nowhere to record movement for an unknown ask.
            return


__all__ = ["DEFAULT_MAX_ATTEMPTS", "DeliveryWiring"]
