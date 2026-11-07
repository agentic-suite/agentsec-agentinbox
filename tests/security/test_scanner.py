"""Evidence scanner: clean artifacts pass, seeded leaks fail (M22 item 22.1)."""

from __future__ import annotations

import io
import json
import sqlite3
import tarfile
from datetime import timedelta
from pathlib import Path

from agentinbox.audit import export_jsonl, export_records
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.scanner import (
    main as scanner_main,
)
from agentinbox.scanner import (
    scan_archive,
    scan_artifacts,
    scan_store,
    scan_text,
    self_test,
    store_artifacts_from_db,
)
from agentinbox.store import AskRecord, DeliveryRecord, utcnow
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload

SECRET = "ghp_" + "a" * 24


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def seed(home: Path, *, secret: str | None = None) -> None:
    now = utcnow()
    body = payload(
        arguments={"command": f"psql {secret or 'prod'}", "timeout_s": 30},
        context={"note": f"use {secret or 'nothing'} carefully"},
        expires_at=(now + timedelta(minutes=5))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
    )
    store = load_store("sqlite", home=home)
    try:
        ingest(
            body,
            store=store,
            config=load_config(resolve_config_path(home)),
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        )
    finally:
        store.close()


def test_self_test_passes_clean_and_detects_the_seeded_leak() -> None:
    clean, seeded = self_test()

    assert clean.ok, clean.findings
    assert not seeded.ok
    rules = {finding.rule for finding in seeded.findings}
    assert {"SECRET", "PRIVATE_KEY", "CONNECTION_STRING"} <= rules


def test_clean_store_renders_and_audit_exports_have_zero_findings(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home, secret=SECRET)  # redaction must strip it before storage
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    try:
        report = scan_store(store, config)
        assert report.ok, report.findings
        ask_id = store.list_pending(now=utcnow())[0].ask_id
        store.record_delivery(
            DeliveryRecord(
                delivery_id="del_scan",
                ask_id=ask_id,
                channel="terminal",
                attempt=1,
                status="delivered",
                at=utcnow(),
                target="terminal",
            )
        )
        assert scan_store(store, config).ok
        exported = export_jsonl(export_records(store, ask_id=ask_id))
    finally:
        store.close()

    assert scan_text(exported, artifact="export").ok


def test_a_raw_secret_written_directly_is_found() -> None:
    store = MemoryStore()
    try:
        store.create_or_get_by_identity(
            AskRecord(
                ask_id="ask_raw",
                action_identity="sha256:raw",
                session_id="sess_raw",
                agent_id="agent://raw",
                created_at=utcnow(),
                expires_at=utcnow() + timedelta(minutes=5),
                payload={"context": {"token": SECRET}},
            )
        )
        report = scan_store(store, config=None)  # type: ignore[arg-type]
    finally:
        store.close()

    assert not report.ok
    assert any(
        finding.rule == "SECRET" and "ask:ask_raw" in finding.artifact
        for finding in report.findings
    )


def test_db_scan_is_read_only_and_clean(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    seed(home)
    before = (home / "inbox.db").stat().st_mtime_ns

    artifacts = store_artifacts_from_db(home / "inbox.db")
    report = scan_artifacts(artifacts)

    assert report.ok, report.findings
    assert (home / "inbox.db").stat().st_mtime_ns == before


def test_backup_archive_is_clean_and_a_seeded_archive_fails(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    home = make_home(tmp_path)
    secret_value = "super-secret-hmac"
    config_path = resolve_config_path(home)
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + '\n[producers.agentpolicy]\nkey_ref = "env:SCAN_KEY"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("SCAN_KEY", secret_value)
    seed(home)
    from agentinbox.ops import backup_home

    archive = tmp_path / "backup.tar"
    backup_home(home, archive)
    assert scan_archive(archive).ok

    bad = tmp_path / "bad.tar"
    with tarfile.open(bad, "w") as tar:
        body = f"token {SECRET}".encode()
        info = tarfile.TarInfo("member.txt")
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    assert not scan_archive(bad).ok


def test_cli_self_test_and_home_scan(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert scanner_main(["--self-test"]) == 0
    assert "seeded" in capsys.readouterr().out

    home = make_home(tmp_path)
    seed(home)
    assert scanner_main(["--home", str(home)]) == 0
    assert "0 finding" in capsys.readouterr().out

    with sqlite3.connect(home / "inbox.db") as connection:
        connection.execute(
            "UPDATE asks SET payload = ? WHERE ask_id = (SELECT ask_id FROM asks LIMIT 1)",
            (json.dumps({"context": {"token": SECRET}}),),
        )
    assert scanner_main(["--home", str(home)]) == 1
    assert "SECRET" in capsys.readouterr().err


def test_scanner_cli_requires_a_target_and_tolerates_absent_inputs(
    tmp_path: Path, capsys
) -> None:  # type: ignore[no-untyped-def]
    assert scanner_main([]) == 1
    assert "pass --home" in capsys.readouterr().err

    absent = tmp_path / "absent"
    assert scanner_main(["--home", str(absent)]) == 0
    assert "0 finding" in capsys.readouterr().out

    bad = tmp_path / "bad.tar"
    bad.write_bytes(b"not a tar")
    assert scanner_main(["--archive", str(bad)]) == 0
    assert scan_archive(bad).artifacts == 0
