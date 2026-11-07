"""Durability and recovery conformance (M1 item 1.4).

Semantics 5 and 6: exactly-once recovery from persisted absolute instants, and
durable-commit-before-ack. A crash after the store returns must not lose the write.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentinbox.store import AskRecord, AskStatus, TransitionRecord
from agentinbox.store.sqlite import SqliteStore

T0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)

CRASH_SCRIPT = """
import os
import sys
from datetime import datetime, timezone

from agentinbox.store import AskRecord
from agentinbox.store.sqlite import SqliteStore

path = sys.argv[1]
store = SqliteStore(path)
ask = AskRecord(
    ask_id="ask_crashproof",
    action_identity="sha256:" + "c" * 64,
    session_id="sess_crash",
    agent_id="agent://crash/1",
    created_at=datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc),
    expires_at=datetime(2026, 11, 6, 12, 5, tzinfo=timezone.utc),
    payload={"contract": "ask/1.0"},
)
created = store.create_or_get_by_identity(ask)
assert created.created is True
# Simulate kill -9 immediately after the ack: no close(), no flush, no cleanup.
os._exit(0)
"""


def test_write_survives_process_kill(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"

    completed = subprocess.run(
        [sys.executable, "-c", CRASH_SCRIPT, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    reopened = SqliteStore(path)
    try:
        loaded = reopened.get("ask_crashproof")
        assert loaded is not None
        assert loaded.session_id == "sess_crash"
        reopened.verify_chain()
    finally:
        reopened.close()


def test_recovery_sees_the_same_pending_set(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    first = SqliteStore(path)
    for index in range(3):
        first.create_or_get_by_identity(
            AskRecord(
                ask_id=f"ask_recover_{index}",
                action_identity="sha256:" + format(index, "064x"),
                session_id=f"sess_{index}",
                agent_id="agent://recover/1",
                created_at=T0 - timedelta(minutes=index),
                expires_at=T0 - timedelta(minutes=index, seconds=-300),
                payload={"index": index},
            )
        )
    before = [(item.ask_id, item.expires_at) for item in first.list_pending(now=T0)]
    first.close()

    second = SqliteStore(path)
    try:
        after = [(item.ask_id, item.expires_at) for item in second.list_pending(now=T0)]
        assert after == before
        assert len(after) == 3
    finally:
        second.close()


def test_resolution_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    first = SqliteStore(path)
    ask = AskRecord(
        ask_id="ask_resolved",
        action_identity="sha256:" + "d" * 64,
        session_id="sess_resolved",
        agent_id="agent://recover/1",
        created_at=T0,
        expires_at=T0 + timedelta(minutes=5),
        payload={},
    )
    first.create_or_get_by_identity(ask)
    first.cas_status(
        ask.ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.APPROVED,
        transition=TransitionRecord(
            ask_id=ask.ask_id,
            at=T0 + timedelta(seconds=10),
            kind="answer",
            to_status=AskStatus.APPROVED,
            principal="alice",
            channel="terminal",
        ),
    )
    first.close()

    second = SqliteStore(path)
    try:
        loaded = second.get(ask.ask_id)
        assert loaded is not None
        assert loaded.status is AskStatus.APPROVED
        assert loaded.decided_at == T0 + timedelta(seconds=10)
        assert second.list_pending(now=T0) == []
    finally:
        second.close()
