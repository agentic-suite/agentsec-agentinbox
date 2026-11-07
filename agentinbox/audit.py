"""Audit export and retention (M15, R5).

Design: ``docs/design/v0.1.0/audit.md``. Exports are read-only evidence: ordered asks, transitions,
deliveries, and the **whole chain**, as JSONL or CSV. There is no import path — evidence leaves, it
never re-enters as authority. Retention prunes detail rows and appends a chain marker.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from agentinbox.config import Config
from agentinbox.store import AskStore, canonical_json, to_iso, utcnow

EXPORT_CONTRACT = "export/1.0"
RETENTION_MARKER = "retention-pruned"

CSV_COLUMNS = (
    "record_type",
    "ask_id",
    "seq",
    "at",
    "kind",
    "from_status",
    "to_status",
    "principal",
    "channel",
    "claim_id",
    "reason",
    "detail",
    "status",
    "prev_hash",
    "entry_hash",
    "payload_digest",
)


def export_records(
    store: AskStore,
    *,
    session_id: str | None = None,
    ask_id: str | None = None,
    format: str = "jsonl",
    now: Callable[[], datetime] = utcnow,
) -> list[dict[str, Any]]:
    """Build the ordered evidence export and audit the export itself."""
    if (session_id is None) == (ask_id is None):
        raise ValueError("export exactly one of session_id or ask_id")

    if session_id is not None:
        session_export = store.export_session(session_id)
        asks = list(session_export.asks)
        transitions = list(session_export.transitions)
        scope: dict[str, Any] = {"session_id": session_id}
        ref_id = session_id
    else:
        assert ask_id is not None
        ask = store.get(ask_id)
        if ask is None:
            raise KeyError(f"unknown ask: {ask_id}")
        asks = [ask]
        transitions = store.transitions_for(ask_id)
        scope = {"ask_id": ask_id}
        ref_id = ask_id

    ask_ids = [item.ask_id for item in asks]
    known = set(ask_ids)
    deliveries = [
        delivery for item in ask_ids for delivery in store.list_deliveries(item)
    ]
    audit = [entry for entry in store.audit_entries() if entry.ref_id in known]

    moment = now()
    records: list[dict[str, Any]] = [
        {
            "type": "meta",
            "contract": EXPORT_CONTRACT,
            "generated_at": to_iso(moment),
            "authority": "none",
            "format": format,
            **scope,
            "asks": len(asks),
            "transitions": len(transitions),
            "deliveries": len(deliveries),
            "audit_entries": len(audit),
        }
    ]
    for ask in asks:
        records.append(
            {
                "type": "ask",
                "ask_id": ask.ask_id,
                "action_identity": ask.action_identity,
                "session_id": ask.session_id,
                "agent_id": ask.agent_id,
                "status": ask.status.value,
                "created_at": to_iso(ask.created_at),
                "expires_at": to_iso(ask.expires_at),
                "decided_at": None if ask.decided_at is None else to_iso(ask.decided_at),
                "tier": ask.tier,
                "payload": dict(ask.payload),
            }
        )
    for transition in transitions:
        records.append(
            {
                "type": "transition",
                "ask_id": transition.ask_id,
                "seq": transition.seq,
                "at": to_iso(transition.at),
                "kind": transition.kind,
                "from_status": (
                    None if transition.from_status is None else transition.from_status.value
                ),
                "to_status": transition.to_status.value,
                "principal": transition.principal,
                "channel": transition.channel,
                "claim_id": transition.claim_id,
                "reason": transition.reason,
                "detail": dict(transition.detail),
            }
        )
    for delivery in deliveries:
        records.append(
            {
                "type": "delivery",
                "ask_id": delivery.ask_id,
                "channel": delivery.channel,
                "attempt": delivery.attempt,
                "status": delivery.status,
                "at": to_iso(delivery.at),
                "target": delivery.target,
                "error": delivery.error,
            }
        )
    for entry in audit:
        records.append(
            {
                "type": "audit",
                "seq": entry.seq,
                "prev_hash": entry.prev_hash,
                "entry_hash": entry.entry_hash,
                "kind": entry.kind,
                "ref_id": entry.ref_id,
                "at": to_iso(entry.at),
                "payload_digest": entry.payload_digest,
            }
        )

    store.append_audit(
        kind="export",
        ref_id=ref_id,
        at=moment,
        payload={"format": format, **scope, "records": len(records)},
    )
    return records


def export_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(canonical_json(record) + "\n" for record in records)


def export_csv(records: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        row = dict(record)
        row["record_type"] = record["type"]
        if "detail" not in row and "payload" in row:
            row["detail"] = canonical_json(record["payload"])
        elif "detail" in row:
            row["detail"] = canonical_json(record["detail"])
        if isinstance(row.get("detail"), (dict, list)):
            row["detail"] = canonical_json(row["detail"])
        writer.writerow(row)
    return buffer.getvalue()


def retention_cutoff(policy: str, now: datetime) -> datetime | None:
    if policy == "never":
        return None
    if policy == "1y":
        return now - timedelta(days=365)
    if policy.endswith("d") and policy[:-1].isdigit():
        return now - timedelta(days=int(policy[:-1]))
    raise ValueError(f"unknown retention policy: {policy!r}")


def apply_retention(
    store: AskStore, config: Config, *, now: Callable[[], datetime] = utcnow
) -> tuple[int, int] | None:
    moment = now()
    cutoff = retention_cutoff(config.audit.retention, moment)
    if cutoff is None:
        return None
    return store.prune_evidence(cutoff, at=moment)


__all__ = [
    "CSV_COLUMNS",
    "EXPORT_CONTRACT",
    "RETENTION_MARKER",
    "apply_retention",
    "export_csv",
    "export_jsonl",
    "export_records",
    "retention_cutoff",
]
