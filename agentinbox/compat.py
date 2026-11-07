"""The v0.x compatibility matrix (E10 / M21 item 21.3).

One source for the frozen surface: contract versions, the reserved exit-code integers, the
agentwatch event vocabulary, and the store schema. A test matrix asserts that new releases are
**additive only** — removing an event, changing an exit code, or repurposing a contract version is
reported as a violation instead of shipping silently.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agentinbox.audit import EXPORT_CONTRACT
from agentinbox.channels.webhook import CONTRACT as WEBHOOK_CONTRACT
from agentinbox.contract.ask_v1 import CONTRACT_VERSION as ASK_CONTRACT
from agentinbox.events.base import EVENT_TYPES, EVENT_VERSION
from agentinbox.exit_codes import ExitCode
from agentinbox.ops import BACKUP_CONTRACT
from agentinbox.resolve import RESOLVE_CONTRACT
from agentinbox.store.sqlite import SCHEMA_VERSION

REPORT_CONTRACT = "report/1.0"

#: The v0.1.0 event vocabulary. Later releases may add events; these may not disappear.
FROZEN_EVENTS = frozenset(
    {
        "ask-raised",
        "ask-delivered",
        "ask-delivery-failed",
        "ask-warned",
        "ask-escalated",
        "ask-answered",
        "ask-expired",
        "ask-cancelled",
        "ask-flood",
        "answer-rejected",
    }
)

#: The reserved exit-code integers. ``0`` is the only approval; ``4`` is always fail-closed.
EXIT_CODES: dict[int, str] = {
    0: "approved",
    1: "usage",
    2: "denied",
    3: "expired",
    4: "unavailable",
    5: "pending",
}


def compatibility_matrix() -> dict[str, Any]:
    """The frozen surface this build promises, in one machine-readable artifact."""
    return {
        "contracts": {
            "ask": ASK_CONTRACT,
            "resolve": RESOLVE_CONTRACT,
            "webhook": WEBHOOK_CONTRACT,
            "export": EXPORT_CONTRACT,
            "backup": BACKUP_CONTRACT,
            "report": REPORT_CONTRACT,
        },
        "exit_codes": dict(EXIT_CODES),
        "approval_code": int(ExitCode.APPROVED),
        "events": sorted(EVENT_TYPES),
        "event_version": EVENT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "downgrade": "refused",
    }


def additive_violations(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Return breaking changes between two matrix snapshots (empty = additive only)."""
    violations: list[str] = []

    previous_codes = previous.get("exit_codes", {})
    current_codes = current.get("exit_codes", {})
    if isinstance(previous_codes, Mapping) and isinstance(current_codes, Mapping):
        for code, label in previous_codes.items():
            if current_codes.get(code) != label:
                violations.append(f"exit code {code} changed or disappeared")

    removed_events = set(previous.get("events", ())) - set(current.get("events", ()))
    for event in sorted(removed_events):
        violations.append(f"event removed: {event}")

    previous_contracts = previous.get("contracts", {})
    current_contracts = current.get("contracts", {})
    if isinstance(previous_contracts, Mapping) and isinstance(current_contracts, Mapping):
        for name, version in previous_contracts.items():
            if current_contracts.get(name) != version:
                violations.append(f"contract {name} changed or disappeared")

    if previous.get("event_version") not in (None, current.get("event_version")):
        violations.append("event version changed")
    previous_schema = previous.get("schema_version")
    current_schema = current.get("schema_version")
    if (
        isinstance(previous_schema, int)
        and isinstance(current_schema, int)
        and current_schema < previous_schema
    ):
        violations.append("schema version moved backwards")
    return violations


__all__ = [
    "EXIT_CODES",
    "FROZEN_EVENTS",
    "REPORT_CONTRACT",
    "additive_violations",
    "compatibility_matrix",
]
