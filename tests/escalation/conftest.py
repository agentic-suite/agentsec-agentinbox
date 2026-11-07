"""Shared escalation fixtures (M11)."""

from __future__ import annotations

from datetime import datetime, timedelta

from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import AskStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


class Clock:
    def __init__(self, start: datetime = NOW) -> None:
        self.moment = start

    def __call__(self) -> datetime:
        return self.moment


def make_config(
    *,
    tiers: tuple[str, ...] = ("tier-1", "on-call"),
    delays: tuple[int, ...] = (0, 300),
    ttl_seconds: int = 3600,
    roster: dict[str, dict[str, tuple[str, ...]]] | None = None,
) -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=ttl_seconds,
                warn_seconds=60,
                ladder=tiers,
                ladder_delays=delays,
            )
        },
        roster=roster
        or {
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
        },
        channels={"terminal": _channel()},
    )


def _channel():  # type: ignore[no-untyped-def]
    from agentinbox.config import ChannelConfig

    return ChannelConfig(enabled=True)


def make_ask(
    store: AskStore,
    *,
    config: Config | None = None,
    now: datetime = NOW,
    ttl_seconds: int = 3600,
) -> object:
    config = config or make_config()
    body = payload()
    body["expires_at"] = (
        (now + timedelta(seconds=ttl_seconds))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    return ingest(
        body,
        store=store,
        config=config,
        producer=ProducerIdentity.unauthenticated(),
        now=now,
    ).ask
