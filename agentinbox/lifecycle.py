"""The v0.1.0 ask lifecycle: one edge table, enforced in one place (M3).

Design: ``docs/design/v0.1.0/lifecycle.md``. Nothing else may write a status directly; every
change goes through :func:`transition` so the guard, the transition log, and the audit chain
agree by construction. Terminal is terminal — a late answer is an observation, not a decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from agentinbox.store import (
    AskStatus,
    AskStore,
    TransitionRecord,
)

#: The only legal edges in v0.1.0. Terminal states have no outgoing edges.
LEGAL_EDGES: Mapping[AskStatus, frozenset[AskStatus]] = {
    AskStatus.PENDING: AskStatus.terminal(),
}

#: Evidence-only observations that remain meaningful after the decision (movement ≠ truth).
POST_TERMINAL_OBSERVATIONS = frozenset({"late-answer", "delivery-skipped", "delivery-failed"})


class LifecycleError(Exception):
    """Base class for lifecycle refusals."""


class IllegalTransition(LifecycleError):
    """The requested edge is not in the v0.1.0 state machine."""


class UnknownAsk(LifecycleError):
    """No such ask."""


def assert_can_transition(current: AskStatus, new: AskStatus) -> None:
    if new not in LEGAL_EDGES.get(current, frozenset()):
        raise IllegalTransition(f"illegal transition: {current.value} -> {new.value}")


def transition(
    store: AskStore,
    ask_id: str,
    new: AskStatus,
    *,
    kind: str,
    at: datetime,
    principal: str | None = None,
    channel: str | None = None,
    claim_id: str | None = None,
    reason: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> bool:
    """Apply a legal edge; return ``False`` if another writer won the race.

    An illegal attempt is recorded as a non-state-changing observation **before** raising, so
    attempts are evidence (PRD 30 groundwork) and never silent.
    """
    ask = store.get(ask_id)
    if ask is None:
        raise UnknownAsk(f"unknown ask: {ask_id}")

    try:
        assert_can_transition(ask.status, new)
    except IllegalTransition:
        store.append_event(
            TransitionRecord(
                ask_id=ask_id,
                at=at,
                kind="illegal-transition-rejected",
                from_status=ask.status,
                to_status=ask.status,
                detail={"attempted": new.value, "reason": reason or "guard"},
            )
        )
        raise

    return store.cas_status(
        ask_id,
        expected=ask.status,
        new=new,
        transition=TransitionRecord(
            ask_id=ask_id,
            at=at,
            kind=kind,
            from_status=ask.status,
            to_status=new,
            principal=principal,
            channel=channel,
            claim_id=claim_id,
            reason=reason,
            detail=detail or {},
        ),
    )


def observe(
    store: AskStore,
    ask_id: str,
    *,
    kind: str,
    at: datetime,
    principal: str | None = None,
    channel: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> None:
    """Append a non-state-changing observation (delivered, warned, late-answer, …)."""
    ask = store.get(ask_id)
    if ask is None:
        raise UnknownAsk(f"unknown ask: {ask_id}")

    if ask.status in AskStatus.terminal() and kind not in POST_TERMINAL_OBSERVATIONS:
        raise IllegalTransition(
            f"{kind!r} is not allowed after terminal state {ask.status.value}"
        )

    store.append_event(
        TransitionRecord(
            ask_id=ask_id,
            at=at,
            kind=kind,
            from_status=ask.status,
            to_status=ask.status,
            principal=principal,
            channel=channel,
            detail=detail or {},
        )
    )


def winning_answer(transitions: Sequence[TransitionRecord]) -> TransitionRecord | None:
    """The transition that decided the ask (approved/denied), if any."""
    for item in reversed(transitions):
        if (
            item.to_status in {AskStatus.APPROVED, AskStatus.DENIED}
            and item.from_status == AskStatus.PENDING
        ):
            return item
    return None


__all__ = [
    "LEGAL_EDGES",
    "POST_TERMINAL_OBSERVATIONS",
    "IllegalTransition",
    "LifecycleError",
    "UnknownAsk",
    "assert_can_transition",
    "observe",
    "transition",
    "winning_answer",
]
