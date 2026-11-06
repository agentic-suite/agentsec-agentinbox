"""Fail-closed configuration model (TOML).

Design of record: ``docs/design/v0.1.0/foundation.md`` §4–§5. Configuration is a security
surface: unknown keys are errors (a typo must not disable a control), forward-slate keys are
rejected as unsupported, secrets are references only, and the bind is loopback.

The runtime is stdlib-only; ``tomllib`` is the parser and the file is never rewritten.
"""

from __future__ import annotations

import os
import re
import stat
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path.home() / ".agentinbox"
DEFAULT_CONFIG_NAME = "config.toml"
DEFAULT_BIND = "127.0.0.1:8377"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})
HOME_ENV = "AGENTINBOX_HOME"

_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_STORE_DRIVERS = frozenset({"sqlite", "memory"})
_BUS_DRIVERS = frozenset({"filesystem", "in-proc"})
_SELF_REVIEW = frozenset({"deny", "allow", "escalate"})
_CHANNELS = {"terminal": frozenset(), "desktop": frozenset(), "webhook": frozenset()}

_TOP_LEVEL = frozenset(
    {"classes", "roster", "throttle", "channels", "bus", "store", "limits", "webui"}
)
_FORWARD_SLATE = frozenset(
    {
        "quiet_hours",
        "incident",
        "hooks",
        "standing_rules",
        "calendars",
        "writeback",
        "drills",
        "deadman",
    }
)

_CLASS_KEYS = frozenset(
    {"ttl_seconds", "warn_seconds", "self_review", "require_reason_on_deny", "ladder"}
)
_THROTTLE_KEYS = frozenset({"per_agent_burst", "per_agent_rate_per_min", "flood_window_seconds"})
_LIMITS_KEYS = frozenset({"max_hold_rounds", "max_evidence_revisions", "max_thread_entries"})
_WEBUI_KEYS = frozenset({"enabled", "bind"})
_CHANNEL_KEYS = {
    "terminal": frozenset({"enabled"}),
    "desktop": frozenset({"enabled"}),
    "webhook": frozenset({"enabled", "url_ref", "hmac_key_ref"}),
}
_SECRET_KEY = re.compile(r"(secret|token|password|api_?key|hmac|private_?key)", re.IGNORECASE)


class ConfigError(Exception):
    """Invalid configuration. Always fatal (exit ``4``); never downgraded to a warning."""


# --------------------------------------------------------------------------- data model


@dataclass(frozen=True, slots=True)
class ClassConfig:
    ttl_seconds: int
    warn_seconds: int | None = None
    self_review: str = "deny"
    require_reason_on_deny: bool = False
    ladder: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    enabled: bool = False
    url_ref: str | None = None
    hmac_key_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ThrottleConfig:
    per_agent_burst: int = 20
    per_agent_rate_per_min: int = 10
    flood_window_seconds: int = 30


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    max_hold_rounds: int = 2
    max_evidence_revisions: int = 4
    max_thread_entries: int = 20


@dataclass(frozen=True, slots=True)
class BusConfig:
    driver: str = "filesystem"


@dataclass(frozen=True, slots=True)
class StoreConfig:
    driver: str = "sqlite"


@dataclass(frozen=True, slots=True)
class WebuiConfig:
    enabled: bool = False
    bind: str = DEFAULT_BIND


@dataclass(frozen=True, slots=True)
class Config:
    classes: Mapping[str, ClassConfig] = field(default_factory=dict)
    roster: Mapping[str, Mapping[str, tuple[str, ...]]] = field(default_factory=dict)
    throttle: ThrottleConfig = field(default_factory=ThrottleConfig)
    channels: Mapping[str, ChannelConfig] = field(default_factory=dict)
    bus: BusConfig = field(default_factory=BusConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    webui: WebuiConfig = field(default_factory=WebuiConfig)


# --------------------------------------------------------------------------- home paths


def resolve_home(cli_home: str | None = None, env: Mapping[str, str] | None = None) -> Path:
    """Resolve the agentinbox home: ``--home`` > ``AGENTINBOX_HOME`` > ``~/.agentinbox``."""
    environ = os.environ if env is None else env
    raw = cli_home if cli_home is not None else environ.get(HOME_ENV)

    if raw is None:
        return DEFAULT_HOME
    if not raw or not Path(raw).is_absolute():
        raise ConfigError(
            f"home must be an absolute path (got {raw!r}); "
            f"set {HOME_ENV} or pass --home with an absolute path"
        )
    return Path(raw)


def resolve_config_path(home: Path, cli_config: str | None = None) -> Path:
    """Resolve the config file: ``--config`` > ``<home>/config.toml``."""
    if cli_config is None:
        return home / DEFAULT_CONFIG_NAME
    if not cli_config or not Path(cli_config).is_absolute():
        raise ConfigError(f"--config must be an absolute path (got {cli_config!r})")
    return Path(cli_config)


# --------------------------------------------------------------------------- loading


def load_config(path: Path) -> Config:
    """Parse and validate ``path``; raise :class:`ConfigError` on any problem."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise ConfigError(f"{path}: config not found; run `agentinbox init`") from None
    except IsADirectoryError:
        raise ConfigError(f"{path}: config path is a directory") from None
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read config: {exc.strerror}") from None

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ConfigError(f"{path}: config is not valid UTF-8") from None

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from None

    return _parse(data, path)


def _parse(data: dict[str, Any], path: Path) -> Config:
    _check_top_level(data)

    return Config(
        classes=_parse_classes(_table(data.get("classes", {}), "classes")),
        roster=_parse_roster(_table(data.get("roster", {}), "roster")),
        throttle=_parse_throttle(_table(data.get("throttle", {}), "throttle")),
        channels=_parse_channels(_table(data.get("channels", {}), "channels")),
        bus=_parse_bus(_table(data.get("bus", {}), "bus")),
        store=_parse_store(_table(data.get("store", {}), "store")),
        limits=_parse_limits(_table(data.get("limits", {}), "limits")),
        webui=_parse_webui(_table(data.get("webui", {}), "webui")),
    )


def _check_top_level(data: Mapping[str, Any]) -> None:
    for section in data:
        if section in _FORWARD_SLATE:
            raise ConfigError(
                f"[{section}]: not supported in v0.1.0 "
                "(forward-slate feature from PRDs 24–30)"
            )
        if section not in _TOP_LEVEL:
            raise ConfigError(f"unknown section: [{section}]")


def _table(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"[{path}]: must be a TOML table")
    return value


def _reject_unknown(table: Mapping[str, Any], allowed: frozenset[str], path: str) -> None:
    for key in table:
        if key not in allowed:
            raise ConfigError(f"[{path}].{key}: unknown key")
        if _SECRET_KEY.search(key) and not key.endswith("_ref"):
            raise ConfigError(f"[{path}].{key}: secrets must use a *_ref reference, not a literal")


def _parse_classes(value: dict[str, Any]) -> dict[str, ClassConfig]:
    classes: dict[str, ClassConfig] = {}
    for name, raw in value.items():
        table = _table(raw, f"classes.{name}")
        _reject_unknown(table, _CLASS_KEYS, f"classes.{name}")
        key_path = f"[classes.{name}]"

        ttl = table.get("ttl_seconds")
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
            raise ConfigError(f"{key_path}.ttl_seconds: required positive integer")

        warn = table.get("warn_seconds")
        if warn is not None:
            if not isinstance(warn, int) or isinstance(warn, bool) or warn <= 0:
                raise ConfigError(f"{key_path}.warn_seconds: must be a positive integer")
            if warn >= ttl:
                raise ConfigError(f"{key_path}.warn_seconds: must be less than ttl_seconds")

        self_review = table.get("self_review", "deny")
        if self_review not in _SELF_REVIEW:
            raise ConfigError(
                f"{key_path}.self_review: must be one of deny, allow, escalate"
            )

        require_reason = table.get("require_reason_on_deny", False)
        if not isinstance(require_reason, bool):
            raise ConfigError(f"{key_path}.require_reason_on_deny: must be a boolean")

        ladder = table.get("ladder", [])
        if not isinstance(ladder, list) or not all(
            isinstance(tier, str) and tier for tier in ladder
        ):
            raise ConfigError(f"{key_path}.ladder: must be a list of non-empty strings")

        classes[name] = ClassConfig(
            ttl_seconds=ttl,
            warn_seconds=warn,
            self_review=self_review,
            require_reason_on_deny=require_reason,
            ladder=tuple(ladder),
        )
    return classes


def _parse_roster(value: dict[str, Any]) -> dict[str, dict[str, tuple[str, ...]]]:
    roster: dict[str, dict[str, tuple[str, ...]]] = {}
    for tier, raw in value.items():
        table = _table(raw, f"roster.{tier}")
        channels: dict[str, tuple[str, ...]] = {}
        for channel, principals in table.items():
            if not isinstance(principals, list) or not principals:
                raise ConfigError(
                    f"[roster.{tier}].{channel}: roster must list at least one principal"
                )
            if not all(isinstance(p, str) and p for p in principals):
                raise ConfigError(
                    f"[roster.{tier}].{channel}: principals must be non-empty strings"
                )
            channels[channel] = tuple(principals)
        roster[tier] = channels
    return roster


def _positive_int(table: Mapping[str, Any], key: str, path: str) -> int:
    value = table[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"[{path}].{key}: must be a positive integer")
    return value


def _parse_throttle(value: dict[str, Any]) -> ThrottleConfig:
    _reject_unknown(value, _THROTTLE_KEYS, "throttle")
    defaults = ThrottleConfig()
    return ThrottleConfig(
        per_agent_burst=_positive_int(value, "per_agent_burst", "throttle")
        if "per_agent_burst" in value
        else defaults.per_agent_burst,
        per_agent_rate_per_min=_positive_int(value, "per_agent_rate_per_min", "throttle")
        if "per_agent_rate_per_min" in value
        else defaults.per_agent_rate_per_min,
        flood_window_seconds=_positive_int(value, "flood_window_seconds", "throttle")
        if "flood_window_seconds" in value
        else defaults.flood_window_seconds,
    )


def _parse_limits(value: dict[str, Any]) -> LimitsConfig:
    _reject_unknown(value, _LIMITS_KEYS, "limits")
    defaults = LimitsConfig()
    return LimitsConfig(
        max_hold_rounds=_positive_int(value, "max_hold_rounds", "limits")
        if "max_hold_rounds" in value
        else defaults.max_hold_rounds,
        max_evidence_revisions=_positive_int(value, "max_evidence_revisions", "limits")
        if "max_evidence_revisions" in value
        else defaults.max_evidence_revisions,
        max_thread_entries=_positive_int(value, "max_thread_entries", "limits")
        if "max_thread_entries" in value
        else defaults.max_thread_entries,
    )


def _parse_bus(value: dict[str, Any]) -> BusConfig:
    _reject_unknown(value, frozenset({"driver"}), "bus")
    driver = value.get("driver", "filesystem")
    if driver not in _BUS_DRIVERS:
        raise ConfigError(
            f"[bus].driver: unknown driver {driver!r} (expected filesystem or in-proc)"
        )
    return BusConfig(driver=driver)


def _parse_store(value: dict[str, Any]) -> StoreConfig:
    _reject_unknown(value, frozenset({"driver"}), "store")
    driver = value.get("driver", "sqlite")
    if driver not in _STORE_DRIVERS:
        raise ConfigError(
            f"[store].driver: unknown driver {driver!r} (expected sqlite or memory)"
        )
    return StoreConfig(driver=driver)


def _parse_channels(value: dict[str, Any]) -> dict[str, ChannelConfig]:
    channels: dict[str, ChannelConfig] = {}
    for name, raw in value.items():
        if name not in _CHANNEL_KEYS:
            raise ConfigError(
                f"[channels].{name}: unknown channel (supported in v0.1.0: "
                f"{', '.join(sorted(_CHANNEL_KEYS))})"
            )
        table = _table(raw, f"channels.{name}")
        _reject_unknown(table, _CHANNEL_KEYS[name], f"channels.{name}")

        enabled = table.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ConfigError(f"[channels.{name}].enabled: must be a boolean")

        url_ref = table.get("url_ref")
        if url_ref is not None:
            _validate_ref(url_ref, f"[channels.{name}].url_ref")
        hmac_key_ref = table.get("hmac_key_ref")
        if hmac_key_ref is not None:
            _validate_ref(hmac_key_ref, f"[channels.{name}].hmac_key_ref")

        channels[name] = ChannelConfig(
            enabled=enabled, url_ref=url_ref, hmac_key_ref=hmac_key_ref
        )
    return channels


def _parse_webui(value: dict[str, Any]) -> WebuiConfig:
    _reject_unknown(value, _WEBUI_KEYS, "webui")

    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError("[webui].enabled: must be a boolean")
    if enabled:
        raise ConfigError("[webui].enabled: not supported in v0.1.0 (arrives in v0.1.x)")

    bind = value.get("bind", DEFAULT_BIND)
    if not isinstance(bind, str):
        raise ConfigError("[webui].bind: must be a string host:port")
    _validate_loopback_bind(bind)

    return WebuiConfig(enabled=enabled, bind=bind)


def _validate_loopback_bind(bind: str) -> None:
    host, separator, port_text = bind.rpartition(":")
    if not separator:
        raise ConfigError("[webui].bind: must be host:port with a valid port")

    try:
        port = int(port_text)
    except ValueError:
        raise ConfigError("[webui].bind: port must be an integer") from None
    if not 1 <= port <= 65535:
        raise ConfigError("[webui].bind: port must be between 1 and 65535")

    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host not in LOOPBACK_HOSTS:
        raise ConfigError(
            f"[webui].bind: host must be loopback ({', '.join(sorted(LOOPBACK_HOSTS))}); "
            f"got {host!r}"
        )


def _validate_ref(value: Any, key_path: str) -> None:
    if not isinstance(value, str) or ":" not in value:
        raise ConfigError(
            f"{key_path}: secrets are references only — use env:NAME or file:/absolute/path"
        )
    scheme, _, rest = value.partition(":")
    if scheme == "env":
        if not _ENV_NAME.fullmatch(rest):
            raise ConfigError(f"{key_path}: env reference must be env:NAME")
        return
    if scheme == "file":
        if not Path(rest).is_absolute():
            raise ConfigError(f"{key_path}: file reference must be an absolute path")
        return
    raise ConfigError(f"{key_path}: unknown reference scheme {scheme!r} (use env: or file:)")


# --------------------------------------------------------------------------- init scaffold


SCAFFOLD = """# agentinbox configuration — v0.1.0
#
# This file is security-relevant: TTLs, rosters, ladders, and thresholds are policy.
# Review changes like code. Secrets are references only (env:NAME or file:/absolute/path).

[classes.irreversible]
ttl_seconds = 300
warn_seconds = 60
self_review = "deny"
require_reason_on_deny = true
ladder = []

[roster.tier-1]
terminal = ["alice"]

[throttle]
per_agent_burst = 20
per_agent_rate_per_min = 10
flood_window_seconds = 30

[channels.terminal]
enabled = true

[channels.desktop]
enabled = false

[channels.webhook]
enabled = false

[bus]
driver = "filesystem"

[store]
driver = "sqlite"

[limits]
max_hold_rounds = 2
max_evidence_revisions = 4
max_thread_entries = 20

[webui]
enabled = false
bind = "127.0.0.1:8377"
"""

HOME_SUBDIRS = (
    "",
    "spool/jobs",
    "spool/done",
    "spool/locks",
    "keys",
    "logs",
    "exports",
)


def init_home(home: Path, config_path: Path, *, force: bool = False) -> Path:
    """Create the private home skeleton and a valid config scaffold; return the config path."""
    if config_path.exists() and not force:
        raise ConfigError(
            f"{config_path}: config already exists; pass --force to overwrite"
        )

    home.mkdir(parents=True, exist_ok=True)
    _chmod(home, 0o700)
    for relative in HOME_SUBDIRS[1:]:
        subdir = home / relative
        subdir.mkdir(parents=True, exist_ok=True)
        _chmod(subdir, 0o700)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(SCAFFOLD)
    _chmod(config_path, 0o600)
    return config_path


def _chmod(path: Path, mode: int) -> None:
    os.chmod(path, stat.S_IMODE(mode))
