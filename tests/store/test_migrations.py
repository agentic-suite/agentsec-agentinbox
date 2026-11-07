"""Schema versioning and migrations (M1 item 1.5).

Forward migration must preserve old rows; downgrade must refuse loudly (E10/N-10).
"""

from __future__ import annotations

import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentinbox.store import SchemaVersionError, StoreError
from agentinbox.store.sqlite import MIGRATIONS, SCHEMA_VERSION, SqliteStore


def build_v1_store(path: Path) -> None:
    """An on-disk v1 store (the shipped v0→v1 DDL), with one row to preserve."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        for statement in MIGRATIONS[0]:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_version (version) VALUES (1)")
        connection.execute(
            "INSERT INTO asks (ask_id, action_identity, session_id, agent_id, status,"
            " created_at, expires_at, payload, dedupe_key)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "ask_old",
                "sha256:" + "a" * 64,
                "sess_old",
                "agent://old/1",
                "pending",
                "2026-11-06T12:00:00.000000Z",
                "2026-11-06T12:05:00.000000Z",
                "{}",
                "sha256:" + "a" * 64 + "\nsess_old",
            ),
        )
    path.chmod(0o600)


def test_new_store_is_at_the_current_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    store = SqliteStore(path)
    store.close()

    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]

    assert version == SCHEMA_VERSION


def test_old_store_migrates_forward_and_preserves_rows(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    build_v1_store(path)

    store = SqliteStore(path)
    try:
        loaded = store.get("ask_old")
        assert loaded is not None
        assert loaded.session_id == "sess_old"
        assert loaded.payload == {}
        assert loaded.decided_at is None
        pending = store.list_pending(now=datetime(2026, 11, 6, tzinfo=UTC))
        assert [item.ask_id for item in pending] == ["ask_old"]
        store.verify_chain()
    finally:
        store.close()

    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(asks)").fetchall()
        }

    assert version == SCHEMA_VERSION
    assert "decided_at" in columns


def test_downgrade_is_refused_loudly(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION + 1,))
    path.chmod(0o600)

    with pytest.raises(SchemaVersionError, match="downgrade"):
        SqliteStore(path)


def test_failed_migration_leaves_the_old_version(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (1)")
        # No asks table: the v1→v2 ALTER must fail and roll back.
    path.chmod(0o600)

    with pytest.raises(StoreError, match="store unavailable"):
        SqliteStore(path)

    with sqlite3.connect(path) as connection:
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]

    assert version == 1


def test_store_does_not_loosen_permissions_on_open(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    first = SqliteStore(path)
    first.close()
    path.chmod(0o644)

    second = SqliteStore(path)
    second.close()

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
