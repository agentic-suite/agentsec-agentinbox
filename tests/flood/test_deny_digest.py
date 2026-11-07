"""Flood auto-deny: N denies, one event, one digest (M12 items 12.3/12.4)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.bus import InProcBus, JobKind
from agentinbox.claims import mint_claim
from agentinbox.config import ClassConfig, Config
from agentinbox.flood import FloodGuard
from agentinbox.ingest import ingest
from agentinbox.resolve import resolve
from agentinbox.store import AskStatus
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def config() -> Config:
    return Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})


def make(store, guard, bus, index: int, *, session: str = "sess_flood", now=NOW):  # type: ignore[no-untyped-def]
    return ingest(
        payload(
            arguments={"command": f"echo {index}"},
            agent_id="agent://flooder/1",
            session_id=session,
        ),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=now,
        flood_guard=guard,
        bus=bus,
    )


def test_a_flood_produces_n_denies_one_event_one_digest(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)
    results = [make(store, guard, bus, index) for index in range(200)]

    allowed = [result for result in results if result.ask.status is AskStatus.PENDING]
    denied = [result for result in results if result.ask.status is AskStatus.FLOOD_DENIED]
    assert len(allowed) == 20
    assert len(denied) == 180

    # One ask-flood event for the window (on the first ask).
    events = [
        item
        for ask in (result.ask for result in results)
        for item in store.transitions_for(ask.ask_id)
        if item.kind == "ask-flood"
    ]
    assert len(events) == 1
    assert events[0].detail["first_ask_id"] == denied[0].ask.ask_id
    assert events[0].detail["agent_id"] == "agent://flooder/1"
    assert events[0].detail["session_id"] == "sess_flood"

    jobs = []
    bus.consume(jobs.append)
    digests = [job for job in jobs if job.kind is JobKind.DIGEST]
    assert len(digests) == 1
    assert digests[0].payload["count"] == 180
    assert digests[0].ask_id == denied[0].ask.ask_id


def test_flood_denied_is_retryable_after_the_window(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)
    results = [make(store, guard, bus, index) for index in range(21)]
    denied = results[-1].ask

    outcome = resolve(store, denied.ask_id, now=NOW)

    assert outcome.status == "deny"
    assert outcome.reason_code == "ask_flood_throttled"
    assert outcome.retryable is True
    detail = store.transitions_for(denied.ask_id)[-1]
    assert detail.kind == "flood-denied"
    assert detail.detail["retry_after_s"] == 30


def test_a_flood_denied_ask_cannot_be_resurrected(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)
    results = [make(store, guard, bus, index) for index in range(21)]
    denied = results[-1].ask
    minted = mint_claim(store, denied, channel="terminal", tier=None, now=NOW)

    verifier = AnswerVerifier(store, config(), now=lambda: NOW)
    with pytest.raises(AnswerRejected):
        verifier.submit(
            AnswerRequest(
                ask_id=denied.ask_id,
                claim_id=minted.claim.claim_id,
                secret=minted.secret,
                principal="alice",
                channel="terminal",
                decision="approve",
                typed_confirmation="run_command",
            ),
            channel_authenticated=True,
        )

    assert store.get(denied.ask_id).status is AskStatus.FLOOD_DENIED  # type: ignore[union-attr]
    assert guard.resurrections == 0


def test_pre_flood_asks_remain_answerable(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    cfg = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
    )
    guard = FloodGuard(store, cfg, now=lambda: NOW, bus=bus)
    results = [
        ingest(
            payload(
                arguments={"command": f"legit {index}"},
                agent_id="agent://flooder/1",
                session_id="sess_flood",
            ),
            store=store,
            config=cfg,
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
            flood_guard=guard,
            bus=bus,
        )
        for index in range(21)
    ]
    survivor = results[0].ask
    assert survivor.status is AskStatus.PENDING

    minted = mint_claim(store, survivor, channel="terminal", tier=None, now=NOW)
    verdict = AnswerVerifier(store, cfg, now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=survivor.ask_id,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal="alice",
            channel="terminal",
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )
    assert verdict.winner is True
    assert store.get(survivor.ask_id).status is AskStatus.APPROVED  # type: ignore[union-attr]


def test_a_new_window_produces_a_new_event_and_digest(store) -> None:  # type: ignore[no-untyped-def]
    bus = InProcBus(now=lambda: NOW)
    guard = FloodGuard(store, config(), now=lambda: NOW, bus=bus)
    for index in range(21):
        make(store, guard, bus, index)

    later = NOW + timedelta(seconds=31)
    results = [make(store, guard, bus, index + 100, now=later) for index in range(6)]
    assert results[-1].ask.status is AskStatus.FLOOD_DENIED

    jobs = []
    bus.consume(jobs.append)
    assert len([job for job in jobs if job.kind is JobKind.DIGEST]) == 2
