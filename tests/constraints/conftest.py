"""Shared helpers for M27 tests."""

from __future__ import annotations

from typing import Any

from agentinbox.alternatives import alternative_fingerprint
from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.ingest import ingest
from agentinbox.store import AskRecord, AskStore
from agentinbox.trust import ProducerIdentity
from tests.readiness.conftest import NOW, config, good_body


def alternative(identifier: str = "staging", **overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": identifier,
        "label": f"Run {identifier}",
        "enforcer": "agentpolicy",
        "arguments": {"command": "psql staging -c 'select 1'"},
        "constraints": [
            {
                "id": "environment",
                "enforcer_ref": "agentpolicy:env",
                "params": {"environment": "staging"},
            }
        ],
    }
    item.update(overrides)
    item["fingerprint"] = alternative_fingerprint(item)
    return item


def signed() -> ProducerIdentity:
    return ProducerIdentity(adapter="agentpolicy", authenticated=True, principal="maya@team")


def ingest_ask(
    store: AskStore,
    *,
    session: str = "sess_constraints",
    command: str = "psql prod -c 'select 1'",
    alternatives: list[dict[str, Any]] | None = None,
    arguments: dict[str, Any] | None = None,
    **body_overrides: Any,
) -> AskRecord:
    body = good_body(
        session_id=session,
        arguments=arguments or {"command": command},
        **body_overrides,
    )
    if alternatives is not None:
        body["alternatives"] = alternatives
    return ingest(
        body, store=store, config=config(), producer=signed(), now=NOW
    ).ask


def approve(store: AskStore, ask: AskRecord, *, cfg=None, **overrides: Any):  # type: ignore[no-untyped-def]
    from agentinbox.claims import mint_claim

    minted = mint_claim(
        store, ask, channel="terminal", tier=None, now=NOW, secret="z" * 32
    )
    request = {
        "ask_id": ask.ask_id,
        "claim_id": minted.claim.claim_id,
        "secret": minted.secret,
        "principal": "alice",
        "channel": "terminal",
        "decision": "approve",
        "typed_confirmation": "run_command",
    }
    request.update(overrides)
    return AnswerVerifier(store, cfg or config(), now=lambda: NOW).submit(
        AnswerRequest(**request), channel_authenticated=True
    )


def deny(store: AskStore, ask: AskRecord, *, reason: str, cfg=None):  # type: ignore[no-untyped-def]
    from agentinbox.claims import mint_claim

    minted = mint_claim(
        store, ask, channel="terminal", tier=None, now=NOW, secret="y" * 32
    )
    return AnswerVerifier(store, cfg or config(), now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=ask.ask_id,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal="alice",
            channel="terminal",
            decision="deny",
            reason=reason,
        ),
        channel_authenticated=True,
    )
