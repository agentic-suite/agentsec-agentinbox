"""Input/log/permission sweep and no approval shortcut (M22 item 22.5)."""

from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path

import pytest

from agentinbox.cli import build_parser, main
from agentinbox.config import init_home, resolve_config_path
from agentinbox.contract import ContractError
from agentinbox.ingest import ingest
from agentinbox.logsafe import sanitize_log_line
from agentinbox.ops import install_service
from agentinbox.store import utcnow
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import config, payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def test_control_characters_and_ansi_are_stripped() -> None:
    hostile = "line1\nFORGED LOG ENTRY\r\x1b[31mred\x1b[0m\x00"

    cleaned = sanitize_log_line(hostile)

    assert "\n" not in cleaned
    assert "\r" not in cleaned
    assert "\x1b" not in cleaned
    assert "\x00" not in cleaned
    assert cleaned.startswith("line1 FORGED LOG ENTRY")


def test_cli_parse_errors_stay_on_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bad\nINJECTED"]) == 1
    err = capsys.readouterr().err
    assert "\nINJECTED" not in err
    assert "INJECTED" in err


def test_creation_paths_force_private_modes_under_a_permissive_umask(tmp_path: Path) -> None:
    previous = os.umask(0)
    try:
        home = make_home(tmp_path)
        assert stat.S_IMODE(home.stat().st_mode) == 0o700
        assert stat.S_IMODE((home / "config.toml").stat().st_mode) == 0o600

        store = load_store("sqlite", home=home)
        store.close()
        assert stat.S_IMODE((home / "inbox.db").stat().st_mode) == 0o600

        unit = install_service(home, resolve_config_path(home), platform="darwin")
        assert stat.S_IMODE(unit.path.stat().st_mode) == 0o600
        assert stat.S_IMODE(unit.path.parent.stat().st_mode) == 0o700
    finally:
        os.umask(previous)


def collected_options() -> dict[str, set[str]]:
    parser = build_parser()
    group = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return {
        name: {option for action in sub._actions for option in action.option_strings}
        for name, sub in group.choices.items()
    }


def test_no_yes_flag_and_only_the_documented_force_flags() -> None:
    options = collected_options()
    assert all("--yes" not in values for values in options.values())
    force = {name for name, values in options.items() if "--force" in values}
    assert force == {"init", "doctor"}


def test_oversized_input_rejects_and_stores_nothing() -> None:
    store = MemoryStore()
    try:
        oversized = payload(arguments={"command": "x" * (300 * 1024)})
        with pytest.raises(ContractError):
            ingest(
                oversized,
                store=store,
                config=config(),
                producer=ProducerIdentity.unauthenticated(),
                now=utcnow(),
            )
        assert store.audit_entries() == []
    finally:
        store.close()
