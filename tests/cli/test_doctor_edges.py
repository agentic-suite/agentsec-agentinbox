"""Remaining ``doctor`` branches (M0 item 0.6)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from agentinbox import doctor
from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def test_home_path_that_is_a_file_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "not-a-dir"
    home.write_text("x", encoding="utf-8")

    assert main(["--home", str(home), "doctor"]) == 4
    assert "not a directory" in capsys.readouterr().out


def test_loose_home_permissions_warn_but_do_not_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    home.chmod(0o755)
    try:
        assert main(["--home", str(home), "doctor"]) == 0
        assert "warn home" in capsys.readouterr().out
    finally:
        home.chmod(0o700)


def test_empty_schema_version_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    database = home / "inbox.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    database.chmod(0o600)

    assert main(["--home", str(home), "doctor"]) == 4
    assert "schema_version is empty" in capsys.readouterr().out


def test_clock_exception_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> float:
        raise OSError("no clock")

    monkeypatch.setattr(doctor.time, "time", boom)

    check = doctor._clock()

    assert check.status == doctor.FAIL
    assert "unavailable" in check.detail


def test_insane_clock_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks: Iterator[float] = iter([10.0, 5.0])
    monkeypatch.setattr(doctor.time, "time", lambda: 1.0)
    monkeypatch.setattr(doctor.time, "monotonic", lambda: next(ticks))

    check = doctor._clock()

    assert check.status == doctor.FAIL
    assert "not sane" in check.detail


def test_explain_lists_roster_and_channels(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    (home / "config.toml").write_text(
        """
[classes.irreversible]
ttl_seconds = 300

[roster.tier-1]
terminal = ["alice"]

[channels.terminal]
enabled = true
""",
        encoding="utf-8",
    )

    assert main(["--home", str(home), "doctor", "--explain"]) == 0
    out = capsys.readouterr().out
    assert "roster tier-1" in out
    assert "channel terminal: enabled=True" in out


def test_explain_with_invalid_config_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    (home / "config.toml").write_text("[classes.x]\nttl_seconds = 0\n", encoding="utf-8")

    assert main(["--home", str(home), "doctor", "--explain"]) == 4
    assert "explain unavailable" in capsys.readouterr().out


def test_relative_home_is_a_doctor_usage_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--home", "relative", "doctor"]) == 4
    assert "absolute" in capsys.readouterr().err


def test_missing_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 1
    assert "required: COMMAND" in capsys.readouterr().err


def test_unknown_flag_after_real_command_is_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["version", "--bogus"]) == 1
    assert "unrecognized arguments" in capsys.readouterr().err
