"""Home and config-path resolution (M0 item 0.4).

Resolution order is strict first-hit-wins: ``--home`` > ``AGENTINBOX_HOME`` > ``~/.agentinbox``.
An explicit but unusable value (empty, relative) is an error — never silently replaced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, resolve_config_path, resolve_home


def test_default_home_is_dot_agentinbox() -> None:
    assert resolve_home(None, env={}) == Path.home() / ".agentinbox"


def test_env_overrides_default() -> None:
    assert resolve_home(None, env={"AGENTINBOX_HOME": "/srv/inbox"}) == Path("/srv/inbox")


def test_flag_overrides_env() -> None:
    assert resolve_home("/tmp/flag", env={"AGENTINBOX_HOME": "/srv/inbox"}) == Path("/tmp/flag")


def test_relative_flag_is_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute"):
        resolve_home("relative/home", env={})


def test_empty_env_is_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute"):
        resolve_home(None, env={"AGENTINBOX_HOME": ""})


def test_relative_env_is_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute"):
        resolve_home(None, env={"AGENTINBOX_HOME": "inbox"})


def test_config_path_defaults_under_home() -> None:
    assert resolve_config_path(Path("/srv/inbox")) == Path("/srv/inbox/config.toml")


def test_config_flag_overrides_home_path() -> None:
    assert resolve_config_path(Path("/srv/inbox"), "/etc/inbox.toml") == Path("/etc/inbox.toml")


def test_relative_config_flag_is_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute"):
        resolve_config_path(Path("/srv/inbox"), "inbox.toml")
