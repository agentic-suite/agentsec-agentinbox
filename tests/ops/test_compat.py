"""Compatibility matrix and forward migrations (M21 item 21.3)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agentinbox import compat
from agentinbox.events.base import EVENT_TYPES, EVENT_VERSION
from agentinbox.exit_codes import ExitCode
from agentinbox.store import SchemaVersionError
from agentinbox.store.sqlite import MIGRATIONS, SCHEMA_VERSION, SqliteStore


def test_contract_versions_are_frozen() -> None:
    matrix = compat.compatibility_matrix()

    assert matrix["contracts"] == {
        "ask": "ask/1.0",
        "resolve": "resolve/1.0",
        "webhook": "webhook/1.0",
        "export": "export/1.0",
        "backup": "backup/1.0",
        "report": "report/1.0",
    }
    assert matrix["event_version"] == EVENT_VERSION == "0.2.0"


def test_exit_codes_match_the_reserved_contract() -> None:
    matrix = compat.compatibility_matrix()

    assert matrix["exit_codes"] == {
        0: "approved",
        1: "usage",
        2: "denied",
        3: "expired",
        4: "unavailable",
        5: "pending",
    }
    assert {int(code): code.name.lower() for code in ExitCode} == matrix["exit_codes"]
    assert matrix["approval_code"] == 0


def test_the_event_vocabulary_never_shrinks() -> None:
    matrix = compat.compatibility_matrix()
    frozen = compat.FROZEN_EVENTS

    assert set(frozen) <= set(matrix["events"])
    assert set(matrix["events"]) == set(EVENT_TYPES)
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "agentinbox"
            / "events"
            / "security-event.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert set(schema["properties"]["event_type"]["enum"]) == set(matrix["events"])


def test_migrations_cover_every_version_without_gaps() -> None:
    assert set(MIGRATIONS) == set(range(SCHEMA_VERSION))
    for version, statements in MIGRATIONS.items():
        assert statements, f"migration {version} is empty"
        assert all(statement.strip() for statement in statements), f"migration {version} blank"


def build_store_at(path: Path, version: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        for step in range(version):
            for statement in MIGRATIONS[step]:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (step + 1,)
            )
    path.chmod(0o600)


@pytest.mark.parametrize("version", range(SCHEMA_VERSION + 1))
def test_every_released_schema_version_migrates_forward(tmp_path: Path, version: int) -> None:
    path = tmp_path / f"v{version}" / "inbox.db"
    build_store_at(path, version)

    store = SqliteStore(path)
    try:
        store.verify_chain()
    finally:
        store.close()

    with sqlite3.connect(path) as connection:
        current = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert current == SCHEMA_VERSION


def test_downgrade_refuses_loudly(tmp_path: Path) -> None:
    path = tmp_path / "inbox.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute(
            "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION + 1,)
        )
    path.chmod(0o600)

    with pytest.raises(SchemaVersionError, match="downgrade"):
        SqliteStore(path)


def test_the_matrix_detects_a_breaking_change() -> None:
    current = compat.compatibility_matrix()
    assert compat.additive_violations(current, current) == []

    removed_event = dict(current)
    removed_event["events"] = [event for event in current["events"] if event != "ask-flood"]
    violations = compat.additive_violations(current, removed_event)
    assert any("ask-flood" in violation for violation in violations)

    changed_code = dict(current)
    changed_code["exit_codes"] = {**current["exit_codes"], 0: "denied"}
    violations = compat.additive_violations(current, changed_code)
    assert any("exit code 0" in violation for violation in violations)


def test_the_matrix_detects_contract_event_and_schema_drift() -> None:
    current = compat.compatibility_matrix()

    changed_contract = dict(current)
    changed_contract["contracts"] = {**current["contracts"], "ask": "ask/2.0"}
    assert any(
        "contract ask" in violation
        for violation in compat.additive_violations(current, changed_contract)
    )

    changed_event_version = dict(current)
    changed_event_version["event_version"] = "1.0.0"
    assert any(
        "event version" in violation
        for violation in compat.additive_violations(current, changed_event_version)
    )

    older_schema = dict(current)
    older_schema["schema_version"] = 0
    assert any(
        "schema version" in violation
        for violation in compat.additive_violations(current, older_schema)
    )
