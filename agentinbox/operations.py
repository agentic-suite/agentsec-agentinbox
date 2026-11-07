"""Operation bundles, handoff, incident overlay, narrative and timeline (M28).

Design: ``docs/design/v0.1.0/operations.md``. Bundles are derived on read; every child ask keeps its
own status, claims, and audit rows. There is no bundle-level decision path.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.alternatives import alternatives_for
from agentinbox.config import Config
from agentinbox.lifecycle import observe
from agentinbox.store import AskRecord, AskStatus, AskStore, TransitionRecord, to_iso, utcnow

DEFAULT_BUNDLE_WINDOW_SECONDS = 900


@dataclass(frozen=True, slots=True)
class Bundle:
    operation_id: str | None
    derived: bool
    asks: tuple[AskRecord, ...]
    phases: tuple[str, ...]
    environments: tuple[str, ...]
    counts: Mapping[str, int]
    critical_path: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "derived": self.derived,
            "ask_ids": [ask.ask_id for ask in self.asks],
            "phases": list(self.phases),
            "environments": list(self.environments),
            "counts": dict(self.counts),
            "critical_path": None if self.critical_path is None else dict(self.critical_path),
        }

    def render(self) -> str:
        label = self.operation_id or "derived"
        lines = [
            f"OPERATION {label}{' (derived)' if self.derived else ''}",
            "  asks: "
            + ", ".join(f"{key}={value}" for key, value in sorted(self.counts.items())),
            "  environments: " + (", ".join(self.environments) or "unknown"),
            "  phases: " + " → ".join(self.phases),
        ]
        if self.critical_path is not None:
            lines.append(
                "  critical path: "
                f"{self.critical_path.get('ask_id')} "
                f"(expires {self.critical_path.get('expires_at')})"
            )
        else:
            lines.append("  critical path: none (nothing pending)")
        for ask in self.asks:
            lines.append(
                f"  {ask.ask_id}  {ask.status.value}  "
                f"{ask.payload.get('action', 'unknown')}  "
                f"{ask.payload.get('class', 'unknown')}"
            )
        return "\n".join(lines)


def derive_bundle(
    store: AskStore,
    ask: AskRecord,
    *,
    window_seconds: int = DEFAULT_BUNDLE_WINDOW_SECONDS,
    operation_id: str | None = None,
) -> Bundle:
    context = ask.payload.get("context") or {}
    declared = operation_id or (
        str(context.get("operation_id")) if context.get("operation_id") else None
    )
    candidates: list[AskRecord] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "created":
            continue
        candidate = store.get(entry.ref_id)
        if candidate is None:
            continue
        if declared is not None:
            candidate_operation = (candidate.payload.get("context") or {}).get(
                "operation_id"
            )
            if str(candidate_operation) != declared:
                continue
        else:
            if candidate.session_id != ask.session_id:
                continue
            if str(candidate.payload.get("class")) != str(ask.payload.get("class")):
                continue
            if abs((candidate.created_at - ask.created_at).total_seconds()) > window_seconds:
                continue
        candidates.append(candidate)
    candidates.sort(key=lambda item: (item.created_at, item.ask_id))
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.status.value] = counts.get(candidate.status.value, 0) + 1
    phases: list[str] = []
    for candidate in candidates:
        phase = str((candidate.payload.get("context") or {}).get("phase") or "")
        if not phase:
            phase = "decided" if candidate.status in AskStatus.terminal() else "review"
        if phase not in phases:
            phases.append(phase)
    environments = sorted(
        {
            str(candidate.payload.get("environment", "unknown"))
            for candidate in candidates
        }
    )
    pending = [item for item in candidates if item.status is AskStatus.PENDING]
    critical = min(pending, key=lambda item: item.expires_at) if pending else None
    return Bundle(
        operation_id=declared,
        derived=declared is None,
        asks=tuple(candidates),
        phases=tuple(phases or ["review"]),
        environments=tuple(environments),
        counts=counts,
        critical_path=(
            None
            if critical is None
            else {"ask_id": critical.ask_id, "expires_at": to_iso(critical.expires_at)}
        ),
    )


def claim_ask(
    store: AskStore,
    ask_id: str,
    *,
    principal: str,
    at: datetime | None = None,
) -> None:
    observe(
        store,
        ask_id,
        kind="claimed",
        at=at or utcnow(),
        principal=principal,
        detail={"routing_only": True},
    )


def assign_ask(
    store: AskStore,
    ask_id: str,
    *,
    assignee: str,
    by: str,
    at: datetime | None = None,
) -> None:
    observe(
        store,
        ask_id,
        kind="assigned",
        at=at or utcnow(),
        principal=by,
        detail={"assignee": assignee, "routing_only": True},
    )


def record_handoff(
    store: AskStore,
    ask_id: str,
    *,
    outgoing: str,
    incoming: str,
    note: str,
    open_questions: Sequence[str] = (),
    evidence: Sequence[str] = (),
    at: datetime | None = None,
) -> Mapping[str, Any]:
    ask = store.get(ask_id)
    if ask is None:
        raise KeyError(f"unknown ask: {ask_id}")
    moment = at or utcnow()
    detail = {
        "outgoing": outgoing,
        "incoming": incoming,
        "note": note,
        "open_questions": list(open_questions),
        "evidence": list(evidence),
        "remaining_s": max(0, int((ask.expires_at - moment).total_seconds())),
    }
    observe(store, ask_id, kind="handoff", at=moment, principal=outgoing, detail=detail)
    return detail


def handoff_for(transitions: Sequence[TransitionRecord]) -> Mapping[str, Any] | None:
    for transition in reversed(transitions):
        if transition.kind == "handoff":
            return transition.detail
    return None


def handoff_fields(handoff: Mapping[str, Any]) -> tuple[Any, ...]:
    from agentinbox.card import Field

    questions = ", ".join(str(item) for item in handoff.get("open_questions") or []) or "none"
    evidence = ", ".join(str(item) for item in handoff.get("evidence") or []) or "none"
    return (
        Field(
            "from → to",
            f"{handoff.get('outgoing')} → {handoff.get('incoming')}",
        ),
        Field("note", str(handoff.get("note") or "none")),
        Field("open questions", questions),
        Field("evidence gathered", evidence),
        Field("remaining ttl", f"{handoff.get('remaining_s')}s"),
    )


def incident_state(config: Config) -> dict[str, Any]:
    incident = config.incident
    return {
        "enabled": incident.enabled,
        "owner": incident.owner,
        "reason": incident.reason,
        "ttl_scale": incident.ttl_scale,
        "classes": list(incident.classes),
    }


def record_incident(
    store: AskStore, config: Config, *, at: datetime | None = None
) -> bool:
    """Audit the declared incident state once; returns True when it wrote a marker."""
    state = incident_state(config)
    store.append_audit(
        kind="incident-on" if state["enabled"] else "incident-off",
        ref_id="incident",
        at=at or utcnow(),
        payload=state,
    )
    return True


def incident_banner(state: Mapping[str, Any]) -> str:
    return (
        f"INCIDENT MODE: {state.get('reason')} (owner={state.get('owner')}; "
        f"ttl_scale={state.get('ttl_scale')}; denies still deny)"
    )


def timeline(
    asks: Sequence[AskRecord], transitions: Sequence[TransitionRecord]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_ask = {ask.ask_id: ask for ask in asks}
    for transition in sorted(
        transitions, key=lambda item: (item.at, item.ask_id, item.seq)
    ):
        rows.append(
            {
                "ask_id": transition.ask_id,
                "seq": transition.seq,
                "at": to_iso(transition.at),
                "kind": transition.kind,
                "from_status": (
                    None
                    if transition.from_status is None
                    else transition.from_status.value
                ),
                "to_status": transition.to_status.value,
                "principal": transition.principal,
                "channel": transition.channel,
                "reason": transition.reason,
                "detail": dict(transition.detail),
                "operation_id": (
                    (by_ask[transition.ask_id].payload.get("context") or {}).get(
                        "operation_id"
                    )
                    if transition.ask_id in by_ask
                    else None
                ),
            }
        )
    return rows


def narrative(ask: AskRecord, transitions: Sequence[TransitionRecord]) -> str:
    readiness = ask.payload.get("_readiness") or {}
    policy = ask.payload.get("policy_ref") or {}
    answer = next(
        (
            item
            for item in transitions
            if item.kind in {"answer", "expired", "cancelled"}
        ),
        None,
    )
    lines = [
        f"Decision narrative — {ask.ask_id}",
        f"Ask: {ask.payload.get('action', 'unknown')} via {ask.payload.get('tool', 'unknown')} "
        f"for {ask.payload.get('requested_by', 'unknown')} "
        "("
        f"class={ask.payload.get('class', 'unknown')}, "
        f"env={ask.payload.get('environment', 'unknown')})",
        f"Rule: {policy.get('rule_id', 'unknown')} {policy.get('policy_version', '')} "
        f"{policy.get('clause', '')}".strip(),
        f"Evidence: {readiness.get('evidence', 'unknown')} "
        f"(freshness: {readiness.get('freshness', 'unknown')})",
    ]
    if readiness.get("missing"):
        lines.append("Missing: " + ", ".join(str(item) for item in readiness["missing"]))
    if readiness.get("contradictions"):
        lines.append(
            "Contradictions: " + ", ".join(str(item) for item in readiness["contradictions"])
        )
    offered = [str(item.get("id")) for item in alternatives_for(ask)]
    if offered:
        lines.append("Alternatives offered: " + ", ".join(offered))
    if answer is not None:
        detail = dict(answer.detail)
        who = answer.principal or "nobody"
        lines.append(
            f"Outcome: {answer.to_status.value} by {who} "
            f"({answer.channel or 'unknown'}) at {to_iso(answer.at)}"
        )
        if answer.reason:
            lines.append(f"Reason: {answer.reason}")
        if detail.get("constraints"):
            lines.append(
                "Constraints: "
                + ", ".join(str(item.get("id")) for item in detail["constraints"])
            )
        if detail.get("edits"):
            lines.append("Edits: " + ", ".join(sorted(detail["edits"])))
        outcome = next(
            (item for item in reversed(transitions) if item.kind == "outcome"), None
        )
        if outcome is not None:
            comparison = outcome.detail.get("comparison") or {}
            lines.append(
                f"Execution: {outcome.detail.get('state')} "
                f"(comparison={comparison.get('status', 'unknown')})"
            )
            if comparison.get("exceeding"):
                lines.append(
                    "Exceeding: " + ", ".join(str(item) for item in comparison["exceeding"])
                )
    else:
        lines.append("Outcome: still pending")
    return "\n".join(lines)


def bundle_export(store: AskStore, bundle: Bundle) -> dict[str, Any]:
    transitions: list[TransitionRecord] = []
    for ask in bundle.asks:
        transitions.extend(store.transitions_for(ask.ask_id))
    return {
        "contract": "bundle/1.0",
        "bundle": bundle.to_dict(),
        "asks": [
            {
                "ask_id": ask.ask_id,
                "status": ask.status.value,
                "payload": dict(ask.payload),
                "created_at": to_iso(ask.created_at),
                "expires_at": to_iso(ask.expires_at),
            }
            for ask in bundle.asks
        ],
        "timeline": timeline(bundle.asks, transitions),
    }


__all__ = [
    "Bundle",
    "assign_ask",
    "bundle_export",
    "claim_ask",
    "derive_bundle",
    "handoff_for",
    "incident_banner",
    "incident_state",
    "narrative",
    "record_handoff",
    "record_incident",
    "timeline",
]
