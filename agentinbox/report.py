"""Local success-metric report (M21 item 21.4, PRD 07 / N-28).

Design: ``docs/design/v0.1.0/ops.md`` §4. Everything is computed from the owner's own audit chain
and store; the report opens no socket and writes nothing. Percentiles use nearest-rank over the
answered asks' ``delivery → answer`` intervals.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.compat import REPORT_CONTRACT
from agentinbox.events.trace import ANSWER_CAUSE_MAP
from agentinbox.resolve import derived_status
from agentinbox.store import AskStatus, AskStore, to_iso, utcnow

DENY_STATUSES = frozenset({AskStatus.DENIED, AskStatus.EXPIRED, AskStatus.FLOOD_DENIED})


@dataclass(frozen=True, slots=True)
class ReportMetrics:
    generated_at: datetime
    response_time_p50_s: float | None
    response_time_p99_s: float | None
    response_samples: int
    expiries: int
    escalation_firings: int
    flood_events: int
    answer_rejected_causes: Mapping[str, int]
    deny_rate_by_class: Mapping[str, float]
    pending: int
    total_asks: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": REPORT_CONTRACT,
            "generated_at": to_iso(self.generated_at),
            "local_only": True,
            "response_time_s": {
                "p50": self.response_time_p50_s,
                "p99": self.response_time_p99_s,
                "samples": self.response_samples,
            },
            "expiries": self.expiries,
            "escalation_firings": self.escalation_firings,
            "flood_events": self.flood_events,
            "answer_rejected_causes": dict(sorted(self.answer_rejected_causes.items())),
            "deny_rate_by_class": dict(sorted(self.deny_rate_by_class.items())),
            "pending": self.pending,
            "total_asks": self.total_asks,
        }


def percentile(values: Sequence[float], p: float) -> float | None:
    """Nearest-rank percentile (``p`` in 0..100); ``None`` for an empty sample."""
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil((p / 100.0) * len(ordered))
    index = min(len(ordered) - 1, max(0, rank - 1))
    return ordered[index]


def build_report(
    store: AskStore, *, now: Callable[[], datetime] = utcnow
) -> ReportMetrics:
    """Compute the PRD 07 metrics from the audit chain; never writes to the store."""
    created: dict[str, datetime] = {}
    answered_at: dict[str, datetime] = {}
    delivered_at: dict[str, datetime] = {}
    ask_ids: set[str] = set()
    expiries = 0
    escalation_firings = 0
    flood_ids: set[str] = set()
    causes: Counter[str] = Counter()

    for entry in store.audit_entries():
        body = entry.payload or {}
        if entry.kind == "transition":
            ask_ids.add(entry.ref_id)
            kind = str(body.get("kind", ""))
            if kind == "created":
                created[entry.ref_id] = entry.at
            elif kind == "answer" and body.get("to_status") in {"approved", "denied"}:
                answered_at[entry.ref_id] = entry.at
            elif kind == "expired":
                expiries += 1
            elif kind == "ask-escalated":
                escalation_firings += 1
            elif kind in {"answer-rejected", "late-answer"}:
                detail = body.get("detail") or {}
                cause = str(detail.get("cause", "late"))
                causes[ANSWER_CAUSE_MAP.get(cause, "binding_mismatch")] += 1
        elif entry.kind == "delivery":
            if body.get("status") == "delivered" and entry.ref_id not in delivered_at:
                delivered_at[entry.ref_id] = entry.at
        elif entry.kind == "flood":
            flood_ids.add(entry.ref_id)

    responses: list[float] = []
    for ask_id, answered in answered_at.items():
        start = delivered_at.get(ask_id) or created.get(ask_id)
        if start is None:
            continue
        elapsed = (answered - start).total_seconds()
        if elapsed >= 0:
            responses.append(elapsed)

    moment = now()
    resolved: Counter[str] = Counter()
    denied: Counter[str] = Counter()
    pending = 0
    for ask_id in sorted(ask_ids):
        ask = store.get(ask_id)
        if ask is None:  # pragma: no cover - transitions always reference a stored ask
            continue
        status = derived_status(ask, now=moment)
        class_name = str(ask.payload.get("class", "unknown"))
        if status in AskStatus.terminal():
            resolved[class_name] += 1
            if status in DENY_STATUSES:
                denied[class_name] += 1
        else:
            pending += 1

    rates = {
        class_name: round(denied[class_name] / resolved[class_name], 4)
        for class_name in resolved
        if resolved[class_name]
    }
    p50 = percentile(responses, 50)
    p99 = percentile(responses, 99)
    return ReportMetrics(
        generated_at=moment,
        response_time_p50_s=None if p50 is None else round(p50, 3),
        response_time_p99_s=None if p99 is None else round(p99, 3),
        response_samples=len(responses),
        expiries=expiries,
        escalation_firings=escalation_firings,
        flood_events=len(flood_ids),
        answer_rejected_causes=dict(causes),
        deny_rate_by_class=rates,
        pending=pending,
        total_asks=len(ask_ids),
    )


__all__ = ["DENY_STATUSES", "ReportMetrics", "build_report", "percentile"]
