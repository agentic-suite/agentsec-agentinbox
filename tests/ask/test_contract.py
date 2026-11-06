"""Ask contract model + shipped JSON Schema (M2 item 2.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentinbox.contract import (
    ContractError,
    ask_schema,
    compute_action_identity,
    parse_ask,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "agentinbox" / "contract" / "ask-1.0.schema.json"
)


def valid_payload(**overrides: Any) -> dict[str, Any]:
    arguments = {"command": "psql prod -c 'DROP TABLE customers'", "timeout_s": 30}
    payload: dict[str, Any] = {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": "agent://ops-agent/7f31",
        "session_id": "sess_20261106T030412Z",
        "environment": "production",
        "data_class": "customer-pii",
        "class": "irreversible",
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": "irreversible-ask-gate",
            "policy_version": "v0.4.2",
            "clause": 'permit ... advice { human_gate = "required" }',
        },
        "criticality": "critical",
        "requested_by": "maya@team",
        "expires_at": "2026-11-06T03:09:12.000000Z",
        "context": {
            "blast_radius": {
                "resource": "db:prod/customers",
                "reversibility": "irreversible",
                "affected_estimate": "unknown",
            },
            "session_tail": [
                {"tool": "read_file", "action": "read", "at": "2026-11-06T03:03:55Z"}
            ],
            "flags": ["code_freeze_window"],
            "alternatives": ["staging database", "request standing approval"],
        },
        "traceparent": "00-4bf9-01",
    }
    payload.update(overrides)
    return payload


def test_shipped_schema_is_valid_json_schema_2020_12() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("ask-1.0.schema.json")
    assert schema["properties"]["contract"]["const"] == "ask/1.0"


def test_schema_and_model_agree_on_required_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    model_fields = {
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
    }

    assert set(schema["required"]) == model_fields
    assert set(schema["properties"]) >= model_fields | {"ask_id", "traceparent"}
    assert schema["additionalProperties"] is True


def test_ask_schema_helper_returns_the_shipped_truth() -> None:
    assert ask_schema()["properties"]["contract"]["const"] == "ask/1.0"


def test_valid_payload_round_trips() -> None:
    contract = parse_ask(valid_payload())

    assert contract.tool == "shell"
    assert contract.action_class == "irreversible"
    assert contract.policy_ref.rule_id == "irreversible-ask-gate"
    assert contract.expires_at.isoformat().endswith("+00:00")
    assert contract.to_dict() == valid_payload()


def test_unknown_fields_are_tolerated_and_preserved() -> None:
    payload = valid_payload(experimental_hint={"keep": "me"})

    contract = parse_ask(payload)

    assert contract.extra == {"experimental_hint": {"keep": "me"}}
    assert contract.to_dict()["experimental_hint"] == {"keep": "me"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tool", None),
        ("action", 7),
        ("arguments", []),
        ("agent_id", ""),
        ("session_id", ""),
        ("policy_ref", "policy"),
        ("expires_at", "not-a-date"),
        ("context", []),
    ],
)
def test_bad_types_name_the_failing_field(field: str, value: Any) -> None:
    with pytest.raises(ContractError) as excinfo:
        parse_ask(valid_payload(**{field: value}))

    assert excinfo.value.field == field


def test_wrong_contract_version_is_rejected() -> None:
    with pytest.raises(ContractError) as excinfo:
        parse_ask(valid_payload(contract="ask/2.0"))

    assert excinfo.value.field == "contract"


def test_policy_ref_requires_rule_id_and_version() -> None:
    with pytest.raises(ContractError) as excinfo:
        parse_ask(valid_payload(policy_ref={"rule_id": "r"}))

    assert excinfo.value.field == "policy_ref.policy_version"


def test_identity_is_canonical_and_order_insensitive() -> None:
    first = compute_action_identity(
        tool="shell", action="run", arguments={"a": 1, "b": 2}
    )
    second = compute_action_identity(
        tool="shell", action="run", arguments={"b": 2, "a": 1}
    )
    different = compute_action_identity(
        tool="shell", action="run", arguments={"a": 1, "b": 3}
    )

    assert first == second
    assert first != different
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64
