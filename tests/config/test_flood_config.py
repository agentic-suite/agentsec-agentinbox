"""Flood thresholds are security-relevant config (M12 item 12.2/12.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, load_config
from agentinbox.doctor import Report, render_explain


def write(tmp_path: Path, extra: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(
        f"""
[classes.irreversible]
ttl_seconds = 300
{extra}

[throttle]
per_agent_burst = 10
per_agent_rate_per_min = 5
flood_window_seconds = 30
""",
        encoding="utf-8",
    )
    return path


def test_class_overrides_are_parsed(tmp_path: Path) -> None:
    parsed = load_config(
        write(tmp_path, "flood_burst = 2\nflood_rate_per_min = 1")
    )
    ask_class = parsed.classes["irreversible"]
    assert ask_class.flood_burst == 2
    assert ask_class.flood_rate_per_min == 1


@pytest.mark.parametrize("value", ["0", "-1"])
def test_non_positive_thresholds_refuse(tmp_path: Path, value: str) -> None:
    with pytest.raises(ConfigError, match="flood_burst"):
        load_config(write(tmp_path, f"flood_burst = {value}"))


def test_doctor_explains_the_effective_thresholds(tmp_path: Path) -> None:
    path = write(tmp_path, "flood_burst = 2")
    parsed = load_config(path)
    text = render_explain(Report(checks=(), config=parsed), tmp_path, path)

    assert text is not None
    assert "throttle: burst=10 rate_per_min=5 window=30s" in text
    assert "flood_burst=2" in text
    assert "flood_rate_per_min=5" in text
