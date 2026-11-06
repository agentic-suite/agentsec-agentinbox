"""Ask ingest pipeline (E1, E6, T13).

Order is the security property: validate → cap → verify identity → expiry ceiling → redact →
classify → store. Nothing partial is ever stored, and the raw arguments used to verify the
action identity are discarded after the check.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from agentinbox.config import ClassConfig, Config
from agentinbox.contract import AskContract, ContractError, compute_action_identity, parse_ask
from agentinbox.redaction import RedactionReceipt, redact_value
from agentinbox.store import AskRecord, AskStore, canonical_json, utcnow
from agentinbox.trust import ProducerIdentity, TrustMap, classify_trust

TOTAL_CAP_BYTES = 256 * 1024
STRING_CAP_BYTES = 4 * 1024
OBJECT_CAP_BYTES = 64 * 1024
CLAUSE_CAP_BYTES = 8 * 1024

ASK_ID_PATTERN = re.compile(r"^ask_[0-9a-f]{16}$")
RESERVED_METADATA = frozenset({"_trust", "_redactions", "_producer"})
_IDENTITY_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class IngestResult:
    ask: AskRecord
    created: bool
    trust: TrustMap
    receipts: tuple[RedactionReceipt, ...]


def enforce_caps(raw: dict[str, Any]) -> None:
    """Per-field and total size caps, before any regex work."""
    if len(canonical_json(raw).encode("utf-8")) > TOTAL_CAP_BYTES:
        raise ContractError(
            "body", f"payload exceeds {TOTAL_CAP_BYTES} bytes (256 KiB)", status_code=413
        )

    for key in ("arguments", "context"):
        value = raw.get(key)
        if (
            isinstance(value, dict | list)
            and len(canonical_json(value).encode("utf-8")) > OBJECT_CAP_BYTES
        ):
            raise ContractError(key, f"object exceeds {OBJECT_CAP_BYTES} bytes (64 KiB)")

    policy = raw.get("policy_ref")
    clause = policy.get("clause") if isinstance(policy, dict) else None
    if isinstance(clause, str) and len(clause.encode("utf-8")) > CLAUSE_CAP_BYTES:
        raise ContractError(
            "policy_ref.clause", f"clause exceeds {CLAUSE_CAP_BYTES} bytes (8 KiB)"
        )

    _walk_caps(raw, "")


def _walk_caps(value: Any, path: str) -> None:
    if path == "policy_ref.clause":
        return
    if isinstance(value, str):
        if len(value.encode("utf-8")) > STRING_CAP_BYTES:
            raise ContractError(path or "body", f"string exceeds {STRING_CAP_BYTES} bytes (4 KiB)")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _walk_caps(item, f"{path}.{key}" if path else str(key))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_caps(item, f"{path}[{index}]")


def verify_action_identity(contract: AskContract) -> None:
    if not _IDENTITY_PATTERN.fullmatch(contract.action_identity):
        raise ContractError("action_identity", "must be sha256:<64 lowercase hex>")
    expected = compute_action_identity(
        tool=contract.tool, action=contract.action, arguments=contract.arguments
    )
    if contract.action_identity != expected:
        raise ContractError(
            "action_identity",
            "does not match the canonical hash of tool/action/arguments",
        )


def validate_ask(raw: dict[str, Any], *, now: datetime, config: Config) -> AskContract:
    contract = parse_ask(raw)
    enforce_caps(raw)
    verify_action_identity(contract)
    resolve_class(config, contract)
    _validate_expiry(
        contract.expires_at, now=now, config=config, action_class=contract.action_class
    )
    _validate_ask_id(contract.ask_id)
    return contract


def resolve_class(config: Config, contract: AskContract) -> ClassConfig:
    ask_class = config.classes.get(contract.action_class)
    if ask_class is None:
        raise ContractError(
            "class",
            f"does not resolve to a configured class ({contract.action_class!r})",
        )
    return ask_class


def _validate_expiry(
    expires_at: datetime, *, now: datetime, config: Config, action_class: str
) -> None:
    if expires_at <= now:
        raise ContractError("expires_at", "must be in the future")
    ceiling = now + timedelta(seconds=config.classes[action_class].ttl_seconds)
    if expires_at > ceiling:
        raise ContractError(
            "expires_at",
            f"exceeds class ceiling of {config.classes[action_class].ttl_seconds}s",
        )


def _validate_ask_id(ask_id: str | None) -> None:
    if ask_id is not None and not ASK_ID_PATTERN.fullmatch(ask_id):
        raise ContractError("ask_id", "must match ask_<16 lowercase hex>")


def ingest(
    raw: dict[str, Any],
    *,
    store: AskStore,
    config: Config,
    producer: ProducerIdentity,
    now: datetime | None = None,
) -> IngestResult:
    moment = now or utcnow()
    contract = validate_ask(raw, now=moment, config=config)

    if contract.ask_id is not None:
        existing = store.get(contract.ask_id)
        if existing is not None and (
            existing.action_identity != contract.action_identity
            or existing.session_id != contract.session_id
        ):
            raise ContractError(
                "ask_id", "already exists for a different action identity", status_code=409
            )

    arguments, argument_receipts = redact_value(dict(contract.arguments), "arguments")
    context, context_receipts = redact_value(dict(contract.context), "context")
    extra_raw = {
        key: value for key, value in contract.extra.items() if key not in RESERVED_METADATA
    }
    extra, extra_receipts = redact_value(extra_raw, "extra")
    receipts = argument_receipts + context_receipts + extra_receipts

    trust = classify_trust(producer)
    payload = contract.to_dict()
    payload["arguments"] = arguments
    payload["context"] = context
    for key, value in extra.items():
        payload[key] = value
    payload["_trust"] = trust.to_dict()
    payload["_redactions"] = [receipt.to_dict() for receipt in receipts]
    payload["_producer"] = {
        "adapter": producer.adapter,
        "authenticated": producer.authenticated,
        "principal": producer.principal,
        "remote_addr": producer.remote_addr,
    }

    ask_id = contract.ask_id or f"ask_{secrets.token_hex(8)}"
    record = AskRecord(
        ask_id=ask_id,
        action_identity=contract.action_identity,
        session_id=contract.session_id,
        agent_id=contract.agent_id,
        created_at=moment,
        expires_at=contract.expires_at,
        payload=payload,
    )
    result = store.create_or_get_by_identity(record)
    return IngestResult(
        ask=result.ask,
        created=result.created,
        trust=trust,
        receipts=receipts,
    )



__all__ = [
    "ASK_ID_PATTERN",
    "CLAUSE_CAP_BYTES",
    "OBJECT_CAP_BYTES",
    "RESERVED_METADATA",
    "STRING_CAP_BYTES",
    "TOTAL_CAP_BYTES",
    "IngestResult",
    "enforce_caps",
    "ingest",
    "resolve_class",
    "validate_ask",
    "verify_action_identity",
]
