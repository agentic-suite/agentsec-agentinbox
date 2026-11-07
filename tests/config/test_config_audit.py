"""Config governance: digested ``inbox-config-changed`` evidence (M11 item 11.5)."""

from __future__ import annotations

import json
from pathlib import Path

from agentinbox.cli import main
from agentinbox.config import ClassConfig, Config, init_home, resolve_config_path
from agentinbox.config_audit import EVENT_KIND, policy_digest, record_config_change
from tests.ask.conftest import NOW


def events(home: Path) -> list[dict[str, object]]:
    path = home / "logs" / "inbox-config-changed.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_first_start_records_one_digested_event(tmp_path: Path) -> None:
    home = tmp_path
    config = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
    )

    digest = record_config_change(home, config, now=lambda: NOW)

    assert digest == policy_digest(config)
    assert len(digest) == 64
    recorded = events(home)
    assert len(recorded) == 1
    assert recorded[0]["kind"] == EVENT_KIND
    assert recorded[0]["digest"] == digest
    assert recorded[0]["previous"] is None
    assert (home / "logs" / "config-digest").read_text().strip() == digest
    assert (home / "logs" / "inbox-config-changed.jsonl").stat().st_mode & 0o777 == 0o600


def test_an_unchanged_config_does_not_re_emit(tmp_path: Path) -> None:
    home = tmp_path
    config = Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})

    assert record_config_change(home, config, now=lambda: NOW) is not None
    assert record_config_change(home, config, now=lambda: NOW) is None
    assert len(events(home)) == 1


def test_a_policy_change_emits_a_new_event(tmp_path: Path) -> None:
    home = tmp_path
    first = Config(classes={"irreversible": ClassConfig(ttl_seconds=300)})
    second = Config(classes={"irreversible": ClassConfig(ttl_seconds=600)})

    old = record_config_change(home, first, now=lambda: NOW)
    new = record_config_change(home, second, now=lambda: NOW)

    assert old is not None
    assert new is not None
    assert old != new
    recorded = events(home)
    assert len(recorded) == 2
    assert recorded[1]["previous"] == old
    assert recorded[1]["digest"] == new


def test_serve_records_the_config_once(tmp_path: Path) -> None:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))

    assert main(["--home", str(home), "serve", "--once"]) == 0
    assert main(["--home", str(home), "serve", "--once"]) == 0

    recorded = events(home)
    assert len(recorded) == 1
    assert recorded[0]["kind"] == EVENT_KIND
