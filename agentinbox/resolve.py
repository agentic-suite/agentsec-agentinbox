"""The ``resolve/1.0`` read path (M3).

Status is stored; **expiry is derived on read** from ``expires_at``. Nothing here writes: a read
that discovers an overdue ask returns deny, and M4's scheduler is what records the transition
exactly once.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.lifecycle import winning_answer
from agentinbox.store import AskRecord, AskStatus, AskStore, TransitionRecord

REASON_ALLOW = "allow_ask_approved"
REASON_DENIED = "deny_ask_denied"
REASON_TIMEOUT = "human_gate_timeout"
REASON_FLOOD = "ask_flood_throttled"
REASON_PENDING = "deny_ask_pending"
REASON_UNKNOWN = "deny_ask_unknown"


@dataclass(frozen=True, slots=True)
class ResolveResult:
    ask_id: str
    status: str
    reason_code: str
    explanation: str
    retryable: bool
    action_identity: str | None
    answered_by: str | None = None
    rescope_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": "resolve/1.0",
            "ask_id": self.ask_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "retryable": self.retryable,
            "answered_by": self.answered_by,
            "rescope_hint": self.rescope_hint,
            "action_identity": self.action_identity,
        }


def derived_status(ask: AskRecord, *, now: datetime) -> AskStatus:
    """Pending asks whose TTL elapsed read as expired — never resurrected by a clock jump."""
    if ask.status is AskStatus.PENDING and ask.expires_at <= now:
        return AskStatus.EXPIRED
    return ask.status


def rescope_hint(ask: AskRecord) -> str:
    action_class = str(ask.payload.get("class", "unknown"))
    return (
        f"narrow the target, or request a standing approval for class {action_class} "
        "(timeout is a deny, not a failure)"
    )


def resolve_ask(
    ask: AskRecord, *, now: datetime, transitions: Sequence[TransitionRecord] = ()
) -> ResolveResult:
    status = derived_status(ask, now=now)

    if status is AskStatus.PENDING:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="pending",
            reason_code=REASON_PENDING,
            explanation="no answer yet",
            retryable=True,
            action_identity=ask.action_identity,
        )

    winner = winning_answer(transitions)
    answered_by = winner.principal if winner is not None else None

    if status is AskStatus.APPROVED:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="allow",
            reason_code=REASON_ALLOW,
            explanation="approved by an authenticated approver",
            retryable=False,
            action_identity=ask.action_identity,
            answered_by=answered_by,
        )
    if status is AskStatus.FLOOD_DENIED:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="deny",
            reason_code=REASON_FLOOD,
            explanation="denied by flood protection",
            retryable=False,
            action_identity=ask.action_identity,
        )
    if status is AskStatus.CANCELLED:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="deny",
            reason_code=REASON_DENIED,
            explanation="cancelled by the producer",
            retryable=False,
            action_identity=ask.action_identity,
        )
    if status is AskStatus.EXPIRED:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="deny",
            reason_code=REASON_TIMEOUT,
            explanation="no answer before expiry",
            retryable=False,
            action_identity=ask.action_identity,
            rescope_hint=rescope_hint(ask),
        )
    return ResolveResult(
        ask_id=ask.ask_id,
        status="deny",
        reason_code=REASON_DENIED,
        explanation="denied by an approver",
        retryable=False,
        action_identity=ask.action_identity,
        answered_by=answered_by,
    )


def resolve(store: AskStore, ask_id: str, *, now: datetime) -> ResolveResult:
    ask = store.get(ask_id)
    if ask is None:
        return ResolveResult(
            ask_id=ask_id,
            status="deny",
            reason_code=REASON_UNKNOWN,
            explanation="unknown ask",
            retryable=False,
            action_identity=None,
        )
    return resolve_ask(ask, now=now, transitions=store.transitions_for(ask_id))


__all__ = [
    "REASON_ALLOW",
    "REASON_DENIED",
    "REASON_FLOOD",
    "REASON_PENDING",
    "REASON_TIMEOUT",
    "REASON_UNKNOWN",
    "ResolveResult",
    "derived_status",
    "rescope_hint",
    "resolve",
    "resolve_ask",
]
