"""Desktop channel: wake-up only, content rules, hygiene, availability (M8)."""

from __future__ import annotations

import subprocess
from datetime import timedelta

import pytest

from agentinbox.channels.base import ChannelError
from agentinbox.channels.desktop import (
    DesktopChannel,
    LinuxNotifier,
    MacOSNotifier,
    Notification,
    UnavailableNotifier,
    default_notifier,
    desktop_availability,
    render_notification,
)
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import AskRecord
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload
from tests.channels.conformance import check_channel_contract


class Recorder:
    """A backend double; records notifications instead of touching the desktop."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> None:
        self.sent.append(notification)


def make_config(*, enabled: bool = True) -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(ttl_seconds=300, warn_seconds=60),
        },
        channels={"desktop": ChannelConfig(enabled=enabled)},
    )


def make_ask(store, *, cfg: Config | None = None, **overrides: object) -> AskRecord:  # type: ignore[no-untyped-def]
    cfg = cfg or make_config()
    body = payload(**overrides)
    return ingest(
        body,
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def test_content_is_fingerprint_class_and_ttl_only(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store, arguments={"command": "aws s3 rm secret-bucket --token sk-live-SECRET"})

    notification = render_notification(ask, now=NOW, tier="tier-1")

    assert "sha256:" in notification.body
    assert "irreversible" in notification.body
    assert "5m00s" in notification.body or "4m59s" in notification.body
    assert "tier-1" in notification.body
    # Arguments, tool output, and secrets never reach the notification.
    assert "aws" not in notification.body
    assert "secret-bucket" not in notification.body
    assert "sk-live-SECRET" not in notification.body
    assert "psql" not in notification.body
    assert notification.thread_id == ask.ask_id


def test_deliver_only_contract(store) -> None:  # type: ignore[no-untyped-def]
    cfg = make_config()
    recorder = Recorder()
    channel = DesktopChannel(config=cfg, notifier=recorder, now=lambda: NOW)
    ask = make_ask(store, cfg=cfg)

    check_channel_contract(channel)
    channel.deliver(ask, card=None)  # type: ignore[arg-type]

    assert channel.authenticate() is None
    assert channel.authenticate(as_name="alice") is None
    assert len(recorder.sent) == 1
    assert not hasattr(channel, "answer")
    assert not hasattr(channel, "decide")


def test_disabled_channel_delivers_nothing(store) -> None:  # type: ignore[no-untyped-def]
    cfg = make_config(enabled=False)
    recorder = Recorder()
    channel = DesktopChannel(config=cfg, notifier=recorder, now=lambda: NOW)
    ask = make_ask(store, cfg=cfg)

    channel.deliver(ask, card=None)  # type: ignore[arg-type]

    assert recorder.sent == []


def test_once_per_tier(store) -> None:  # type: ignore[no-untyped-def]
    cfg = make_config()
    recorder = Recorder()
    channel = DesktopChannel(config=cfg, notifier=recorder, now=lambda: NOW)
    ask = make_ask(store, cfg=cfg)

    channel.deliver(ask, card=None)  # type: ignore[arg-type]
    channel.deliver(ask, card=None)  # type: ignore[arg-type]
    assert len(recorder.sent) == 1

    escalated = AskRecord(
        ask_id=ask.ask_id,
        action_identity=ask.action_identity,
        session_id=ask.session_id,
        agent_id=ask.agent_id,
        created_at=ask.created_at,
        expires_at=ask.expires_at,
        payload=ask.payload,
        status=ask.status,
        tier="tier-2",
    )
    channel.deliver(escalated, card=None)  # type: ignore[arg-type]
    assert len(recorder.sent) == 2
    assert "tier-2" in recorder.sent[-1].body


def test_a_warning_is_a_second_notification(store) -> None:  # type: ignore[no-untyped-def]
    from dataclasses import replace

    from agentinbox.card import build_card

    cfg = make_config()
    recorder = Recorder()
    channel = DesktopChannel(config=cfg, notifier=recorder, now=lambda: NOW)
    ask = make_ask(store, cfg=cfg)
    card = build_card(ask, now=NOW)

    channel.deliver(ask, card)
    channel.deliver(ask, replace(card, warning=True))
    channel.deliver(ask, replace(card, warning=True))

    assert len(recorder.sent) == 2
    assert recorder.sent[-1].kind == "warn"
    assert "expires soon" in recorder.sent[-1].body


def test_one_digest_per_flood_window(store) -> None:  # type: ignore[no-untyped-def]
    cfg = make_config()
    recorder = Recorder()
    channel = DesktopChannel(config=cfg, notifier=recorder, now=lambda: NOW)

    channel.notify_digest(window_start=NOW, first_ask_id="ask-1", count=200)
    channel.notify_digest(window_start=NOW, first_ask_id="ask-1", count=201)
    channel.notify_digest(window_start=NOW + timedelta(seconds=31), first_ask_id="ask-9", count=3)

    assert len(recorder.sent) == 2
    assert "200" in recorder.sent[0].body
    assert recorder.sent[0].thread_id == "digest"


def test_macos_backend_invokes_osascript_without_a_shell() -> None:
    calls: list[list[str]] = []

    def runner(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        assert kwargs["shell"] is False
        assert kwargs["check"] is True
        return subprocess.CompletedProcess(argv, 0)

    notifier = MacOSNotifier(runner=runner)
    notifier.send(Notification(title="t", body="b", thread_id="ask-1", ask_id="ask-1"))

    argv = calls[0]
    assert argv[0] == "osascript"
    assert any("ask-1" in part or "t" in part for part in argv)


def test_linux_backend_invokes_notify_send_without_a_shell() -> None:
    calls: list[list[str]] = []

    def runner(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(argv, 0)

    notifier = LinuxNotifier(runner=runner)
    notifier.send(Notification(title="t", body="b", thread_id="ask-1", ask_id="ask-1"))

    argv = calls[0]
    assert argv[:2] == ["notify-send", "--app-name"]
    assert "agentinbox" in argv


def test_backend_failure_is_a_channel_error() -> None:
    def runner(argv, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("osascript")

    notifier = MacOSNotifier(runner=runner)
    with pytest.raises(ChannelError):
        notifier.send(Notification(title="t", body="b", thread_id="a", ask_id="a"))


def test_availability_macos_reports_missing_binary() -> None:
    available, detail = desktop_availability(
        platform="darwin", which=lambda _name: None, environ={}
    )
    assert available is False
    assert "osascript" in detail


def test_availability_linux_requires_a_display() -> None:
    available, detail = desktop_availability(
        platform="linux", which=lambda _name: "/usr/bin/notify-send", environ={}
    )
    assert available is False
    assert "DISPLAY" in detail

    available, _ = desktop_availability(
        platform="linux",
        which=lambda _name: "/usr/bin/notify-send",
        environ={"DISPLAY": ":0"},
    )
    assert available is True


def test_availability_macos_available_with_a_gui_session() -> None:
    available, detail = desktop_availability(
        platform="darwin", which=lambda _name: "/usr/bin/osascript", environ={}
    )
    assert available is True
    assert "osascript" in detail


def test_availability_unsupported_platform() -> None:
    available, detail = desktop_availability(
        platform="win32", which=lambda _name: None, environ={}
    )
    assert available is False
    assert "unsupported" in detail


def test_unavailable_notifier_fails_loudly() -> None:
    notifier = UnavailableNotifier("no backend")
    with pytest.raises(ChannelError):
        notifier.send(Notification(title="t", body="b", thread_id="a", ask_id="a"))


def test_default_notifier_matches_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agentinbox.channels.desktop.sys.platform", "linux")
    assert isinstance(default_notifier(), LinuxNotifier)
    monkeypatch.setattr("agentinbox.channels.desktop.sys.platform", "freebsd")
    assert isinstance(default_notifier(), UnavailableNotifier)


def test_availability_macos_headless_ssh_is_unavailable() -> None:
    available, detail = desktop_availability(
        platform="darwin",
        which=lambda _name: "/usr/bin/osascript",
        environ={"SSH_CONNECTION": "10.0.0.1 1 10.0.0.2 22"},
    )
    assert available is False
    assert "headless" in detail.lower() or "GUI" in detail
