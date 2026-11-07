"""Doctor completion: chain, spool, keys, and the healthy-path time budget (M20 item 20.4)."""

from __future__ import annotations

import sqlite3
import time
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.store import utcnow
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def seed(home: Path) -> None:
    config = load_config(resolve_config_path(home))
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
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        )
    finally:
        store.close()


def test_a_healthy_store_reports_chain_spool_and_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "chain" in out
    assert "entries verify" in out
    assert "spool" in out
    assert "keys" in out


def test_a_tampered_chain_turns_doctor_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute("UPDATE audit SET payload_digest = ? WHERE seq = 1", ("0" * 64,))
    connection.commit()
    connection.close()

    assert main(["--home", str(home), "doctor"]) == 4
    out = capsys.readouterr().out
    assert "chain" in out
    assert "seq 1" in out


def test_staging_files_are_a_warning_not_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    staging = home / "spool" / "tmp"
    staging.mkdir(parents=True)
    (staging / "half.tmp").write_text("x", encoding="utf-8")
    (home / "spool" / "locks" / "bus.lock").write_text("", encoding="utf-8")

    assert main(["--home", str(home), "doctor"]) == 0
    assert "staging" in capsys.readouterr().out


def test_a_missing_producer_key_is_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    path = home / "config.toml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[producers.agentpolicy]\nkey_ref = "env:NO_SUCH_KEY"\n',
        encoding="utf-8",
    )

    assert main(["--home", str(home), "doctor"]) == 4
    out = capsys.readouterr().out
    assert "keys" in out
    assert "NO_SUCH_KEY" in out


def test_the_healthy_path_is_under_two_seconds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)

    started = time.monotonic()
    assert main(["--home", str(home), "doctor"]) == 0
    elapsed = time.monotonic() - started

    assert elapsed < 2.0
    capsys.readouterr()
