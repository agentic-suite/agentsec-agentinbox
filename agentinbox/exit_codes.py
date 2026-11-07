"""The reserved exit-code contract (PRD 02 §interfaces).

Frozen for v0.1.0: producers, CI, and every later milestone consume these integers. ``0`` is
the *only* approval code; a fail-closed condition is always ``4`` and never ``1`` (which is
reserved for usage/internal mistakes) or ``2`` (a real denial).

This module is the single source; :mod:`tests.contract.exit_codes` asserts the literal values
so the contract cannot drift silently.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Reserved, stable v0.1.0 exit codes."""

    APPROVED = 0
    USAGE = 1
    DENIED = 2
    EXPIRED = 3
    UNAVAILABLE = 4
    PENDING = 5


#: CI treats these as failure (PRD 02).
FAILURE_CODES: frozenset[ExitCode] = frozenset(
    {ExitCode.DENIED, ExitCode.EXPIRED, ExitCode.UNAVAILABLE}
)

#: CI retries on these.
RETRY_CODES: frozenset[ExitCode] = frozenset({ExitCode.PENDING})


def is_failure(code: int) -> bool:
    """True when CI should mark the job failed for this exit code."""
    return code in FAILURE_CODES


def is_retry(code: int) -> bool:
    """True when CI should retry (the ask is still pending)."""
    return code in RETRY_CODES
