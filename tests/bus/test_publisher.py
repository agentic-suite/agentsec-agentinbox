"""Lock-free producer publishing while the daemon owns the spool (M18/E12 review fix)."""

from __future__ import annotations

from pathlib import Path

from agentinbox.bus import (
    InProcBus,
    JobKind,
    SpoolBus,
    SpoolPublisher,
    load_publisher,
    new_job,
)
from agentinbox.config import BusConfig, Config
from tests.ask.conftest import NOW


def test_the_publisher_writes_while_a_consumer_holds_the_lock(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    daemon = SpoolBus(spool, now=lambda: NOW)
    publisher = SpoolPublisher(spool)
    job = new_job(JobKind.DELIVER, ask_id="ask_1", now=NOW)
    try:
        assert publisher.publish(job) is True
        assert publisher.publish(job) is False  # dedupe by id
        assert publisher.upsert(job) is True
        seen = []
        assert daemon.consume(seen.append) == 1
        assert seen[0].ask_id == "ask_1"
        # A consumed job is never republished, even through upsert.
        assert publisher.publish(job) is False
        assert publisher.upsert(job) is False
    finally:
        publisher.close()
        daemon.close()


def test_load_publisher_selects_the_driver(tmp_path: Path) -> None:
    inproc = load_publisher(Config(bus=BusConfig(driver="in-proc")), home=tmp_path)
    assert isinstance(inproc, InProcBus)
    inproc.close()

    files = load_publisher(Config(bus=BusConfig(driver="filesystem")), home=tmp_path)
    assert isinstance(files, SpoolPublisher)
    files.close()
