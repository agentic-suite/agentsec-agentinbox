"""Every channel passes the shared conformance contract (M14 item 14.5)."""

from __future__ import annotations

import io

import pytest

from agentinbox.channels.ci import CiWaitChannel
from agentinbox.channels.desktop import DesktopChannel, Notification
from agentinbox.channels.terminal import TerminalChannel
from agentinbox.channels.webhook import WebhookChannel
from agentinbox.config import ChannelConfig, Config
from tests.channels.conformance import check_channel_contract


class Recorder:
    def send(self, notification: Notification) -> None:
        del notification


def channel_config() -> Config:
    return Config(
        classes={},
        roster={},
        channels={
            "terminal": ChannelConfig(enabled=True),
            "desktop": ChannelConfig(enabled=True),
            "webhook": ChannelConfig(enabled=True),
        },
    )


def test_terminal_channel_passes_conformance() -> None:
    channel = TerminalChannel(
        config=Config(classes={}, roster={}),
        output=io.StringIO(),
        input_fn=lambda _prompt: "",
        interactive=True,
    )

    check_channel_contract(channel)


def test_every_v010_channel_passes_conformance() -> None:
    channels = [
        TerminalChannel(
            config=Config(classes={}, roster={}),
            output=io.StringIO(),
            input_fn=lambda _prompt: "",
            interactive=True,
        ),
        DesktopChannel(config=channel_config(), notifier=Recorder()),
        WebhookChannel(config=channel_config(), post=lambda *_args: None),
        CiWaitChannel(output=io.StringIO()),
    ]

    for channel in channels:
        check_channel_contract(channel)

    for display_only in channels[1:]:
        assert display_only.authenticate() is None


def test_a_deciding_channel_fails_conformance() -> None:
    class Deciding:
        name = "decider"

        def deliver(self, ask, card) -> None:  # type: ignore[no-untyped-def]
            return None

        def authenticate(self, *, as_name: str | None = None) -> str | None:
            return "alice"

        def decide(self, *args: object) -> None:
            return None

    with pytest.raises(AssertionError):
        check_channel_contract(Deciding())
