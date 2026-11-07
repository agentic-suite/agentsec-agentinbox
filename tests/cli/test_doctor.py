"""``agentinbox doctor`` checks (M0 item 0.6).

``doctor`` must return ``0`` on a healthy fresh install and name every failing check, exit
``4``. Checks are the M0 set from the design doc §6 and grow in M1/M20/M21.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    return home


def test_healthy_fresh_install_returns_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    for check in ("platform", "home", "config", "store-path", "schema", "clock"):
        assert check in out


def test_missing_home_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--home", str(tmp_path / "absent"), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "home" in captured.out + captured.err
    assert "init" in captured.out + captured.err


def test_missing_config_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir(mode=0o700)

    assert main(["--home", str(home), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "config" in captured.out + captured.err


def test_invalid_config_names_the_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    (home / "config.toml").write_text("[classes.x]\nttl_seconds = 0\n", encoding="utf-8")

    assert main(["--home", str(home), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "ttl_seconds" in captured.out + captured.err


def test_world_readable_store_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    database = home / "inbox.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (1)")
    database.chmod(0o644)

    assert main(["--home", str(home), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "inbox.db" in captured.out + captured.err


def test_store_with_schema_version_is_healthy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    database = home / "inbox.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (1)")
    database.chmod(0o600)

    assert main(["--home", str(home), "doctor"]) == 0
    assert "schema" in capsys.readouterr().out


def test_non_database_store_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    database = home / "inbox.db"
    database.write_text("not a database", encoding="utf-8")
    database.chmod(0o600)

    assert main(["--home", str(home), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "schema" in captured.out + captured.err


def test_explain_prints_effective_config_without_resolving_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTINBOX_WEBHOOK_URL", "https://hooks.example/abc")
    home = make_home(tmp_path)
    (home / "config.toml").write_text(
        """
[classes.irreversible]
ttl_seconds = 300

[channels.webhook]
enabled = true
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
""",
        encoding="utf-8",
    )

    assert main(["--home", str(home), "doctor", "--explain"]) == 0
    out = capsys.readouterr().out
    assert "env:AGENTINBOX_WEBHOOK_URL" in out
    assert "sqlite" in out


def test_json_output_is_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--json", "--home", str(home), "doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {item["id"] for item in payload} >= {"platform", "home", "config", "clock"}


def test_windows_is_named_as_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from agentinbox import doctor

    home = make_home(tmp_path)
    monkeypatch.setattr(doctor.sys, "platform", "win32")

    assert main(["--home", str(home), "doctor"]) == 4
    captured = capsys.readouterr()
    assert "Windows" in captured.out + captured.err


def test_unwritable_home_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    home.chmod(0o500)
    try:
        assert main(["--home", str(home), "doctor"]) == 4
        captured = capsys.readouterr()
        assert "home" in captured.out + captured.err
    finally:
        home.chmod(0o700)
