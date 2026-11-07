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

from agentinbox.channels.desktop import desktop_availability
from agentinbox.config import Config, ConfigError, effective_ladder_delays, load_config
from agentinbox.secrets import SecretError, resolve_ref
from agentinbox.store import AuditEntry, ChainHashMismatch, verify_audit_chain
from agentinbox.store.sqlite import SCHEMA_VERSION

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
        _desktop(config),
        _store_path(home),
        _schema(home / "inbox.db"),
        _chain(home / "inbox.db"),
        _spool(home),
        _keys(config),
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


def _desktop(config: Config | None) -> Check:
    """Enabled desktop channel must be reachable; unusable is a finding, never silent."""
    if config is None:
        return Check("desktop", OK, "no valid config; channel state unknown")
    channel = config.channels.get("desktop")
    if channel is None or not channel.enabled:
        return Check("desktop", OK, "disabled")
    available, detail = desktop_availability()
    if not available:
        return Check(
            "desktop",
            FAIL,
            f"{detail}; run the desktop channel on a GUI session or set "
            "[channels.desktop] enabled = false (asks stay pending either way)",
        )
    return Check("desktop", OK, detail)


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
    version = int(row[0])
    if version > SCHEMA_VERSION:
        return Check(
            "schema",
            FAIL,
            f"{database}: schema v{version} is newer than this build "
            f"(v{SCHEMA_VERSION}); downgrade is refused loudly",
        )
    if version < SCHEMA_VERSION:
        return Check(
            "schema", WARN, f"{database}: schema v{version}; migrates to v{SCHEMA_VERSION}"
        )
    return Check("schema", OK, f"schema version {version}")


def _chain(database: Path) -> Check:
    if not database.exists():
        return Check("chain", OK, "no store yet")
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            rows = connection.execute(
                "SELECT seq, prev_hash, entry_hash, kind, ref_id, at, payload_digest"
                " FROM audit ORDER BY seq ASC"
            ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table: audit" in str(exc).lower():
            return Check("chain", OK, "audit table not present yet (migrates on open)")
        return Check("chain", FAIL, f"{database}: cannot read the audit chain ({exc})")
    except sqlite3.Error as exc:
        return Check("chain", FAIL, f"{database}: cannot read the audit chain ({exc})")

    entries = [
        AuditEntry(
            seq=int(row[0]),
            prev_hash=str(row[1]),
            entry_hash=str(row[2]),
            kind=str(row[3]),
            ref_id=str(row[4]),
            at=_parse_moment(str(row[5])),
            payload_digest=str(row[6]),
        )
        for row in rows
    ]
    try:
        verify_audit_chain(entries)
    except ChainHashMismatch as exc:
        return Check("chain", FAIL, f"{database}: {exc}")
    return Check("chain", OK, f"{len(entries)} entries verify")


def _parse_moment(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)


def _spool(home: Path) -> Check:
    spool = home / "spool"
    if not spool.exists():
        return Check("spool", OK, "no spool yet (created by `agentinbox init`)")
    pending = _count(spool / "jobs", "*.json")
    done = _count(spool / "done", "*.json")
    staging = _count(spool / "tmp", "*.tmp")
    lock = spool / "locks" / "bus.lock"
    if not lock.exists():
        return Check("spool", WARN, f"{spool}: bus.lock missing; run `agentinbox serve`")
    if staging:
        return Check(
            "spool", WARN, f"{spool}: {staging} staging files (swept on daemon boot)"
        )
    return Check("spool", OK, f"{pending} pending, {done} done")


def _count(directory: Path, pattern: str) -> int:
    return len(list(directory.glob(pattern))) if directory.exists() else 0


def _keys(config: Config | None) -> Check:
    if config is None:
        return Check("keys", WARN, "config is invalid; secret references unchecked")
    refs: list[tuple[str, str]] = []
    for name, producer in config.producers.items():
        refs.append((f"producer.{name}.key_ref", producer.key_ref))
    webhook = config.channels.get("webhook")
    if webhook is not None and webhook.enabled:
        for label, ref in (
            ("channels.webhook.url_ref", webhook.url_ref),
            ("channels.webhook.hmac_key_ref", webhook.hmac_key_ref),
        ):
            if ref is not None:
                refs.append((label, ref))
    for label, ref in refs:
        try:
            resolve_ref(ref)
        except SecretError as exc:
            return Check("keys", FAIL, f"{label}: {exc}")
    return Check("keys", OK, f"{len(refs)} references resolve")


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
        f"  audit.retention: {config.audit.retention}",
    ]
    for name in sorted(config.classes):
        ask_class = config.classes[name]
        lines.append(
            f"  class {name}: ttl={ask_class.ttl_seconds}s "
            f"warn={ask_class.warn_seconds} self_review={ask_class.self_review} "
            f"ladder={list(ask_class.ladder)} "
            f"ladder_delays={list(effective_ladder_delays(ask_class))} "
            f"flood_burst={ask_class.flood_burst or config.throttle.per_agent_burst} "
            f"flood_rate_per_min="
            f"{ask_class.flood_rate_per_min or config.throttle.per_agent_rate_per_min}"
        )
    lines.append(
        f"  throttle: burst={config.throttle.per_agent_burst} "
        f"rate_per_min={config.throttle.per_agent_rate_per_min} "
        f"window={config.throttle.flood_window_seconds}s"
    )
    for tier in sorted(config.roster):
        principals = ", ".join(
            f"{channel}={list(values)}" for channel, values in sorted(config.roster[tier].items())
        )
        lines.append(f"  roster {tier}: {principals}")
    for producer_name in sorted(config.producers):
        producer = config.producers[producer_name]
        lines.append(f"  producer {producer_name}: key_ref={producer.key_ref}")
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
