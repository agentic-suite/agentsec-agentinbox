"""The v0.1.0 state machine guard (M3 item 3.3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentinbox.ingest import ingest
from agentinbox.lifecycle import (
    LEGAL_EDGES,
    IllegalTransition,
    UnknownAsk,
    observe,
    transition,
    winning_answer,
)
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload

TERMINAL = sorted(AskStatus.terminal())


def make_ask(store) -> str:  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask.ask_id


@pytest.mark.parametrize("target", TERMINAL)
def test_every_pending_edge_is_legal(store, target: AskStatus) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)

    assert (
        transition(
            store,
            ask_id,
            target,
            kind="test",
            at=NOW,
            principal="alice",
            channel="terminal",
        )
        is True
    )

    ask = store.get(ask_id)
    assert ask is not None
    assert ask.status is target
    assert store.transitions_for(ask_id)[-1].to_status is target


def test_terminal_states_have_no_outgoing_edges() -> None:
    for terminal in TERMINAL:
        assert LEGAL_EDGES.get(terminal, frozenset()) == frozenset()


def test_illegal_edge_is_rejected_and_recorded(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)

    with pytest.raises(IllegalTransition):
        transition(store, ask_id, AskStatus.PENDING, kind="test", at=NOW)

    ask = store.get(ask_id)
    assert ask is not None
    assert ask.status is AskStatus.PENDING
    rejected = store.transitions_for(ask_id)[-1]
    assert rejected.kind == "illegal-transition-rejected"
    assert rejected.detail["attempted"] == "pending"


def test_terminal_is_terminal(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.APPROVED, kind="answer", at=NOW, principal="alice")

    with pytest.raises(IllegalTransition):
        transition(store, ask_id, AskStatus.DENIED, kind="answer", at=NOW, principal="mallory")

    ask = store.get(ask_id)
    assert ask is not None
    assert ask.status is AskStatus.APPROVED
    assert [item.kind for item in store.transitions_for(ask_id)].count(
        "illegal-transition-rejected"
    ) == 1


def test_late_answer_is_an_observation(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.APPROVED, kind="answer", at=NOW, principal="alice")

    observe(
        store,
        ask_id,
        kind="late-answer",
        at=NOW + timedelta(seconds=5),
        principal="mallory",
        channel="terminal",
        detail={"outcome": "denied"},
    )

    ask = store.get(ask_id)
    assert ask is not None
    assert ask.status is AskStatus.APPROVED
    winner = winning_answer(store.transitions_for(ask_id))
    assert winner is not None
    assert winner.principal == "alice"
    assert store.transitions_for(ask_id)[-1].kind == "late-answer"


def test_non_late_observation_after_terminal_is_rejected(store) -> None:  # type: ignore[no-untyped-def]
    ask_id = make_ask(store)
    transition(store, ask_id, AskStatus.DENIED, kind="answer", at=NOW, principal="alice")

    with pytest.raises(IllegalTransition):
        observe(store, ask_id, kind="warned", at=NOW)


def test_unknown_ask_is_refused(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(UnknownAsk):
        transition(store, "ask_missing", AskStatus.APPROVED, kind="answer", at=NOW)

    with pytest.raises(UnknownAsk):
        observe(store, "ask_missing", kind="warned", at=NOW)
