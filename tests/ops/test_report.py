"""Local metrics report: hand-computed values over a scripted corpus (M21 item 21.4)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path
from agentinbox.report import build_report, percentile
from agentinbox.store import (
    AskRecord,
    AskStatus,
    DeliveryRecord,
    FloodRecord,
    TransitionRecord,
)
from agentinbox.store.memory import MemoryStore

BASE = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def add_ask(
    store: MemoryStore,
    ask_id: str,
    *,
    cls: str,
    created: object,
    expires: object,
    status: AskStatus | None = None,
    answered_at: object | None = None,
    response_s: int | None = None,
) -> None:
    store.create_or_get_by_identity(
        AskRecord(
            ask_id=ask_id,
            action_identity=f"sha256:{ask_id}",
            session_id=f"sess_{ask_id}",
            agent_id="agent://ops",
            created_at=created,  # type: ignore[arg-type]
            expires_at=expires,  # type: ignore[arg-type]
            payload={"class": cls},
        )
    )
    if response_s is not None:
        assert answered_at is not None
        delivered = answered_at - timedelta(seconds=response_s)  # type: ignore[operator]
        store.record_delivery(
            DeliveryRecord(
                delivery_id=f"del_{ask_id}",
                ask_id=ask_id,
                channel="terminal",
                attempt=1,
                status="delivered",
                at=delivered,
            )
        )
    if status is not None:
        assert answered_at is not None
        kind = "answer" if status in {AskStatus.APPROVED, AskStatus.DENIED} else "expired"
        assert store.cas_status(
            ask_id,
            expected=AskStatus.PENDING,
            new=status,
            transition=TransitionRecord(
                ask_id=ask_id,
                at=answered_at,  # type: ignore[arg-type]
                kind=kind,
                from_status=AskStatus.PENDING,
                to_status=status,
                principal="alice",
                channel="terminal",
                detail={"decision": status.value},
            ),
        )


def build_corpus(store: MemoryStore) -> None:
    add_ask(
        store, "a1", cls="irreversible", created=BASE, expires=BASE + timedelta(minutes=5),
        status=AskStatus.APPROVED, answered_at=BASE + timedelta(seconds=15), response_s=10,
    )
    add_ask(
        store, "a2", cls="irreversible", created=BASE, expires=BASE + timedelta(minutes=5),
        status=AskStatus.APPROVED, answered_at=BASE + timedelta(seconds=25), response_s=20,
    )
    add_ask(
        store, "a3", cls="irreversible", created=BASE, expires=BASE + timedelta(minutes=5),
        status=AskStatus.DENIED, answered_at=BASE + timedelta(seconds=35), response_s=30,
    )
    add_ask(
        store, "a4", cls="irreversible", created=BASE, expires=BASE + timedelta(minutes=1),
        status=AskStatus.EXPIRED, answered_at=BASE + timedelta(minutes=1),
    )
    add_ask(
        store, "a5", cls="reversible", created=BASE, expires=BASE + timedelta(minutes=5),
        status=AskStatus.DENIED, answered_at=BASE + timedelta(seconds=45), response_s=40,
    )
    add_ask(store, "a6", cls="irreversible", created=BASE, expires=BASE + timedelta(minutes=5))

    store.append_event(
        TransitionRecord(
            ask_id="a2",
            at=BASE + timedelta(seconds=10),
            kind="ask-escalated",
            from_status=AskStatus.PENDING,
            to_status=AskStatus.PENDING,
            detail={"to_tier": "tier-2", "recipients": 2},
        )
    )
    store.record_flood(
        FloodRecord(
            flood_id="flood_1",
            agent_id="agent://ops",
            session_id="sess_flood",
            window_start=BASE,
            window_end=BASE + timedelta(seconds=30),
            denied_count=180,
            first_ask_id="a1",
            at=BASE + timedelta(seconds=30),
        )
    )
    store.append_event(
        TransitionRecord(
            ask_id="a3",
            at=BASE + timedelta(seconds=40),
            kind="answer-rejected",
            from_status=AskStatus.DENIED,
            to_status=AskStatus.DENIED,
            detail={"cause": "bad_secret"},
        )
    )
    store.append_event(
        TransitionRecord(
            ask_id="a4",
            at=BASE + timedelta(seconds=50),
            kind="late-answer",
            from_status=AskStatus.EXPIRED,
            to_status=AskStatus.EXPIRED,
            detail={"cause": "late"},
        )
    )


def test_report_matches_hand_computed_metrics() -> None:
    store = MemoryStore()
    try:
        build_corpus(store)
        report = build_report(store, now=lambda: BASE + timedelta(minutes=1))
        data = report.to_dict()
    finally:
        store.close()

    assert data["contract"] == "report/1.0"
    assert data["local_only"] is True
    assert data["total_asks"] == 6
    assert data["pending"] == 1
    assert data["expiries"] == 1
    assert data["escalation_firings"] == 1
    assert data["flood_events"] == 1
    assert data["response_time_s"] == {"p50": 20.0, "p99": 40.0, "samples": 4}
    assert data["answer_rejected_causes"] == {"bad_signature": 1, "late": 1}
    assert data["deny_rate_by_class"] == {"irreversible": 0.5, "reversible": 1.0}


def test_report_is_read_only() -> None:
    store = MemoryStore()
    try:
        build_corpus(store)
        before = len(store.audit_entries())
        build_report(store)
        assert len(store.audit_entries()) == before
    finally:
        store.close()


def test_report_skips_answers_without_bounds_and_negative_intervals() -> None:
    store = MemoryStore()
    try:
        from agentinbox.store import AskRecord

        store.create_or_get_by_identity(
            AskRecord(
                ask_id="neg",
                action_identity="sha256:neg",
                session_id="sess_neg",
                agent_id="agent://ops",
                created_at=BASE,
                expires_at=BASE + timedelta(minutes=5),
                payload={"class": "irreversible"},
            )
        )
        store.record_delivery(
            DeliveryRecord(
                delivery_id="del_neg",
                ask_id="neg",
                channel="terminal",
                attempt=1,
                status="delivered",
                at=BASE + timedelta(seconds=50),
            )
        )
        store.cas_status(
            "neg",
            expected=AskStatus.PENDING,
            new=AskStatus.APPROVED,
            transition=TransitionRecord(
                ask_id="neg",
                at=BASE + timedelta(seconds=10),
                kind="answer",
                from_status=AskStatus.PENDING,
                to_status=AskStatus.APPROVED,
                detail={"decision": "approved"},
            ),
        )
        # An answer event with no matching created transition: no start bound exists.
        store.append_event(
            TransitionRecord(
                ask_id="ghost",
                at=BASE + timedelta(seconds=5),
                kind="answer",
                from_status=AskStatus.PENDING,
                to_status=AskStatus.APPROVED,
                detail={"decision": "approved"},
            )
        )
        data = build_report(store, now=lambda: BASE + timedelta(minutes=1)).to_dict()
    finally:
        store.close()

    assert data["response_time_s"] == {"p50": None, "p99": None, "samples": 0}
    assert data["total_asks"] == 2


def test_empty_store_reports_nulls_not_zeros() -> None:
    store = MemoryStore()
    try:
        data = build_report(store).to_dict()
    finally:
        store.close()

    assert data["response_time_s"] == {"p50": None, "p99": None, "samples": 0}
    assert data["total_asks"] == 0
    assert data["pending"] == 0
    assert data["deny_rate_by_class"] == {}
    json.dumps(data)  # the artifact is always JSON-serializable


def test_percentile_is_nearest_rank() -> None:
    values = [30.0, 10.0, 40.0, 20.0]
    assert percentile(values, 50) == 20.0
    assert percentile(values, 99) == 40.0
    assert percentile([7.0], 99) == 7.0
    assert percentile([], 50) is None


def test_cli_report_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    from agentinbox.config import load_config
    from agentinbox.ingest import ingest
    from agentinbox.store import utcnow
    from agentinbox.store.loader import load_store
    from agentinbox.trust import ProducerIdentity
    from tests.ask.conftest import payload

    now = utcnow()
    store = load_store("sqlite", home=home)
    try:
        ingest(
            payload(
                expires_at=(now + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=load_config(resolve_config_path(home)),
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        )
    finally:
        store.close()

    assert main(["--home", str(home), "report", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["local_only"] is True
    assert data["total_asks"] == 1
    assert data["pending"] == 1
    assert data["response_time_s"]["samples"] == 0
