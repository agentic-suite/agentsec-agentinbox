"""Ladder configuration: delays, roster resolution, and load-time refusals (M11 item 11.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import (
    ClassConfig,
    ConfigError,
    default_ladder_delays,
    effective_ladder_delays,
    load_config,
)

BASE = """
[classes.irreversible]
ttl_seconds = 600
warn_seconds = 60
ladder = ["tier-1", "on-call"]
{ladder_delays}

[roster.tier-1]
terminal = ["alice"]

[roster.on-call]
terminal = ["bob"]

[channels.terminal]
enabled = true
"""


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return path


def config(tmp_path: Path, *, delays: str = "") -> Path:
    return write(tmp_path, BASE.format(ladder_delays=delays))


def test_explicit_delays_are_parsed(tmp_path: Path) -> None:
    parsed = load_config(config(tmp_path, delays="ladder_delays = [0, 300]"))
    ask_class = parsed.classes["irreversible"]
    assert ask_class.ladder == ("tier-1", "on-call")
    assert ask_class.ladder_delays == (0, 300)


def test_defaults_spread_the_ladder_inside_the_ttl(tmp_path: Path) -> None:
    parsed = load_config(config(tmp_path))
    ask_class = parsed.classes["irreversible"]
    assert ask_class.ladder_delays == default_ladder_delays(2, 600)
    assert ask_class.ladder_delays == (0, 300)
    assert effective_ladder_delays(ask_class) == (0, 300)


@pytest.mark.parametrize(
    ("delays", "message"),
    [
        ("ladder_delays = [0]", "exactly 2"),
        ("ladder_delays = [1, 300]", "first tier must start at 0"),
        ("ladder_delays = [0, 0]", "strictly increasing"),
        ("ladder_delays = [0, 600]", "before the TTL"),
        ('ladder_delays = ["0", 300]', "integer seconds"),
    ],
)
def test_invalid_delays_refuse_at_load(tmp_path: Path, delays: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(config(tmp_path, delays=delays))


def test_delays_without_a_ladder_refuse(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
[classes.x]
ttl_seconds = 60
ladder_delays = [0]
""",
    )
    with pytest.raises(ConfigError, match="requires a non-empty ladder"):
        load_config(path)


def test_duplicate_tiers_refuse(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
[classes.x]
ttl_seconds = 60
ladder = ["tier-1", "tier-1"]
""",
    )
    with pytest.raises(ConfigError, match="unique"):
        load_config(path)


def test_a_missing_roster_tier_refuses(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
[classes.x]
ttl_seconds = 60
ladder = ["tier-1", "on-call"]

[roster.tier-1]
terminal = ["alice"]
""",
    )
    with pytest.raises(ConfigError, match=r"no \[roster.on-call\] entry"):
        load_config(path)


def test_an_empty_roster_tier_refuses(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        """
[classes.x]
ttl_seconds = 60
ladder = ["tier-1"]

[roster.tier-1]
""",
    )
    with pytest.raises(ConfigError, match="at least one channel"):
        load_config(path)


def test_doctor_explain_prints_the_effective_ladder(tmp_path: Path) -> None:
    from agentinbox.doctor import Report, render_explain

    path = config(tmp_path, delays="ladder_delays = [0, 300]")
    parsed = load_config(path)
    text = render_explain(Report(checks=(), config=parsed), tmp_path, path)

    assert text is not None
    assert "ladder=['tier-1', 'on-call']" in text
    assert "ladder_delays=[0, 300]" in text


def test_direct_class_config_falls_back_to_defaults() -> None:
    ask_class = ClassConfig(ttl_seconds=300, ladder=("tier-1", "on-call"))
    assert effective_ladder_delays(ask_class) == (0, 150)
    assert effective_ladder_delays(ClassConfig(ttl_seconds=300)) == ()
