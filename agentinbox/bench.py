"""Executable performance floors N-1..N-7 (M21 item 21.6).

Design: ``docs/design/v0.1.0/ops.md`` §6. The benches measure the real store and channel paths so a
regression is a red test, not a release-day surprise. The 10k-load bench uses the in-memory driver
to isolate algorithmic cost; the SQLite ingest floor is measured separately.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentinbox.bus import JobKind, SpoolBus, new_job
from agentinbox.card import build_card
from agentinbox.channels.webhook import WebhookChannel
from agentinbox.contract import compute_action_identity
from agentinbox.doctor import run_checks
from agentinbox.ingest import ingest
from agentinbox.report import percentile
from agentinbox.resolve import resolve
from agentinbox.scheduler import Scheduler
from agentinbox.store import (
    AskRecord,
    AskStatus,
    AskStore,
    TransitionRecord,
    to_iso,
    utcnow,
)
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity


@dataclass(frozen=True, slots=True)
class Floor:
    name: str
    threshold_ms: float
    detail: str


@dataclass(frozen=True, slots=True)
class BenchResult:
    name: str
    value_ms: float
    threshold_ms: float
    ok: bool
    detail: str


NFR: dict[str, Floor] = {
    "N-1-p50": Floor("N-1-p50", 50.0, "ingest p50 < 50 ms"),
    "N-1-p99": Floor("N-1-p99", 250.0, "ingest p99 < 250 ms"),
    "N-2": Floor("N-2", 100.0, "terminal render < 100 ms"),
    "N-3a": Floor("N-3a", 1000.0, "desktop notification p99 < 1 s"),
    "N-3b": Floor("N-3b", 2000.0, "external delivery p50 < 2 s (mocked)"),
    "N-3c": Floor("N-3c", 1000.0, "spool pickup ≤ 1 s"),
    "N-4": Floor("N-4", 100.0, "resolve p99 < 100 ms"),
    "N-5": Floor("N-5", 1000.0, "scheduler tick ≤ 1 s"),
    "N-6": Floor("N-6", 250.0, "10k load holds the ingest floors"),
    "N-7": Floor("N-7", 2000.0, "startup + doctor < 2 s cold"),
}


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _benchmark_payload(index: int, now: datetime) -> dict[str, Any]:
    arguments = {"command": f"echo bench-{index}", "timeout_s": 30}
    return {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": "agent://bench",
        "session_id": f"sess_bench_{index}",
        "environment": "local",
        "data_class": "unknown",
        "class": "irreversible",
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": "bench",
            "policy_version": "v0.1.0",
            "clause": "performance bench",
        },
        "criticality": "normal",
        "requested_by": "agent://bench",
        "expires_at": to_iso(now + timedelta(minutes=5)),
        "context": {},
    }


def make_ask(store: AskStore, config: Any, *, index: int = 0, now: datetime | None = None) -> Any:
    moment = now or utcnow()
    return ingest(
        _benchmark_payload(index, moment),
        store=store,
        config=config,
        producer=ProducerIdentity.unauthenticated(),
        now=moment,
    ).ask


def bench_ingest(
    store: AskStore, config: Any, *, count: int = 20, now: datetime | None = None
) -> tuple[float, float]:
    moment = now or utcnow()
    durations: list[float] = []
    for index in range(count):
        started = time.perf_counter()
        make_ask(store, config, index=index, now=moment)
        durations.append(_elapsed_ms(started))
    p50 = percentile(durations, 50)
    p99 = percentile(durations, 99)
    return float(p50 or 0.0), float(p99 or 0.0)


def bench_render(store: AskStore, config: Any, *, now: datetime | None = None) -> float:
    moment = now or utcnow()
    ask = make_ask(store, config, index=900_000, now=moment)
    started = time.perf_counter()
    card = build_card(ask, now=moment, transitions=store.transitions_for(ask.ask_id))
    card.render("terminal")
    return _elapsed_ms(started)


def bench_resolve(
    store: AskStore, ask_id: str, config: Any, *, count: int = 10
) -> float:
    durations: list[float] = []
    for _ in range(count):
        started = time.perf_counter()
        resolve(store, ask_id, now=utcnow(), config=config)
        durations.append(_elapsed_ms(started))
    return float(percentile(durations, 99) or 0.0)


def bench_spool_pickup(home: Path, *, now: datetime | None = None) -> float:
    moment = now or utcnow()
    bus = SpoolBus(Path(home) / "spool", now=lambda: moment)
    try:
        started = time.perf_counter()
        assert bus.publish(new_job(JobKind.DELIVER, ask_id="ask_bench", now=moment))
        consumed: list[Any] = []
        bus.consume(consumed.append)
    finally:
        bus.close()
    assert consumed, "the spool did not deliver the job"
    return _elapsed_ms(started)


def bench_scheduler_tick(scheduler: Scheduler) -> float:
    started = time.perf_counter()
    scheduler.tick()
    return _elapsed_ms(started)


def bench_startup(home: Path, config_path: Path | None = None) -> float:
    path = Path(config_path) if config_path is not None else Path(home) / "config.toml"
    started = time.perf_counter()
    store = load_store("sqlite", home=Path(home))
    try:
        run_checks(Path(home), path)
    finally:
        store.close()
    return _elapsed_ms(started)


def bench_external(
    config: Any, ask: AskRecord, *, count: int = 5, environ: Mapping[str, str] | None = None
) -> float:
    channel = WebhookChannel(
        config=config,
        post=lambda _url, _body, _headers: 200,
        now=utcnow,
        environ=environ
        or {"HOOK_URL": "https://example.invalid/hook", "HOOK_KEY": "bench-key"},
    )
    durations: list[float] = []
    for _ in range(count):
        started = time.perf_counter()
        channel.deliver(ask)
        durations.append(_elapsed_ms(started))
    return float(percentile(durations, 50) or 0.0)


def bench_load(
    store: AskStore,
    config: Any,
    *,
    total: int = 10_000,
    pending: int = 100,
    now: datetime | None = None,
) -> None:
    """Seed a pathological corpus: ``total`` resolved asks plus ``pending`` pending ones."""
    moment = now or utcnow()
    for index in range(total):
        ask_id = f"load_{index:06d}"
        store.create_or_get_by_identity(
            AskRecord(
                ask_id=ask_id,
                action_identity=f"sha256:load{index:06d}",
                session_id=f"sess_load_{index:06d}",
                agent_id="agent://load",
                created_at=moment,
                expires_at=moment + timedelta(minutes=5),
                payload={"class": "irreversible"},
            )
        )
        if index < total - pending:
            store.cas_status(
                ask_id,
                expected=AskStatus.PENDING,
                new=AskStatus.APPROVED,
                transition=TransitionRecord(
                    ask_id=ask_id,
                    at=moment,
                    kind="answer",
                    from_status=AskStatus.PENDING,
                    to_status=AskStatus.APPROVED,
                    principal="load",
                    channel="terminal",
                    detail={"decision": "approved"},
                ),
            )


def run_benchmarks(
    home: Path,
    *,
    count: int = 20,
    load_total: int = 10_000,
    now: datetime | None = None,
) -> list[BenchResult]:
    """Measure every floor and return the machine-readable release artifact."""
    from dataclasses import replace

    from agentinbox.config import ChannelConfig, load_config, resolve_config_path

    moment = now or utcnow()
    config = load_config(resolve_config_path(Path(home)))
    store = load_store("sqlite", home=Path(home))
    results: list[BenchResult] = []
    try:
        p50, p99 = bench_ingest(store, config, count=count, now=moment)
        results.append(
            BenchResult(
                "N-1",
                p50,
                NFR["N-1-p50"].threshold_ms,
                p50 < NFR["N-1-p50"].threshold_ms and p99 < NFR["N-1-p99"].threshold_ms,
                f"p50={p50:.2f} ms, p99={p99:.2f} ms",
            )
        )

        render = bench_render(store, config, now=moment)
        results.append(_result(NFR["N-2"], render, f"{render:.2f} ms"))

        ask = make_ask(store, config, index=990_001, now=moment)
        resolve_p99 = bench_resolve(store, ask.ask_id, config, count=count)
        results.append(_result(NFR["N-4"], resolve_p99, f"p99={resolve_p99:.2f} ms"))

        webhook_config = replace(
            config,
            channels={
                **config.channels,
                "webhook": ChannelConfig(
                    enabled=True, url_ref="env:HOOK_URL", hmac_key_ref="env:HOOK_KEY"
                ),
            },
        )
        external = bench_external(webhook_config, ask, count=max(3, count // 4))
        results.append(_result(NFR["N-3b"], external, f"p50={external:.2f} ms (mocked)"))
    finally:
        store.close()

    pickup = bench_spool_pickup(Path(home), now=moment)
    results.append(_result(NFR["N-3c"], pickup, f"{pickup:.2f} ms"))

    load_store_driver = MemoryStore()
    try:
        load_config_simple = load_config(resolve_config_path(Path(home)))
        bench_load(load_store_driver, load_config_simple, total=load_total, now=moment)
        scheduler = Scheduler(load_store_driver, now=lambda: moment)
        tick = bench_scheduler_tick(scheduler)
        load_p50, load_p99 = bench_ingest(
            load_store_driver, load_config_simple, count=max(5, count // 4), now=moment
        )
    finally:
        load_store_driver.close()
    results.append(_result(NFR["N-5"], tick, f"{tick:.2f} ms"))
    results.append(
        BenchResult(
            "N-6",
            load_p50,
            NFR["N-6"].threshold_ms,
            load_p50 < NFR["N-1-p50"].threshold_ms
            and load_p99 < NFR["N-1-p99"].threshold_ms,
            f"10k resolved: p50={load_p50:.2f} ms, p99={load_p99:.2f} ms",
        )
    )

    startup = bench_startup(Path(home), resolve_config_path(Path(home)))
    results.append(_result(NFR["N-7"], startup, f"{startup:.2f} ms"))
    return results


def _result(floor: Floor, value_ms: float, detail: str) -> BenchResult:
    return BenchResult(
        name=floor.name,
        value_ms=value_ms,
        threshold_ms=floor.threshold_ms,
        ok=value_ms < floor.threshold_ms,
        detail=detail,
    )


__all__ = [
    "NFR",
    "BenchResult",
    "Floor",
    "bench_external",
    "bench_ingest",
    "bench_load",
    "bench_render",
    "bench_resolve",
    "bench_scheduler_tick",
    "bench_spool_pickup",
    "bench_startup",
    "make_ask",
    "run_benchmarks",
]
