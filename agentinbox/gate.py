"""CI checkpoint: block on an ask and map the decision to the reserved exit codes (M10).

Design: ``docs/design/v0.1.0/gate.md``. The gate is a reader: it never writes a decision. The only
write it performs is a ``cancelled`` transition when the waiting process is signalled, so a killed
pipeline cannot leave an orphan pending ask.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from agentinbox.exit_codes import ExitCode
from agentinbox.lifecycle import IllegalTransition, transition
from agentinbox.resolve import REASON_TIMEOUT, resolve_ask
from agentinbox.store import AskStatus, AskStore, utcnow

DEFAULT_POLL_SECONDS = 0.25


@dataclass(frozen=True, slots=True)
class GateResult:
    code: ExitCode
    status: str
    reason: str
    ask_id: str


def gate(
    store: AskStore,
    ask_id: str,
    *,
    now: Callable[[], datetime] = utcnow,
    wait: bool = False,
    timeout: float | None = None,
    poll_interval: float = DEFAULT_POLL_SECONDS,
    cancel: threading.Event | None = None,
    sleep: Callable[[float], None] = time.sleep,
    principal: str | None = None,
) -> GateResult:
    """Resolve ``ask_id`` into an exit code; never allows without an explicit approval."""
    if store.get(ask_id) is None:
        return GateResult(ExitCode.UNAVAILABLE, "unknown", "unknown ask", ask_id)

    deadline = None if timeout is None else now() + timedelta(seconds=timeout)
    while True:
        if cancel is not None and cancel.is_set():
            return _cancel(store, ask_id, now=now, principal=principal)

        ask = store.get(ask_id)
        if ask is None:
            return GateResult(ExitCode.UNAVAILABLE, "unknown", "unknown ask", ask_id)

        result = resolve_ask(
            ask, now=now(), transitions=store.transitions_for(ask_id)
        )
        if result.status == "allow":
            return GateResult(ExitCode.APPROVED, "approved", result.reason_code, ask_id)
        if result.status == "deny":
            code = ExitCode.EXPIRED if result.reason_code == REASON_TIMEOUT else ExitCode.DENIED
            return GateResult(code, result.status, result.reason_code, ask_id)

        if not wait:
            return GateResult(ExitCode.PENDING, "pending", result.reason_code, ask_id)

        moment = now()
        if ask.expires_at <= moment:
            return GateResult(ExitCode.EXPIRED, "expired", "ask_ttl_elapsed", ask_id)
        if deadline is not None and moment >= deadline:
            return GateResult(ExitCode.EXPIRED, "expired", "gate_budget_lapsed", ask_id)
        sleep(poll_interval)


def _cancel(
    store: AskStore,
    ask_id: str,
    *,
    now: Callable[[], datetime],
    principal: str | None,
) -> GateResult:
    ask = store.get(ask_id)
    if ask is None:
        return GateResult(ExitCode.UNAVAILABLE, "unknown", "unknown ask", ask_id)

    moment = now()
    if ask.status is AskStatus.PENDING and ask.expires_at > moment:
        with contextlib.suppress(IllegalTransition):
            # Another writer may win the race; report whatever really happened.
            transition(
                store,
                ask_id,
                AskStatus.CANCELLED,
                kind="gate-cancelled",
                at=moment,
                principal=principal or "ci",
                channel="ci",
                reason="producer-cancelled",
                detail={"signal": "SIGTERM/SIGINT"},
            )

    ask = store.get(ask_id)
    if ask is None:
        return GateResult(ExitCode.UNAVAILABLE, "unknown", "unknown ask", ask_id)
    result = resolve_ask(ask, now=now(), transitions=store.transitions_for(ask_id))
    code = ExitCode.APPROVED if result.status == "allow" else ExitCode.DENIED
    reason = "cancelled" if ask.status is AskStatus.CANCELLED else result.reason_code
    return GateResult(code, ask.status.value, reason, ask_id)


__all__ = ["DEFAULT_POLL_SECONDS", "GateResult", "gate"]
