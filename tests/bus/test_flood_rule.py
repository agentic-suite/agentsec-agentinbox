"""Flood-before-bus rule: a flood publishes one digest job, never N (M9 item 9.5)."""

from __future__ import annotations

from pathlib import Path

from agentinbox.bus.base import JobKind, SpoolBus, publish_digest
from tests.ask.conftest import NOW


def test_200_ask_flood_publishes_exactly_one_digest_job(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    bus = SpoolBus(spool, now=lambda: NOW)
    try:
        published = [
            publish_digest(
                bus,
                window_start=NOW,
                first_ask_id="ask-0",
                count=count,
                now=NOW,
            )
            for count in range(1, 201)
        ]
        jobs = list((spool / "jobs").glob("*.json"))
        seen = []
        consumed = bus.consume(seen.append)
    finally:
        bus.close()

    assert all(published), "republishing a digest in the same window is an accepted update"
    assert len(jobs) == 1
    assert consumed == 1
    assert seen[0].kind is JobKind.DIGEST
    assert seen[0].payload["count"] == 200


def test_a_new_window_publishes_a_new_digest(tmp_path: Path) -> None:
    bus = SpoolBus(tmp_path / "spool", now=lambda: NOW)
    try:
        first = publish_digest(
            bus, window_start=NOW, first_ask_id="ask-0", count=5, now=NOW
        )
        second = publish_digest(
            bus, window_start=NOW.replace(second=30), first_ask_id="ask-9", count=2, now=NOW
        )
    finally:
        bus.close()

    assert first is True
    assert second is True
