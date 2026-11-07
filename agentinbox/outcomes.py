"""Outcome closure, execution proof, divergence, and portable packets (M29).

Design: ``docs/design/v0.1.0/outcomes.md``. Outcomes describe; they never authorize and never reopen
the decision. Every closure is an observation; divergence is a chained audit event.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from agentinbox.config import Config
from agentinbox.lifecycle import observe
from agentinbox.operations import narrative, timeline
from agentinbox.resolve import resolve
from agentinbox.scanner import scan_text
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    AuditEntry,
    TransitionRecord,
    canonical_json,
    to_iso,
    utcnow,
    verify_audit_chain,
)

CLOSURE_STATES = frozenset({"executed", "failed", "cancelled", "rolled_back", "superseded"})
COMPARISONS = frozenset({"match", "partial", "exceeded", "divergent", "unknown"})
_RECEIPT_KEYS = {"run_url", "url", "digest", "job_id", "resources"}
DIVERGENT = frozenset({"exceeded", "divergent"})


class OutcomeError(Exception):
    """A closure refused: wrong state, wrong decision, or unsafe receipt."""


def _clean_receipt(receipt: Mapping[str, Any] | None) -> dict[str, Any]:
    if receipt is None:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in receipt.items():
        if key not in _RECEIPT_KEYS:
            continue
        if key == "resources":
            if not isinstance(value, (list, tuple)):
                raise OutcomeError("receipt.resources: must be a list")
            cleaned[key] = [str(item)[:256] for item in list(value)[:50]]
        else:
            text = str(value)
            if len(text) > 2048:
                raise OutcomeError(f"receipt.{key}: too long (max 2048)")
            cleaned[key] = text
    report = scan_text(canonical_json(cleaned), artifact="execution-receipt")
    if not report.ok:
        rules = ", ".join(sorted({item.rule for item in report.findings}))
        raise OutcomeError(f"receipt contains a credential ({rules})")
    return cleaned


def _manifest(manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if manifest is None:
        return {}
    resources = manifest.get("resources") or []
    if not isinstance(resources, (list, tuple)):
        raise OutcomeError("manifest.resources: must be a list")
    constraints = manifest.get("constraints") or []
    if not isinstance(constraints, (list, tuple)):
        raise OutcomeError("manifest.constraints: must be a list")
    return {
        "fingerprint": manifest.get("fingerprint"),
        "environment": manifest.get("environment"),
        "resources": [str(item)[:256] for item in list(resources)[:100]],
        "constraints": [dict(item) for item in constraints if isinstance(item, Mapping)],
    }


def _approved_identity(ask: AskRecord, transitions: Sequence[TransitionRecord]) -> str:
    for transition in reversed(transitions):
        if transition.kind == "answer" and transition.detail.get("edited_action_identity"):
            return str(transition.detail["edited_action_identity"])
    return ask.action_identity


def _approved_resources(ask: AskRecord) -> set[str]:
    context = ask.payload.get("context") or {}
    blast = context.get("blast_radius") or {}
    approved = set()
    if blast.get("resource"):
        approved.add(str(blast["resource"]))
    for item in context.get("approved_resources") or []:
        approved.add(str(item))
    return approved


def compare_execution(
    ask: AskRecord,
    transitions: Sequence[TransitionRecord],
    manifest: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Derive the comparison from stored facts; the producer claim is untrusted."""
    executed = _manifest(manifest)
    if (
        manifest is not None
        and not executed.get("resources")
        and executed.get("fingerprint") is None
    ):
        executed = {}
    approved_identity = _approved_identity(ask, transitions)
    approved_resources = _approved_resources(ask)
    executed_resources = set(executed.get("resources") or [])
    exceeding = sorted(executed_resources - approved_resources)
    missing = sorted(approved_resources - executed_resources)
    if not executed:
        return {
            "status": "unknown",
            "approved_fingerprint": approved_identity,
            "executed_fingerprint": None,
            "approved_resources": sorted(approved_resources),
            "executed_resources": [],
            "exceeding": [],
            "missing": sorted(approved_resources),
        }
    fingerprint = executed.get("fingerprint")
    if fingerprint is not None and str(fingerprint) != approved_identity:
        status = "divergent"
    elif exceeding:
        status = "exceeded"
    elif fingerprint is not None:
        status = "match"
    else:
        status = "partial"
    return {
        "status": status,
        "approved_fingerprint": approved_identity,
        "executed_fingerprint": None if fingerprint is None else str(fingerprint),
        "approved_resources": sorted(approved_resources),
        "executed_resources": sorted(executed_resources),
        "exceeding": exceeding,
        "missing": missing,
    }


def record_outcome(
    store: AskStore,
    ask_id: str,
    *,
    state: str,
    principal: str,
    receipt: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    at: datetime | None = None,
) -> Mapping[str, Any]:
    if state not in CLOSURE_STATES:
        raise OutcomeError(f"unknown outcome state: {state}")
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    if ask.status is not AskStatus.APPROVED:
        raise OutcomeError("only an approved ask can be closed")
    moment = at or utcnow()
    transitions = store.transitions_for(ask_id)
    comparison = compare_execution(ask, transitions, manifest)
    detail = {
        "state": state,
        "principal": principal,
        "receipt": _clean_receipt(receipt),
        "comparison": comparison,
    }
    observe(store, ask_id, kind="outcome", at=moment, principal=principal, detail=detail)
    if comparison["status"] in DIVERGENT:
        store.append_audit(
            kind="outcome-divergence",
            ref_id=ask_id,
            at=moment,
            payload={
                "ask_id": ask_id,
                "status": comparison["status"],
                "approved_fingerprint": comparison["approved_fingerprint"],
                "executed_fingerprint": comparison["executed_fingerprint"],
                "exceeding": comparison["exceeding"],
            },
        )
    return detail


def latest_outcome(transitions: Sequence[TransitionRecord]) -> Mapping[str, Any] | None:
    for transition in reversed(transitions):
        if transition.kind == "outcome":
            return transition.detail
    return None


def divergence_ack(transitions: Sequence[TransitionRecord]) -> Mapping[str, Any] | None:
    for transition in reversed(transitions):
        if transition.kind == "divergence-acked":
            return transition.detail
    return None


def acknowledge_divergence(
    store: AskStore, ask_id: str, *, principal: str, at: datetime | None = None
) -> Mapping[str, Any]:
    transitions = store.transitions_for(ask_id)
    outcome = latest_outcome(transitions)
    if outcome is None or outcome.get("comparison", {}).get("status") not in DIVERGENT:
        raise OutcomeError("no divergence to acknowledge")
    detail = {"principal": principal}
    observe(
        store,
        ask_id,
        kind="divergence-acked",
        at=at or utcnow(),
        principal=principal,
        detail=detail,
    )
    return detail


def outcome_sla_pending(
    store: AskStore, config: Config, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    moment = now or utcnow()
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in reversed(store.audit_entries()):
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "created" or entry.ref_id in seen:
            continue
        seen.add(entry.ref_id)
        ask = store.get(entry.ref_id)
        if ask is None or ask.status is not AskStatus.APPROVED:
            continue
        className = str(ask.payload.get("class", ""))
        ask_class = config.classes.get(className)
        sla = None if ask_class is None else ask_class.closure_sla_seconds
        if sla is None:
            continue
        transitions = store.transitions_for(ask.ask_id)
        if latest_outcome(transitions) is not None:
            continue
        approved = next(
            (
                item
                for item in transitions
                if item.kind == "answer" and item.to_status is AskStatus.APPROVED
            ),
            None,
        )
        if approved is None:
            continue
        age = max(0, int((moment - approved.at).total_seconds()))
        if age > sla:
            findings.append(
                {
                    "ask_id": ask.ask_id,
                    "class": className,
                    "approved_at": to_iso(approved.at),
                    "age_s": age,
                    "sla_s": sla,
                    "reason": "outcome-pending-past-sla",
                }
            )
    return findings


def trace(store: AskStore, ask_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    transitions = store.transitions_for(ask_id)
    decision = resolve(store, ask_id, now=now or utcnow())
    outcome = latest_outcome(transitions)
    divergence = [
        _audit_dict(entry)
        for entry in store.audit_entries()
        if entry.kind == "outcome-divergence" and entry.ref_id == ask_id
    ]
    return {
        "ask": ask.ask_id,
        "policy": ask.payload.get("policy_ref"),
        "decision": decision.to_dict(),
        "outcome": None if outcome is None else dict(outcome),
        "divergence": divergence,
        "writeback": None,
    }


def _audit_dict(entry: AuditEntry) -> dict[str, Any]:
    return {
        "seq": entry.seq,
        "prev_hash": entry.prev_hash,
        "entry_hash": entry.entry_hash,
        "kind": entry.kind,
        "ref_id": entry.ref_id,
        "at": to_iso(entry.at),
        "payload_digest": entry.payload_digest,
        "payload": None if entry.payload is None else dict(entry.payload),
    }


def _audit_entry(raw: Mapping[str, Any]) -> AuditEntry:
    return AuditEntry(
        seq=int(raw["seq"]),
        prev_hash=str(raw["prev_hash"]),
        entry_hash=str(raw["entry_hash"]),
        kind=str(raw["kind"]),
        ref_id=str(raw["ref_id"]),
        at=datetime.fromisoformat(str(raw["at"]).replace("Z", "+00:00")),
        payload_digest=str(raw["payload_digest"]),
        payload=None if raw.get("payload") is None else dict(raw["payload"]),
    )


def verify_packet(packet: Mapping[str, Any]) -> None:
    entries = [_audit_entry(item) for item in packet.get("chain_segment") or []]
    verify_audit_chain(entries)


def decision_packet(
    store: AskStore, ask_id: str, *, now: datetime | None = None
) -> dict[str, Any]:
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    transitions = store.transitions_for(ask_id)
    packet = {
        "contract": "decision-packet/1.0",
        "ask": {
            "ask_id": ask.ask_id,
            "payload": dict(ask.payload),
            "status": ask.status.value,
            "created_at": to_iso(ask.created_at),
            "expires_at": to_iso(ask.expires_at),
            "action_identity": ask.action_identity,
        },
        "decision": resolve(store, ask_id, now=now or utcnow()).to_dict(),
        "narrative": narrative(ask, transitions),
        "outcome": (
            None if latest_outcome(transitions) is None else dict(latest_outcome(transitions) or {})
        ),
        "timeline": timeline((ask,), transitions),
        "trace": trace(store, ask_id, now=now),
        "chain_segment": [_audit_dict(entry) for entry in store.audit_entries()],
        "verification": {
            "algorithm": "sha256 hash chain over canonical payloads",
            "instructions": [
                "Recompute each entry_hash from the canonical payload; prev_hash must link.",
                "Check seq starts at 1 and increments by one.",
                "The decision is valid only if the chain verifies AND the answer "
                "transition is present.",
            ],
        },
    }
    return packet


def packet_json(packet: Mapping[str, Any]) -> str:
    return json.dumps(packet, indent=2, sort_keys=True) + "\n"


def outcome_block(
    transitions: Sequence[TransitionRecord],
) -> tuple[str, str, str, str] | None:
    outcome = latest_outcome(transitions)
    if outcome is None:
        return None
    comparison = outcome.get("comparison") or {}
    receipt = outcome.get("receipt") or {}
    ack = divergence_ack(transitions)
    divergence = "none"
    if comparison.get("status") in DIVERGENT:
        divergence = "acknowledged" if ack is not None else "UNACKNOWLEDGED"
    receipt_bits = [
        f"{key}={value}" for key, value in sorted(receipt.items()) if key != "resources"
    ]
    resources = ", ".join(str(item) for item in receipt.get("resources") or []) or "none"
    return (
        str(outcome.get("state", "unknown")),
        str(comparison.get("status", "unknown")),
        divergence,
        "; ".join(receipt_bits) + f"; resources={resources}",
    )


__all__ = [
    "CLOSURE_STATES",
    "COMPARISONS",
    "OutcomeError",
    "acknowledge_divergence",
    "compare_execution",
    "decision_packet",
    "divergence_ack",
    "latest_outcome",
    "outcome_block",
    "outcome_sla_pending",
    "packet_json",
    "record_outcome",
    "trace",
    "verify_packet",
]
