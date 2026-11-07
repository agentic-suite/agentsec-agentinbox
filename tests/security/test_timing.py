"""Uniform public errors, constant-time comparisons, and guessing lockout (M22 item 22.4)."""

from __future__ import annotations

import hmac
from datetime import timedelta

import pytest

from agentinbox.answers import (
    CREDENTIAL_CAUSES,
    AnswerRejected,
    AnswerRequest,
    AnswerVerifier,
)
from agentinbox.claims import mint_claim, secret_matches
from tests.security.test_invariants import BASE, config, make_ask


def test_credential_failures_share_one_public_cause() -> None:
    for cause in CREDENTIAL_CAUSES:
        assert AnswerRejected(cause).public_cause == "bad_claim"
    assert AnswerRejected("late").public_cause == "already_resolved"
    assert AnswerRejected("off_roster").public_cause == "off_roster"


def test_secret_comparison_is_constant_time(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentinbox.store.memory import MemoryStore

    calls: list[int] = []
    original = hmac.compare_digest

    def spy(left: object, right: object) -> bool:
        calls.append(1)
        return original(left, right)  # type: ignore[arg-type]

    monkeypatch.setattr(hmac, "compare_digest", spy)
    store = MemoryStore()
    try:
        ask = make_ask(store)
        minted = mint_claim(
            store, ask, channel="terminal", tier=None, now=BASE, secret="h" * 32
        )
        assert secret_matches(minted.claim, "h" * 32)
        assert calls
    finally:
        store.close()


def test_guessing_locks_out_and_keeps_the_public_cause_uniform() -> None:
    from agentinbox.store.memory import MemoryStore

    store = MemoryStore()
    try:
        ask = make_ask(store)
        minted = mint_claim(
            store, ask, channel="terminal", tier=None, now=BASE, secret="i" * 32
        )
        verifier = AnswerVerifier(store, config(), now=lambda: BASE, max_attempts=3)
        causes: list[str] = []
        for _ in range(4):
            with pytest.raises(AnswerRejected) as rejected:
                verifier.submit(
                    _request(ask.ask_id, minted.claim.claim_id, "wrong"),
                    channel_authenticated=True,
                )
            causes.append(rejected.value.cause)
            assert rejected.value.public_cause == "bad_claim"

        assert causes[:3] == ["bad_secret", "bad_secret", "bad_secret"]
        assert causes[3] == "guessing"
        stored = store.get(ask.ask_id)
        assert stored is not None
        assert stored.status.value == "pending"
    finally:
        store.close()


def _request(ask_id: str, claim_id: str, secret: str):  # type: ignore[no-untyped-def]
    return AnswerRequest(
        ask_id=ask_id,
        claim_id=claim_id,
        secret=secret,
        principal="alice",
        channel="terminal",
        decision="approve",
        typed_confirmation="run_command",
    )


def test_unknown_ask_and_invalid_decision_are_rejected() -> None:
    from agentinbox.store.memory import MemoryStore

    store = MemoryStore()
    try:
        verifier = AnswerVerifier(store, config(), now=lambda: BASE)
        with pytest.raises(AnswerRejected) as rejected:
            verifier.submit(
                _request("ask_missing", "cl_missing", "x"),
                channel_authenticated=True,
            )
        assert rejected.value.cause == "unknown_ask"

        with pytest.raises(ValueError, match="decision must be"):
            verifier.submit(
                AnswerRequest(
                    ask_id="ask_missing",
                    claim_id="cl_missing",
                    secret="x",
                    principal="alice",
                    channel="terminal",
                    decision="maybe",
                ),
                channel_authenticated=True,
            )
    finally:
        store.close()


def test_unknown_class_and_stale_tier_are_rejected() -> None:
    from agentinbox.store import AskRecord
    from agentinbox.store.memory import MemoryStore

    store = MemoryStore()
    try:
        minted_missing = store.create_or_get_by_identity(
            AskRecord(
                ask_id="ask_noclass",
                action_identity="sha256:noclass",
                session_id="sess_noclass",
                agent_id="agent://x",
                created_at=BASE,
                expires_at=BASE + timedelta(minutes=5),
                payload={"class": "mystery"},
            )
        ).ask
        minted = mint_claim(
            store, minted_missing, channel="terminal", tier=None, now=BASE, secret="j" * 32
        )
        verifier = AnswerVerifier(store, config(), now=lambda: BASE)
        with pytest.raises(AnswerRejected) as rejected:
            verifier.submit(
                _request(minted_missing.ask_id, minted.claim.claim_id, "j" * 32),
                channel_authenticated=True,
            )
        assert rejected.value.cause == "unknown_class"

        tiered = store.create_or_get_by_identity(
            AskRecord(
                ask_id="ask_tiered",
                action_identity="sha256:tiered",
                session_id="sess_tiered",
                agent_id="agent://x",
                created_at=BASE,
                expires_at=BASE + timedelta(minutes=5),
                payload={"class": "irreversible"},
                tier="tier-2",
            )
        ).ask
        stale = mint_claim(
            store, tiered, channel="terminal", tier="tier-1", now=BASE, secret="k" * 32
        )
        with pytest.raises(AnswerRejected) as rejected:
            verifier.submit(
                _request(tiered.ask_id, stale.claim.claim_id, "k" * 32),
                channel_authenticated=True,
            )
        assert rejected.value.cause == "identity_mismatch"
    finally:
        store.close()
