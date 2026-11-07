"""Unroutable classes refuse at load (M13 item 13.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, load_config


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_an_enabled_channel_makes_the_class_routable(tmp_path: Path) -> None:
    parsed = load_config(
        write(
            tmp_path,
            """
[classes.irreversible]
ttl_seconds = 300
ladder = ["tier-1"]

[roster.tier-1]
terminal = ["alice"]

[channels.terminal]
enabled = true
""",
        )
    )
    assert "irreversible" in parsed.classes


def test_a_class_with_no_enabled_channel_refuses(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"irreversible.*enabled channel"):
        load_config(
            write(
                tmp_path,
                """
[classes.irreversible]
ttl_seconds = 300
ladder = ["tier-1"]

[roster.tier-1]
webhook = ["alice"]

[channels.webhook]
enabled = false
""",
            )
        )


def test_library_configs_without_channels_still_load(tmp_path: Path) -> None:
    parsed = load_config(
        write(
            tmp_path,
            """
[classes.irreversible]
ttl_seconds = 300
""",
        )
    )
    assert "irreversible" in parsed.classes


def test_a_disabled_tier_channel_is_named(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="desktop"):
        load_config(
            write(
                tmp_path,
                """
[classes.irreversible]
ttl_seconds = 900
ladder = ["on-call"]
ladder_delays = [0]

[roster.on-call]
desktop = ["bob"]

[channels.terminal]
enabled = true

[channels.desktop]
enabled = false
""",
            )
        )
