"""Policy-learning and governance insights from stored decisions (M31).

Design: ``docs/design/v0.1.0/insights.md``. Insights are aggregated and redacted: they carry shapes,
counts, time ranges, and a representative ask id — never raw arguments. Queries are read-only except
an explicit per-principal calibration access log and an explicit insight-to-action record.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from agentinbox.config import Config
from agentinbox.outcomes import latest_outcome
from agentinbox.scanner import scan_text
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    TransitionRecord,
    canonical_json,
    to_iso,
    utcnow,
)

INSIGHT_KINDS = frozenset(
    {
        "repetitive-approval",
        "deny-cluster",
        "escalation-hotspot",
        "evidence-gap",
        "outcome-tuning",
    }
)
ACTION_KINDS = frozenset({"config_diff", "runbook", "grant"})


class InsightsError(Exception):
    """An insight query or export refused by the privacy/access guard."""


@dataclass(frozen=True, slots=True)
class Insight:
    insight_id: str
    kind: str
    title: str
    summary: str
    counts: Mapping[str, Any]
    first_seen: datetime
    last_seen: datetime
    representative_ask: str | None
    recommendation: str
    proposed_diff: Mapping[str, Any]
    expires_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "counts": dict(self.counts),
            "time_range": {"first": to_iso(self.first_seen), "last": to_iso(self.last_seen)},
            "representative_ask": self.representative_ask,
            "recommendation": self.recommendation,
            "proposed_diff": dict(self.proposed_diff),
            "expires_at": to_iso(self.expires_at),
        }

    def render(self) -> str:
        return (
            f"{self.title}\n  {self.summary}\n  representative: {self.representative_ask}\n"
            f"  recommendation: {self.recommendation}"
        )


@dataclass(frozen=True, slots=True)
class InsightAction:
    insight_id: str
    kind: str
    reviewer: str
    origin: str
    body: str
    at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "kind": self.kind,
            "reviewer": self.reviewer,
            "origin": self.origin,
            "body": self.body,
            "at": to_iso(self.at),
        }


def _asks(store: AskStore) -> list[AskRecord]:
    seen: set[str] = set()
    asks: list[AskRecord] = []
    for entry in store.audit_entries():
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "created" or entry.ref_id in seen:
            continue
        seen.add(entry.ref_id)
        ask = store.get(entry.ref_id)
        if ask is not None:
            asks.append(ask)
    asks.sort(key=lambda item: (item.created_at, item.ask_id))
    return asks


def _shape(ask: AskRecord) -> str:
    arguments = ask.payload.get("arguments") or {}
    fields = ",".join(
        f"{key}:{type(value).__name__}" for key, value in sorted(arguments.items())
    )
    return (
        f"{ask.payload.get('class')}|{ask.payload.get('tool')}|"
        f"{ask.payload.get('action')}|{fields}"
    )


def _insight_id(kind: str, material: str) -> str:
    digest = hashlib.sha256(f"{kind}:{material}".encode()).hexdigest()[:12]
    return f"ins-{kind}-{digest}"


def _answers(transitions: Sequence[TransitionRecord]) -> list[TransitionRecord]:
    return [item for item in transitions if item.kind == "answer"]


def _time_range(asks: Sequence[AskRecord]) -> tuple[datetime, datetime]:
    return asks[0].created_at, asks[-1].created_at


def _expiry(last_seen: datetime, config: Config) -> datetime:
    return last_seen + timedelta(seconds=config.insights.stale_after_seconds)


def _repetitive(
    store: AskStore,
    config: Config,
    asks: Sequence[AskRecord],
    now: datetime,
) -> list[Insight]:
    groups: dict[str, list[AskRecord]] = {}
    for ask in asks:
        groups.setdefault(_shape(ask), []).append(ask)
    found: list[Insight] = []
    for shape, members in groups.items():
        if len(members) < config.insights.approval_threshold:
            continue
        approved = denied = 0
        divergent = 0
        for ask in members:
            transitions = store.transitions_for(ask.ask_id)
            answers = _answers(transitions)
            if any(item.to_status is AskStatus.APPROVED for item in answers):
                approved += 1
            if any(item.to_status is AskStatus.DENIED for item in answers):
                denied += 1
            outcome = latest_outcome(transitions)
            if outcome and outcome.get("comparison", {}).get("status") in {"exceeded", "divergent"}:
                divergent += 1
        if approved < config.insights.approval_threshold:
            continue
        if denied > max(0, len(members) // 20) or divergent > max(0, len(members) // 20):
            continue
        first, last = _time_range(members)
        found.append(
            Insight(
                insight_id=_insight_id("repetitive-approval", shape),
                kind="repetitive-approval",
                title=f"Repetitive approvals: {members[0].payload.get('class')}",
                summary=(
                    f"{approved} approvals of the same shape with low outcome variance; "
                    "a bounded window, standing rule, or producer self-certification may fit."
                ),
                counts={"approvals": approved, "asks": len(members)},
                first_seen=first,
                last_seen=last,
                representative_ask=members[0].ask_id,
                recommendation=(
                    "propose a timeboxed class grant or a standing rule; "
                    "apply only through reviewed config"
                ),
                proposed_diff={
                    "class": members[0].payload.get("class"),
                    "action": "grant",
                    "max_uses": max(1, approved // 2),
                },
                expires_at=_expiry(last, config),
            )
        )
    return found


def _deny_clusters(
    store: AskStore,
    config: Config,
    asks: Sequence[AskRecord],
    now: datetime,
) -> list[Insight]:
    groups: dict[tuple[str, str], list[AskRecord]] = {}
    for ask in asks:
        answers = _answers(store.transitions_for(ask.ask_id))
        if not any(item.to_status is AskStatus.DENIED for item in answers):
            continue
        key = (str(ask.payload.get("reason_code")), _shape(ask))
        groups.setdefault(key, []).append(ask)
    found: list[Insight] = []
    for (reason, shape), members in groups.items():
        if len(members) < config.insights.deny_threshold:
            continue
        first, last = _time_range(members)
        found.append(
            Insight(
                insight_id=_insight_id("deny-cluster", f"{reason}:{shape}"),
                kind="deny-cluster",
                title=f"Noisy denials: {reason}",
                summary=(
                    f"{len(members)} denials share reason code {reason!r} for one shape; "
                    "this class/policy may be generating noise."
                ),
                counts={"denials": len(members), "reason_code": reason},
                first_seen=first,
                last_seen=last,
                representative_ask=members[0].ask_id,
                recommendation=(
                    "consider a TTL change, a class split, or relaxing an evidence requirement"
                ),
                proposed_diff={
                    "class": members[0].payload.get("class"),
                    "reason_code": reason,
                    "options": ["ttl", "class_split", "evidence_relaxation"],
                },
                expires_at=_expiry(last, config),
            )
        )
    return found


def _hotspots(
    store: AskStore,
    config: Config,
    asks: Sequence[AskRecord],
    now: datetime,
) -> list[Insight]:
    groups: dict[tuple[str, str, int], list[AskRecord]] = {}
    for ask in asks:
        for transition in store.transitions_for(ask.ask_id):
            if transition.kind not in {"escalated", "expired"}:
                continue
            tier = str(
                transition.detail.get("to_tier") or ask.tier or "unassigned"
            )
            groups.setdefault(
                (str(ask.payload.get("class")), tier, transition.at.hour), []
            ).append(ask)
    found: list[Insight] = []
    for (className, tier, hour), members in groups.items():
        if len(members) < config.insights.hotspot_threshold:
            continue
        first, last = _time_range(members)
        recommendation = (
            f"route {className}/{tier} to an on-call roster at {hour:02d}:00 UTC"
            if hour < 6
            else (
                f"shorten the TTL or add a daytime {tier} rota for "
                f"{className} at {hour:02d}:00 UTC"
            )
        )
        found.append(
            Insight(
                insight_id=_insight_id("escalation-hotspot", f"{className}:{tier}:{hour}"),
                kind="escalation-hotspot",
                title=f"Escalation hotspot: {className} x {tier} x {hour:02d}:00",
                summary=(
                    f"{len(members)} escalations/expiries at hour {hour:02d} UTC for {tier}; "
                    "the same tier keeps carrying the pattern."
                ),
                counts={"events": len(members), "tier": tier, "hour_utc": hour},
                first_seen=first,
                last_seen=last,
                representative_ask=members[0].ask_id,
                recommendation=recommendation,
                proposed_diff={
                    "class": className,
                    "tier": tier,
                    "hour_utc": hour,
                    "routing": "on-call" if hour < 6 else "daytime-rota",
                },
                expires_at=_expiry(last, config),
            )
        )
    return found


def _evidence_gaps(
    store: AskStore,
    config: Config,
    asks: Sequence[AskRecord],
    now: datetime,
) -> list[Insight]:
    groups: dict[tuple[str, str], list[AskRecord]] = {}
    for ask in asks:
        answers = _answers(store.transitions_for(ask.ask_id))
        if not any(item.to_status is AskStatus.DENIED for item in answers):
            continue
        readiness = ask.payload.get("_readiness") or {}
        for dimension in readiness.get("missing") or []:
            groups.setdefault((str(ask.payload.get("class")), str(dimension)), []).append(ask)
    found: list[Insight] = []
    for (className, dimension), members in groups.items():
        first, last = _time_range(members)
        found.append(
            Insight(
                insight_id=_insight_id("evidence-gap", f"{className}:{dimension}"),
                kind="evidence-gap",
                title=f"Evidence gap: {className} lacks {dimension}",
                summary=(
                    f"{len(members)} denials for {className} had missing {dimension}; "
                    "tighten the class evidence requirement or teach the producer."
                ),
                counts={"denials": len(members), "missing": dimension},
                first_seen=first,
                last_seen=last,
                representative_ask=members[0].ask_id,
                recommendation=f"consider requiring {dimension} for {className}",
                proposed_diff={"class": className, "required_evidence_add": dimension},
                expires_at=_expiry(last, config),
            )
        )
    return found


def _outcome_tuning(
    store: AskStore,
    config: Config,
    asks: Sequence[AskRecord],
    now: datetime,
) -> list[Insight]:
    groups: dict[str, list[AskRecord]] = {}
    for ask in asks:
        outcome = latest_outcome(store.transitions_for(ask.ask_id))
        if outcome is None:
            continue
        if outcome.get("comparison", {}).get("status") not in {"exceeded", "divergent"}:
            continue
        groups.setdefault(str(ask.payload.get("class")), []).append(ask)
    found: list[Insight] = []
    for className, members in groups.items():
        if len(members) < 2:
            continue
        first, last = _time_range(members)
        found.append(
            Insight(
                insight_id=_insight_id("outcome-tuning", className),
                kind="outcome-tuning",
                title=f"Outcome divergence: {className}",
                summary=(
                    f"{len(members)} approvals for {className} were followed by an exceeded or "
                    "divergent execution; propose hardening, never an automatic change."
                ),
                counts={"divergences": len(members)},
                first_seen=first,
                last_seen=last,
                representative_ask=members[0].ask_id,
                recommendation=(
                    "propose a typed confirmation, a tier bump, or a shorter TTL for review"
                ),
                proposed_diff={
                    "class": className,
                    "require_typed_confirmation": True,
                    "tier_bump": True,
                    "ttl_seconds": "halve after review",
                },
                expires_at=_expiry(last, config),
            )
        )
    return found


def compute_insights(
    store: AskStore, config: Config, *, now: datetime | None = None
) -> list[Insight]:
    moment = now or utcnow()
    asks = _asks(store)
    found: list[Insight] = []
    found.extend(_repetitive(store, config, asks, moment))
    found.extend(_deny_clusters(store, config, asks, moment))
    found.extend(_hotspots(store, config, asks, moment))
    found.extend(_evidence_gaps(store, config, asks, moment))
    found.extend(_outcome_tuning(store, config, asks, moment))
    active = [item for item in found if item.expires_at > moment]
    return sorted(active, key=lambda item: (item.kind, item.insight_id))


def calibration(
    store: AskStore,
    config: Config,
    *,
    principal: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    moment = now or utcnow()
    groups: dict[str, dict[str, Any]] = {}
    for ask in _asks(store):
        shape = _shape(ask)
        bucket = groups.setdefault(
            shape,
            {
                "class": ask.payload.get("class"),
                "asks": 0,
                "approved": 0,
                "denied": 0,
                "time_to_answer_s": [],
                "deny_reasons": {},
            },
        )
        bucket["asks"] += 1
        transitions = store.transitions_for(ask.ask_id)
        for transition in _answers(transitions):
            if transition.to_status is AskStatus.APPROVED:
                bucket["approved"] += 1
            elif transition.to_status is AskStatus.DENIED:
                bucket["denied"] += 1
                reason = str(ask.payload.get("reason_code"))
                bucket["deny_reasons"][reason] = bucket["deny_reasons"].get(reason, 0) + 1
            bucket["time_to_answer_s"].append(
                max(0, int((transition.at - ask.created_at).total_seconds()))
            )
    aggregate: list[dict[str, Any]] = []
    for bucket in groups.values():
        decisions = bucket["approved"] + bucket["denied"]
        times = bucket["time_to_answer_s"]
        aggregate.append(
            {
                "class": bucket["class"],
                "asks": bucket["asks"],
                "approved": bucket["approved"],
                "denied": bucket["denied"],
                "approve_rate": (
                    None
                    if decisions == 0
                    else round(bucket["approved"] / decisions, 3)
                ),
                "median_time_to_answer_s": None if not times else int(median(times)),
                "deny_reasons": dict(bucket["deny_reasons"]),
            }
        )
    result: dict[str, Any] = {"contract": "calibration/1.0", "aggregate": aggregate}
    if principal is None:
        return result
    if principal not in config.insights.governance_principals:
        raise InsightsError("per-principal calibration requires governance access")
    store.append_audit(
        kind="insight-calibration-access",
        ref_id="insights",
        at=moment,
        payload={"principal": principal},
    )
    per_principal: dict[str, dict[str, int]] = {}
    for ask in _asks(store):
        for transition in _answers(store.transitions_for(ask.ask_id)):
            who = transition.principal or "unknown"
            row = per_principal.setdefault(who, {"approved": 0, "denied": 0})
            if transition.to_status is AskStatus.APPROVED:
                row["approved"] += 1
            elif transition.to_status is AskStatus.DENIED:
                row["denied"] += 1
    result["per_principal"] = per_principal
    result["access_logged_for"] = principal
    return result


def to_action(
    store: AskStore,
    insight: Insight,
    *,
    kind: str,
    reviewer: str,
    now: datetime | None = None,
) -> InsightAction:
    if kind not in ACTION_KINDS:
        raise InsightsError(f"unknown action kind: {kind}")
    if not reviewer.strip():
        raise InsightsError("a reviewer is required")
    if kind == "config_diff":
        lines = ["# proposed config change — apply via reviewed PR", "[classes.review]"]
        body = "\n".join([*lines, f"# {insight.recommendation}"])
        for key, value in insight.proposed_diff.items():
            body += f"\n# {key} = {value!r}"
    elif kind == "runbook":
        body = f"Runbook task: review {insight.insight_id} — {insight.recommendation}"
    else:
        body = f"Grant proposal for {insight.proposed_diff} (review required)"
    moment = now or utcnow()
    store.append_audit(
        kind="insight-action",
        ref_id=insight.insight_id,
        at=moment,
        payload={
            "insight_id": insight.insight_id,
            "kind": kind,
            "reviewer": reviewer,
            "origin": insight.kind,
        },
    )
    return InsightAction(
        insight_id=insight.insight_id,
        kind=kind,
        reviewer=reviewer,
        origin=insight.kind,
        body=body,
        at=moment,
    )


def export_insights(insights: Sequence[Insight]) -> dict[str, Any]:
    payload = {
        "contract": "insights/1.0",
        "insights": [item.to_dict() for item in insights],
    }
    report = scan_text(canonical_json(payload), artifact="insights-export")
    if not report.ok:
        rules = ", ".join(sorted({item.rule for item in report.findings}))
        raise InsightsError(f"insight export contains sensitive data ({rules})")
    return payload


__all__ = [
    "ACTION_KINDS",
    "INSIGHT_KINDS",
    "Insight",
    "InsightAction",
    "InsightsError",
    "calibration",
    "compute_insights",
    "export_insights",
    "to_action",
]
