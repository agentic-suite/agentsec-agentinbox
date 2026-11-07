"""Tiny stdlib validator for the shipped security-event fixture (M16 item 16.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "agentinbox"
    / "events"
    / "security-event.schema.json"
)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(record: dict[str, Any]) -> None:
    schema = load_schema()
    properties = schema["properties"]

    assert set(record) <= set(properties), (
        f"unknown top-level fields: {sorted(set(record) - set(properties))}"
    )
    for field in schema["required"]:
        assert field in record, f"missing required field: {field}"

    assert record["event_version"] == properties["event_version"]["const"]
    assert record["emitter"] == properties["emitter"]["const"]
    assert isinstance(record["at"], str)
    assert record["at"]
    assert isinstance(record["event_id"], str)
    assert record["event_id"]
    assert record["event_type"] in properties["event_type"]["enum"]

    event_type = record["event_type"]
    payload = record["payload"]
    assert isinstance(payload, dict)
    required = schema["x-payload-requirements"][event_type]
    allowed = schema["x-payload-allowed"][event_type]
    assert set(required) <= set(payload), (
        f"{event_type} missing payload keys: {sorted(set(required) - set(payload))}"
    )
    assert set(payload) <= set(allowed), (
        f"{event_type} has unlisted payload keys: {sorted(set(payload) - set(allowed))}"
    )
