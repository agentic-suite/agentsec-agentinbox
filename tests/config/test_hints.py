"""Rescope-hint config validation (M17 item 17.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, load_config


def write(tmp_path: Path, hint: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(
        f"""
[classes.irreversible]
ttl_seconds = 300
{hint}
""",
        encoding="utf-8",
    )
    return path


def test_a_hint_is_parsed(tmp_path: Path) -> None:
    parsed = load_config(write(tmp_path, 'rescope_hint = "use db:staging"'))
    assert parsed.classes["irreversible"].rescope_hint == "use db:staging"


@pytest.mark.parametrize(
    ("hint", "message"),
    [
        ('rescope_hint = ""', "non-empty"),
        ('rescope_hint = "line\\nbreak"', "control"),
        ('rescope_hint = "' + "x" * 600 + '"', "512"),
        ("rescope_hint = 3", "non-empty"),
    ],
)
def test_invalid_hints_refuse(tmp_path: Path, hint: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, hint))
