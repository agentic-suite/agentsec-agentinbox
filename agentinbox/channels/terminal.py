"""Terminal channel: blocking card, a/d answers, typed confirm + reason (M7).

The OS session is the principal. ``--as`` is refused unless ``[channels.terminal] allow_as = true``
and is recorded as an **assumed** principal. Non-interactive invocations never prompt and can never
approve: they return a pending decision (exit 5).
"""

from __future__ import annotations

import getpass
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TextIO

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.card import Card, build_card
from agentinbox.channels.base import ChannelError
from agentinbox.claims import mint_claim
from agentinbox.config import Config
from agentinbox.exit_codes import ExitCode
from agentinbox.resolve import resolve
from agentinbox.store import AskRecord, AskStore, utcnow

InputFn = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class TerminalChannel:
    name = "terminal"

    config: Config
    output: TextIO
    input_fn: InputFn
    interactive: bool

    def deliver(self, ask: AskRecord, card: Card) -> None:
        self.output.write(card.render("terminal"))
        self.output.flush()

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        if as_name is None:
            return getpass.getuser()
        terminal = self.config.channels.get("terminal")
        if terminal is None or not terminal.allow_as:
            raise ChannelError(
                "--as is refused: set [channels.terminal] allow_as = true "
                "to permit assumed principals"
            )
        return as_name

    def answer(
        self,
        store: AskStore,
        verifier: AnswerVerifier,
        ask: AskRecord,
        *,
        decision: str | None = None,
        reason: str | None = None,
        as_name: str | None = None,
        now: datetime | None = None,
    ) -> ExitCode:
        moment = now or utcnow()
        if not self.interactive:
            self._write_non_interactive(resolve(store, ask.ask_id, now=moment).to_dict())
            return ExitCode.PENDING

        principal = self.authenticate(as_name=as_name)
        if principal is None:
            return ExitCode.UNAVAILABLE
        assumed = as_name is not None

        minted = mint_claim(
            store, ask, channel=self.name, tier=ask.tier, now=moment
        )
        card = build_card(ask, now=moment, transitions=store.transitions_for(ask.ask_id))
        self.deliver(ask, card)

        chosen = decision or self._choose()
        if chosen == "q":
            self.output.write("left pending\n")
            return ExitCode.PENDING
        if chosen not in {"approve", "deny"}:
            return ExitCode.UNAVAILABLE

        if chosen == "deny" and reason is None and self._reason_required(ask):
            reason = self.input_fn("reason (required): ").strip()
        if chosen == "approve" and self._requires_confirmation(ask):
            action = ask.payload.get("action")
            typed = self.input_fn(f"type the action name to confirm ({action}): ")
            typed = typed.strip()
        else:
            typed = None

        try:
            result = verifier.submit(
                AnswerRequest(
                    ask_id=ask.ask_id,
                    claim_id=minted.claim.claim_id,
                    secret=minted.secret,
                    principal=principal,
                    channel=self.name,
                    decision=chosen,
                    reason=reason,
                    typed_confirmation=typed,
                    assumed=assumed,
                ),
                channel_authenticated=True,
            )
        except AnswerRejected as exc:
            self.output.write(f"answer rejected: {exc.public_cause}\n")
            return ExitCode.UNAVAILABLE

        self.output.write(
            f"ask {result.ask.ask_id}: {result.ask.status.value}"
            f"{' (assumed principal)' if assumed else ''}\n"
        )
        return ExitCode.APPROVED if chosen == "approve" else ExitCode.DENIED

    # ------------------------------------------------------------------ helpers

    def _choose(self) -> str:
        while True:
            prompt = "[a]pprove / [d]eny / [?]details / [q]leave pending: "
            answer = self.input_fn(prompt).strip().lower()
            if answer in {"a", "approve"}:
                return "approve"
            if answer in {"d", "deny"}:
                return "deny"
            if answer in {"q", "quit"}:
                return "q"
            if answer in {"?", "help"}:
                self.output.write("a=approve  d=deny  ?=details  q=leave pending\n")
                continue
            self.output.write("unrecognized choice\n")

    def _requires_confirmation(self, ask: AskRecord) -> bool:
        return str(ask.payload.get("class")) == "irreversible"

    def _reason_required(self, ask: AskRecord) -> bool:
        name = str(ask.payload.get("class", ""))
        ask_class = self.config.classes.get(name)
        return bool(ask_class and ask_class.require_reason_on_deny)

    def _write_non_interactive(self, payload: dict[str, object]) -> None:
        self.output.write(json.dumps(payload, sort_keys=True) + "\n")
        self.output.flush()


__all__ = ["ChannelError", "TerminalChannel"]
