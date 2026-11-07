"""Operations edge cases: unit quoting, lock reads, restore refusals, and CLI fail-closed."""

from __future__ import annotations

import io
import json
import sqlite3
import tarfile
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox import ops
from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.ops import (
    OpsError,
    backup_home,
    daemon_alive,
    read_daemon_lock,
    render_service_unit,
    restore_home,
)
from agentinbox.store import utcnow
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path, name: str = "home") -> Path:
    home = tmp_path / name
    init_home(home, resolve_config_path(home))
    return home


def seed(home: Path) -> None:
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


def rewrite_member(archive: Path, name: str, data: bytes) -> None:
    with tarfile.open(archive) as tar:
        members = {
            member.name: tar.extractfile(member).read()  # type: ignore[union-attr]
            for member in tar.getmembers()
            if member.isfile()
        }
    members[name] = data
    with tarfile.open(archive, "w") as tar:
        for member_name, body in members.items():
            info = tarfile.TarInfo(member_name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))


def test_unit_render_refuses_relative_interpreters_and_unknown_platforms(
    tmp_path: Path,
) -> None:
    home = make_home(tmp_path)
    config_path = resolve_config_path(home)

    with pytest.raises(OpsError, match="absolute"):
        render_service_unit(home, config_path, platform="darwin", python="python3")
    with pytest.raises(OpsError, match="not supported"):
        render_service_unit(home, config_path, platform="freebsd")


def test_systemd_unit_quotes_paths_with_spaces(tmp_path: Path) -> None:
    home = make_home(tmp_path, name="home with space")

    unit = render_service_unit(home, resolve_config_path(home), platform="linux")

    assert f'--home "{home}"' in unit.content
    assert "ExecStart=" in unit.content


def test_malformed_and_negative_locks_are_absent(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    (home / "serve.lock").write_text("not json", encoding="utf-8")
    assert read_daemon_lock(home) is None

    (home / "serve.lock").write_text(
        '{"pid": -3, "started_at": "2026-11-07T00:00:00Z"}', encoding="utf-8"
    )
    assert read_daemon_lock(home) is None


def test_pid_permission_and_generic_errors_are_handled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = make_home(tmp_path)
    (home / "serve.lock").write_text(
        '{"pid": 123456, "started_at": "2026-11-07T00:00:00Z"}', encoding="utf-8"
    )

    def permission_error(_pid: int, _signal: int) -> None:
        raise PermissionError

    monkeypatch.setattr(ops.os, "kill", permission_error)
    assert daemon_alive(home) is True

    def generic_error(_pid: int, _signal: int) -> None:
        raise OSError

    monkeypatch.setattr(ops.os, "kill", generic_error)
    assert daemon_alive(home) is False


def test_backup_records_webhook_references(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config_path = resolve_config_path(home)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "[channels.webhook]\nenabled = false",
            '[channels.webhook]\nenabled = false\nurl_ref = "env:HOOK_URL"\n'
            'hmac_key_ref = "env:HOOK_KEY"',
        ),
        encoding="utf-8",
    )
    seed(home)
    out = tmp_path / "backup.tar"

    backup_home(home, out)

    with tarfile.open(out) as tar:
        slots = json.loads(tar.extractfile("keys/slots.json").read())  # type: ignore[union-attr]
    assert slots["channels"]["webhook"] == {
        "url_ref": "env:HOOK_URL",
        "hmac_key_ref": "env:HOOK_KEY",
    }


def test_backup_refuses_without_a_store(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    with pytest.raises(OpsError, match="no store"):
        backup_home(home, tmp_path / "backup.tar")


def test_backup_refuses_a_garbage_store(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    (home / "inbox.db").write_bytes(b"not a database")
    with pytest.raises(OpsError, match="unavailable"):
        backup_home(home, tmp_path / "backup.tar")


def test_backup_refuses_a_newer_schema(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    with sqlite3.connect(home / "inbox.db") as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (999)")
    with pytest.raises(OpsError, match="downgrade"):
        backup_home(home, tmp_path / "backup.tar")


def test_restore_force_replaces_a_non_empty_home(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    fresh = tmp_path / "restored"
    fresh.mkdir()
    (fresh / "old.txt").write_text("replace me", encoding="utf-8")

    restore_home(out, fresh, force=True)
    assert not (fresh / "old.txt").exists()
    assert (fresh / "inbox.db").exists()


def test_restore_refuses_a_home_that_is_a_file(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    target = tmp_path / "target"
    target.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OpsError, match="not a directory"):
        restore_home(out, target)


def test_restore_refuses_an_unreadable_archive(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar"
    archive.write_bytes(b"not a tar")
    with pytest.raises(OpsError, match="unreadable"):
        restore_home(archive, tmp_path / "restored")


def test_restore_refuses_a_non_object_manifest(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar"
    with tarfile.open(archive, "w") as tar:
        body = b"[]"
        info = tarfile.TarInfo("manifest.json")
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    with pytest.raises(OpsError, match="not an object"):
        restore_home(archive, tmp_path / "restored")


def test_restore_refuses_an_unknown_contract(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar"
    with tarfile.open(archive, "w") as tar:
        body = json.dumps({"contract": "backup/9.0"}).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    with pytest.raises(OpsError, match="unsupported backup contract"):
        restore_home(archive, tmp_path / "restored")


def test_restore_refuses_a_manifest_chain_head_mismatch(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    with tarfile.open(out) as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())  # type: ignore[union-attr]
    manifest["chain_head"] = "0" * 64
    rewrite_member(out, "manifest.json", json.dumps(manifest).encode())

    with pytest.raises(OpsError, match="chain verification failed"):
        restore_home(out, tmp_path / "restored")


def test_restore_refuses_a_missing_member(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    with tarfile.open(out) as tar:
        members = {
            member.name: tar.extractfile(member).read()  # type: ignore[union-attr]
            for member in tar.getmembers()
            if member.isfile()
        }
    del members["keys/slots.json"]
    with tarfile.open(out, "w") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))

    with pytest.raises(OpsError, match=r"missing keys/slots\.json"):
        restore_home(out, tmp_path / "restored")


def test_cli_backup_and_restore_errors_fail_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = make_home(tmp_path)
    assert main(["--home", str(empty), "doctor", "--backup", str(tmp_path / "x.tar")]) == 4
    assert "backup failed" in capsys.readouterr().err

    archive = tmp_path / "bad.tar"
    archive.write_bytes(b"not a tar")
    assert main(["--home", str(empty), "doctor", "--restore", str(archive)]) == 4
    assert "restore failed" in capsys.readouterr().err


def test_cli_serve_install_refuses_without_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    absent = tmp_path / "absent"
    assert main(["--home", str(absent), "serve", "--install"]) == 4
    assert "config" in capsys.readouterr().err.lower()


def test_gate_exception_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("agentinbox.cli.gate", explode)
    assert main(["--home", str(home), "gate", "--ask", "ask_any"]) == 4
    assert "gate unavailable" in capsys.readouterr().err


def test_verify_log_refuses_a_relative_home(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--home", "relative", "verify-log"]) == 4
    assert "home" in capsys.readouterr().err.lower()


def test_report_human_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path)
    seed(home)

    assert main(["--home", str(home), "report"]) == 0
    out = capsys.readouterr().out
    assert "asks: 1" in out
    assert "response p50/p99" in out
    assert "deny rate" in out or "expiries" in out
