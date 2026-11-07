"""Backup and restore: WAL-safe evidence, no secrets, chain-verified (M21 item 21.2)."""

from __future__ import annotations

import io
import json
import sqlite3
import tarfile
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.audit import read_audit_entries
from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.ops import OpsError, backup_home, restore_home
from agentinbox.store import AskStatus, utcnow, verify_audit_chain
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path, name: str = "home") -> Path:
    home = tmp_path / name
    init_home(home, resolve_config_path(home))
    return home


def seed(
    home: Path,
    *,
    status: AskStatus | None = None,
    now=None,  # type: ignore[no-untyped-def]
    session: str = "sess_m21",
    command: str = "psql prod -c 'DROP TABLE customers'",
) -> str:
    moment = now or utcnow()
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    try:
        ask = ingest(
            payload(
                session_id=session,
                arguments={"command": command, "timeout_s": 30},
                expires_at=(moment + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=moment,
        ).ask
        if status is not None:
            from agentinbox.lifecycle import transition

            assert transition(
                store,
                ask.ask_id,
                status,
                kind="answered",
                at=moment,
                principal="alice",
                channel="terminal",
            )
    finally:
        store.close()
    return ask.ask_id


def test_backup_then_restore_verifies_the_chain(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    approved = seed(home, status=AskStatus.APPROVED)
    pending = seed(home, session="sess_pending", command="echo pending")
    out = tmp_path / "backup.tar"

    result = backup_home(home, out)
    assert out.exists()
    assert out.stat().st_mode & 0o777 == 0o600
    assert result.asks == 2
    assert result.chain_head

    fresh = tmp_path / "restored"
    restored = restore_home(out, fresh)

    assert restored.asks == 2
    assert (fresh / "inbox.db").stat().st_mode & 0o777 == 0o600
    assert (fresh / "config.toml").stat().st_mode & 0o777 == 0o600
    assert (fresh / "inbox.db").exists()
    entries = read_audit_entries(fresh / "inbox.db")
    verify_audit_chain(entries)
    assert entries[-1].entry_hash == result.chain_head

    store = load_store("sqlite", home=fresh)
    try:
        assert store.get(approved) is not None
        assert store.get(approved).status is AskStatus.APPROVED  # type: ignore[union-attr]
        assert store.get(pending) is not None
        assert store.get(pending).status is AskStatus.PENDING  # type: ignore[union-attr]
    finally:
        store.close()


def test_backup_contains_no_secret_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = make_home(tmp_path)
    secret = "super-secret-hmac-value"
    monkeypatch.setenv("TEST_HMAC_KEY", secret)
    config_path = resolve_config_path(home)
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + '\n[producers.agentpolicy]\nkey_ref = "env:TEST_HMAC_KEY"\n',
        encoding="utf-8",
    )
    (home / "keys" / "signing.key").write_text(secret, encoding="utf-8")
    (home / "api-token").write_text(secret, encoding="utf-8")
    seed(home)
    out = tmp_path / "backup.tar"

    backup_home(home, out)

    archive = out.read_bytes()
    assert secret.encode() not in archive
    with tarfile.open(out) as tar:
        names = set(tar.getnames())
        slots = json.loads(tar.extractfile("keys/slots.json").read())  # type: ignore[union-attr]
        assert slots["producers"]["agentpolicy"] == "env:TEST_HMAC_KEY"
    assert "api-token" not in names
    assert "keys/signing.key" not in names


def test_restore_refuses_a_tampered_chain(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    with tarfile.open(out) as tar:
        members = {member.name: tar.extractfile(member).read() for member in tar.getmembers()}  # type: ignore[union-attr]
    database = tmp_path / "tampered.db"
    database.write_bytes(members["inbox.db"])
    connection = sqlite3.connect(database)
    connection.execute("UPDATE audit SET payload_digest = ? WHERE seq = 1", ("0" * 64,))
    connection.commit()
    connection.close()

    tampered = tmp_path / "tampered.tar"
    with tarfile.open(tampered, "w") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(database.read_bytes() if name == "inbox.db" else data)
            payload_bytes = database.read_bytes() if name == "inbox.db" else data
            tar.addfile(info, io.BytesIO(payload_bytes))

    fresh = tmp_path / "restored"
    with pytest.raises(OpsError, match="chain"):
        restore_home(tampered, fresh)
    assert not fresh.exists() or not any(fresh.iterdir())


def test_restore_never_resurrects_an_expired_ask(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    moment = utcnow() - timedelta(hours=2)
    expired = seed(home, now=moment)
    approved = seed(
        home, status=AskStatus.APPROVED, now=moment, session="sess_approved"
    )
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    fresh = tmp_path / "restored"
    restore_home(out, fresh)

    store = load_store("sqlite", home=fresh)
    try:
        expired_ask = store.get(expired)
        approved_ask = store.get(approved)
        assert expired_ask is not None
        assert expired_ask.status is AskStatus.EXPIRED
        assert approved_ask is not None
        assert approved_ask.status is AskStatus.APPROVED
    finally:
        store.close()


def test_restore_refuses_a_non_empty_home(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"
    backup_home(home, out)

    fresh = tmp_path / "restored"
    fresh.mkdir()
    (fresh / "keep.txt").write_text("do not clobber", encoding="utf-8")

    with pytest.raises(OpsError, match="not empty"):
        restore_home(out, fresh)
    assert (fresh / "keep.txt").read_text(encoding="utf-8") == "do not clobber"


def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, "w") as tar:
        info = tarfile.TarInfo("../escape.txt")
        data = b"escape"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    with pytest.raises(OpsError, match="member"):
        restore_home(archive, tmp_path / "restored")
    assert not (tmp_path / "escape.txt").exists()


def test_backup_refuses_a_corrupt_chain(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    connection = sqlite3.connect(home / "inbox.db")
    connection.execute("UPDATE audit SET payload_digest = ? WHERE seq = 1", ("0" * 64,))
    connection.commit()
    connection.close()

    with pytest.raises(OpsError, match="chain"):
        backup_home(home, tmp_path / "backup.tar")


def test_cli_backup_and_restore(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = make_home(tmp_path)
    seed(home)
    out = tmp_path / "backup.tar"

    assert main(["--home", str(home), "doctor", "--backup", str(out)]) == 0
    assert out.exists()
    capsys.readouterr()

    fresh = tmp_path / "restored"
    assert main(["--home", str(fresh), "doctor", "--restore", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "chain" in printed
    assert "entries verify" in printed
