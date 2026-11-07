"""The full v0.1.0 event set: one event per fact, schema-valid, joinable (M16 items 16.1/16.4)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

import pytest

from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.bus import JobKind, new_job
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.claims import mint_claim
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.escalation import Escalator
from agentinbox.events import EVENT_TYPES, EventTracer, JsonlEventSink, ListSink
from agentinbox.flood import FloodGuard
from agentinbox.gate import gate
from agentinbox.ingest import ingest
from agentinbox.scheduler import Scheduler
from agentinbox.store import canonical_json
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload
from tests.events.schema import validate

TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
MARKER = "sk-live-NEVER-IN-AN-EVENT"


class Clock:
    def __init__(self, start: datetime = NOW) -> None:
        self.moment = start

    def __call__(self) -> datetime:
        return self.moment


class Recorder:
    name = "terminal"

    def __init__(self) -> None:
        self.delivered: list[str] = []

    def deliver(self, ask: Any, card: Any) -> None:
        self.delivered.append(ask.ask_id)

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        return None


class DownChannel(Recorder):
    name = "webhook"

    def deliver(self, ask: Any, card: Any) -> None:
        raise OSError("channel is down")


def config() -> Config:
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300,
                warn_seconds=60,
                ladder=("tier-1", "on-call"),
                ladder_delays=(0, 60),
            )
        },
        roster={
            "tier-1": {"terminal": ("alice",)},
            "on-call": {"terminal": ("bob",)},
        },
        channels={"terminal": ChannelConfig(enabled=True)},
    )


def make_ask(store, *, index: int, traceparent: str | None = None, agent="agent://ops/1"):  # type: ignore[no-untyped-def]
    body = payload(
        arguments={"command": f"echo {index} {MARKER}"},
        agent_id=agent,
        session_id=f"sess_events_{agent}",
    )
    if traceparent:
        body["traceparent"] = traceparent
    return ingest(
        body,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def answer(  # type: ignore[no-untyped-def]
    store,
    ask,
    *,
    principal: str,
    channel: str = "terminal",
    secret: str | None = None,
    now: datetime = NOW,
):
    minted = mint_claim(
        store, ask, channel=channel, tier=ask.tier, now=now, secret=secret
    )
    return AnswerVerifier(store, config(), now=lambda: now).submit(
        AnswerRequest(
            ask_id=ask.ask_id,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal=principal,
            channel=channel,
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )


def run_integration(store) -> list[dict[str, Any]]:
    tracer = EventTracer(store, sink=ListSink())
    clock = Clock()

    first = make_ask(store, index=1, traceparent=TRACEPARENT)
    down = DownChannel()
    up = Recorder()
    DeliveryWiring(
        store, [down, up], now=clock, backoff=lambda _attempt: None
    ).handle(new_job(JobKind.DELIVER, ask_id=first.ask_id, now=NOW))

    scheduler = Scheduler(
        store,
        now=clock,
        escalator=Escalator(store, config(), now=clock),
    )
    clock.moment = NOW + timedelta(seconds=60)
    scheduler.tick()
    clock.moment = NOW + timedelta(seconds=240)
    scheduler.tick()
    escalated = store.get(first.ask_id)
    answer(store, escalated, principal="bob", now=clock())

    second = make_ask(store, index=2)
    clock.moment = second.expires_at + timedelta(seconds=1)
    scheduler.tick()

    third = make_ask(store, index=3)
    cancel = threading.Event()
    cancel.set()
    gate(store, third.ask_id, now=lambda: NOW, wait=True, cancel=cancel)

    fourth = make_ask(store, index=4)
    minted = mint_claim(store, fourth, channel="terminal", tier=fourth.tier, now=NOW)
    with pytest.raises(AnswerRejected):
        AnswerVerifier(store, config(), now=lambda: NOW).submit(
            AnswerRequest(
                ask_id=fourth.ask_id,
                claim_id=minted.claim.claim_id,
                secret="not-the-secret",
                principal="alice",
                channel="terminal",
                decision="approve",
                typed_confirmation="run_command",
            ),
            channel_authenticated=True,
        )

    guard = FloodGuard(store, config(), now=lambda: NOW)
    for index in range(21):
        ingest(
            payload(
                arguments={"command": f"flood {index}"},
                agent_id="agent://flooder/1",
                session_id="sess_events_flood",
            ),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
            flood_guard=guard,
        )

    return tracer.drain()


def test_every_event_type_is_emitted_and_validates(store) -> None:  # type: ignore[no-untyped-def]
    events = run_integration(store)

    assert {event["event_type"] for event in events} == EVENT_TYPES
    for event in events:
        validate(event)
    assert len({event["event_id"] for event in events}) == len(events)


def test_events_carry_join_keys_and_traceparent(store) -> None:  # type: ignore[no-untyped-def]
    events = run_integration(store)
    raised = [event for event in events if event["event_type"] == "ask-raised"]
    traced = [event for event in raised if event["traceparent"] == TRACEPARENT]

    assert traced
    for event in events:
        assert event["emitter"] == "agentinbox"
        assert event["ask_id"]
        assert event["session_id"]
        assert event["agent_id"]
        assert event["action_identity"].startswith("sha256:")
    for event in traced:
        assert event["session_id"].startswith("sess_events_")


def test_delivery_events_are_emitted_once_per_attempt(store) -> None:  # type: ignore[no-untyped-def]
    events = run_integration(store)
    delivered = [event for event in events if event["event_type"] == "ask-delivered"]
    failed = [event for event in events if event["event_type"] == "ask-delivery-failed"]

    assert len(delivered) == 1
    assert len(failed) == 3
    assert [event["payload"]["attempt"] for event in failed] == [1, 2, 3]
    assert all(event["payload"]["channel"] == "webhook" for event in failed)


def test_no_untrusted_text_reaches_an_event(store) -> None:  # type: ignore[no-untyped-def]
    events = run_integration(store)
    blob = canonical_json(events)

    assert MARKER not in blob
    assert "psql" not in blob
    assert "arguments" not in blob
    assert "context" not in blob


def test_the_schema_rejects_a_breaking_shape() -> None:
    event = {
        "event_version": "0.2.0",
        "event_type": "ask-raised",
        "emitter": "agentinbox",
        "event_id": "agentinbox:1",
        "at": "2026-11-08T00:00:00.000000Z",
        "ask_id": "ask_0123456789abcdef",
        "session_id": "sess",
        "agent_id": "agent",
        "action_identity": "sha256:" + "a" * 64,
        "payload": {
            "class": "irreversible",
            "criticality": "critical",
            "expires_at": "2026-11-08T00:05:00.000000Z",
            "requested_by": "maya",
        },
    }
    validate(event)

    broken = dict(event)
    broken.pop("session_id")
    with pytest.raises(AssertionError):
        validate(broken)

    unknown = dict(event, event_type="ask-unknown")
    with pytest.raises(AssertionError):
        validate(unknown)

    leaked = dict(event, payload={**event["payload"], "arguments": "psql"})
    with pytest.raises(AssertionError):
        validate(leaked)


def test_the_jsonl_sink_is_private(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sink = JsonlEventSink(tmp_path / "events.jsonl")
    sink.write({"event_type": "ask-raised"})
    assert (tmp_path / "events.jsonl").stat().st_mode & 0o777 == 0o600
