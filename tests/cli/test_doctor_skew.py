"""doctor clock-skew check (M4 item 4.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path
from agentinbox.store import AskRecord
from agentinbox.store.sqlite import SqliteStore


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def write_ask(home: Path, created_at: datetime) -> None:
    store = SqliteStore(home / "inbox.db")
    try:
        store.create_or_get_by_identity(
            AskRecord(
                ask_id="ask_" + "a" * 16,
                action_identity="sha256:" + "a" * 64,
                session_id="sess_skew",
                agent_id="agent://skew/1",
                created_at=created_at,
                expires_at=created_at + timedelta(minutes=5),
                payload={},
            )
        )
    finally:
        store.close()


def test_evidence_ahead_of_the_clock_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    write_ask(home, datetime.now(UTC) + timedelta(hours=1))

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "warn clock-skew" in out


def test_consistent_clock_is_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path)
    write_ask(home, datetime.now(UTC) - timedelta(minutes=1))

    assert main(["--home", str(home), "doctor"]) == 0
    assert "ok   clock-skew" in capsys.readouterr().out
