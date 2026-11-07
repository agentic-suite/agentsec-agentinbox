"""Signed, display-only outbound webhook (M13).

Design: ``docs/design/v0.1.0/webhook.md``. The payload is a notification: it says "answer in your
terminal", carries no arguments, and cannot answer. The channel implements ``deliver()`` only.
"""

from __future__ import annotations

import hashlib
import hmac
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.card import Card
from agentinbox.channels.base import ChannelError
from agentinbox.config import Config
from agentinbox.secrets import SecretError, resolve_ref
from agentinbox.store import AskRecord, canonical_json, to_iso, utcnow

CONTRACT = "webhook/1.0"
DEFAULT_TIMEOUT_SECONDS = 5.0

Poster = Callable[[str, bytes, dict[str, str]], object]


def build_payload(ask: AskRecord, *, now: datetime) -> dict[str, Any]:
    """The display-only view. It deliberately has no arguments and no decision affordance."""
    remaining = max(0, int((ask.expires_at - now).total_seconds()))
    return {
        "contract": CONTRACT,
        "ask_id": ask.ask_id,
        "class": str(ask.payload.get("class", "unknown")),
        "action": str(ask.payload.get("action", "unknown")),
        "fingerprint": _fingerprint(ask.action_identity),
        "status": ask.status.value,
        "ttl_seconds": remaining,
        "expires_at": to_iso(ask.expires_at),
        "answer_command": f"agentinbox answer {ask.ask_id}",
        "answer_channel": "terminal",
        "decision": None,
    }


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _fingerprint(identity: str) -> str:
    value = identity.removeprefix("sha256:")
    return f"sha256:{value[:12]}…" if value else "sha256:unknown"


def _default_post(url: str, body: bytes, headers: dict[str, str]) -> object:
    if not url.startswith(("http://", "https://")):
        raise ChannelError("webhook URL must be http(s)")
    request = urllib.request.Request(  # noqa: S310 - scheme checked above
        url, data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(  # noqa: S310 - scheme checked above
        request, timeout=DEFAULT_TIMEOUT_SECONDS
    ) as response:
        response.read()
        return response.status


@dataclass(frozen=True, slots=True)
class WebhookChannel:
    name = "webhook"

    config: Config
    post: Poster = _default_post
    now: Callable[[], datetime] = utcnow
    environ: Mapping[str, str] | None = None

    def deliver(self, ask: AskRecord, card: Card | None = None) -> None:
        del card  # the display-only payload is built from the record, never arguments
        channel = self.config.channels.get("webhook")
        if channel is None or not channel.enabled:
            return
        if not channel.url_ref or not channel.hmac_key_ref:
            raise ChannelError(
                "webhook is enabled but url_ref/hmac_key_ref is not configured"
            )
        try:
            url = resolve_ref(channel.url_ref, environ=self.environ)
            secret = resolve_ref(channel.hmac_key_ref, environ=self.environ)
        except SecretError as exc:
            raise ChannelError(f"webhook reference unavailable: {exc}") from None

        body = canonical_json(build_payload(ask, now=self.now())).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-AgentInbox-Contract": CONTRACT,
            "X-AgentInbox-Signature": sign(secret, body),
        }
        try:
            self.post(url, body, headers)
        except (OSError, urllib.error.URLError) as exc:
            raise ChannelError(f"webhook delivery failed: {exc}") from None

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        del as_name
        return None


__all__ = ["CONTRACT", "WebhookChannel", "build_payload", "sign"]
