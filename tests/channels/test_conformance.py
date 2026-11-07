"""Every channel passes the shared conformance contract."""

from __future__ import annotations

import io

from agentinbox.channels.terminal import TerminalChannel
from agentinbox.config import Config
from tests.channels.conformance import check_channel_contract


def test_terminal_channel_passes_conformance() -> None:
    channel = TerminalChannel(
        config=Config(classes={}, roster={}),
        output=io.StringIO(),
        input_fn=lambda _prompt: "",
        interactive=True,
    )

    check_channel_contract(channel)
