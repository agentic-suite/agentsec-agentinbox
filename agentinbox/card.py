"""Surface-neutral decision card (M5).

Design: ``docs/design/v0.1.0/card.md``. One core builds four blocks; per-surface frontends only
add chrome. Every missing field renders an explicit **unknown**; agent-supplied text is inert
plain text, labelled, capped, and never turned into markup, links, or an approve affordance.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agentinbox.alternatives import (
    alternatives_for,
    recall_line,
    render_alternative,
    suggestions_for,
)
from agentinbox.store import AskRecord, AskStatus, TransitionRecord

FIELD_CAP = 512
CARD_CAP = 4000
SURFACES = ("text", "terminal", "desktop", "ci")
UNTRUSTED_LABEL = "[untrusted: tool output]"

_CONTROL = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]"
)
_MARKUP = re.compile(r"<[^>]{0,200}>")


@dataclass(frozen=True, slots=True)
class Field:
    label: str
    value: str
    untrusted: bool = False


@dataclass(frozen=True, slots=True)
class Block:
    title: str
    fields: tuple[Field, ...]


@dataclass(frozen=True, slots=True)
class Redaction:
    field: str
    redaction_class: str
    count: int


@dataclass(frozen=True, slots=True)
class Card:
    ask_id: str
    status: str
    ttl_seconds: int | None
    fingerprint: str
    blocks: tuple[Block, ...]
    redactions: tuple[Redaction, ...]
    flags: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    #: True once the ask is inside its pre-expiry warning window.
    warning: bool = False
    #: One-line readiness banner (M26); ``None`` when readiness is fully green.
    readiness_banner: str | None = None

    def render(self, surface: str = "text", *, color: bool = False) -> str:
        if surface not in SURFACES:
            raise ValueError(f"unknown surface: {surface!r}")
        return _render(self, surface=surface, color=color)


def build_card(
    ask: AskRecord,
    *,
    now: datetime,
    transitions: Sequence[TransitionRecord] = (),
    status: AskStatus | None = None,
    prior_asks: Sequence[AskRecord] = (),
    similar_cases: Sequence[Mapping[str, Any]] = (),
    prior_objections: Sequence[Mapping[str, Any]] = (),
    handoff: Mapping[str, Any] | None = None,
) -> Card:
    payload: Mapping[str, Any] = ask.payload
    trust = payload.get("_trust") or {}
    unverified = set(trust.get("unverified") or [])
    context = payload.get("context") or {}
    blast = context.get("blast_radius") or {}
    policy = payload.get("policy_ref") or {}

    effective_status = status or ask.status
    remaining = max(0, int((ask.expires_at - now).total_seconds()))

    action_fields = (
        Field("tool", _text(payload.get("tool"), untrusted=True), untrusted=True),
        Field("action", _text(payload.get("action"), untrusted=True), untrusted=True),
        Field("arguments", _arguments(payload.get("arguments")), untrusted=True),
        Field("fingerprint", _fingerprint(ask.action_identity)),
        Field("class", _text(payload.get("class"), trusted="class" not in unverified)),
        Field(
            "criticality",
            _text(payload.get("criticality"), trusted="criticality" not in unverified),
        ),
        Field(
            "requested by",
            _text(payload.get("requested_by"), trusted="requested_by" not in unverified),
        ),
    )
    policy_fields = (
        Field(
            "reason code",
            _text(payload.get("reason_code"), trusted="reason_code" not in unverified),
        ),
        Field("rule", _text(policy.get("rule_id"), trusted="policy_ref" not in unverified)),
        Field(
            "policy version",
            _text(policy.get("policy_version"), trusted="policy_ref" not in unverified),
        ),
        Field("clause", _text(policy.get("clause")), untrusted=True),
    )
    blast_fields = (
        Field("resource", _text(blast.get("resource"), untrusted=True)),
        Field("reversibility", _reversibility(blast.get("reversibility"), payload.get("class"))),
        Field("affected estimate", _text(blast.get("affected_estimate"), untrusted=True)),
        Field(
            "environment",
            _text(payload.get("environment"), trusted="environment" not in unverified),
        ),
        Field(
            "data class",
            _text(payload.get("data_class"), trusted="data_class" not in unverified),
        ),
        Field("credential class", _text(blast.get("credential_class"))),
    )
    session_fields = (
        Field("session", _text(payload.get("session_id"))),
        Field("agent", _text(payload.get("agent_id"))),
        Field("tier", _text(ask.tier)),
        Field("escalations", _escalation_history(transitions)),
        Field("prior asks", _prior_asks(prior_asks)),
        Field("similar cases", _similar_cases(similar_cases)),
        Field("prior objection", recall_line(prior_objections)),
        Field("session tail", _session_tail(context.get("session_tail")), untrusted=True),
        Field("flags", _text(", ".join(str(flag) for flag in context.get("flags") or []))),
        Field(
            "alternatives",
            _text(", ".join(str(item) for item in context.get("alternatives") or [])),
        ),
        Field("transitions", str(len(transitions))),
    )

    redactions = tuple(
        Redaction(
            field=str(item.get("field", "unknown")),
            redaction_class=str(item.get("class", "unknown")),
            count=int(item.get("count", 0)),
        )
        for item in payload.get("_redactions") or []
        if isinstance(item, Mapping)
    )

    return Card(
        ask_id=ask.ask_id,
        status=effective_status.value,
        ttl_seconds=remaining,
        fingerprint=_fingerprint(ask.action_identity),
        blocks=_with_choices(
            ask,
            (
                *(() if handoff is None else (Block("HANDOFF", _handoff_fields(handoff)),)),
                Block("ACTION", action_fields),
                *(() if _outcome_fields(transitions) is None else (
                    Block("OUTCOME", _outcome_fields(transitions) or ()),
                )),
                Block("POLICY", policy_fields),
                Block("BLAST RADIUS", blast_fields),
                Block("SESSION SO FAR", session_fields),
            ),
        ),
        redactions=redactions,
        flags=tuple(str(flag) for flag in context.get("flags") or []),
        alternatives=tuple(str(item) for item in context.get("alternatives") or []),
        warning=(
            effective_status is AskStatus.PENDING
            and ask.warn_at is not None
            and ask.warn_at <= now
        ),
        readiness_banner=_readiness_banner(payload.get("_readiness")),
    )


# --------------------------------------------------------------------------- rendering


def _render(card: Card, *, surface: str, color: bool) -> str:
    del color  # color is never the sole signal; NO_COLOR simply yields the same layout
    lines = [
        f"ASKS: {card.ask_id}   status={card.status}   ttl={_ttl(card.ttl_seconds)}",
        f"fingerprint: {card.fingerprint}",
    ]
    if card.readiness_banner:
        lines.append(card.readiness_banner)
    lines.append("")
    for block in card.blocks:
        lines.append(block.title)
        for field in block.fields:
            prefix = (
                f"{UNTRUSTED_LABEL} "
                if field.untrusted and field.value != "unknown"
                else ""
            )
            lines.append(f"  {field.label}: {prefix}{field.value}")
        lines.append("")

    if card.redactions:
        lines.append("REDACTIONS")
        for redaction in card.redactions:
            lines.append(
                f"  {redaction.field}: [{redaction.redaction_class} x{redaction.count}]"
            )
        lines.append("")

    lines.extend(_surface_footer(surface, card))
    rendered = "\n".join(lines).rstrip() + "\n"
    if len(rendered) > CARD_CAP:
        omitted = len(rendered) - CARD_CAP
        rendered = rendered[:CARD_CAP].rstrip() + f"\n+N chars omitted ({omitted})\n"
    return rendered


def _surface_footer(surface: str, card: Card) -> list[str]:
    if surface == "ci":
        return [
            f"::notice::agentinbox ask {card.ask_id} is {card.status}; "
            "exit code follows the decision"
        ]
    if surface == "desktop":
        return [
            "Answer in the terminal: agentinbox answer <id>  "
            "(this notification is a wake-up, not a decision surface)"
        ]
    return [
        "Answer with: agentinbox answer <id> --approve|--deny  (q leaves it pending)"
    ]


# --------------------------------------------------------------------------- helpers


def _outcome_fields(transitions: Sequence[TransitionRecord]) -> tuple[Field, ...] | None:
    from agentinbox.outcomes import outcome_block

    block = outcome_block(transitions)
    if block is None:
        return None
    state, comparison, divergence, receipt = block
    return (
        Field("state", state),
        Field("comparison", comparison),
        Field("divergence", divergence),
        Field("receipt", receipt),
    )


def _handoff_fields(handoff: Mapping[str, Any]) -> tuple[Field, ...]:
    from agentinbox.operations import handoff_fields

    return handoff_fields(handoff)


def _with_choices(
    ask: AskRecord, blocks: tuple[Block, ...]
) -> tuple[Block, ...]:
    alternatives = alternatives_for(ask)
    fields: tuple[Field, ...]
    if alternatives:
        fields = tuple(Field("choice", render_alternative(item)) for item in alternatives)
    else:
        fields = tuple(Field("suggestion", item) for item in suggestions_for(ask))
    if not fields:
        return blocks
    return (Block("CHOICES", fields), *blocks)


def _readiness_banner(readiness: object) -> str | None:
    if not isinstance(readiness, Mapping):
        return None
    from agentinbox.readiness import banner_for

    return banner_for(readiness)


def _similar_cases(cases: Sequence[Mapping[str, Any]]) -> str:
    if not cases:
        return "none (precedent only)"
    rendered = "; ".join(
        f"{case.get('ask_id')} {case.get('outcome')} "
        f"(env={case.get('environment')}, criticality={case.get('criticality')})"
        for case in cases
    )
    return "precedent only: " + rendered


def _ttl(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    return f"{seconds // 60}m{seconds % 60:02d}s"


def _fingerprint(action_identity: str) -> str:
    value = action_identity.removeprefix("sha256:")
    return f"sha256:{value[:12]}…" if value else "unknown"


def _text(value: Any, *, untrusted: bool = False, trusted: bool = True) -> str:
    if value is None or value == "":
        return "unknown"
    text = str(value)
    text = _CONTROL.sub("", text)
    text = _MARKUP.sub("", text)
    if len(text) > FIELD_CAP:
        omitted = len(text) - FIELD_CAP
        text = text[:FIELD_CAP] + f" +{omitted} chars omitted"
    # Trusted-class fields are only verified when a signed producer adapter supplied them.
    if not trusted:
        text = f"[unverified] {text}"
    return text


def _arguments(arguments: Any) -> str:
    if not isinstance(arguments, Mapping) or not arguments:
        return "unknown"
    parts = [f"{key}={value}" for key, value in sorted(arguments.items())]
    return _text("; ".join(parts))


def _escalation_history(transitions: Sequence[TransitionRecord]) -> str:
    rows = [
        f"{item.detail.get('from_tier', 'unknown')} did not answer → "
        f"{item.detail.get('to_tier', 'unknown')}"
        for item in transitions
        if item.kind == "ask-escalated"
    ]
    return _text(", ".join(rows)) if rows else "none"


def _prior_asks(asks: Sequence[AskRecord]) -> str:
    if not asks:
        return "none"
    rows = [f"{item.ask_id} {item.status.value}" for item in asks[-3:]]
    return _text(", ".join(rows))


def _session_tail(tail: Any) -> str:
    if not isinstance(tail, list) or not tail:
        return "unknown"
    rows = []
    for item in tail[:5]:
        if isinstance(item, Mapping):
            rows.append(f"{item.get('tool', 'unknown')}.{item.get('action', 'unknown')}")
        else:
            rows.append(str(item))
    return _text(", ".join(rows))


def _reversibility(value: Any, action_class: Any) -> str:
    if value is None or value == "":
        if str(action_class) == "irreversible":
            return "unknown (irreversible class)"
        return "unknown"
    return _text(value)


__all__ = [
    "CARD_CAP",
    "FIELD_CAP",
    "SURFACES",
    "Block",
    "Card",
    "Field",
    "Redaction",
    "build_card",
]
