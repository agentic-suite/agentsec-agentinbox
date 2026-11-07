"""Bus drivers: in-proc and filesystem spool pass the same conformance (M9)."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agentinbox.bus.base import BusLockedError, InProcBus, JobKind, SpoolBus, new_job
from tests.ask.conftest import NOW
from tests.bus.conformance import check_bus_contract


@pytest.fixture
def inproc() -> InProcBus:
    bus = InProcBus(now=lambda: NOW)
    yield bus  # type: ignore[misc]
    bus.close()


def spool(tmp_path: Path) -> SpoolBus:
    return SpoolBus(tmp_path / "spool", now=lambda: NOW)


def test_inproc_conformance(inproc: InProcBus) -> None:
    check_bus_contract(inproc, now=NOW)


def test_spool_conformance(tmp_path: Path) -> None:
    bus = spool(tmp_path)
    try:
        check_bus_contract(bus, now=NOW)
    finally:
        bus.close()


def test_broken_driver_fails_conformance() -> None:
    class BrokenBus:
        name = "broken"

        def publish(self, job) -> bool:  # type: ignore[no-untyped-def]
            return True

        def consume(self, handler) -> int:  # type: ignore[no-untyped-def]
            return 0

        def close(self) -> None:
            return None

    with pytest.raises(AssertionError):
        check_bus_contract(BrokenBus(), now=NOW)  # type: ignore[arg-type]


def test_spool_is_single_owner_and_releases_on_close(tmp_path: Path) -> None:
    first = spool(tmp_path)
    with pytest.raises(BusLockedError):
        spool(tmp_path)
    first.close()

    second = spool(tmp_path)
    second.close()


def test_spool_survives_a_crash_and_resumes(tmp_path: Path) -> None:
    job = new_job(JobKind.DELIVER, ask_id="ask-crash", now=NOW)
    bus = spool(tmp_path)
    assert bus.publish(job) is True

    def boom(_job) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("crash mid-job")

    with pytest.raises(RuntimeError):
        bus.consume(boom)
    bus.close()

    resumed = spool(tmp_path)
    seen = []
    try:
        assert resumed.consume(seen.append) == 1
    finally:
        resumed.close()
    assert seen == [job]


def test_spool_sweeps_tmp_on_boot(tmp_path: Path) -> None:
    spool_dir = tmp_path / "spool"
    staging = spool_dir / "tmp"
    staging.mkdir(parents=True)
    junk = staging / "half-written.tmp"
    junk.write_text("partial", encoding="utf-8")

    bus = SpoolBus(spool_dir, now=lambda: NOW)
    bus.close()

    assert not junk.exists()


def test_spool_publishes_private_0600_files(tmp_path: Path) -> None:
    spool_dir = tmp_path / "spool"
    bus = SpoolBus(spool_dir, now=lambda: NOW)
    try:
        bus.publish(new_job(JobKind.DELIVER, ask_id="ask-mode", now=NOW))
        files = list((spool_dir / "jobs").glob("*.json"))
    finally:
        bus.close()

    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600


def test_spool_prunes_done_aggressively(tmp_path: Path) -> None:
    spool_dir = tmp_path / "spool"
    bus = SpoolBus(spool_dir, now=lambda: NOW)
    try:
        for index in range(5):
            bus.publish(new_job(JobKind.DELIVER, ask_id=f"ask-{index}", now=NOW))
            assert bus.consume(lambda _job: None) == 1
        bus.prune_done(keep=2)
        assert len(list((spool_dir / "done").glob("*.json"))) == 2
    finally:
        bus.close()


def test_spool_pickup_is_bounded_by_one_second(tmp_path: Path) -> None:
    bus = SpoolBus(tmp_path / "spool", poll_interval=0.05)
    job = new_job(
        JobKind.DELIVER,
        ask_id="ask-latency",
        now=datetime.now(UTC),
        not_before=datetime.now(UTC) + timedelta(milliseconds=200),
    )
    try:
        bus.publish(job)
        started = time.monotonic()
        seen = []
        # Poll until due, but never longer than the N-3c bound.
        while not seen and time.monotonic() - started < 1.0:
            bus.consume(seen.append)
            time.sleep(bus.poll_interval)
        elapsed = time.monotonic() - started
    finally:
        bus.close()

    assert seen == [job]
    assert elapsed < 1.0
    assert bus.poll_interval <= 1.0
