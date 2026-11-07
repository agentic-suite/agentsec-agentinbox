"""Digested config-change evidence (M11 item 11.5).

Policy (TTLs, ladders, rosters, thresholds, channel references) is security-relevant. It is
reviewed like code, and every effective change is recorded as one digested
``inbox-config-changed`` line in ``<home>/logs``. The audit chain (M15) covers ask evidence; this
log covers policy movement and never re-enters as authority.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from agentinbox.config import Config, effective_ladder_delays
from agentinbox.store import canonical_json, payload_digest, to_iso, utcnow

EVENT_KIND = "inbox-config-changed"
EVENT_FILE = "inbox-config-changed.jsonl"
DIGEST_FILE = "config-digest"


def policy_material(config: Config) -> dict[str, Any]:
    """The deterministic, secret-reference-only view of effective policy."""
    return {
        "classes": {
            name: {
                "ttl_seconds": ask_class.ttl_seconds,
                "warn_seconds": ask_class.warn_seconds,
                "self_review": ask_class.self_review,
                "require_reason_on_deny": ask_class.require_reason_on_deny,
                "ladder": list(ask_class.ladder),
                "ladder_delays": list(effective_ladder_delays(ask_class)),
            }
            for name, ask_class in sorted(config.classes.items())
        },
        "roster": {
            tier: {
                channel: list(principals)
                for channel, principals in sorted(channels.items())
            }
            for tier, channels in sorted(config.roster.items())
        },
        "throttle": {
            "per_agent_burst": config.throttle.per_agent_burst,
            "per_agent_rate_per_min": config.throttle.per_agent_rate_per_min,
            "flood_window_seconds": config.throttle.flood_window_seconds,
        },
        "channels": {
            name: {
                "enabled": channel.enabled,
                "url_ref": channel.url_ref,
                "hmac_key_ref": channel.hmac_key_ref,
            }
            for name, channel in sorted(config.channels.items())
        },
        "bus": config.bus.driver,
        "store": config.store.driver,
        "limits": {
            "max_hold_rounds": config.limits.max_hold_rounds,
            "max_evidence_revisions": config.limits.max_evidence_revisions,
            "max_thread_entries": config.limits.max_thread_entries,
        },
    }


def policy_digest(config: Config) -> str:
    return payload_digest(policy_material(config))


def record_config_change(
    home: Path,
    config: Config,
    *,
    now: Callable[[], datetime] = utcnow,
) -> str | None:
    """Record one event when policy changed; return the new digest (or ``None``)."""
    logs = home / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    _chmod(logs, 0o700)

    digest = policy_digest(config)
    state = logs / DIGEST_FILE
    previous = state.read_text(encoding="utf-8").strip() if state.exists() else None
    if previous == digest:
        return None

    event = {
        "kind": EVENT_KIND,
        "at": to_iso(now()),
        "digest": digest,
        "previous": previous,
    }
    descriptor = os.open(
        logs / EVENT_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
    )
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(canonical_json(event) + "\n")

    staging = logs / f"{DIGEST_FILE}.tmp"
    staging.write_text(digest + "\n", encoding="utf-8")
    _chmod(staging, 0o600)
    os.replace(staging, state)
    return digest


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:  # pragma: no cover - exotic filesystems
        return


__all__ = [
    "DIGEST_FILE",
    "EVENT_FILE",
    "EVENT_KIND",
    "policy_digest",
    "policy_material",
    "record_config_change",
]
