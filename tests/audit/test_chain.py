"""The audit chain covers transitions, deliveries, and flood events (M15 item 15.1)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import (
    AskStatus,
    ChainHashMismatch,
    DeliveryRecord,
    FloodRecord,
    TransitionRecord,
)
from agentinbox.store.sqlite import SqliteStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def make_ask(store, ask_id: str = "ask_0123456789abcdef"):  # type: ignore[no-untyped-def]
    return ingest(
        payload(ask_id=ask_id),
        store=store,
        config=Config(classes={"irreversible": ClassConfig(ttl_seconds=300)}),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def test_deliveries_and_floods_append_audit_entries(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    store.record_delivery(
        DeliveryRecord(
            delivery_id="delivery_1",
            ask_id=ask.ask_id,
            channel="terminal",
            attempt=1,
            status="delivered",
            at=NOW,
        )
    )
    store.record_flood(
        FloodRecord(
            flood_id="flood_1",
            agent_id=ask.agent_id,
            session_id=ask.session_id,
            window_start=NOW,
            window_end=NOW,
            denied_count=1,
            first_ask_id=ask.ask_id,
            at=NOW,
        )
    )

    entries = store.audit_entries()
    kinds = [entry.kind for entry in entries]
    assert kinds.count("delivery") == 1
    assert kinds.count("flood") == 1
    assert entries[-1].seq == len(entries)
    store.verify_chain()


def test_append_audit_is_chained(store) -> None:  # type: ignore[no-untyped-def]
    first = store.append_audit(
        kind="export", ref_id="sess_1", at=NOW, payload={"format": "jsonl"}
    )
    second = store.append_audit(
        kind="export", ref_id="sess_1", at=NOW, payload={"format": "csv"}
    )
    assert second.seq == first.seq + 1
    assert second.prev_hash == first.entry_hash
    store.verify_chain()


def test_tampering_is_detected_by_exact_seq(tmp_path: Path) -> None:
    database = tmp_path / "inbox.db"
    store = SqliteStore(database)
    ask = make_ask(store)
    store.append_event(
        TransitionRecord(
            ask_id=ask.ask_id,
            at=NOW,
            kind="observed",
            to_status=AskStatus.PENDING,
        )
    )
    store.close()

    connection = sqlite3.connect(database)
    connection.execute("UPDATE audit SET payload_digest = ? WHERE seq = 2", ("0" * 64,))
    connection.commit()
    connection.close()

    reopened = SqliteStore(database)
    try:
        with pytest.raises(ChainHashMismatch, match="seq 2"):
            reopened.verify_chain()
    finally:
        reopened.close()
