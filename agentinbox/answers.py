"""The answer-verification pipeline (M6, E4).

Design: ``docs/design/v0.1.0/claims.md``. Six steps in a fixed order:

1. channel authenticity (only an adapter may speak for a principal);
2. claim validity (exists, secret matches, unexpired, unused, unrevoked);
3. binding (ask, channel, action identity);
4. ask state (pending; terminal → late-answer observation);
5. principal authorization (roster membership, self-review, reason/confirm rules);
6. first-wins commit (CAS + single-use claim consumption).

Every failure is recorded as an ``answer-rejected`` event with a distinct internal cause; public
messages stay uniform so a caller cannot probe claim existence.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.alternatives import constraints_of, select_alternative
from agentinbox.claims import secret_matches
from agentinbox.config import ClassConfig, Config
from agentinbox.contract import compute_action_identity
from agentinbox.lifecycle import observe
from agentinbox.repair import repair_packet
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    TransitionRecord,
    to_iso,
    utcnow,
)

CREDENTIAL_CAUSES = frozenset(
    {"unknown_claim", "bad_secret", "expired_token", "used", "revoked", "guessing"}
)
_PUBLIC = {
    "unknown_claim": "bad_claim",
    "bad_secret": "bad_claim",
    "expired_token": "bad_claim",
    "used": "bad_claim",
    "revoked": "bad_claim",
    "guessing": "bad_claim",
    "late": "already_resolved",
}


class AnswerRejected(Exception):
    """An answer that must not decide anything."""

    def __init__(self, cause: str, message: str = "") -> None:
        super().__init__(f"{cause}: {message}" if message else cause)
        self.cause = cause
        self.public_cause = _PUBLIC.get(cause, cause)
        self.message = message


@dataclass(frozen=True, slots=True)
class AnswerRequest:
    ask_id: str
    claim_id: str
    secret: str
    principal: str
    channel: str
    decision: str  # "approve" | "deny"
    reason: str | None = None
    typed_confirmation: str | None = None
    assumed: bool = False
    alternative_id: str | None = None
    edits: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AnswerResult:
    ask: AskRecord
    winner: bool
    claim_id: str


class AnswerVerifier:
    """Channel-agnostic verifier; adapters supply an authenticated principal."""

    def __init__(
        self,
        store: AskStore,
        config: Config,
        *,
        now: Callable[[], datetime] = utcnow,
        max_attempts: int = 5,
    ) -> None:
        self.store = store
        self.config = config
        self._now = now
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._lock = threading.Lock()

    def submit(
        self, request: AnswerRequest, *, channel_authenticated: bool
    ) -> AnswerResult:
        if request.decision not in {"approve", "deny"}:
            raise ValueError("decision must be 'approve' or 'deny'")
        now = self._now()

        ask = self.store.get(request.ask_id)
        if ask is None:
            raise AnswerRejected("unknown_ask", "no such ask")

        if not channel_authenticated:
            self._reject(ask, request, now, "bad_signature", "channel did not authenticate")
            raise AnswerRejected("bad_signature", "channel authentication required")

        # --- claim validity -------------------------------------------------
        claim = self._find_claim(request.claim_id)
        if claim is None:
            self._credential_failure(ask, request, now, "unknown_claim")
        assert claim is not None
        if not secret_matches(claim, request.secret):
            self._credential_failure(ask, request, now, "bad_secret")
        if claim.revoked_at is not None:
            self._credential_failure(ask, request, now, "revoked")
        if claim.consumed_at is not None:
            self._credential_failure(ask, request, now, "used")
        if claim.expires_at <= now:
            self._credential_failure(ask, request, now, "expired_token")

        # --- binding --------------------------------------------------------
        if claim.ask_id != ask.ask_id or claim.channel != request.channel:
            self._reject(ask, request, now, "identity_mismatch", "claim is bound elsewhere")
            raise AnswerRejected("identity_mismatch", "claim is bound to another ask/channel")
        if (
            claim.action_identity is not None
            and claim.action_identity != ask.action_identity
        ):
            self._reject(ask, request, now, "identity_mismatch", "claim identity is stale")
            raise AnswerRejected("identity_mismatch", "claim is bound to another action")
        if claim.tier is not None and ask.tier is not None and claim.tier != ask.tier:
            self._reject(ask, request, now, "identity_mismatch", "claim tier is stale")
            raise AnswerRejected("identity_mismatch", "claim tier is stale")

        # --- authorization --------------------------------------------------
        ask_class = self._class_for(ask)
        allowed = self._allowed_principals(ask_class, request.channel, tier=ask.tier)
        if request.principal not in allowed:
            self._reject(ask, request, now, "off_roster", "principal is not on the roster")
            raise AnswerRejected("off_roster", "principal is not authorized for this ask")

        requested_by = str(ask.payload.get("requested_by", ""))
        producer = ask.payload.get("_producer") or {}
        if producer.get("authenticated") and producer.get("principal"):
            # A signed adapter's principal is verified; it outranks the self-reported field.
            requested_by = str(producer["principal"])
        if request.principal == requested_by and ask_class.self_review != "allow":
            self._reject(ask, request, now, "self_review", "requester cannot decide their own ask")
            raise AnswerRejected("self_review", "self-review is not allowed for this class")

        # --- ask state ------------------------------------------------------
        if ask.status is not AskStatus.PENDING:
            winner = self._late(ask, request, now)
            raise AnswerRejected("late", _late_message(winner))

        if request.decision == "deny" and ask_class.require_reason_on_deny and not request.reason:
            self._reject(ask, request, now, "reason_required", "deny requires a reason")
            raise AnswerRejected("reason_required", "deny requires a reason")

        if request.decision == "approve" and ask.payload.get("class") == "irreversible":
            expected = str(ask.payload.get("action", ""))
            if request.typed_confirmation != expected:
                self._reject(ask, request, now, "confirmation", "typed confirmation required")
                raise AnswerRejected("confirmation", "typed confirmation of the action is required")

        # --- constrained allow / edits --------------------------------------
        if request.alternative_id and request.edits:
            raise AnswerRejected("conflicting_choice", "choose one alternative or one edit set")
        if request.alternative_id and request.decision != "approve":
            raise AnswerRejected("conflicting_choice", "an alternative can only be allowed")
        alternative = None
        chosen_constraints: tuple[Mapping[str, Any], ...] = ()
        alternative_fingerprint: str | None = None
        if request.alternative_id:
            try:
                alternative = select_alternative(ask, request.alternative_id)
            except KeyError as exc:
                cause = str(exc.args[0])
                self._reject(ask, request, now, cause, "alternative is not selectable")
                raise AnswerRejected(cause, "alternative is not selectable") from None
            chosen_constraints = constraints_of(alternative)
            alternative_fingerprint = str(alternative.get("fingerprint"))

        edits: dict[str, Any] | None = None
        original_identity: str | None = None
        edited_identity: str | None = None
        if request.edits:
            editable = set(ask_class.edit_schema)
            if not editable:
                self._reject(ask, request, now, "edit_schema", "class does not allow edits")
                raise AnswerRejected("edit_schema", "class does not allow edits")
            invalid = sorted(set(request.edits) - editable)
            if invalid:
                self._reject(
                    ask, request, now, "edit_schema", f"field not editable: {invalid[0]}"
                )
                raise AnswerRejected("edit_schema", f"field not editable: {invalid[0]}")
            if request.decision != "approve":
                raise AnswerRejected("conflicting_choice", "edits only apply to an allow")
            merged = {**dict(ask.payload.get("arguments") or {}), **dict(request.edits)}
            edited_identity = compute_action_identity(
                tool=str(ask.payload.get("tool", "")),
                action=str(ask.payload.get("action", "")),
                arguments=merged,
            )
            original_identity = ask.action_identity
            edits = dict(request.edits)

        # --- first-wins commit ---------------------------------------------
        target = AskStatus.APPROVED if request.decision == "approve" else AskStatus.DENIED
        won = self.store.cas_status(
            ask.ask_id,
            expected=AskStatus.PENDING,
            new=target,
            transition=TransitionRecord(
                ask_id=ask.ask_id,
                at=now,
                kind="answer",
                from_status=AskStatus.PENDING,
                to_status=target,
                principal=request.principal,
                channel=request.channel,
                claim_id=request.claim_id,
                reason=request.reason,
                detail=self._answer_detail(
                    ask,
                    request,
                    alternative=alternative,
                    constraints=chosen_constraints,
                    alternative_fingerprint=alternative_fingerprint,
                    edits=edits,
                    original_identity=original_identity,
                    edited_identity=edited_identity,
                ),
            ),
        )
        if not won:
            winner = self._late(ask, request, now)
            raise AnswerRejected("late", _late_message(winner))

        consumed = self.store.consume_claim(request.claim_id, ask_id=ask.ask_id, at=now)
        if not consumed:  # pragma: no cover - the claim was validated above under lock
            raise AnswerRejected("used", "claim was consumed concurrently")

        resolved = self.store.get(ask.ask_id)
        assert resolved is not None
        return AnswerResult(ask=resolved, winner=True, claim_id=request.claim_id)

    # ------------------------------------------------------------------ helpers

    def _answer_detail(
        self,
        ask: AskRecord,
        request: AnswerRequest,
        *,
        alternative: Mapping[str, Any] | None,
        constraints: Sequence[Mapping[str, Any]],
        alternative_fingerprint: str | None,
        edits: Mapping[str, Any] | None,
        original_identity: str | None,
        edited_identity: str | None,
    ) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "decision": request.decision,
            "assumed_principal": request.assumed,
        }
        if alternative is not None:
            detail["alternative"] = alternative.get("id")
            detail["alternative_fingerprint"] = alternative_fingerprint
            detail["constraints"] = [dict(item) for item in constraints]
        if edits:
            detail["edits"] = dict(edits)
            detail["original_action_identity"] = original_identity
            detail["edited_action_identity"] = edited_identity
        if request.decision == "deny":
            detail["repair"] = repair_packet(
                ask, reason=request.reason, config=self.config
            )
        return detail

    def _find_claim(self, claim_id: str):  # type: ignore[no-untyped-def]
        return self.store.get_claim(claim_id)

    def _class_for(self, ask: AskRecord) -> ClassConfig:
        name = str(ask.payload.get("class", ""))
        ask_class = self.config.classes.get(name)
        if ask_class is None:
            raise AnswerRejected("unknown_class", f"no configured class {name!r}")
        return ask_class

    def _allowed_principals(
        self, ask_class: ClassConfig, channel: str, *, tier: str | None = None
    ) -> tuple[str, ...]:
        # A tier change is routing: only the current tier may answer (M11, R4).
        if tier is not None:
            tiers: tuple[str, ...] = (tier,)
        else:
            tiers = ask_class.ladder or tuple(self.config.roster.keys())
        allowed: list[str] = []
        for tier in tiers:
            allowed.extend(self.config.roster.get(tier, {}).get(channel, ()))
        return tuple(allowed)

    def _credential_failure(
        self, ask: AskRecord, request: AnswerRequest, now: datetime, cause: str
    ) -> None:
        with self._lock:
            count = self._attempts.get(request.claim_id, 0) + 1
            self._attempts[request.claim_id] = count
        if count > self.max_attempts:
            self._reject(ask, request, now, "guessing", "claim attempt limit exceeded")
            raise AnswerRejected("guessing", "too many attempts for this claim")
        self._reject(ask, request, now, cause, "claim rejected")
        raise AnswerRejected(cause, "claim rejected")

    def _reject(
        self, ask: AskRecord, request: AnswerRequest, now: datetime, cause: str, message: str
    ) -> None:
        self.store.append_event(
            TransitionRecord(
                ask_id=ask.ask_id,
                at=now,
                kind="answer-rejected",
                from_status=ask.status,
                to_status=ask.status,
                principal=request.principal,
                channel=request.channel,
                claim_id=request.claim_id,
                detail={
                    "cause": cause,
                    "message": message,
                    "public_cause": _PUBLIC.get(cause, cause),
                },
            )
        )

    def _late(
        self, ask: AskRecord, request: AnswerRequest, now: datetime
    ) -> TransitionRecord | None:
        transitions: Sequence[TransitionRecord] = self.store.transitions_for(ask.ask_id)
        winner = next(
            (
                item
                for item in reversed(transitions)
                if item.to_status in {AskStatus.APPROVED, AskStatus.DENIED}
            ),
            None,
        )
        observe(
            self.store,
            ask.ask_id,
            kind="late-answer",
            at=now,
            principal=request.principal,
            channel=request.channel,
            detail={
                "attempted": request.decision,
                "winner": None if winner is None else winner.principal,
                "winner_at": None if winner is None else winner.at.isoformat(),
            },
        )
        return winner


def _late_message(winner: TransitionRecord | None) -> str:
    if winner is None:
        return "ask is already resolved"
    return f"already resolved by {winner.principal} at {to_iso(winner.at)}"


__all__ = [
    "CREDENTIAL_CAUSES",
    "AnswerRejected",
    "AnswerRequest",
    "AnswerResult",
    "AnswerVerifier",
]
