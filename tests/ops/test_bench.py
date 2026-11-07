"""Performance floors N-1..N-7 recorded as executable benches (M21 item 21.6)."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

from agentinbox.bench import (
    NFR,
    bench_external,
    bench_ingest,
    bench_load,
    bench_render,
    bench_resolve,
    bench_scheduler_tick,
    bench_spool_pickup,
    bench_startup,
    run_benchmarks,
)
from agentinbox.config import ChannelConfig, init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.store import utcnow
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def test_ingest_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    try:
        p50, p99 = bench_ingest(store, config, count=20)
    finally:
        store.close()

    assert p50 < NFR["N-1-p50"].threshold_ms
    assert p99 < NFR["N-1-p99"].threshold_ms


def test_render_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    try:
        elapsed = bench_render(store, config)
    finally:
        store.close()

    assert elapsed < NFR["N-2"].threshold_ms


def test_resolve_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    try:
        now = utcnow()
        ask = ingest(
            payload(
                session_id="sess_resolve_bench",
                expires_at=(now + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        ).ask
        p99 = bench_resolve(store, ask.ask_id, config, count=10)
    finally:
        store.close()

    assert p99 < NFR["N-4"].threshold_ms


def test_spool_pickup_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    elapsed = bench_spool_pickup(home)

    assert elapsed <= NFR["N-3c"].threshold_ms


def test_scheduler_tick_floor_is_met() -> None:
    store = MemoryStore()
    try:
        now = utcnow()
        from agentinbox.scheduler import Scheduler

        for index in range(100):
            from agentinbox.store import AskRecord

            store.create_or_get_by_identity(
                AskRecord(
                    ask_id=f"tick_{index}",
                    action_identity=f"sha256:tick{index}",
                    session_id=f"sess_tick_{index}",
                    agent_id="agent://ops",
                    created_at=now,
                    expires_at=now + timedelta(minutes=5),
                    payload={"class": "irreversible"},
                )
            )
        scheduler = Scheduler(store, now=lambda: now)
        elapsed = bench_scheduler_tick(scheduler)
    finally:
        store.close()

    assert elapsed <= NFR["N-5"].threshold_ms


def test_startup_and_doctor_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    elapsed = bench_startup(home)

    assert elapsed < NFR["N-7"].threshold_ms


def test_external_delivery_floor_is_met(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))
    webhook = ChannelConfig(
        enabled=True, url_ref="env:HOOK_URL", hmac_key_ref="env:HOOK_KEY"
    )
    from dataclasses import replace

    config = replace(
        config, channels={**config.channels, "webhook": webhook}
    )
    store = load_store("sqlite", home=home)
    try:
        now = utcnow()
        ask = ingest(
            payload(
                session_id="sess_external_bench",
                expires_at=(now + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        ).ask
        p50 = bench_external(config, ask, count=5)
    finally:
        store.close()

    assert p50 < NFR["N-3b"].threshold_ms


def test_10k_load_holds_the_ingest_floors() -> None:
    store = MemoryStore()
    try:
        from agentinbox.config import ClassConfig, Config

        corpus = Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})
        started = time.monotonic()
        bench_load(store, corpus, total=10_000, pending=100)
        seed_seconds = time.monotonic() - started
        p50, p99 = bench_ingest(store, corpus, count=20)
    finally:
        store.close()

    assert seed_seconds < 60
    assert p50 < NFR["N-6"].threshold_ms
    assert p99 < NFR["N-6"].threshold_ms


def test_run_benchmarks_records_every_floor(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    results = run_benchmarks(home, count=5)

    names = {result.name for result in results}
    assert {"N-1", "N-2", "N-3b", "N-3c", "N-4", "N-5", "N-6", "N-7"} <= names
    assert all(result.ok for result in results), [
        result for result in results if not result.ok
    ]
