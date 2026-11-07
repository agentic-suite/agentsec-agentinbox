"""Webhook delivery accounting: a down receiver fails over, never blocks (M13 item 13.4)."""

from __future__ import annotations

from typing import Any

from agentinbox.bus import JobKind, new_job
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.channels.webhook import WebhookChannel
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


class FailingPost:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, url: str, body: bytes, headers: dict[str, str]) -> object:
        self.calls += 1
        raise OSError("receiver 500s")


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
            "webhook": ChannelConfig(
                enabled=True,
                url_ref="env:HOOK_URL",
                hmac_key_ref="env:HOOK_KEY",
            ),
            "terminal": ChannelConfig(enabled=True),
        },
    )


def test_a_down_webhook_records_every_attempt_and_fails_over(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = ingest(
        payload(),
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask
    post = FailingPost()
    webhook = WebhookChannel(
        config=cfg,
        post=post,
        now=lambda: NOW,
        environ={"HOOK_URL": "https://hooks.example/abc", "HOOK_KEY": "k"},
    )
    terminal = Terminal()
    wiring = DeliveryWiring(
        store, [webhook, terminal], now=lambda: NOW, backoff=lambda _attempt: None
    )

    wiring.handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

    assert post.calls == 3
    assert terminal.delivered == [ask.ask_id]
    records = sorted(
        store.list_deliveries(ask.ask_id), key=lambda item: (item.channel, item.attempt)
    )
    assert [(item.channel, item.attempt, item.status) for item in records] == [
        ("terminal", 1, "delivered"),
        ("webhook", 1, "failed"),
        ("webhook", 2, "failed"),
        ("webhook", 3, "failed"),
    ]
    kinds = [item.kind for item in store.transitions_for(ask.ask_id)]
    assert kinds.count("delivery-failed") == 3
    assert kinds.count("ask-delivered") == 1
    # Delivery failure never decides the ask and never changes its TTL.
    stored = store.get(ask.ask_id)
    assert stored.status is AskStatus.PENDING  # type: ignore[union-attr]
    assert stored.expires_at == ask.expires_at  # type: ignore[union-attr]
