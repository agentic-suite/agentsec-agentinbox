"""The ``ask/1.0`` contract: parsed model + strict shape validation.

Design: ``docs/design/v0.1.0/ask-contract.md``. Size caps, expiry ceilings, identity
verification, redaction, and trust classification are separate stages in :mod:`agentinbox.ingest`
so each can be tested and reasoned about in order.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agentinbox.store import canonical_json, parse_iso, to_iso

SCHEMA_PATH = Path(__file__).with_name("ask-1.0.schema.json")
CONTRACT_VERSION = "ask/1.0"
_REQUIRED = (
    "contract",
    "action_identity",
    "tool",
    "action",
    "arguments",
    "agent_id",
    "session_id",
    "environment",
    "data_class",
    "class",
    "reason_code",
    "policy_ref",
    "criticality",
    "requested_by",
    "expires_at",
    "context",
)
_KNOWN = frozenset(_REQUIRED) | {"ask_id", "traceparent", "alternatives"}


class ContractError(Exception):
    """A rejected ask; ``field`` is stable so producers (and tests) can act on it."""

    def __init__(
        self,
        field: str,
        message: str,
        *,
        status_code: int = 400,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message
        self.status_code = status_code
        self.details = dict(details) if details else None


@dataclass(frozen=True, slots=True)
class PolicyRef:
    rule_id: str
    policy_version: str
    clause: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "rule_id": self.rule_id,
            "policy_version": self.policy_version,
        }
        if self.clause is not None:
            data["clause"] = self.clause
        return data


@dataclass(frozen=True, slots=True)
class AskContract:
    action_identity: str
    tool: str
    action: str
    arguments: Mapping[str, Any]
    agent_id: str
    session_id: str
    environment: str
    data_class: str
    action_class: str
    reason_code: str
    policy_ref: PolicyRef
    criticality: str
    requested_by: str
    expires_at: datetime
    context: Mapping[str, Any]
    ask_id: str | None = None
    traceparent: str | None = None
    alternatives: tuple[Mapping[str, Any], ...] = ()
    extra: Mapping[str, Any] = None  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "contract": CONTRACT_VERSION,
            "action_identity": self.action_identity,
            "tool": self.tool,
            "action": self.action,
            "arguments": dict(self.arguments),
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "environment": self.environment,
            "data_class": self.data_class,
            "class": self.action_class,
            "reason_code": self.reason_code,
            "policy_ref": self.policy_ref.to_dict(),
            "criticality": self.criticality,
            "requested_by": self.requested_by,
            "expires_at": to_iso(self.expires_at),
            "context": dict(self.context),
        }
        if self.ask_id is not None:
            data["ask_id"] = self.ask_id
        if self.traceparent is not None:
            data["traceparent"] = self.traceparent
        if self.alternatives:
            data["alternatives"] = [dict(item) for item in self.alternatives]
        for key, value in self.extra.items():
            data.setdefault(key, value)
        return data


def ask_schema() -> dict[str, Any]:
    """The shipped schema — the contract truth producers validate against."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema: dict[str, Any] = json.load(handle)
    return schema


def compute_action_identity(
    *, tool: str, action: str, arguments: Mapping[str, Any]
) -> str:
    """One canonical construction, matching the producer side (D-2)."""
    import hashlib

    material = canonical_json({"tool": tool, "action": action, "arguments": dict(arguments)})
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def parse_ask(raw: Mapping[str, Any]) -> AskContract:
    """Shape/type validation only (caps and expiry live in :mod:`agentinbox.ingest`)."""
    if not isinstance(raw, Mapping):
        raise ContractError("body", "must be a JSON object")

    for field in _REQUIRED:
        if field not in raw:
            raise ContractError(field, "is required")

    if raw["contract"] != CONTRACT_VERSION:
        raise ContractError("contract", f"must be {CONTRACT_VERSION!r}")

    policy_raw = raw["policy_ref"]
    if not isinstance(policy_raw, Mapping):
        raise ContractError("policy_ref", "must be an object")
    for key in ("rule_id", "policy_version"):
        if key not in policy_raw:
            raise ContractError(f"policy_ref.{key}", "is required")

    return AskContract(
        action_identity=_string(raw, "action_identity"),
        tool=_string(raw, "tool"),
        action=_string(raw, "action"),
        arguments=_mapping(raw, "arguments"),
        agent_id=_string(raw, "agent_id"),
        session_id=_string(raw, "session_id"),
        environment=_string(raw, "environment"),
        data_class=_string(raw, "data_class"),
        action_class=_string(raw, "class"),
        reason_code=_string(raw, "reason_code"),
        policy_ref=PolicyRef(
            rule_id=_string(policy_raw, "rule_id", field="policy_ref.rule_id"),
            policy_version=_string(policy_raw, "policy_version", field="policy_ref.policy_version"),
            clause=_optional_string(policy_raw, "clause", field="policy_ref.clause"),
        ),
        criticality=_string(raw, "criticality"),
        requested_by=_string(raw, "requested_by"),
        expires_at=_timestamp(raw, "expires_at"),
        context=_mapping(raw, "context"),
        ask_id=_optional_string(raw, "ask_id"),
        traceparent=_optional_string(raw, "traceparent"),
        alternatives=_alternatives(raw.get("alternatives")),
        extra={key: value for key, value in raw.items() if key not in _KNOWN},
    )


def _alternatives(raw: Any) -> tuple[Mapping[str, Any], ...]:
    """Validate the optional ``alternatives[]``; malformed entries are contract errors."""
    if raw is None:
        return ()
    if not isinstance(raw, list) or len(raw) > 5:
        raise ContractError("alternatives", "must be a list of at most 5 entries")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ContractError(f"alternatives[{index}]", "must be an object")
        identifier = item.get("id")
        label = item.get("label")
        if not isinstance(identifier, str) or not identifier:
            raise ContractError(f"alternatives[{index}].id", "must be a non-empty string")
        if identifier in seen:
            raise ContractError(f"alternatives[{index}].id", "must be unique")
        seen.add(identifier)
        if not isinstance(label, str) or not label:
            raise ContractError(f"alternatives[{index}].label", "must be a non-empty string")
        enforcer = item.get("enforcer")
        if enforcer is not None and (not isinstance(enforcer, str) or not enforcer):
            raise ContractError(f"alternatives[{index}].enforcer", "must be a non-empty string")
        fingerprint = item.get("fingerprint")
        if fingerprint is not None and not isinstance(fingerprint, str):
            raise ContractError(f"alternatives[{index}].fingerprint", "must be a string")
        constraints = item.get("constraints") or []
        if not isinstance(constraints, list):
            raise ContractError(f"alternatives[{index}].constraints", "must be a list")
        for cindex, constraint in enumerate(constraints):
            if not isinstance(constraint, Mapping):
                raise ContractError(
                    f"alternatives[{index}].constraints[{cindex}]", "must be an object"
                )
            if not isinstance(constraint.get("id"), str) or not constraint.get("id"):
                raise ContractError(
                    f"alternatives[{index}].constraints[{cindex}].id",
                    "must be a non-empty string",
                )
            if not isinstance(constraint.get("enforcer_ref"), str) or not constraint.get(
                "enforcer_ref"
            ):
                raise ContractError(
                    f"alternatives[{index}].constraints[{cindex}].enforcer_ref",
                    "must name the enforcer binding",
                )
        normalized.append(
            {
                "id": identifier,
                "label": label,
                "enforcer": enforcer,
                "fingerprint": fingerprint,
                "arguments": dict(item.get("arguments") or {}),
                "constraints": [dict(constraint) for constraint in constraints],
            }
        )
    return tuple(normalized)


def _string(raw: Mapping[str, Any], key: str, *, field: str | None = None) -> str:
    value = raw[key]
    if not isinstance(value, str) or not value:
        raise ContractError(field or key, "must be a non-empty string")
    return value


def _optional_string(raw: Mapping[str, Any], key: str, *, field: str | None = None) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractError(field or key, "must be a string")
    return value


def _mapping(raw: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = raw[key]
    if not isinstance(value, Mapping):
        raise ContractError(key, "must be an object")
    return value


def _timestamp(raw: Mapping[str, Any], key: str) -> datetime:
    value = raw[key]
    if not isinstance(value, str):
        raise ContractError(key, "must be an RFC 3339 UTC timestamp")
    try:
        return parse_iso(value)
    except ValueError:
        raise ContractError(key, "must be an RFC 3339 UTC timestamp") from None
