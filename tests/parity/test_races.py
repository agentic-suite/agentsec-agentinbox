"""Cross-surface races: exactly one decision, losers are visible no-ops (M14 items 14.2/14.3)."""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload

ASK_ID = "ask_0123456789abcdef"


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": tuple(f"user{index}" for index in range(8))}},
        channels={"terminal": _enabled()},
    )


def _enabled():  # type: ignore[no-untyped-def]
    from agentinbox.config import ChannelConfig

    return ChannelConfig(enabled=True)


def make(store):  # type: ignore[no-untyped-def]
    return ingest(
        payload(ask_id=ASK_ID),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def test_two_surfaces_racing_produce_one_decision(store) -> None:  # type: ignore[no-untyped-def]
    ask = make(store)
    claims = [
        mint_claim(store, ask, channel="terminal", tier=None, now=NOW) for _ in range(8)
    ]
    barrier = threading.Barrier(8)
    winners: list[str] = []
    losers: list[AnswerRejected] = []
    lock = threading.Lock()

    def answer(index: int) -> None:
        verifier = AnswerVerifier(store, config(), now=lambda: NOW)
        barrier.wait()
        try:
            result = verifier.submit(
                AnswerRequest(
                    ask_id=ASK_ID,
                    claim_id=claims[index].claim.claim_id,
                    secret=claims[index].secret,
                    principal=f"user{index}",
                    channel="terminal",
                    decision="approve",
                    typed_confirmation="run_command",
                ),
                channel_authenticated=True,
            )
        except AnswerRejected as exc:
            with lock:
                losers.append(exc)
            return
        with lock:
            winners.append(result.claim_id)

    threads = [threading.Thread(target=answer, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(winners) == 1
    assert len(losers) == 7
    assert {exc.cause for exc in losers} == {"late"}
    assert store.get(ASK_ID).status is AskStatus.APPROVED  # type: ignore[union-attr]
    decisions = [
        item
        for item in store.transitions_for(ASK_ID)
        if item.kind == "answer" and item.to_status is AskStatus.APPROVED
    ]
    assert len(decisions) == 1


def test_late_answers_name_the_winner_and_are_visible_no_ops(store) -> None:  # type: ignore[no-untyped-def]
    ask = make(store)
    first = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)
    winner = AnswerVerifier(store, config(), now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=ASK_ID,
            claim_id=first.claim.claim_id,
            secret=first.secret,
            principal="user0",
            channel="terminal",
            decision="deny",
            reason="unsafe",
        ),
        channel_authenticated=True,
    )
    assert winner.winner is True

    later = mint_claim(
        store, ask, channel="terminal", tier=None, now=NOW + timedelta(seconds=1)
    )
    with pytest.raises(AnswerRejected) as caught:
        AnswerVerifier(store, config(), now=lambda: NOW + timedelta(seconds=1)).submit(
            AnswerRequest(
                ask_id=ASK_ID,
                claim_id=later.claim.claim_id,
                secret=later.secret,
                principal="user1",
                channel="terminal",
                decision="approve",
                typed_confirmation="run_command",
            ),
            channel_authenticated=True,
        )

    assert caught.value.cause == "late"
    assert "already resolved by user0 at" in caught.value.message
    assert store.get(ASK_ID).status is AskStatus.DENIED  # type: ignore[union-attr]

    late = [item for item in store.transitions_for(ASK_ID) if item.kind == "late-answer"]
    assert len(late) == 1
    assert late[0].detail["winner"] == "user0"
    assert late[0].detail["winner_at"] == NOW.isoformat()
