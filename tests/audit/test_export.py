"""Export shapes: ordered evidence with the chain included (M15 item 15.3)."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from agentinbox.audit import EXPORT_CONTRACT, export_csv, export_jsonl, export_records
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import DeliveryRecord
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload

ASK_ID = "ask_0123456789abcdef"
SESSION = "sess_20261106T030412Z"


def seed(store):  # type: ignore[no-untyped-def]
    ask = ingest(
        payload(ask_id=ASK_ID),
        store=store,
        config=Config(classes={"irreversible": ClassConfig(ttl_seconds=300)}),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask
    store.record_delivery(
        DeliveryRecord(
            delivery_id="delivery_1",
            ask_id=ASK_ID,
            channel="terminal",
            attempt=1,
            status="delivered",
            at=NOW,
            target="terminal",
        )
    )
    return ask


def test_jsonl_is_ordered_and_carries_the_chain(store) -> None:  # type: ignore[no-untyped-def]
    seed(store)
    before = len(store.audit_entries())
    records = export_records(store, session_id=SESSION, now=lambda: NOW)
    lines = [json.loads(line) for line in export_jsonl(records).splitlines()]

    assert lines[0]["type"] == "meta"
    assert lines[0]["contract"] == EXPORT_CONTRACT
    assert lines[0]["authority"] == "none"
    types = [line["type"] for line in lines]
    assert types.index("ask") < types.index("transition") < types.index("delivery")
    assert types.count("audit") == before
    assert all("prev_hash" in line for line in lines if line["type"] == "audit")
    assert any(line["type"] == "delivery" and line["status"] == "delivered" for line in lines)
    assert any(line["type"] == "ask" and line["ask_id"] == ASK_ID for line in lines)
    assert any(
        line["type"] == "ask" and "_redactions" in line["payload"] for line in lines
    )


def test_csv_has_the_same_chain_columns(store) -> None:  # type: ignore[no-untyped-def]
    seed(store)
    text = export_csv(export_records(store, ask_id=ASK_ID, now=lambda: NOW))
    rows = list(csv.DictReader(io.StringIO(text)))

    assert {row["record_type"] for row in rows} >= {"meta", "ask", "transition", "audit"}
    audit_rows = [row for row in rows if row["record_type"] == "audit"]
    assert audit_rows
    assert all(row["entry_hash"] for row in audit_rows)
    assert all(row["prev_hash"] for row in audit_rows)


def test_the_exported_chain_is_complete_and_offline_verifiable(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.store import AuditEntry, FloodRecord, verify_audit_chain

    seed(store)
    # An interleaved entry that does not belong to the exported ask.
    store.record_flood(
        FloodRecord(
            flood_id="flood_interleaved",
            agent_id="agent://other",
            session_id="sess_other",
            window_start=NOW,
            window_end=NOW,
            denied_count=1,
            first_ask_id=None,
            at=NOW,
        )
    )

    records = export_records(store, ask_id=ASK_ID, now=lambda: NOW)
    entries = [
        AuditEntry(
            seq=record["seq"],
            prev_hash=record["prev_hash"],
            entry_hash=record["entry_hash"],
            kind=record["kind"],
            ref_id=record["ref_id"],
            at=datetime.fromisoformat(record["at"].replace("Z", "+00:00")),
            payload_digest=record["payload_digest"],
            payload=record["payload"],
        )
        for record in records
        if record["type"] == "audit"
    ]

    assert [entry.seq for entry in entries] == list(range(1, len(entries) + 1))
    verify_audit_chain(entries)


def test_export_is_itself_audited(store) -> None:  # type: ignore[no-untyped-def]
    seed(store)
    before = len(store.audit_entries())
    export_records(store, session_id=SESSION, now=lambda: NOW)
    after = store.audit_entries()

    assert len(after) == before + 1
    assert after[-1].kind == "export"
    assert after[-1].ref_id == SESSION
    store.verify_chain()


def test_export_of_a_single_ask(store) -> None:  # type: ignore[no-untyped-def]
    seed(store)
    records = export_records(store, ask_id=ASK_ID, now=lambda: NOW)
    assert records[0]["ask_id"] == ASK_ID
    assert all(record.get("ask_id") in (None, ASK_ID) for record in records[1:])


def test_export_requires_a_scope(store) -> None:  # type: ignore[no-untyped-def]
    import pytest

    with pytest.raises(ValueError, match="exactly one"):
        export_records(store)


def test_export_of_an_unknown_ask(store) -> None:  # type: ignore[no-untyped-def]
    import pytest

    with pytest.raises(KeyError):
        export_records(store, ask_id="ask_missing", now=lambda: NOW)


def test_no_import_authority_exists() -> None:
    import agentinbox.audit as audit
    import agentinbox.cli as cli

    assert not any(name.startswith("import_") for name in dir(audit))
    assert "import" not in cli.COMMAND_HELP
