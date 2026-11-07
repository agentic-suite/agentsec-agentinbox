"""Tier change revokes prior-tier claims; a sleeper approval is rejected (M11 item 11.3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.escalation import Escalator
from agentinbox.store import AskStatus
from tests.ask.conftest import NOW
from tests.escalation.conftest import Clock, make_ask, make_config


def submit(store, config, ask, claim, secret, *, principal: str, now=NOW):  # type: ignore[no-untyped-def]
    verifier = AnswerVerifier(store, config, now=lambda: now)
    return verifier.submit(
        AnswerRequest(
            ask_id=ask.ask_id,
            claim_id=claim.claim_id,
            secret=secret,
            principal=principal,
            channel="terminal",
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )


def escalate_once(store, config, ask, clock) -> None:  # type: ignore[no-untyped-def]
    clock.moment = NOW + timedelta(seconds=300)
    assert Escalator(store, config, now=clock).tick().escalated == 1


def test_tier_change_revokes_prior_tier_claims(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    minted = mint_claim(store, ask, channel="terminal", tier="tier-1", now=NOW)

    escalate_once(store, config, ask, Clock())

    claim = store.get_claim(minted.claim.claim_id)
    assert claim is not None
    assert claim.revoked_at is not None


def test_sleeper_tier_one_approval_is_rejected(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    minted = mint_claim(store, ask, channel="terminal", tier="tier-1", now=NOW)
    escalate_once(store, config, ask, Clock())
    escalated = store.get(ask.ask_id)

    with pytest.raises(AnswerRejected) as caught:
        submit(
            store,
            config,
            escalated,
            minted.claim,
            minted.secret,
            principal="alice",
            now=NOW + timedelta(seconds=301),
        )
    assert caught.value.cause == "revoked"

    rejected = [
        item
        for item in store.transitions_for(ask.ask_id)
        if item.kind == "answer-rejected" and item.detail.get("cause") == "revoked"
    ]
    assert len(rejected) == 1
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_the_new_tier_can_still_answer(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    escalate_once(store, config, ask, Clock())
    escalated = store.get(ask.ask_id)

    minted = mint_claim(
        store, escalated, channel="terminal", tier="on-call", now=NOW + timedelta(seconds=301)
    )
    result = submit(
        store,
        config,
        escalated,
        minted.claim,
        minted.secret,
        principal="bob",
        now=NOW + timedelta(seconds=301),
    )

    assert result.winner is True
    assert store.get(ask.ask_id).status is AskStatus.APPROVED  # type: ignore[union-attr]


def test_a_prior_tier_principal_cannot_answer_the_new_tier(store) -> None:  # type: ignore[no-untyped-def]
    config = make_config()
    ask = make_ask(store, config=config)
    escalate_once(store, config, ask, Clock())
    escalated = store.get(ask.ask_id)

    # A channel mints at the *current* tier; the verifier must still refuse alice (tier-1).
    minted = mint_claim(
        store, escalated, channel="terminal", tier="on-call", now=NOW + timedelta(seconds=301)
    )
    with pytest.raises(AnswerRejected) as caught:
        submit(
            store,
            config,
            escalated,
            minted.claim,
            minted.secret,
            principal="alice",
            now=NOW + timedelta(seconds=301),
        )
    assert caught.value.cause == "off_roster"
