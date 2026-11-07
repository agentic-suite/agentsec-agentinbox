"""CI-wait surface adapter (M14): renders the ``ci`` card, never answers.

The actual blocking behaviour lives in :func:`agentinbox.gate.gate`; this adapter exists so the
channel conformance suite covers the CI surface like every other surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TextIO

from agentinbox.card import Card
from agentinbox.store import AskRecord


@dataclass(frozen=True, slots=True)
class CiWaitChannel:
    name = "ci"

    output: TextIO

    def deliver(self, ask: AskRecord, card: Card) -> None:
        del ask
        self.output.write(card.render("ci"))
        self.output.flush()

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        del as_name
        return None


__all__ = ["CiWaitChannel"]
