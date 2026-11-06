"""The frozen exit-code contract, asserted as literal integers in exactly one place.

Design: ``docs/design/v0.1.0/foundation.md`` §3. Every other test and module must import this
mapping (or ``agentinbox.exit_codes``) instead of re-listing numbers, so a renumbering can
never slip in silently.
"""

from __future__ import annotations

EXIT_CODES: dict[str, int] = {
    "APPROVED": 0,
    "USAGE": 1,
    "DENIED": 2,
    "EXPIRED": 3,
    "UNAVAILABLE": 4,
    "PENDING": 5,
}

#: CI treats these as failure, per PRD 02.
FAILURE_CODES: frozenset[int] = frozenset({EXIT_CODES["DENIED"], EXIT_CODES["EXPIRED"], EXIT_CODES["UNAVAILABLE"]})
#: CI retries on this one.
RETRY_CODES: frozenset[int] = frozenset({EXIT_CODES["PENDING"]})
