"""Shared fixtures for the ask/ingest suite (M2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from agentinbox.config import ClassConfig, Config
from agentinbox.contract import compute_action_identity
from agentinbox.store.memory import MemoryStore

NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def payload(**overrides: Any) -> dict[str, Any]:
    arguments = {"command": "psql prod -c 'DROP TABLE customers'", "timeout_s": 30}
    body: dict[str, Any] = {
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
            "clause": "permit advice { human_gate = \"required\" }",
        },
        "criticality": "critical",
        "requested_by": "maya@team",
        "expires_at": "2026-11-06T12:05:00.000000Z",
        "context": {
            "blast_radius": {
                "resource": "db:prod/customers",
                "reversibility": "irreversible",
                "affected_estimate": "unknown",
            },
            "session_tail": [{"tool": "read_file", "action": "read"}],
            "flags": ["code_freeze_window"],
            "alternatives": ["staging database"],
        },
    }
    if "arguments" in overrides and "action_identity" not in overrides:
        body["action_identity"] = compute_action_identity(
            tool=overrides.get("tool", body["tool"]),
            action=overrides.get("action", body["action"]),
            arguments=overrides["arguments"],
        )
    body.update(overrides)
    return body


def config(ttl_seconds: int = 300, warn_seconds: int | None = 60) -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=ttl_seconds, warn_seconds=warn_seconds
            )
        }
    )


@pytest.fixture
def store() -> Iterator[MemoryStore]:
    driver = MemoryStore()
    try:
        yield driver
    finally:
        driver.close()
