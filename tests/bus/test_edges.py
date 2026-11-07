"""Bus edge paths: malformed jobs, closed drivers, loader selection (M9)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentinbox.bus import (
    BusError,
    InProcBus,
    Job,
    JobKind,
    SpoolBus,
    load_bus,
    new_job,
    publish_digest,
)
from agentinbox.config import BusConfig, Config
from tests.ask.conftest import NOW


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        "[]",
        '{"job_id": "a", "kind": "nonsense", "ask_id": "a", "created_at": "x"}',
        '{"job_id": "a", "kind": "deliver", "ask_id": "a", "created_at": "x", "payload": 3}',
    ],
)
def test_from_json_rejects_malformed_jobs(text: str) -> None:
    with pytest.raises(BusError):
        Job.from_json(text)


def test_job_round_trips_with_not_before() -> None:
    job = new_job(
        JobKind.RENOTIFY,
        ask_id="ask-1",
        now=NOW,
        not_before=NOW,
        payload={"tier": "tier-2"},
    )
    restored = Job.from_json(job.to_json())
    assert restored == job
    assert restored.due(NOW) is True


def test_inproc_run_stops_and_drains() -> None:
    bus = InProcBus(now=lambda: NOW)
    seen = []
    bus.publish(new_job(JobKind.DELIVER, ask_id="ask-1", now=NOW))

    class Stop:
        def __init__(self) -> None:
            self.calls = 0

        def is_set(self) -> bool:
            return self.calls >= 1

        def wait(self, _timeout: float) -> bool:
            self.calls += 1
            return True

    bus.run(seen.append, Stop())  # type: ignore[arg-type]
    bus.close()
    assert [job.ask_id for job in seen] == ["ask-1"]


def test_closed_drivers_refuse(tmp_path: Path) -> None:
    inproc = InProcBus(now=lambda: NOW)
    inproc.close()
    with pytest.raises(BusError):
        inproc.publish(new_job(JobKind.DELIVER, ask_id="a", now=NOW))
    with pytest.raises(BusError):
        inproc.upsert(new_job(JobKind.DELIVER, ask_id="a", now=NOW))
    with pytest.raises(BusError):
        inproc.consume(lambda _job: None)

    spool = SpoolBus(tmp_path / "spool", now=lambda: NOW)
    spool.close()
    spool.close()  # idempotent
    with pytest.raises(BusError):
        spool.publish(new_job(JobKind.DELIVER, ask_id="a", now=NOW))
    with pytest.raises(BusError):
        spool.upsert(new_job(JobKind.DELIVER, ask_id="a", now=NOW))
    with pytest.raises(BusError):
        spool.consume(lambda _job: None)


def test_spool_rejects_an_unbounded_poll_interval(tmp_path: Path) -> None:
    with pytest.raises(BusError):
        SpoolBus(tmp_path / "spool", poll_interval=2.0, now=lambda: NOW)
    with pytest.raises(BusError):
        SpoolBus(tmp_path / "spool2", poll_interval=0, now=lambda: NOW)


def test_spool_reports_an_unreadable_job(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    bus = SpoolBus(spool, now=lambda: NOW)
    try:
        (spool / "jobs" / "broken.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(BusError):
            bus.consume(lambda _job: None)
    finally:
        bus.close()


def test_spool_consume_tolerates_a_job_that_vanishes(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    bus = SpoolBus(spool, now=lambda: NOW)
    job = new_job(JobKind.DELIVER, ask_id="ask-1", now=NOW)
    try:
        bus.publish(job)
        (spool / "jobs" / f"{job.job_id}.json").unlink()
        assert bus.consume(lambda _job: None) == 0
    finally:
        bus.close()


def test_spool_prune_zero_keeps_nothing(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    bus = SpoolBus(spool, now=lambda: NOW)
    try:
        bus.publish(new_job(JobKind.DELIVER, ask_id="ask-1", now=NOW))
        bus.consume(lambda _job: None)
        bus.prune_done(keep=0)
        assert list((spool / "done").glob("*.json")) == []
    finally:
        bus.close()


def test_upsert_refuses_a_completed_digest(tmp_path: Path) -> None:
    spool = tmp_path / "spool"
    bus = SpoolBus(spool, now=lambda: NOW)
    try:
        assert publish_digest(
            bus, window_start=NOW, first_ask_id="ask-0", count=1, now=NOW
        )
        assert bus.consume(lambda _job: None) == 1
        assert not publish_digest(
            bus, window_start=NOW, first_ask_id="ask-0", count=2, now=NOW
        )
    finally:
        bus.close()


def test_load_bus_selects_the_driver(tmp_path: Path) -> None:
    inproc = load_bus(Config(bus=BusConfig(driver="in-proc")), home=tmp_path)
    assert isinstance(inproc, InProcBus)
    inproc.close()

    spool = load_bus(Config(bus=BusConfig(driver="filesystem")), home=tmp_path)
    assert isinstance(spool, SpoolBus)
    spool.close()


def test_job_due_respects_not_before() -> None:
    job = new_job(JobKind.DELIVER, ask_id="a", now=NOW)
    assert job.due(datetime(2000, 1, 1, tzinfo=UTC)) is True
    later = new_job(JobKind.DELIVER, ask_id="a", now=NOW, not_before=NOW)
    assert later.due(NOW) is True
    assert later.due(datetime(2020, 1, 1, tzinfo=UTC)) is False
