"""Retention prunes detail with a chain marker; verification still passes (M15 item 15.4)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentinbox.audit import apply_retention, retention_cutoff
from agentinbox.config import AuditConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import DeliveryRecord
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload

ASK_ID = "ask_0123456789abcdef"


def seed(store, *, now):  # type: ignore[no-untyped-def]
    body = payload(
        ask_id=ASK_ID,
        expires_at=(now + timedelta(minutes=5))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
    )
    ask = ingest(
        body,
        store=store,
        config=Config(classes={"irreversible": ClassConfig(ttl_seconds=300)}),
        producer=ProducerIdentity.unauthenticated(),
        now=now,
    ).ask
    store.record_delivery(
        DeliveryRecord(
            delivery_id="delivery_1",
            ask_id=ASK_ID,
            channel="terminal",
            attempt=1,
            status="delivered",
            at=now,
        )
    )
    return ask


def test_pruning_records_a_marker_and_keeps_the_chain_valid(store) -> None:  # type: ignore[no-untyped-def]
    seed(store, now=NOW)
    before = len(store.audit_entries())

    transitions, deliveries = store.prune_evidence(NOW + timedelta(seconds=1), at=NOW)

    assert transitions >= 1
    assert deliveries == 1
    entries = store.audit_entries()
    assert len(entries) == before + 1
    assert entries[-1].kind == "retention-pruned"
    assert entries[-1].ref_id == "retention"
    store.verify_chain()
    assert store.transitions_for(ASK_ID) == []


def test_apply_retention_honours_never(store) -> None:  # type: ignore[no-untyped-def]
    seed(store, now=NOW - timedelta(days=365))
    config = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        audit=AuditConfig(retention="never"),
    )

    assert apply_retention(store, config, now=lambda: NOW) is None
    assert store.transitions_for(ASK_ID) != []


def test_apply_retention_prunes_old_detail(store) -> None:  # type: ignore[no-untyped-def]
    seed(store, now=NOW - timedelta(days=365))
    config = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        audit=AuditConfig(retention="90d"),
    )

    result = apply_retention(store, config, now=lambda: NOW)

    assert result is not None
    assert result[0] >= 1
    store.verify_chain()


def test_cutoffs_for_supported_policies() -> None:
    now = NOW
    assert retention_cutoff("never", now) is None
    assert retention_cutoff("90d", now) == now - timedelta(days=90)
    assert retention_cutoff("1y", now) == now - timedelta(days=365)
    assert retention_cutoff("7d", now) == now - timedelta(days=7)
    with pytest.raises(ValueError, match="unknown retention"):
        retention_cutoff("forever", now)
