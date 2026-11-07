"""A deliberately broken driver must fail the suite (M1 item 1.4).

The conformance suite is the admission gate: if a driver with a weakened claim check passes,
the suite is a rubber stamp and E11 is a lie.
"""

from __future__ import annotations

import pytest

from agentinbox.store.memory import MemoryStore
from tests.store import conformance


class BrokenClaimStore(MemoryStore):
    """Claims never get consumed — exactly the single-use violation E3 forbids."""

    def consume_claim(self, claim_id: str, *, ask_id: str, at) -> bool:  # type: ignore[no-untyped-def]
        return True


class BrokenCasStore(MemoryStore):
    """CAS always wins — double-resolution is impossible to catch."""

    def cas_status(self, ask_id: str, *, expected, new, transition) -> bool:  # type: ignore[no-untyped-def]
        return True


def test_broken_claim_driver_fails_conformance() -> None:
    with pytest.raises(AssertionError):
        conformance.check_claim_single_use(BrokenClaimStore())


def test_broken_cas_driver_fails_conformance() -> None:
    with pytest.raises(AssertionError):
        conformance.check_cas_single_winner(BrokenCasStore())


def test_healthy_driver_passes_the_same_checks() -> None:
    conformance.check_claim_single_use(MemoryStore())
    conformance.check_cas_single_winner(MemoryStore())
