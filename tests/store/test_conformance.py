"""Conformance suite runs against every driver (M1 item 1.4)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from agentinbox.store import AskStore
from agentinbox.store.memory import MemoryStore
from agentinbox.store.sqlite import SqliteStore
from tests.store import conformance


@pytest.fixture(params=["memory", "sqlite"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[AskStore]:
    if request.param == "memory":
        yield MemoryStore()
        return
    driver = SqliteStore(tmp_path / "home" / "inbox.db")
    try:
        yield driver
    finally:
        driver.close()


@pytest.mark.parametrize(
    "check",
    [
        conformance.check_idempotent_create,
        conformance.check_dedupe_window_expires,
        conformance.check_cas_single_winner,
        conformance.check_claim_single_use,
        conformance.check_expired_claim_rejected,
        conformance.check_gapless_audit_seq,
        conformance.check_pending_read_is_deterministic,
        conformance.check_resolved_asks_leave_pending,
        conformance.check_delivery_accounting,
        conformance.check_transition_read,
        conformance.check_claim_revocation,
        conformance.check_escalation_cas,
        conformance.check_flood_accounting,
        conformance.check_audit_covers_entities,
        conformance.check_capabilities_fail_closed,
    ],
    ids=lambda check: check.__name__,
)
def test_driver_passes_conformance(store: AskStore, check) -> None:  # type: ignore[no-untyped-def]
    check(store)
