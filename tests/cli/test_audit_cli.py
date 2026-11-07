"""``verify-log`` and ``export`` CLI wiring (M15 items 15.2/15.3)."""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.store import DeliveryRecord, utcnow
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload

ASK_ID = "ask_0123456789abcdef"
SESSION = "sess_20261106T030412Z"


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def seed(home: Path) -> None:
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    now = utcnow()
    try:
        ingest(
            payload(
                ask_id=ASK_ID,
                session_id=SESSION,
                expires_at=(now + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        )
        store.record_delivery(
            DeliveryRecord(
                delivery_id="delivery_1",
                ask_id=ASK_ID,
                channel="terminal",
                attempt=1,
                status="delivered",
                at=now,
            )
        )
    finally:
        store.close()


def test_verify_log_on_a_fresh_store(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "verify-log"]) == 0
    assert "ok: 0 audit entries verify" in capsys.readouterr().out


def test_verify_log_after_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    assert main(["--home", str(home), "verify-log"]) == 0
    assert "audit entries verify" in capsys.readouterr().out


def test_verify_log_detects_tampering(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute("UPDATE audit SET payload_digest = ? WHERE seq = 2", ("0" * 64,))
    connection.commit()
    connection.close()

    assert main(["--home", str(home), "verify-log"]) == 4
    assert "seq 2" in capsys.readouterr().err


def test_verify_log_detects_a_corrupt_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute("UPDATE audit SET payload = '{not json' WHERE seq = 2")
    connection.commit()
    connection.close()

    assert main(["--home", str(home), "verify-log"]) == 4
    assert "corrupt" in capsys.readouterr().err


def test_verify_log_detects_a_payload_body_edit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute(
        "UPDATE audit SET payload = ? WHERE seq = 2", (json.dumps({"x": 1}),)
    )
    connection.commit()
    connection.close()

    assert main(["--home", str(home), "verify-log"]) == 4
    assert "seq 2" in capsys.readouterr().err


def test_export_jsonl_by_session(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)

    assert main(["--home", str(home), "export", "--session", SESSION]) == 0
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines[0]["contract"] == "export/1.0"
    assert any(line["type"] == "ask" and line["ask_id"] == ASK_ID for line in lines)
    assert any(line["type"] == "audit" for line in lines)

    store = load_store("sqlite", home=home)
    try:
        assert store.audit_entries()[-1].kind == "export"
    finally:
        store.close()


def test_export_csv_by_ask(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path)
    seed(home)

    assert main(["--home", str(home), "export", "--ask", ASK_ID, "--format", "csv"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("record_type,")
    assert ASK_ID in out


def test_export_to_a_private_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    destination = tmp_path / "evidence.jsonl"

    assert (
        main(
            [
                "--home",
                str(home),
                "export",
                "--session",
                SESSION,
                "--out",
                str(destination),
            ]
        )
        == 0
    )
    assert "wrote" in capsys.readouterr().out
    assert destination.stat().st_mode & 0o777 == 0o600
    assert '"contract":"export/1.0"' in destination.read_text(encoding="utf-8")


def test_export_requires_exactly_one_scope(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "export"]) == 1
    assert (
        main(
            [
                "--home",
                str(home),
                "export",
                "--session",
                SESSION,
                "--ask",
                ASK_ID,
            ]
        )
        == 1
    )


def test_export_of_an_unknown_ask_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "export", "--ask", "ask_missing"]) == 4
    assert "unknown ask" in capsys.readouterr().err


def test_export_with_a_relative_out_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    seed(home)
    assert (
        main(
            [
                "--home",
                str(home),
                "export",
                "--session",
                SESSION,
                "--out",
                "relative.jsonl",
            ]
        )
        == 1
    )
    assert "absolute" in capsys.readouterr().err
