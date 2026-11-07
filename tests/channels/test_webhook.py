"""Signed, display-only outbound webhook (M13 items 13.1/13.2)."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest

from agentinbox.channels.base import ChannelError
from agentinbox.channels.webhook import WebhookChannel, build_payload
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.secrets import SecretError, resolve_ref
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload
from tests.channels.conformance import check_channel_contract


class Post:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []
        self.fail = fail

    def __call__(self, url: str, body: bytes, headers: dict[str, str]) -> object:
        if self.fail:
            raise OSError("receiver is down")
        self.calls.append((url, body, headers))
        return object()


def config(
    *,
    enabled: bool = True,
    url_ref: str | None = "env:HOOK_URL",
    key_ref: str | None = "env:HOOK_KEY",
) -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        channels={
            "webhook": ChannelConfig(
                enabled=enabled, url_ref=url_ref, hmac_key_ref=key_ref
            )
        },
    )


def make(store, cfg: Config):  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def channel(cfg: Config, post: Post, environ: dict[str, str] | None = None) -> WebhookChannel:
    return WebhookChannel(
        config=cfg,
        post=post,
        now=lambda: NOW,
        environ=environ or {"HOOK_URL": "https://hooks.example/abc", "HOOK_KEY": "s3cret"},
    )


def test_payload_is_display_only(store) -> None:  # type: ignore[no-untyped-def]
    ask = make(store, config())

    payload_body = build_payload(ask, now=NOW)

    assert payload_body["contract"] == "webhook/1.0"
    assert payload_body["ask_id"] == ask.ask_id
    assert payload_body["class"] == "irreversible"
    assert payload_body["fingerprint"].startswith("sha256:")
    assert payload_body["ttl_seconds"] == 300
    assert payload_body["decision"] is None
    assert payload_body["answer_channel"] == "terminal"
    assert payload_body["answer_command"] == f"agentinbox answer {ask.ask_id}"
    # Arguments and secrets never leave the box.
    assert "psql" not in str(payload_body)
    assert "sk-live" not in str(payload_body)
    assert "arguments" not in payload_body


def test_the_post_is_hmac_signed(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = make(store, cfg)
    post = Post()

    channel(cfg, post).deliver(ask)

    url, body, headers = post.calls[0]
    assert url == "https://hooks.example/abc"
    expected = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert headers["X-AgentInbox-Signature"] == f"sha256={expected}"
    assert headers["X-AgentInbox-Contract"] == "webhook/1.0"
    assert headers["Content-Type"] == "application/json"
    assert "s3cret" not in headers.values()


def test_the_channel_never_answers(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = make(store, cfg)
    post = Post()
    adapter = channel(cfg, post)

    check_channel_contract(adapter)
    adapter.deliver(ask)
    assert adapter.authenticate() is None
    assert adapter.authenticate(as_name="alice") is None
    assert not hasattr(adapter, "answer")
    assert not hasattr(adapter, "decide")


def test_disabled_channel_posts_nothing(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config(enabled=False)
    ask = make(store, cfg)
    post = Post()

    channel(cfg, post).deliver(ask)
    assert post.calls == []


def test_a_missing_reference_fails_closed(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = make(store, cfg)
    post = Post()

    with pytest.raises(ChannelError):
        channel(cfg, post, environ={"HOOK_URL": "https://x"}).deliver(ask)
    assert post.calls == []


def test_a_network_failure_is_a_channel_error(store) -> None:  # type: ignore[no-untyped-def]
    cfg = config()
    ask = make(store, cfg)

    with pytest.raises(ChannelError):
        channel(cfg, Post(fail=True)).deliver(ask)


def test_file_references_are_supported(tmp_path: Path) -> None:
    key_file = tmp_path / "hook.key"
    key_file.write_text("file-secret\n", encoding="utf-8")

    assert resolve_ref(f"file:{key_file}") == "file-secret"
    with pytest.raises(SecretError):
        resolve_ref("env:DOES_NOT_EXIST", environ={})
    with pytest.raises(SecretError):
        resolve_ref(f"file:{tmp_path / 'missing'}")
