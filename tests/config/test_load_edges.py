"""Remaining fail-closed branches of the config loader (M0 item 0.4)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agentinbox.config import ConfigError, load_config

MINIMAL = """
[classes.irreversible]
ttl_seconds = 300
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_config_path_that_is_a_directory_fails(tmp_path: Path) -> None:
    directory = tmp_path / "config.toml"
    directory.mkdir()

    with pytest.raises(ConfigError, match="directory"):
        load_config(directory)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read anything")
def test_unreadable_config_fails_with_reason(tmp_path: Path) -> None:
    path = write(tmp_path, MINIMAL)
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigError, match="cannot read"):
            load_config(path)
    finally:
        path.chmod(0o600)


def test_non_utf8_config_fails(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(ConfigError, match="UTF-8"):
        load_config(path)


def test_section_that_is_not_a_table_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="TOML table"):
        load_config(write(tmp_path, "classes = 1\n"))


def test_secret_looking_key_is_named_as_a_secret_error(tmp_path: Path) -> None:
    text = MINIMAL + '\n[channels.webhook]\ntoken = "abc123"\n'

    with pytest.raises(ConfigError, match="secrets must use"):
        load_config(write(tmp_path, text))


def test_warn_seconds_must_be_an_integer(tmp_path: Path) -> None:
    text = '[classes.x]\nttl_seconds = 60\nwarn_seconds = "soon"\n'

    with pytest.raises(ConfigError, match="warn_seconds"):
        load_config(write(tmp_path, text))


def test_require_reason_must_be_boolean(tmp_path: Path) -> None:
    text = '[classes.x]\nttl_seconds = 60\nrequire_reason_on_deny = "yes"\n'

    with pytest.raises(ConfigError, match="require_reason_on_deny"):
        load_config(write(tmp_path, text))


def test_ladder_must_be_a_list(tmp_path: Path) -> None:
    text = '[classes.x]\nttl_seconds = 60\nladder = "tier-1"\n'

    with pytest.raises(ConfigError, match="ladder"):
        load_config(write(tmp_path, text))


def test_roster_principals_must_be_strings(tmp_path: Path) -> None:
    text = MINIMAL + "\n[roster.tier-1]\nterminal = [1]\n"

    with pytest.raises(ConfigError, match="non-empty strings"):
        load_config(write(tmp_path, text))


def test_unknown_bus_driver_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="bus"):
        load_config(write(tmp_path, MINIMAL + '\n[bus]\ndriver = "redis"\n'))


def test_unknown_channel_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown channel"):
        load_config(write(tmp_path, MINIMAL + "\n[channels.pager]\nenabled = true\n"))


def test_channel_enabled_must_be_boolean(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="enabled"):
        load_config(write(tmp_path, MINIMAL + '\n[channels.desktop]\nenabled = "yes"\n'))


def test_webui_enabled_must_be_boolean(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="enabled"):
        load_config(write(tmp_path, MINIMAL + '\n[webui]\nenabled = 1\n'))


def test_bind_must_be_a_string(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="bind"):
        load_config(write(tmp_path, MINIMAL + "\n[webui]\nbind = 8377\n"))


def test_bind_without_port_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="host:port"):
        load_config(write(tmp_path, MINIMAL + '\n[webui]\nbind = "127.0.0.1"\n'))


def test_bind_with_non_numeric_port_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="port"):
        load_config(write(tmp_path, MINIMAL + '\n[webui]\nbind = "127.0.0.1:http"\n'))


def test_ipv6_loopback_bind_is_accepted(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, MINIMAL + '\n[webui]\nbind = "[::1]:8377"\n'))

    assert config.webui.bind == "[::1]:8377"


def test_reference_must_be_a_string(tmp_path: Path) -> None:
    text = MINIMAL + "\n[channels.webhook]\nurl_ref = 5\n"

    with pytest.raises(ConfigError, match="references only"):
        load_config(write(tmp_path, text))


def test_env_reference_name_must_be_valid(tmp_path: Path) -> None:
    text = MINIMAL + '\n[channels.webhook]\nurl_ref = "env:not-a-name"\n'

    with pytest.raises(ConfigError, match="env:NAME"):
        load_config(write(tmp_path, text))
