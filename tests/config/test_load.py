"""Fail-closed TOML config validation (M0 item 0.4).

Design: ``docs/design/v0.1.0/foundation.md`` §5. Every failure must name the file and the key
path, exit-level code ``4`` at the CLI, and never fall back to a default.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import Config, ConfigError, load_config

MINIMAL = """
[classes.irreversible]
ttl_seconds = 300
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_config_loads_with_documented_defaults(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, MINIMAL))

    assert isinstance(config, Config)
    assert config.classes["irreversible"].ttl_seconds == 300
    assert config.classes["irreversible"].self_review == "deny"
    assert config.store.driver == "sqlite"
    assert config.bus.driver == "filesystem"
    assert config.webui.enabled is False
    assert config.webui.bind == "127.0.0.1:8377"
    assert config.throttle.per_agent_burst == 20
    assert config.limits.max_hold_rounds == 2


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.toml")


def test_malformed_toml_names_the_file(tmp_path: Path) -> None:
    path = write(tmp_path, "[classes.irreversible\n")

    with pytest.raises(ConfigError) as excinfo:
        load_config(path)

    assert "config.toml" in str(excinfo.value)


def test_unknown_section_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"unknown section: \[unknown\]"):
        load_config(write(tmp_path, MINIMAL + "\n[unknown]\nkey = 1\n"))


def test_unknown_key_is_rejected_with_its_path(tmp_path: Path) -> None:
    text = MINIMAL + "\nttl_seconds_typo = 60\n"

    with pytest.raises(ConfigError, match=r"\[classes\.irreversible\]\.ttl_seconds_typo"):
        load_config(write(tmp_path, text))


def test_forward_slate_section_is_not_silently_ignored(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not supported in v0.1.0"):
        load_config(write(tmp_path, MINIMAL + '\n[quiet_hours]\nwindow = "22:00-08:00"\n'))


def test_class_requires_positive_ttl(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="ttl_seconds"):
        load_config(write(tmp_path, '[classes.x]\nttl_seconds = 0\n'))


def test_warn_must_be_below_ttl(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="warn_seconds"):
        load_config(write(tmp_path, "[classes.x]\nttl_seconds = 60\nwarn_seconds = 60\n"))


def test_invalid_self_review_value_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="self_review"):
        load_config(write(tmp_path, '[classes.x]\nttl_seconds = 60\nself_review = "maybe"\n'))


def test_unknown_class_is_not_allowed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown key"):
        load_config(write(tmp_path, "[classes.x]\nttl_seconds = 60\nmax_ttl = 90\n"))


def test_empty_roster_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="roster"):
        load_config(write(tmp_path, MINIMAL + "\n[roster.tier-1]\nterminal = []\n"))


def test_secret_reference_must_be_env_or_absolute_file(tmp_path: Path) -> None:
    text = MINIMAL + """
[channels.webhook]
enabled = true
url_ref = "https://example.invalid/hook"
"""
    with pytest.raises(ConfigError, match=r"url_ref"):
        load_config(write(tmp_path, text))


def test_env_and_file_references_are_accepted(tmp_path: Path) -> None:
    text = MINIMAL + """
[channels.webhook]
enabled = true
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "file:/etc/agentinbox/hmac"
"""
    config = load_config(write(tmp_path, text))

    assert config.channels["webhook"].url_ref == "env:AGENTINBOX_WEBHOOK_URL"


def test_relative_file_reference_is_rejected(tmp_path: Path) -> None:
    text = MINIMAL + """
[channels.webhook]
url_ref = "file:hmac"
"""
    with pytest.raises(ConfigError, match="absolute"):
        load_config(write(tmp_path, text))


def test_non_loopback_bind_is_rejected_in_v0_1_0(tmp_path: Path) -> None:
    text = MINIMAL + '\n[webui]\nbind = "0.0.0.0:8377"\n'

    with pytest.raises(ConfigError, match="loopback"):
        load_config(write(tmp_path, text))


def test_webui_enabled_is_not_supported_in_v0_1_0(tmp_path: Path) -> None:
    text = MINIMAL + "\n[webui]\nenabled = true\n"

    with pytest.raises(ConfigError, match="not supported in v0.1.0"):
        load_config(write(tmp_path, text))


def test_invalid_port_is_rejected(tmp_path: Path) -> None:
    text = MINIMAL + '\n[webui]\nbind = "127.0.0.1:70000"\n'

    with pytest.raises(ConfigError, match="port"):
        load_config(write(tmp_path, text))


def test_unknown_driver_is_rejected(tmp_path: Path) -> None:
    text = MINIMAL + '\n[store]\ndriver = "postgres"\n'

    with pytest.raises(ConfigError, match="driver"):
        load_config(write(tmp_path, text))


def test_throttle_values_must_be_positive(tmp_path: Path) -> None:
    text = MINIMAL + "\n[throttle]\nper_agent_burst = -1\n"

    with pytest.raises(ConfigError, match="per_agent_burst"):
        load_config(write(tmp_path, text))
