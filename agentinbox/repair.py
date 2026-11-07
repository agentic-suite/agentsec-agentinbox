"""Denial repair packets (M27 item 27.3, R89): deny becomes a lesson.

Design: ``docs/design/v0.1.0/constrained-allows.md``. Every human deny carries a structured packet
on the resolve, in the audit detail, and (redacted) on the agentwatch event. ``pointless``
suppresses blind retries in a demo agent.
"""

from __future__ import annotations

from typing import Any

from agentinbox.alternatives import alternatives_for, is_selectable
from agentinbox.resolve import rescope_hint
from agentinbox.store import AskRecord

RETRY_WORTHINESS = frozenset({"pointless", "conditional", "likely"})


def repair_packet(
    ask: AskRecord,
    *,
    reason: str | None = None,
    config: Any = None,
) -> dict[str, Any]:
    readiness = ask.payload.get("_readiness") or {}
    band = str(readiness.get("band", "green"))
    missing = [
        str(item)
        for item in (readiness.get("missing") or [])
        if str(item) in {"evidence_presence", "completeness", "target_specificity"}
    ]
    safe = next(
        (item for item in alternatives_for(ask) if is_selectable(item)),
        None,
    )
    worthiness = "pointless" if band == "red" else "conditional"
    if reason and any(token in reason.lower() for token in ("wrong", "unsafe", "never")):
        worthiness = "pointless"
    return {
        "violated_invariant": reason or "human_denied",
        "missing_evidence": missing,
        "suggested_scope": rescope_hint(ask, config if config is not None else None),
        "safe_alternative": None if safe is None else safe.get("id"),
        "retry_worthiness": worthiness,
        "required_tier": ask.tier,
    }


__all__ = ["RETRY_WORTHINESS", "repair_packet"]
