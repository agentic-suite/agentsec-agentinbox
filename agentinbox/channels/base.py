"""Inbox channel contract (M7).

A channel **delivers** and **authenticates a human**; it never decides. Answers go back through
the M6 verifier with the principal the adapter authenticated.
"""

from __future__ import annotations

from typing import Protocol

from agentinbox.card import Card
from agentinbox.store import AskRecord


class ChannelError(Exception):
    """A channel could not deliver or authenticate."""


class InboxChannel(Protocol):
    name: str

    def deliver(self, ask: AskRecord, card: Card) -> None: ...

    def authenticate(self, *, as_name: str | None = None) -> str | None: ...
