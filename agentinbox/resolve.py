"""The ``resolve/1.0`` read path and the agentpolicy reason bridge (M3/M17).

Status is stored; **expiry is derived on read** from ``expires_at``. Nothing here writes. The
reason codes are imported from :mod:`agentinbox.reasons` (the frozen registry), so the bridge can
never drift from agentpolicy's vocabulary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.config import Config
from agentinbox.hints import author_hint
from agentinbox.lifecycle import winning_answer
from agentinbox.reasons import (
    ALLOW_ASK_APPROVED,
    ASK_FLOOD_THROTTLED,
    DENY_ACTION_IDENTITY_MISMATCH,
    DENY_ASK_DENIED,
    DENY_ASK_PENDING,
    DENY_ASK_UNKNOWN,
    HUMAN_GATE_TIMEOUT,
)
from agentinbox.store import AskRecord, AskStatus, AskStore, TransitionRecord

REASON_ALLOW = ALLOW_ASK_APPROVED
REASON_DENIED = DENY_ASK_DENIED
REASON_TIMEOUT = HUMAN_GATE_TIMEOUT
REASON_FLOOD = ASK_FLOOD_THROTTLED
REASON_PENDING = DENY_ASK_PENDING
REASON_UNKNOWN = DENY_ASK_UNKNOWN
REASON_MISMATCH = DENY_ACTION_IDENTITY_MISMATCH


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
    retry_after: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": "resolve/1.0",
            "ask_id": self.ask_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
            "answered_by": self.answered_by,
            "rescope_hint": self.rescope_hint,
            "action_identity": self.action_identity,
        }


def derived_status(ask: AskRecord, *, now: datetime) -> AskStatus:
    """Pending asks whose TTL elapsed read as expired — never resurrected by a clock jump."""
    if ask.status is AskStatus.PENDING and ask.expires_at <= now:
        return AskStatus.EXPIRED
    return ask.status


def rescope_hint(
    ask: AskRecord,
    config: Config | None = None,
    reason: str | None = None,
) -> str:
    action_class = str(ask.payload.get("class", "unknown"))
    environment = str(ask.payload.get("environment", "unknown"))
    ask_class = config.classes.get(action_class) if config is not None else None
    return author_hint(
        ask_class.rescope_hint if ask_class is not None else None,
        action_class=action_class,
        environment=environment,
        reason=reason,
    )


def resolve_ask(
    ask: AskRecord,
    *,
    now: datetime,
    transitions: Sequence[TransitionRecord] = (),
    config: Config | None = None,
    action_identity: str | None = None,
) -> ResolveResult:
    if action_identity is not None and action_identity != ask.action_identity:
        return ResolveResult(
            ask_id=ask.ask_id,
            status="deny",
            reason_code=REASON_MISMATCH,
            explanation="the resolve call presented a different action identity",
            retryable=False,
            action_identity=ask.action_identity,
        )

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
            explanation="denied by flood protection; retry after the flood window",
            retryable=True,
            action_identity=ask.action_identity,
            retry_after=_flood_retry_after(transitions, config),
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
            rescope_hint=rescope_hint(ask, config),
        )
    return ResolveResult(
        ask_id=ask.ask_id,
        status="deny",
        reason_code=REASON_DENIED,
        explanation="denied by an approver",
        retryable=False,
        action_identity=ask.action_identity,
        answered_by=answered_by,
        rescope_hint=rescope_hint(
            ask, config, None if winner is None else winner.reason
        ),
    )


def _flood_retry_after(
    transitions: Sequence[TransitionRecord], config: Config | None
) -> int | None:
    for transition in reversed(transitions):
        if transition.kind == "flood-denied":
            value = transition.detail.get("retry_after_s")
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    if config is not None:
        return config.throttle.flood_window_seconds
    return None


def resolve(
    store: AskStore,
    ask_id: str,
    *,
    now: datetime,
    config: Config | None = None,
    action_identity: str | None = None,
) -> ResolveResult:
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
    return resolve_ask(
        ask,
        now=now,
        transitions=store.transitions_for(ask_id),
        config=config,
        action_identity=action_identity,
    )


__all__ = [
    "REASON_ALLOW",
    "REASON_DENIED",
    "REASON_FLOOD",
    "REASON_MISMATCH",
    "REASON_PENDING",
    "REASON_TIMEOUT",
    "REASON_UNKNOWN",
    "ResolveResult",
    "derived_status",
    "rescope_hint",
    "resolve",
    "resolve_ask",
]
