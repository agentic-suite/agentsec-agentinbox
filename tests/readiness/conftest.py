"""Shared helpers for the readiness suite (M26)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from agentinbox.config import ChannelConfig, ClassConfig, Config
from tests.ask.conftest import payload

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def config(**overrides: Any) -> Config:
    irreversibility = {
        "ttl_seconds": 300,
        "required_evidence": ("diff", "logs"),
        "readiness_enforce": False,
        "readiness_min_score": 0.6,
        "evidence_max_age_seconds": 86400,
        "on_contradiction": "deliver",
    }
    irreversibility.update(overrides)
    return Config(
        classes={
            "irreversible": ClassConfig(**irreversibility),
            "readonly": ClassConfig(ttl_seconds=300),
        },
        roster={"tier-1": {"terminal": ("alice",)}},
        channels={"terminal": ChannelConfig(enabled=True)},
    )


def good_body(**overrides: Any) -> dict[str, Any]:
    evidence = {
        "diff": {
            "at": (NOW - timedelta(minutes=5))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
            "digest": "sha256:" + "a" * 64,
        },
        "logs": {
            "at": (NOW - timedelta(minutes=4))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
        },
    }
    body = payload(
        expires_at=(NOW + timedelta(minutes=5))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        **overrides,
    )
    body["context"] = {
        "blast_radius": {
            "resource": "db:prod/customers",
            "reversibility": "irreversible",
            "affected_estimate": "1200 rows",
            "credential_class": "none",
        },
        "evidence": evidence,
        "flags": ["code_freeze_window"],
        "alternatives": ["dry-run"],
        "session_tail": [{"tool": "psql", "action": "read"}],
    }
    return body


def weak_body() -> dict[str, Any]:
    body = good_body()
    body["context"] = {
        "blast_radius": {
            "resource": "unknown",
            "reversibility": "unknown",
            "affected_estimate": "unknown",
        },
        "flags": [],
        "alternatives": [],
        "session_tail": [],
    }
    return body
