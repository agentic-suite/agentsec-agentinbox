"""The fail-closed fault catalog (M20, E9).

Design: ``docs/design/v0.1.0/fail-closed.md``. Each injected fault names the state it must leave
behind and the evidence it must emit. The invariant is absolute: no fault path produces an allow
and no fault is silently skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agentinbox.exit_codes import ExitCode


class Fault(StrEnum):
    STORE_LOCKED = "store-locked"
    STORE_CORRUPT = "store-corrupt"
    SCHEMA_MISMATCH = "schema-mismatch"
    SINK_OFFLINE = "sink-offline"
    CHANNEL_500 = "channel-500"
    SCHEDULER_KILLED = "scheduler-killed"
    CONFIG_INVALID = "config-invalid"
    CLOCK_SKEW = "clock-skew"


@dataclass(frozen=True, slots=True)
class FaultCase:
    fault: Fault
    expected_state: str
    expected_events: tuple[str, ...]
    allowed_outcomes: frozenset[ExitCode]


FAILURE_MATRIX: tuple[FaultCase, ...] = (
    FaultCase(
        Fault.STORE_LOCKED,
        "ingest refused; existing asks stay pending",
        ("store-refused",),
        frozenset({ExitCode.UNAVAILABLE}),
    ),
    FaultCase(
        Fault.STORE_CORRUPT,
        "no decision is read from an unreadable store",
        ("doctor-failed",),
        frozenset({ExitCode.UNAVAILABLE}),
    ),
    FaultCase(
        Fault.SCHEMA_MISMATCH,
        "downgrade refused; store untouched",
        ("schema-refused",),
        frozenset({ExitCode.UNAVAILABLE}),
    ),
    FaultCase(
        Fault.SINK_OFFLINE,
        "decisions unaffected; events buffered",
        ("event-gap",),
        frozenset({ExitCode.PENDING, ExitCode.APPROVED, ExitCode.DENIED}),
    ),
    FaultCase(
        Fault.CHANNEL_500,
        "ask stays pending; delivery-failed recorded",
        ("ask-delivery-failed",),
        frozenset({ExitCode.PENDING}),
    ),
    FaultCase(
        Fault.SCHEDULER_KILLED,
        "exactly-once recovery; overdue asks expire",
        ("expired", "scheduler-recovered"),
        frozenset({ExitCode.EXPIRED}),
    ),
    FaultCase(
        Fault.CONFIG_INVALID,
        "last-good config stays in force",
        ("inbox-config-changed(failed)",),
        frozenset({ExitCode.PENDING}),
    ),
    FaultCase(
        Fault.CLOCK_SKEW,
        "TTL cannot be extended; doctor warns",
        ("clock-skew",),
        frozenset({ExitCode.PENDING, ExitCode.EXPIRED}),
    ),
)


def case_for(fault: Fault) -> FaultCase:
    for case in FAILURE_MATRIX:
        if case.fault is fault:
            return case
    raise KeyError(f"no fault case for {fault}")


__all__ = ["FAILURE_MATRIX", "Fault", "FaultCase", "case_for"]
