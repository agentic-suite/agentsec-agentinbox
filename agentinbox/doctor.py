"""``doctor`` — honest, exit-coded checks of the local install (M0 item 0.6).

Design: ``docs/design/v0.1.0/foundation.md`` §6. Each check has a stable id so later
milestones can grow the set without renumbering. Any ``fail`` makes the whole command exit
``4`` (fail-closed); warnings do not change the exit code.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentinbox.config import Config, ConfigError, load_config

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass(frozen=True, slots=True)
class Check:
    id: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class Report:
    checks: tuple[Check, ...]
    config: Config | None

    @property
    def ok(self) -> bool:
        return all(check.status != FAIL for check in self.checks)


def run_checks(home: Path, config_path: Path) -> Report:
    config: Config | None = None
    config_check: Check
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        config_check = Check("config", FAIL, str(exc))
    else:
        config_check = Check("config", OK, f"valid: {config_path}")

    checks = (
        _platform(),
        _home(home),
        config_check,
        _store_path(home),
        _schema(home / "inbox.db"),
        _clock(),
        _clock_skew(home / "inbox.db"),
    )
    return Report(checks=checks, config=config)


def _platform() -> Check:
    if sys.platform == "win32":
        return Check(
            "platform", FAIL, "Windows is not supported in v0.1.0 (POSIX only); use WSL"
        )
    return Check("platform", OK, sys.platform)


def _home(home: Path) -> Check:
    if not home.exists():
        return Check("home", FAIL, f"{home}: home does not exist; run `agentinbox init`")
    if not home.is_dir():
        return Check("home", FAIL, f"{home}: home is not a directory")
    if not os.access(home, os.W_OK):
        return Check("home", FAIL, f"{home}: home is not writable")
    mode = stat.S_IMODE(home.stat().st_mode)
    if mode & 0o077:
        return Check("home", WARN, f"{home}: mode {mode:o}, expected 700")
    return Check("home", OK, f"{home} (mode {mode:o})")


def _store_path(home: Path) -> Check:
    database = home / "inbox.db"
    if not database.exists():
        return Check("store-path", OK, "no store yet (created by the M1 store driver)")
    mode = stat.S_IMODE(database.stat().st_mode)
    if mode & 0o077:
        return Check(
            "store-path", FAIL, f"{database}: mode {mode:o} exposes the store; expected 600"
        )
    return Check("store-path", OK, f"{database} (mode {mode:o})")


def _schema(database: Path) -> Check:
    if not database.exists():
        return Check("schema", OK, "no store yet; nothing to verify (M1)")
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
    except sqlite3.Error as exc:
        return Check("schema", FAIL, f"{database}: unreadable schema version ({exc})")
    if row is None:
        return Check("schema", FAIL, f"{database}: schema_version is empty")
    return Check("schema", OK, f"schema version {row[0]}")


def _clock() -> Check:
    try:
        wall = time.time()
        before = time.monotonic()
        after = time.monotonic()
    except (OSError, OverflowError) as exc:
        return Check("clock", FAIL, f"system clock unavailable ({exc})")
    if wall <= 0 or after < before:
        return Check("clock", FAIL, "system clock is not sane")
    return Check("clock", OK, "UTC clock and monotonic time available")


SIGNATURE_WINDOW_SECONDS = 300


def _clock_skew(database: Path) -> Check:
    """Evidence ahead of the wall clock means the machine moved backwards."""
    if not database.exists():
        return Check("clock-skew", OK, "no store yet")
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute("SELECT MAX(at) FROM audit").fetchone()
    except sqlite3.Error as exc:
        return Check("clock-skew", WARN, f"cannot read audit time ({exc})")
    if row is None or row[0] is None:
        return Check("clock-skew", OK, "no audit entries yet")
    try:
        newest = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    except ValueError:
        return Check("clock-skew", WARN, "audit timestamp is not ISO-8601")
    skew = (newest - datetime.now(UTC)).total_seconds()
    if skew > SIGNATURE_WINDOW_SECONDS:
        return Check(
            "clock-skew",
            WARN,
            f"newest audit entry is {int(skew)}s ahead of the clock; a backwards jump "
            "cannot extend a TTL, but check NTP",
        )
    return Check("clock-skew", OK, "audit evidence is consistent with the clock")


def render_human(report: Report) -> str:
    return "\n".join(f"{check.status:4} {check.id}: {check.detail}" for check in report.checks)


def render_explain(report: Report, home: Path, config_path: Path) -> str | None:
    """Effective config with secret **references** shown, never resolved values."""
    config = report.config
    if config is None:
        return None

    lines = [
        "effective config:",
        f"  home: {home}",
        f"  config: {config_path}",
        f"  store.driver: {config.store.driver}",
        f"  bus.driver: {config.bus.driver}",
        f"  webui.bind: {config.webui.bind} (enabled={config.webui.enabled})",
    ]
    for name in sorted(config.classes):
        ask_class = config.classes[name]
        lines.append(
            f"  class {name}: ttl={ask_class.ttl_seconds}s "
            f"warn={ask_class.warn_seconds} self_review={ask_class.self_review} "
            f"ladder={list(ask_class.ladder)}"
        )
    for tier in sorted(config.roster):
        principals = ", ".join(
            f"{channel}={list(values)}" for channel, values in sorted(config.roster[tier].items())
        )
        lines.append(f"  roster {tier}: {principals}")
    for channel_name in sorted(config.channels):
        channel = config.channels[channel_name]
        refs = [
            f"{label}={value}"
            for label, value in (
                ("url_ref", channel.url_ref),
                ("hmac_key_ref", channel.hmac_key_ref),
            )
            if value is not None
        ]
        suffix = f" ({', '.join(refs)})" if refs else ""
        lines.append(f"  channel {channel_name}: enabled={channel.enabled}{suffix}")
    return "\n".join(lines)
