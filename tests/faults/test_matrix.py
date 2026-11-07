"""SC-24 fault matrix: every fault is deny-or-pending, explicit, and never an allow (M20)."""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.api import start_api
from agentinbox.bus import JobKind, new_job
from agentinbox.bus.delivery import DeliveryWiring
from agentinbox.config import init_home, resolve_config_path
from agentinbox.config_audit import record_config_failure
from agentinbox.doctor import WARN, _clock_skew
from agentinbox.events import BufferedEventSink, EventTracer
from agentinbox.faults import FAILURE_MATRIX, Fault, case_for
from agentinbox.ingest import ingest
from agentinbox.reload import ConfigHolder
from agentinbox.scheduler import Scheduler
from agentinbox.store import (
    AskStatus,
    SchemaVersionError,
    StoreError,
    utcnow,
)
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.store.sqlite import SqliteStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload
from tests.ask.test_api import TOKEN, call

M18_ASK = "ask_0123456789abcdef"


class Clock:
    def __init__(self, start=NOW) -> None:  # type: ignore[no-untyped-def]
        self.moment = start

    def __call__(self):  # type: ignore[no-untyped-def]
        return self.moment


class LockedStore(MemoryStore):
    def create_or_get_by_identity(self, ask, *, dedupe_window_s: int = 900):  # type: ignore[no-untyped-def]
        raise StoreError("store is locked")


class DownChannel:
    name = "webhook"

    def deliver(self, ask, card) -> None:  # type: ignore[no-untyped-def]
        raise OSError("channel 500")

    def authenticate(self, *, as_name: str | None = None) -> str | None:
        return None


class FlakySink:
    def __init__(self) -> None:
        self.records = []
        self.down = True

    def write(self, record) -> None:  # type: ignore[no-untyped-def]
        if self.down:
            raise OSError("sink offline")
        self.records.append(record)


def make_ask(store, *, now=NOW):  # type: ignore[no-untyped-def]
    return ingest(
        payload(ask_id=M18_ASK),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=now,
    ).ask


def test_the_matrix_is_complete_and_never_allows_by_itself() -> None:
    assert {case.fault for case in FAILURE_MATRIX} == set(Fault)
    for fault in Fault:
        assert case_for(fault).fault is fault
    for case in FAILURE_MATRIX:
        if case.fault is not Fault.SINK_OFFLINE:  # sink faults do not touch decisions
            assert 0 not in {int(code) for code in case.allowed_outcomes}
        assert case.allowed_outcomes


def test_store_locked_refuses_ingest_and_returns_503() -> None:
    locked = LockedStore()
    with pytest.raises(StoreError, match="locked"):
        ingest(
            payload(),
            store=locked,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )

    api = start_api(store=locked, config=config(), token=TOKEN, now=lambda: NOW)
    try:
        status, body = call(api, "POST", "/v1/asks", body=payload())
    finally:
        api.stop()

    assert status == 503
    assert body["error"]["field"] == "store"


def test_store_corrupt_fails_doctor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from agentinbox.cli import main

    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    (home / "inbox.db").write_bytes(b"not a sqlite database")

    with pytest.raises(StoreError):
        load_store("sqlite", home=home)

    assert main(["--home", str(home), "doctor"]) == 4
    assert "schema" in capsys.readouterr().out


def test_schema_mismatch_refuses_downgrade(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from agentinbox.cli import main

    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    store = SqliteStore(home / "inbox.db")
    store.close()
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute("UPDATE schema_version SET version = 999")
    connection.commit()
    connection.close()

    with pytest.raises(SchemaVersionError, match="downgrade"):
        SqliteStore(home / "inbox.db")

    assert main(["--home", str(home), "doctor"]) == 4
    assert "downgrade" in capsys.readouterr().out


def test_sink_offline_never_changes_a_decision() -> None:
    store = MemoryStore()
    inner = FlakySink()
    tracer = EventTracer(store, sink=BufferedEventSink(inner, now=lambda: NOW))
    try:
        ask = make_ask(store)
        tracer.drain()

        assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]
        assert tracer.sink.pending == 1
        assert inner.records == []
    finally:
        store.close()


def test_channel_500_leaves_the_ask_pending() -> None:
    store = MemoryStore()
    try:
        ask = make_ask(store)
        DeliveryWiring(
            store, [DownChannel()], now=lambda: NOW, backoff=lambda _attempt: None
        ).handle(new_job(JobKind.DELIVER, ask_id=ask.ask_id, now=NOW))

        assert store.get(ask.ask_id).status is AskStatus.PENDING  # type: ignore[union-attr]
        records = store.list_deliveries(ask.ask_id)
        assert [item.status for item in records] == ["failed", "failed", "failed"]
        assert any(
            item.kind == "delivery-failed" for item in store.transitions_for(ask.ask_id)
        )
    finally:
        store.close()


def test_scheduler_kill_recovery_expires_exactly_once() -> None:
    store = MemoryStore()
    try:
        ask = make_ask(store)
        clock = Clock(NOW + timedelta(seconds=301))
        first = Scheduler(store, now=clock)
        second = Scheduler(store, now=clock)

        assert first.tick().expired == 1
        assert second.tick().expired == 0
        assert first.allows_on_expiry == 0
        assert second.allows_on_expiry == 0
        assert store.get(ask.ask_id).status is AskStatus.EXPIRED  # type: ignore[union-attr]
    finally:
        store.close()


def test_invalid_reload_keeps_the_last_good_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    holder = ConfigHolder(config_path)
    before = holder.config

    config_path.write_text("[classes.x]\nttl_seconds = 0\n", encoding="utf-8")
    result = holder.reload()

    assert result.ok is False
    assert result.error is not None
    assert holder.config is before
    record_config_failure(home, result.error)
    events = [
        json.loads(line)
        for line in (home / "logs" / "inbox-config-changed.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[-1]["failed"] is True


def test_a_valid_reload_applies(tmp_path: Path) -> None:
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    holder = ConfigHolder(config_path)
    text = config_path.read_text(encoding="utf-8").replace(
        "ttl_seconds = 300", "ttl_seconds = 600"
    )
    config_path.write_text(text, encoding="utf-8")

    result = holder.reload()

    assert result.ok is True
    assert holder.config.classes["irreversible"].ttl_seconds == 600


def test_clock_skew_is_a_named_doctor_warning(tmp_path: Path) -> None:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    store = SqliteStore(home / "inbox.db")
    try:
        store.append_audit(
            kind="test", ref_id="x", at=utcnow() + timedelta(hours=1), payload={}
        )
    finally:
        store.close()

    check = _clock_skew(home / "inbox.db")
    assert check.status == WARN
    assert "ahead" in check.detail


def test_a_locked_store_makes_the_producer_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentinbox.cli import main

    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    marker = tmp_path / "locked-never"
    connection = sqlite3.connect(home / "inbox.db", isolation_level=None)
    connection.execute("BEGIN EXCLUSIVE")
    try:
        code = main(
            ["--home", str(home), "ask", "--exec", f"touch {marker}"]
        )
    finally:
        connection.execute("ROLLBACK")
        connection.close()

    assert code == 4
    assert not marker.exists()
