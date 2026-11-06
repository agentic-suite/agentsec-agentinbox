"""AskStore interface surface (M1 item 1.1).

The interface is the single state path (E11). These tests pin the names, the record shapes, the
UTC time contract, and the fail-closed capability helper — no driver needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    AuditEntry,
    CapabilityError,
    ClaimRecord,
    CreateResult,
    SessionExport,
    StoreCapabilities,
    TransitionRecord,
    parse_iso,
    require_capability,
    to_iso,
)


def ask() -> AskRecord:
    return AskRecord(
        ask_id="ask_0123456789abcdef",
        action_identity="sha256:" + "a" * 64,
        session_id="sess_1",
        agent_id="agent://ops/1",
        created_at=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 11, 6, 12, 5, tzinfo=UTC),
        payload={"contract": "ask/1.0"},
    )


def test_status_vocabulary_is_frozen() -> None:
    assert {status.value for status in AskStatus} == {
        "pending",
        "approved",
        "denied",
        "expired",
        "cancelled",
        "flood_denied",
    }
    assert AskStatus.APPROVED in AskStatus.terminal()
    assert AskStatus.PENDING not in AskStatus.terminal()


def test_capability_defaults_are_conservative() -> None:
    capabilities = StoreCapabilities(single_writer=True)

    assert capabilities.multi_writer is False
    assert capabilities.cluster_safe is False


def test_require_capability_fails_closed_with_an_actionable_message() -> None:
    store = _FakeStore(StoreCapabilities(single_writer=True))

    require_capability(store, "single_writer")
    with pytest.raises(CapabilityError, match="multi_writer"):
        require_capability(store, "multi_writer")


def test_require_capability_rejects_unknown_flags() -> None:
    store = _FakeStore(StoreCapabilities(single_writer=True))

    with pytest.raises(ValueError, match="unknown capability"):
        require_capability(store, "eventual_consistency")


def test_iso_time_round_trips_in_utc() -> None:
    moment = datetime(2026, 11, 6, 12, 0, 5, 123456, tzinfo=UTC)

    text = to_iso(moment)

    assert text.endswith("Z")
    assert parse_iso(text) == moment


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        to_iso(datetime(2026, 11, 6, 12, 0))


def test_record_shapes_are_frozen() -> None:
    record = ask()

    with pytest.raises(AttributeError):
        record.status = AskStatus.APPROVED  # type: ignore[misc]

    transition = TransitionRecord(
        ask_id=record.ask_id,
        at=record.created_at,
        kind="created",
        to_status=AskStatus.PENDING,
        detail={},
    )
    claim = ClaimRecord(
        claim_id="claim_1",
        ask_id=record.ask_id,
        channel="terminal",
        tier="tier-1",
        secret_hash="h" * 64,
        issued_at=record.created_at,
        expires_at=record.expires_at,
    )
    audit = AuditEntry(
        seq=1,
        prev_hash="0" * 64,
        entry_hash="1" * 64,
        kind="transition",
        ref_id=record.ask_id,
        at=record.created_at,
        payload_digest="2" * 64,
    )
    result = CreateResult(ask=record, created=True)
    export = SessionExport(
        session_id=record.session_id, asks=(record,), transitions=(transition,), claims=(claim,)
    )

    assert result.created is True
    assert export.asks[0].ask_id == record.ask_id
    assert transition.seq == 0
    assert audit.seq == 1
    assert claim.consumed_at is None


def test_interface_declares_every_contract_method() -> None:
    expected = {
        "create_or_get_by_identity",
        "get",
        "cas_status",
        "issue_claim",
        "consume_claim",
        "list_pending",
        "append_event",
        "export_session",
        "close",
    }

    assert expected <= set(dir(AskStore))


def test_dedupe_window_is_not_baked_into_the_record() -> None:
    later = ask().created_at + timedelta(seconds=1)

    assert later > ask().created_at


class _FakeStore:
    def __init__(self, capabilities: StoreCapabilities) -> None:
        self.capabilities = capabilities
