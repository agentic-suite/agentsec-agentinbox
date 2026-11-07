"""``agentinbox init`` scaffold behavior (M0 items 0.2/0.4)."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import load_config


def test_init_creates_private_home_and_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"

    assert main(["--home", str(home), "init"]) == 0

    config_path = home / "config.toml"
    assert config_path.is_file()
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    assert "config.toml" in capsys.readouterr().out

    # The scaffold must be valid, not decorative.
    loaded = load_config(config_path)
    assert loaded.classes, "scaffold must include at least one ask class"


def test_init_refuses_to_overwrite_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    existing = home / "config.toml"
    existing.write_text("keep me", encoding="utf-8")

    assert main(["--home", str(home), "init"]) == 4
    assert "--force" in capsys.readouterr().err
    assert existing.read_text(encoding="utf-8") == "keep me"


def test_init_force_rewrites(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    existing = home / "config.toml"
    existing.write_text("broken", encoding="utf-8")

    assert main(["--home", str(home), "init", "--force"]) == 0
    assert "ttl_seconds" in existing.read_text(encoding="utf-8")


def test_init_rejects_relative_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["--home", "relative", "init"]) == 4


def test_init_honors_agentinbox_home_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "env-home"
    monkeypatch.setenv("AGENTINBOX_HOME", str(home))

    assert main(["init"]) == 0
    assert (home / "config.toml").is_file()
