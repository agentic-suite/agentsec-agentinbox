"""Producer alternatives: canonical fingerprints, selection, and safe suggestions (M27).

Design: ``docs/design/v0.1.0/constrained-allows.md``. A producer may advertise narrowed variants of
the same intent. A variant is **selectable** only when the producer declares an enforcer binding and
its fingerprint matches the canonical form; otherwise it renders as advice and cannot be picked.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from agentinbox.store import AskRecord, canonical_json

CONSTRAINT_STATUSES = frozenset(
    {"allow_with_constraints", "allow_with_edits", "allow", "deny", "pending"}
)


def alternative_fingerprint(alternative: Mapping[str, Any]) -> str:
    material = canonical_json(
        {
            "id": alternative.get("id"),
            "label": alternative.get("label"),
            "enforcer": alternative.get("enforcer"),
            "arguments": dict(alternative.get("arguments") or {}),
            "constraints": [
                dict(item) for item in (alternative.get("constraints") or [])
            ],
        }
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def is_selectable(alternative: Mapping[str, Any]) -> bool:
    enforcer = alternative.get("enforcer")
    fingerprint = alternative.get("fingerprint")
    return bool(
        isinstance(enforcer, str)
        and enforcer
        and isinstance(fingerprint, str)
        and fingerprint == alternative_fingerprint(alternative)
    )


def alternatives_for(ask: AskRecord) -> tuple[Mapping[str, Any], ...]:
    raw = ask.payload.get("alternatives") or ()
    return tuple(item for item in raw if isinstance(item, Mapping))


def select_alternative(ask: AskRecord, alternative_id: str) -> Mapping[str, Any]:
    """Return the selectable alternative or raise ``KeyError`` (the caller names the reason)."""
    for alternative in alternatives_for(ask):
        if alternative.get("id") == alternative_id:
            if not is_selectable(alternative):
                raise KeyError("unbindable_alternative")
            return alternative
    raise KeyError("unknown_alternative")


def constraints_of(alternative: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        dict(item) for item in (alternative.get("constraints") or []) if isinstance(item, Mapping)
    )


_DESTRUCTIVE = ("drop", "delete", "truncate", "rm -rf", "force", "overwrite", "alter")


def suggestions_for(ask: AskRecord, *, limit: int = 3) -> tuple[str, ...]:
    """Class-generic narrowings, labelled suggestions; never selectable, never recorded."""
    suggestions: list[str] = []
    environment = str(ask.payload.get("environment", "")).lower()
    arguments = ask.payload.get("arguments") or {}
    command = " ".join(str(value) for value in arguments.values()).lower()
    if environment in {"production", "prod"}:
        suggestions.append("run against staging first (suggestion)")
    if any(token in command for token in _DESTRUCTIVE):
        suggestions.append("dry-run or explain the change first (suggestion)")
    if "limit" not in arguments and "max_rows" not in arguments:
        suggestions.append("cap the blast radius with an explicit limit (suggestion)")
    return tuple(suggestions[:limit])


def render_alternative(alternative: Mapping[str, Any]) -> str:
    label = str(alternative.get("label", alternative.get("id", "unnamed")))
    if is_selectable(alternative):
        return f"{alternative.get('id')} — {label} (enforcer={alternative.get('enforcer')})"
    return f"{label} — advice only (no enforcer binding)"


def prior_objections(
    store: Any, ask: AskRecord, *, limit: int = 2
) -> tuple[Mapping[str, Any], ...]:
    """Prior human denials of the same class+tool that carried a repair packet."""
    from agentinbox.store import AskStatus

    seen: set[str] = set()
    found: list[Mapping[str, Any]] = []
    target_class = str(ask.payload.get("class", ""))
    target_tool = str(ask.payload.get("tool", ""))
    for entry in reversed(store.audit_entries()):
        if len(found) >= limit:
            break
        if entry.kind != "transition" or entry.payload is None:
            continue
        if entry.payload.get("kind") != "answer":
            continue
        if entry.payload.get("to_status") != AskStatus.DENIED.value:
            continue
        if entry.ref_id in seen or entry.ref_id == ask.ask_id:
            continue
        seen.add(entry.ref_id)
        candidate = store.get(entry.ref_id)
        if candidate is None:
            continue
        if str(candidate.payload.get("class")) != target_class:
            continue
        if str(candidate.payload.get("tool")) != target_tool:
            continue
        detail = entry.payload.get("detail") or {}
        repair = detail.get("repair")
        if not isinstance(repair, Mapping):
            continue
        found.append(
            {
                "ask_id": entry.ref_id,
                "reason": entry.payload.get("reason") or "denied",
                "repair": dict(repair),
            }
        )
    return tuple(found)


def recall_line(objections: Sequence[Mapping[str, Any]]) -> str:
    if not objections:
        return "none"
    return "; ".join(
        f"{item.get('ask_id')} denied once ({item.get('reason')})" for item in objections
    )


__all__ = [
    "alternative_fingerprint",
    "alternatives_for",
    "constraints_of",
    "is_selectable",
    "prior_objections",
    "recall_line",
    "render_alternative",
    "select_alternative",
    "suggestions_for",
]
