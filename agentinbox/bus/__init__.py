"""The AskBus movement layer (E12) — import the contract from here."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from agentinbox.bus.base import (
    DEFAULT_DONE_KEEP,
    DEFAULT_POLL_INTERVAL,
    MAX_POLL_INTERVAL,
    AskBus,
    BusError,
    BusLockedError,
    Handler,
    InProcBus,
    Job,
    JobKind,
    SpoolBus,
    new_job,
    publish_digest,
)
from agentinbox.bus.delivery import DEFAULT_MAX_ATTEMPTS, DeliveryWiring
from agentinbox.config import Config
from agentinbox.store import utcnow


def load_bus(config: Config, *, home: Path, now: Callable[[], datetime] = utcnow) -> AskBus:
    """Select the configured driver. The spool lives under ``<home>/spool``."""
    if config.bus.driver == "in-proc":
        return InProcBus(now=now)
    return SpoolBus(home / "spool", now=now)


__all__ = [
    "DEFAULT_DONE_KEEP",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "AskBus",
    "BusError",
    "BusLockedError",
    "DeliveryWiring",
    "Handler",
    "InProcBus",
    "Job",
    "JobKind",
    "SpoolBus",
    "load_bus",
    "new_job",
    "publish_digest",
]
