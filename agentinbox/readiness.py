"""Ask readiness scoring, contradictions, and the producer repair contract (M26).

Design: ``docs/design/v0.1.0/readiness.md``. Deterministic rules over producer-declared fields —
no ML, no inference. The score is advisory to **delivery** only: it can reject an ask before storage
or add a banner, and it never approves anything.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.config import ClassConfig, Config
from agentinbox.contract import ContractError
from agentinbox.store import AskRecord, AskStore, parse_iso

DIMENSIONS = (
    "completeness",
    "target_specificity",
    "reversibility_clarity",
    "evidence_presence",
    "trust_provenance",
    "contradiction",
)
REVERSIBILITY_VALUES = frozenset(
    {"reversible", "partially_reversible", "irreversible"}
)
GENERIC_TARGETS = frozenset(
    {
        "",
        "unknown",
        "the database",
        "database",
        "db",
        "prod",
        "production",
        "the service",
        "service",
        "it",
        "the system",
    }
)
_DESTRUCTIVE = re.compile(
    r"\b(drop|delete|truncate|rm\s+-rf|force|overwrite|alter|destroy)\b", re.IGNORECASE
)
_READ_ONLY = re.compile(r"(read[-_ ]?only|dry[-_ ]?run|\bselect\b)", re.IGNORECASE)

_FIXES: dict[str, str] = {
    "completeness": "fill the missing required fields",
    "target_specificity": "name the exact resource",
    "reversibility_clarity": "state reversibility (reversible/partially_reversible/irreversible)",
    "evidence_presence": "attach the evidence the class requires",
    "trust_provenance": "sign the ask with a producer key",
    "contradiction": "remove the contradictory signals",
}


@dataclass(frozen=True, slots=True)
class Readiness:
    score: float
    band: str
    dimensions: Mapping[str, float]
    missing: tuple[str, ...]
    contradictions: tuple[str, ...]
    evidence_label: str
    freshness: str
    repairs: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "dimensions": dict(self.dimensions),
            "missing": list(self.missing),
            "contradictions": list(self.contradictions),
            "evidence": self.evidence_label,
            "freshness": self.freshness,
            "repairs": [dict(item) for item in self.repairs],
        }


class ReadinessRejection(ContractError):
    """A non-decisionable ask; carries the machine-usable repair contract."""

    def __init__(self, readiness: Readiness) -> None:
        super().__init__("readiness", "ask is not decisionable")
        self.readiness = readiness
        self.details = {
            "reason_code": "ask_not_decisionable",
            "dimensions": [dict(item) for item in readiness.repairs],
            "contradictions": list(readiness.contradictions),
            "retry": "after-repair",
            "readiness": readiness.to_dict(),
        }


def band_for(score: float) -> str:
    if score >= 0.8:
        return "green"
    if score >= 0.5:
        return "yellow"
    return "red"


def evaluate(
    body: Mapping[str, Any],
    *,
    config: Config,
    producer_authenticated: bool,
    now: datetime,
) -> Readiness:
    """Score a validated ask body. Pure function: reads config, writes nothing."""
    class_name = str(body.get("class", ""))
    ask_class = config.classes.get(class_name)
    context = body.get("context") or {}
    if not isinstance(context, Mapping):
        context = {}
    arguments = body.get("arguments") or {}
    blast = context.get("blast_radius") or {}
    if not isinstance(blast, Mapping):
        blast = {}
    policy = body.get("policy_ref") or {}
    if not isinstance(policy, Mapping):
        policy = {}

    completeness, complete_fixes = _completeness(body, arguments, policy, context)
    target, target_fix = _target_specificity(blast)
    reversibility, reversibility_fix = _reversibility(blast)
    evidence_score, evidence_label, evidence_fix, freshness = _evidence(
        context, ask_class, now
    )
    trust = 1.0 if producer_authenticated else 0.5
    contradictions = detect_contradictions(
        body, context=context, arguments=arguments, producer_authenticated=producer_authenticated
    )
    contradiction_score = 1.0 if not contradictions else 0.0

    dimensions = {
        "completeness": completeness,
        "target_specificity": target,
        "reversibility_clarity": reversibility,
        "evidence_presence": evidence_score,
        "trust_provenance": trust,
        "contradiction": contradiction_score,
    }
    score = round(sum(dimensions.values()) / len(DIMENSIONS), 4)
    fixes: list[Mapping[str, Any]] = []
    for dimension, value in dimensions.items():
        if value >= 0.999:
            continue
        if dimension == "completeness":
            fixes.extend(
                {"name": "completeness", "fix": fix, "score": value}
                for fix in complete_fixes
            )
        elif dimension == "target_specificity" and target_fix:
            fixes.append({"name": dimension, "fix": target_fix, "score": value})
        elif dimension == "reversibility_clarity" and reversibility_fix:
            fixes.append({"name": dimension, "fix": reversibility_fix, "score": value})
        elif dimension == "evidence_presence" and evidence_fix:
            fixes.append({"name": dimension, "fix": evidence_fix, "score": value})
        elif dimension == "contradiction":
            fixes.append(
                {
                    "name": dimension,
                    "fix": "remove: " + ", ".join(contradictions),
                    "score": value,
                }
            )
        else:
            fixes.append({"name": dimension, "fix": _FIXES[dimension], "score": value})

    missing = tuple(
        dimension
        for dimension, value in dimensions.items()
        if value < 0.999
    )
    return Readiness(
        score=score,
        band=band_for(score),
        dimensions=dimensions,
        missing=missing,
        contradictions=contradictions,
        evidence_label=evidence_label,
        freshness=freshness,
        repairs=tuple(fixes),
    )


def _completeness(
    body: Mapping[str, Any],
    arguments: Mapping[str, Any],
    policy: Mapping[str, Any],
    context: Mapping[str, Any],
) -> tuple[float, tuple[str, ...]]:
    checks = (
        ("arguments", bool(arguments)),
        ("policy_ref.rule_id", bool(policy.get("rule_id"))),
        ("policy_ref.clause", bool(policy.get("clause"))),
        ("requested_by", bool(body.get("requested_by"))),
        ("environment", bool(body.get("environment"))),
        ("data_class", bool(body.get("data_class"))),
        ("context", bool(context)),
    )
    missing = tuple(f"fill {name}" for name, ok in checks if not ok)
    return (len(checks) - len(missing)) / len(checks), missing


def _target_specificity(blast: Mapping[str, Any]) -> tuple[float, str | None]:
    resource = str(blast.get("resource") or "").strip().lower()
    if resource and resource not in GENERIC_TARGETS:
        return 1.0, None
    return 0.0, "name the exact resource"


def _reversibility(blast: Mapping[str, Any]) -> tuple[float, str | None]:
    value = str(blast.get("reversibility") or "").strip().lower()
    if value in REVERSIBILITY_VALUES:
        return 1.0, None
    return 0.0, "state reversibility"


def _evidence(
    context: Mapping[str, Any], ask_class: ClassConfig | None, now: datetime
) -> tuple[float, str, str | None, str]:
    required = tuple(ask_class.required_evidence) if ask_class is not None else ()
    evidence = context.get("evidence")
    present = _evidence_names(evidence)
    if not required:
        return 1.0, "strong", None, _freshness(evidence, ask_class, now)
    found = [name for name in required if name in present]
    ratio = len(found) / len(required)
    if ratio >= 1.0:
        label = "strong"
    elif ratio >= 0.5:
        label = "partial"
    elif ratio > 0.0:
        label = "weak"
    else:
        label = "absent"
    missing = [name for name in required if name not in present]
    fix = "attach: " + ", ".join(missing) if missing else None
    return ratio, label, fix, _freshness(evidence, ask_class, now)


def _evidence_names(evidence: object) -> set[str]:
    if isinstance(evidence, Mapping):
        return {str(key) for key in evidence}
    if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        names: set[str] = set()
        for item in evidence:
            if isinstance(item, Mapping):
                names.add(str(item.get("kind") or item.get("name") or "artifact"))
            else:
                names.add(str(item))
        return names
    return set()


def _freshness(
    evidence: object, ask_class: ClassConfig | None, now: datetime
) -> str:
    artifacts: list[Mapping[str, Any]] = []
    if isinstance(evidence, Mapping):
        for value in evidence.values():
            if isinstance(value, Mapping):
                artifacts.append(value)
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        artifacts.extend(item for item in evidence if isinstance(item, Mapping))
    if not artifacts:
        return "unknown freshness"
    max_age = ask_class.evidence_max_age_seconds if ask_class is not None else 86400
    fresh = 0
    stale = 0
    unknown = 0
    for artifact in artifacts:
        stamp = artifact.get("at") or artifact.get("fetched_at")
        if not stamp:
            unknown += 1
            continue
        try:
            moment = parse_iso(str(stamp))
        except ValueError:
            unknown += 1
            continue
        age = (now - moment).total_seconds()
        if age > max_age:
            stale += 1
        else:
            fresh += 1
    if unknown:
        return "unknown freshness"
    if stale and fresh:
        return "mixed"
    return "stale" if stale else "fresh"


def detect_contradictions(
    body: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    arguments: Mapping[str, Any],
    producer_authenticated: bool,
) -> tuple[str, ...]:
    """Return the contradiction ids for this ask (empty = consistent)."""
    found: list[str] = []
    environment = str(body.get("environment", "")).lower()
    blast = context.get("blast_radius") or {}
    resource = str(blast.get("resource", "") if isinstance(blast, Mapping) else "").lower()
    if environment in {"staging", "dev", "test"} and any(
        token in resource for token in ("prod", "production")
    ):
        found.append("staging_vs_prod")

    command = " ".join(str(value) for value in arguments.values()).lower()
    claims_read_only = bool(
        context.get("read_only")
        or str(context.get("mode", "")).lower() in {"read-only", "read_only", "readonly"}
        or arguments.get("dry_run")
    )
    if claims_read_only and _DESTRUCTIVE.search(command):
        found.append("readonly_vs_destructive")

    criticality = str(body.get("criticality", "")).lower()
    reversibility = str(
        blast.get("reversibility", "") if isinstance(blast, Mapping) else ""
    ).lower()
    if criticality in {"low", "info", "informational"} and (
        body.get("class") == "irreversible" or reversibility == "irreversible"
    ):
        found.append("low_criticality_vs_irreversible")

    trust_claim = str(context.get("trust", "")).lower()
    if not producer_authenticated and trust_claim in {"verified", "authenticated"}:
        found.append("unverified_trust_claim")
    return tuple(found)


def rejection_for(
    readiness: Readiness, ask_class: ClassConfig | None
) -> Readiness:
    """Trim the repair list to the dimensions that actually failed the class gate."""
    if ask_class is None:
        return readiness
    threshold = ask_class.readiness_min_score
    failing = {
        name
        for name, value in readiness.dimensions.items()
        if value < threshold
    }
    if not readiness.contradictions:
        failing.discard("contradiction")
    repairs = tuple(
        item for item in readiness.repairs if str(item["name"]) in failing
    )
    return Readiness(
        score=readiness.score,
        band=readiness.band,
        dimensions=readiness.dimensions,
        missing=tuple(name for name in readiness.missing if name in failing),
        contradictions=readiness.contradictions,
        evidence_label=readiness.evidence_label,
        freshness=readiness.freshness,
        repairs=repairs,
    )


def similar_cases(
    store: AskStore, ask: AskRecord, *, limit: int = 3
) -> tuple[Mapping[str, Any], ...]:
    """Up to ``limit`` prior asks with the same class+tool, as labelled precedent."""
    seen: set[str] = set()
    cases: list[Mapping[str, Any]] = []
    target_class = str(ask.payload.get("class", ""))
    target_tool = str(ask.payload.get("tool", ""))
    for entry in reversed(store.audit_entries()):
        if len(cases) >= limit:
            break
        if entry.kind != "transition" or entry.ref_id in seen:
            continue
        if entry.payload is None or entry.payload.get("kind") != "created":
            continue
        seen.add(entry.ref_id)
        if entry.ref_id == ask.ask_id:
            continue
        candidate = store.get(entry.ref_id)
        if candidate is None:
            continue
        if str(candidate.payload.get("class", "")) != target_class:
            continue
        if str(candidate.payload.get("tool", "")) != target_tool:
            continue
        cases.append(
            {
                "ask_id": candidate.ask_id,
                "outcome": candidate.status.value,
                "environment": str(candidate.payload.get("environment", "unknown")),
                "criticality": str(candidate.payload.get("criticality", "unknown")),
                "resource": str(
                    (candidate.payload.get("context") or {})
                    .get("blast_radius", {})
                    .get("resource", "unknown")
                ),
            }
        )
    return tuple(cases)


def banner_for(readiness: Mapping[str, Any]) -> str | None:
    """The one-line quality banner; hidden only when readiness is fully green."""
    band = str(readiness.get("band", "green"))
    contradictions = list(readiness.get("contradictions") or [])
    missing = [str(item) for item in readiness.get("missing") or []]
    if band == "green" and not contradictions:
        return None
    parts = [f"READINESS: {band}"]
    if missing:
        parts.append("missing " + ", ".join(missing))
    parts.append(
        "contradictions: " + (", ".join(contradictions) if contradictions else "none")
    )
    parts.append(f"evidence: {readiness.get('evidence', 'unknown')}")
    return " · ".join(parts)


__all__ = [
    "DIMENSIONS",
    "Readiness",
    "ReadinessRejection",
    "band_for",
    "banner_for",
    "detect_contradictions",
    "evaluate",
    "rejection_for",
    "similar_cases",
]
