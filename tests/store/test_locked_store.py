"""Regression: a permission-locked store must FAIL CLOSED, never self-heal.

Found by the M32 field sweep (FT-SC-24-LIVE, Defect #5): SqliteStore used to
re-chmod an existing db to 0600 before connecting, silently healing a locked
store so `inbox` exited 0 instead of failing closed. This test locks the fix
in: an unreadable db must raise StoreError; a *missing* db may still be
created with 0600.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.store import StoreError
from agentinbox.store.loader import load_store


def _make_db(home: Path) -> Path:
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    load_config(config_path)
    db = home / "inbox.db"
    connection = sqlite3.connect(db)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS asks (ask_id TEXT PRIMARY KEY)"
    )
    connection.commit()
    connection.close()
    return db


def test_locked_store_fails_closed_instead_of_self_healing(tmp_path: Path) -> None:
    db = _make_db(tmp_path / "home")

    os.chmod(db, 0)

    with pytest.raises(StoreError):
        load_store("sqlite", home=tmp_path / "home")

    # The lock survives: nothing silently re-opened it.
    assert db.exists()
    mode = db.stat().st_mode & 0o777
    assert mode == 0


def test_new_store_is_created_with_private_mode(tmp_path: Path) -> None:
    home = tmp_path / "fresh"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    load_config(config_path)

    store = load_store("sqlite", home=home)
    try:
        assert (home / "inbox.db").exists()
    finally:
        store.close()