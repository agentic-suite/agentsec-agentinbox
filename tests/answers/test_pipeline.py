"""The six-step answer pipeline / SC-22 attack matrix (M6 items 6.2-6.6)."""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.store import AskStatus
from tests.answers.conftest import NOW, answer_config, make_ask, mint


def request(ask, minted, **overrides):  # type: ignore[no-untyped-def]
    data = dict(
        ask_id=ask.ask_id,
        claim_id=minted.claim.claim_id,
        secret=minted.secret,
        principal="alice",
        channel="terminal",
        decision="approve",
        typed_confirmation="run_command",
    )
    data.update(overrides)
    return AnswerRequest(**data)


def test_happy_approve(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    result = AnswerVerifier(store, cfg, now=lambda: NOW).submit(
        request(ask, minted), channel_authenticated=True
    )

    assert result.winner is True
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.APPROVED
    transition = store.transitions_for(ask.ask_id)[-1]
    assert transition.principal == "alice"
    assert transition.claim_id == minted.claim.claim_id
    assert store.get_claim(minted.claim.claim_id).consumed_at == NOW  # type: ignore[union-attr]


def test_deny_with_reason(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    AnswerVerifier(store, cfg, now=lambda: NOW).submit(
        request(ask, minted, decision="deny", reason="missing rollback plan"),
        channel_authenticated=True,
    )

    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.DENIED
    assert store.transitions_for(ask.ask_id)[-1].reason == "missing rollback plan"


def test_unauthenticated_channel_cannot_answer(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted), channel_authenticated=False
        )

    assert exc.value.cause == "bad_signature"
    assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]


def test_wrong_secret_is_uniform_but_audited(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, secret="wrong"), channel_authenticated=True
        )

    assert exc.value.cause == "bad_secret"
    assert exc.value.public_cause == "bad_claim"
    assert store.transitions_for(ask.ask_id)[-1].kind == "answer-rejected"
    assert store.transitions_for(ask.ask_id)[-1].detail["cause"] == "bad_secret"


def test_unknown_claim(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, claim_id="cl_missing"), channel_authenticated=True
        )

    assert exc.value.cause == "unknown_claim"


def test_expired_claim(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    late = ask.expires_at + timedelta(seconds=1)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: late).submit(
            request(ask, minted), channel_authenticated=True
        )

    assert exc.value.cause == "expired_token"


def test_used_claim(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    store.consume_claim(minted.claim.claim_id, ask_id=ask.ask_id, at=NOW)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted), channel_authenticated=True
        )

    assert exc.value.cause == "used"


def test_revoked_claim(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    store.revoke_claims(ask.ask_id, at=NOW, tier="tier-1")

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted), channel_authenticated=True
        )

    assert exc.value.cause == "revoked"


def test_wrong_channel_binding(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, channel="desktop"), channel_authenticated=True
        )

    assert exc.value.cause == "identity_mismatch"


def test_off_roster_principal(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, principal="mallory"), channel_authenticated=True
        )

    assert exc.value.cause == "off_roster"


def test_self_review_is_rejected(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store, config=answer_config(roster=("alice", "maya")), requested_by="maya")
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, principal="maya"), channel_authenticated=True
        )

    assert exc.value.cause == "self_review"


def test_deny_requires_reason_on_irreversible(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, decision="deny"), channel_authenticated=True
        )

    assert exc.value.cause == "reason_required"


def test_irreversible_approve_requires_typed_confirmation(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)

    with pytest.raises(AnswerRejected) as exc:
        AnswerVerifier(store, cfg, now=lambda: NOW).submit(
            request(ask, minted, typed_confirmation=None), channel_authenticated=True
        )

    assert exc.value.cause == "confirmation"


def test_guessing_lockout(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    minted = mint(store, ask)
    verifier = AnswerVerifier(store, cfg, now=lambda: NOW, max_attempts=5)
    causes = []

    for _ in range(6):
        with pytest.raises(AnswerRejected) as exc:
            verifier.submit(request(ask, minted, secret="wrong"), channel_authenticated=True)
        causes.append(exc.value.cause)

    assert causes[:5] == ["bad_secret"] * 5
    assert causes[5] == "guessing"
    rejected = [t for t in store.transitions_for(ask.ask_id) if t.kind == "answer-rejected"]
    assert len(rejected) == 6


def test_race_has_one_winner_and_one_late_answer(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    first = mint(store, ask)
    second = mint(store, ask)
    verifier = AnswerVerifier(store, cfg, now=lambda: NOW)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def submit(minted) -> None:  # type: ignore[no-untyped-def]
        barrier.wait()
        try:
            verifier.submit(request(ask, minted), channel_authenticated=True)
            with lock:
                outcomes.append("winner")
        except AnswerRejected as exc:
            with lock:
                outcomes.append(exc.cause)

    threads = [threading.Thread(target=submit, args=(m,)) for m in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("winner") == 1
    assert outcomes.count("late") == 1
    kinds = [t.kind for t in store.transitions_for(ask.ask_id)]
    assert kinds.count("answer") == 1
    assert kinds.count("late-answer") == 1


def test_late_answer_after_resolution(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    winner = mint(store, ask)
    loser = mint(store, ask)
    verifier = AnswerVerifier(store, cfg, now=lambda: NOW)
    verifier.submit(request(ask, winner), channel_authenticated=True)

    with pytest.raises(AnswerRejected) as exc:
        verifier.submit(request(ask, loser), channel_authenticated=True)

    assert exc.value.cause == "late"
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.APPROVED


def test_off_roster_late_answer_does_not_learn_the_winner(store) -> None:  # type: ignore[no-untyped-def]
    ask, cfg = make_ask(store)
    winner = mint(store, ask)
    loser = mint(store, ask)
    verifier = AnswerVerifier(store, cfg, now=lambda: NOW)
    verifier.submit(request(ask, winner), channel_authenticated=True)

    with pytest.raises(AnswerRejected) as exc:
        verifier.submit(
            request(ask, loser, principal="mallory"), channel_authenticated=True
        )

    assert exc.value.cause == "off_roster"

