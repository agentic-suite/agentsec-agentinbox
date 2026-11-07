"""InboxChannel conformance (M7 item 7.4): deliver + authenticate, never decide."""

from __future__ import annotations


def check_channel_contract(channel) -> None:  # type: ignore[no-untyped-def]
    assert isinstance(channel.name, str)
    assert channel.name
    assert callable(getattr(channel, "deliver", None))
    assert callable(getattr(channel, "authenticate", None))
    assert not hasattr(channel, "decide"), "a channel must never decide"
    assert not hasattr(channel, "submit"), "a channel must not own the answer pipeline"
