"""Sink buffering, recovery, and gap markers (M16 item 16.3)."""

from __future__ import annotations

from typing import Any

from agentinbox.config import ClassConfig, Config
from agentinbox.events import BufferedEventSink, EventTracer
from agentinbox.ingest import ingest
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


class FlakySink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.down = False

    def write(self, record: dict[str, Any]) -> None:
        if self.down:
            raise OSError("sink is down")
        self.records.append(record)


def config() -> Config:
    return Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})


def make(store, index: int = 0):  # type: ignore[no-untyped-def]
    return ingest(
        payload(arguments={"command": f"echo {index}"}),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def test_a_down_sink_buffers_without_raising(store) -> None:  # type: ignore[no-untyped-def]
    inner = FlakySink()
    inner.down = True
    sink = BufferedEventSink(inner, now=lambda: NOW)
    tracer = EventTracer(store, sink=sink)
    make(store)

    events = tracer.drain()

    assert len(events) == 1
    assert sink.pending == 1
    assert inner.records == []


def test_recovery_flushes_the_buffer(store) -> None:  # type: ignore[no-untyped-def]
    inner = FlakySink()
    inner.down = True
    sink = BufferedEventSink(inner, now=lambda: NOW)
    tracer = EventTracer(store, sink=sink)
    make(store)
    tracer.drain()

    inner.down = False
    assert sink.flush() == 1
    assert len(inner.records) == 1
    assert sink.pending == 0


def test_flush_while_still_down_keeps_the_buffer(store) -> None:  # type: ignore[no-untyped-def]
    inner = FlakySink()
    inner.down = True
    sink = BufferedEventSink(inner, now=lambda: NOW)
    sink.write({"event_id": 1})

    assert sink.flush() == 0
    assert sink.pending == 1
    assert inner.records == []


def test_overflow_is_marked_not_silent(store) -> None:  # type: ignore[no-untyped-def]
    inner = FlakySink()
    inner.down = True
    sink = BufferedEventSink(inner, capacity=2, now=lambda: NOW)
    for index in range(5):
        sink.write({"event_id": index})

    assert sink.pending == 2
    assert sink.dropped == 3

    inner.down = False
    assert sink.flush() == 2
    assert [record["event_id"] for record in inner.records[:2]] == [3, 4]
    gap = inner.records[-1]
    assert gap["event_type"] == "event-gap"
    assert gap["payload"]["dropped"] == 3
    assert len(inner.records) == 3
    assert sink.gaps == 1
    assert sink.dropped == 0


def test_the_decision_path_never_touches_the_sink(store) -> None:  # type: ignore[no-untyped-def]
    inner = FlakySink()
    inner.down = True
    tracer = EventTracer(store, sink=BufferedEventSink(inner, now=lambda: NOW))

    ask = make(store)  # ingest succeeds with a dead sink

    assert ask.status.value == "pending"
    assert tracer.drain()
    assert inner.records == []
