"""Service units, daemon lock, and fail-closed shutdown (M21 item 21.1)."""

from __future__ import annotations

import os
import plistlib
import signal
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path
from agentinbox.exit_codes import ExitCode
from agentinbox.gate import gate
from agentinbox.ops import (
    OpsError,
    clear_daemon_lock,
    daemon_alive,
    install_service,
    read_daemon_lock,
    write_daemon_lock,
)
from agentinbox.store import AskStatus, utcnow
from agentinbox.store.loader import load_store
from agentinbox.store.sqlite import SqliteStore
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def test_launchd_unit_is_user_scoped_and_parses(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config_path = resolve_config_path(home)

    unit = install_service(home, config_path, platform="darwin")

    assert unit.path == home / "Library" / "LaunchAgents" / "com.agentsec.agentinbox.plist"
    assert unit.path.exists()
    assert unit.path.stat().st_mode & 0o777 == 0o600
    assert unit.path.parent.stat().st_mode & 0o777 == 0o700

    document = plistlib.loads(unit.path.read_bytes())
    assert document["Label"] == "com.agentsec.agentinbox"
    arguments = document["ProgramArguments"]
    assert arguments[1:] == [
        "-m",
        "agentinbox",
        "--home",
        str(home),
        "--config",
        str(config_path),
        "serve",
    ]
    assert Path(arguments[0]).is_absolute()
    assert document["RunAtLoad"] is True
    assert document["KeepAlive"] is False
    assert str(home / "logs" / "serve.log") == document["StandardOutPath"]
    assert str(home / "logs" / "serve.err") == document["StandardErrorPath"]
    assert "sudo" not in unit.content
    assert "root" not in unit.content


def test_systemd_unit_is_user_scoped(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config_path = resolve_config_path(home)

    unit = install_service(home, config_path, platform="linux")

    assert unit.path == home / ".config" / "systemd" / "user" / "agentinbox.service"
    assert unit.path.stat().st_mode & 0o777 == 0o600
    text = unit.content
    assert "[Unit]" in text
    assert "[Service]" in text
    assert "[Install]" in text
    assert "ExecStart=" in text
    assert "-m agentinbox" in text
    assert f"--home {home}" in text
    assert f"--config {config_path}" in text
    assert "serve" in text
    assert "Restart=on-failure" in text
    assert "KillSignal=SIGTERM" in text
    assert "WantedBy=default.target" in text
    assert "sudo" not in text


def test_unsupported_platform_refuses(tmp_path: Path) -> None:
    home = make_home(tmp_path)

    with pytest.raises(OpsError, match="Windows"):
        install_service(home, resolve_config_path(home), platform="win32")


def test_cli_serve_install_writes_the_unit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "serve", "--install"]) == 0
    out = capsys.readouterr().out
    assert "agentinbox" in out
    assert (home / "Library" / "LaunchAgents").exists() or (
        home / ".config" / "systemd" / "user"
    ).exists()


def test_restart_adopts_pending_asks_and_expires_overdue(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    moment = utcnow() - timedelta(hours=2)
    store = load_store("sqlite", home=home)
    try:
        from agentinbox.config import load_config
        from agentinbox.ingest import ingest
        from agentinbox.trust import ProducerIdentity

        ask = ingest(
            payload(
                expires_at=(moment + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=load_config(resolve_config_path(home)),
            producer=ProducerIdentity.unauthenticated(),
            now=moment,
        ).ask
    finally:
        store.close()

    assert main(["--home", str(home), "serve", "--once"]) == 0

    restored = load_store("sqlite", home=home)
    try:
        loaded = restored.get(ask.ask_id)
        assert loaded is not None
        assert loaded.status is AskStatus.EXPIRED
    finally:
        restored.close()


def test_daemon_lock_round_trip_and_liveness(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    assert read_daemon_lock(home) is None
    assert daemon_alive(home) is False

    lock = write_daemon_lock(home)
    try:
        assert lock.pid == os.getpid()
        assert read_daemon_lock(home) is not None
        assert daemon_alive(home) is True
    finally:
        clear_daemon_lock(home)

    assert read_daemon_lock(home) is None


def test_a_stale_lock_is_not_alive(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    path = home / "serve.lock"
    path.write_text('{"pid": 999999999, "started_at": "2026-11-07T00:00:00Z"}', encoding="utf-8")

    assert daemon_alive(home) is False


def test_serve_writes_and_removes_the_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = make_home(tmp_path)
    seen: list[bool] = []

    class FakeBus:
        def run(self, handler, stop) -> None:  # type: ignore[no-untyped-def]
            seen.append(read_daemon_lock(home) is not None)
            raise KeyboardInterrupt

        def consume(self, handler) -> int:  # type: ignore[no-untyped-def]
            return 0

        def close(self) -> None:
            return None

    monkeypatch.setattr("agentinbox.cli.load_bus", lambda *a, **k: FakeBus())
    assert main(["--home", str(home), "serve", "--no-api"]) == 0

    assert seen == [True]
    assert read_daemon_lock(home) is None


def test_gate_fails_closed_when_the_daemon_is_gone(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    store = load_store("sqlite", home=home)
    try:
        assert isinstance(store, SqliteStore)
        now = utcnow()
        body = payload(
            expires_at=(now + timedelta(minutes=5))
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
        )
        from agentinbox.config import load_config
        from agentinbox.ingest import ingest
        from agentinbox.trust import ProducerIdentity

        result = ingest(
            body,
            store=store,
            config=load_config(resolve_config_path(home)),
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        )
        outcome = gate(
            store,
            result.ask.ask_id,
            wait=True,
            timeout=5,
            daemon_alive=lambda: False,
        )
        assert outcome.code is ExitCode.UNAVAILABLE
    finally:
        store.close()


def test_gate_cli_refuses_a_stale_daemon_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    now = utcnow()
    store = load_store("sqlite", home=home)
    try:
        from agentinbox.config import load_config
        from agentinbox.ingest import ingest
        from agentinbox.trust import ProducerIdentity

        result = ingest(
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
        ask_id = result.ask.ask_id
    finally:
        store.close()

    (home / "serve.lock").write_text(
        '{"pid": 999999999, "started_at": "2026-11-07T00:00:00Z"}', encoding="utf-8"
    )
    assert main(["--home", str(home), "gate", "--ask", ask_id, "--wait", "--timeout", "1"]) == 4
    assert "unavailable" in capsys.readouterr().err.lower()


def test_serve_stops_on_sigterm_and_removes_the_lock(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "agentinbox",
            "--home",
            str(home),
            "serve",
            "--no-api",
        ],
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and read_daemon_lock(home) is None:
            time.sleep(0.05)
        assert read_daemon_lock(home) is not None, "serve did not start"

        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=15)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert process.returncode == 0, (stdout, stderr)
    assert read_daemon_lock(home) is None
