"""Escalation ladder: routing only, never a deadline extension (M11, R4, D-11).

Design: ``docs/design/v0.1.0/escalation.md``. A tier change advances the ask's routing and
revokes prior-tier claims in one store transaction. ``expires_at`` is immutable after ingest.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from agentinbox.bus.base import AskBus, Job, JobKind
from agentinbox.config import ClassConfig, Config, effective_ladder_delays
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    TransitionRecord,
    utcnow,
)

BATCH_LIMIT = 1000


@dataclass(frozen=True, slots=True)
class EscalationPlan:
    from_tier: str
    to_tier: str
    escalate_at: datetime | None
    revoke_tiers: tuple[str, ...]
    recipients: int


@dataclass(frozen=True, slots=True)
class EscalationStats:
    escalated: int = 0
    notified: int = 0


def initial_escalation(
    ask_class: ClassConfig, created_at: datetime
) -> tuple[str | None, datetime | None]:
    """The tier an ask starts at and the instant its successor becomes due."""
    if not ask_class.ladder:
        return None, None
    delays = effective_ladder_delays(ask_class)
    if len(ask_class.ladder) < 2:
        return ask_class.ladder[0], None
    return ask_class.ladder[0], created_at + timedelta(seconds=delays[1])


def next_escalation(config: Config, ask: AskRecord) -> EscalationPlan | None:
    ask_class = config.classes.get(str(ask.payload.get("class", "")))
    if ask_class is None or not ask_class.ladder or ask.tier is None:
        return None

    ladder = ask_class.ladder
    try:
        index = ladder.index(ask.tier)
    except ValueError:
        return None
    if index + 1 >= len(ladder):
        return None

    delays = effective_ladder_delays(ask_class)
    to_tier = ladder[index + 1]
    next_at = (
        ask.created_at + timedelta(seconds=delays[index + 2])
        if index + 2 < len(ladder)
        else None
    )
    recipients = sum(len(principals) for principals in config.roster.get(to_tier, {}).values())
    return EscalationPlan(
        from_tier=ask.tier,
        to_tier=to_tier,
        escalate_at=next_at,
        revoke_tiers=tuple(ladder[: index + 1]),
        recipients=recipients,
    )


class Escalator:
    """Fire due tier changes; the scheduler calls :meth:`tick` on every pass."""

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
        self.escalated_total = 0

    def tick(self) -> EscalationStats:
        moment = self._now()
        escalated = 0
        notified = 0
        for pending in self.store.list_pending(now=moment, limit=BATCH_LIMIT):
            ask = self.store.get(pending.ask_id)
            if ask is None or ask.escalate_at is None or ask.escalate_at > moment:
                continue
            plan = next_escalation(self.config, ask)
            if plan is None:
                continue
            if not self.escalate(ask, plan, now=moment):
                continue
            escalated += 1
            if self._notify(ask, plan, now=moment):
                notified += 1
        self.escalated_total += escalated
        return EscalationStats(escalated=escalated, notified=notified)

    def escalate(self, ask: AskRecord, plan: EscalationPlan, *, now: datetime) -> bool:
        remaining = max(0, int((ask.expires_at - now).total_seconds()))
        revoked = self.store.escalate(
            ask.ask_id,
            expected_tier=plan.from_tier,
            new_tier=plan.to_tier,
            escalate_at=plan.escalate_at,
            revoke_tiers=plan.revoke_tiers,
            transition=TransitionRecord(
                ask_id=ask.ask_id,
                at=now,
                kind="ask-escalated",
                to_status=AskStatus.PENDING,
                detail={
                    "from_tier": plan.from_tier,
                    "to_tier": plan.to_tier,
                    "recipients": plan.recipients,
                    "remaining_s": remaining,
                },
            ),
        )
        return revoked >= 0

    def _notify(self, ask: AskRecord, plan: EscalationPlan, *, now: datetime) -> bool:
        if self.bus is None:
            return False
        return self.bus.publish(
            Job(
                job_id=f"renotify:{ask.ask_id}:{plan.to_tier}",
                kind=JobKind.RENOTIFY,
                ask_id=ask.ask_id,
                created_at=now,
                payload={"tier": plan.to_tier},
            )
        )


__all__ = [
    "BATCH_LIMIT",
    "EscalationPlan",
    "EscalationStats",
    "Escalator",
    "initial_escalation",
    "next_escalation",
]
