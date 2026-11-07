"""Failover matrix: a downed surface loses nothing and later shows the outcome (M14 item 14.4)."""

from __future__ import annotations

from typing import Any

from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.bus import JobKind, new_job
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.claims import mint_claim
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.parity import surface_outcome
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload

ASK_ID = "ask_0123456789abcdef"


class DownWebhook:
    name = "webhook"

    def __init__(self) -> None:
        self.attempts = 0

    def deliver(self, ask: Any, card: Any) -> None:
        self.attempts += 1
        raise OSError("webhook is down")

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        return None


class Terminal:
    name = "terminal"

    def __init__(self) -> None:
        self.delivered: list[str] = []

    def deliver(self, ask: Any, card: Any) -> None:
        self.delivered.append(ask.ask_id)

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        return None


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
        channels={
            "terminal": ChannelConfig(enabled=True),
            "webhook": ChannelConfig(enabled=True),
        },
    )


def test_a_downed_surface_updates_without_reasking(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = ingest(
        payload(ask_id=ASK_ID),
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask
    down = DownWebhook()
    up = Terminal()
    DeliveryWiring(
        store, [down, up], now=lambda: NOW, backoff=lambda _attempt: None
    ).handle(new_job(JobKind.DELIVER, ask_id=ASK_ID, now=NOW))

    assert down.attempts == 3
    assert up.delivered == [ASK_ID]
    records = sorted(
        store.list_deliveries(ASK_ID), key=lambda item: (item.channel, item.attempt)
    )
    assert [item.status for item in records] == ["delivered", "failed", "failed", "failed"]
    assert store.list_pending(now=NOW) == [ask]

    minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)
    AnswerVerifier(store, cfg, now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=ASK_ID,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal="alice",
            channel="terminal",
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )

    # The downed surface is not re-asked; it simply reads the new outcome.
    assert store.list_pending(now=NOW) == []
    assert "status=approved" in surface_outcome(
        store, ASK_ID, surface="desktop", now=NOW
    )
    assert any(item.status == "delivered" for item in store.list_deliveries(ASK_ID))
