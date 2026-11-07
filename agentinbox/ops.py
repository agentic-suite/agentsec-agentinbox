"""Operations: units, daemon lock, backup/restore, and offline posture (M21).

Design: ``docs/design/v0.1.0/ops.md``. Units are written by the operator's own account — never
``sudo``, never outside the home — and the daemon lock makes a dead daemon visible to a waiting
``gate`` so it fails closed (exit ``4``) instead of hanging. Backups are WAL-safe and carry
references, never resolved secrets; restore verifies the chain or aborts.
"""

from __future__ import annotations

import contextlib
import json
import os
import plistlib
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agentinbox import __version__
from agentinbox.audit import read_audit_entries
from agentinbox.config import Config, load_config
from agentinbox.store import (
    GENESIS_HASH,
    AskStatus,
    StoreError,
    TransitionRecord,
    parse_iso,
    to_iso,
    utcnow,
    verify_audit_chain,
)
from agentinbox.store.sqlite import SCHEMA_VERSION, SqliteStore

LAUNCHD_LABEL = "com.agentsec.agentinbox"
SERVICE_NAME = "agentinbox"
LOCK_NAME = "serve.lock"
BACKUP_CONTRACT = "backup/1.0"
BACKUP_MEMBERS = ("manifest.json", "inbox.db", "config.toml", "keys/slots.json")


class OpsError(Exception):
    """An operations request cannot be satisfied (fail closed)."""


@dataclass(frozen=True, slots=True)
class ServiceUnit:
    platform: str
    path: Path
    content: str


@dataclass(frozen=True, slots=True)
class DaemonLock:
    pid: int
    started_at: datetime
    path: Path


def render_service_unit(
    home: Path,
    config_path: Path,
    *,
    platform: str | None = None,
    python: str | None = None,
) -> ServiceUnit:
    """Render the user-scoped unit for this platform without touching the filesystem."""
    target = platform or sys.platform
    if target.startswith("win"):
        raise OpsError(
            "Windows service units are not supported in v0.1.0 (POSIX only); use WSL"
        )
    interpreter = python or sys.executable
    if not Path(interpreter).is_absolute():
        raise OpsError(f"interpreter path must be absolute: {interpreter!r}")

    home = Path(os.path.abspath(os.path.expanduser(str(home))))
    config_path = Path(os.path.abspath(os.path.expanduser(str(config_path))))
    arguments = [
        interpreter,
        "-m",
        "agentinbox",
        "--home",
        str(home),
        "--config",
        str(config_path),
        "serve",
    ]

    if target == "darwin":
        document = {
            "Label": LAUNCHD_LABEL,
            "ProgramArguments": arguments,
            "RunAtLoad": True,
            # launchd owns supervision; no internal restart magic (PRD 22 §B).
            "KeepAlive": False,
            "ProcessType": "Background",
            "StandardOutPath": str(home / "logs" / "serve.log"),
            "StandardErrorPath": str(home / "logs" / "serve.err"),
            "WorkingDirectory": str(home),
        }
        content = plistlib.dumps(document).decode("utf-8")
        path = home / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
        return ServiceUnit(platform="darwin", path=path, content=content)

    if target.startswith("linux"):
        content = "\n".join(
            [
                "[Unit]",
                "Description=agentinbox ask gate",
                "After=network.target",
                "",
                "[Service]",
                "Type=simple",
                f"ExecStart={_systemd_join(arguments)}",
                "Restart=on-failure",
                "RestartSec=5",
                "KillSignal=SIGTERM",
                "TimeoutStopSec=10",
                f"StandardOutput=append:{home / 'logs' / 'serve.log'}",
                f"StandardError=append:{home / 'logs' / 'serve.err'}",
                "WorkingDirectory=" + str(home),
                "",
                "[Install]",
                "WantedBy=default.target",
                "",
            ]
        )
        path = home / ".config" / "systemd" / "user" / f"{SERVICE_NAME}.service"
        return ServiceUnit(platform="linux", path=path, content=content)

    raise OpsError(f"service units are not supported on {target!r} (POSIX only)")


def install_service(
    home: Path,
    config_path: Path,
    *,
    platform: str | None = None,
    python: str | None = None,
) -> ServiceUnit:
    """Write the unit (0600) under the user's home; return what was written."""
    unit = render_service_unit(home, config_path, platform=platform, python=python)
    _ensure_private_dir(unit.path.parent)
    _ensure_private_dir(Path(home) / "logs")
    descriptor = os.open(unit.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(unit.content)
    os.chmod(unit.path, 0o600)
    return unit


# --------------------------------------------------------------------------- daemon lock


def lock_path(home: Path) -> Path:
    return Path(home) / LOCK_NAME


def write_daemon_lock(
    home: Path, *, now: Callable[[], datetime] = utcnow
) -> DaemonLock:
    """Record this process as the running daemon (atomic replace, 0600)."""
    path = lock_path(home)
    _ensure_private_dir(path.parent)
    started_at = now()
    payload = {"pid": os.getpid(), "started_at": to_iso(started_at)}
    staging = path.with_name(path.name + ".tmp")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    os.chmod(staging, 0o600)
    os.replace(staging, path)
    return DaemonLock(pid=os.getpid(), started_at=started_at, path=path)


def read_daemon_lock(home: Path) -> DaemonLock | None:
    """Read the lock; a corrupt lock is treated as absent (never a decision)."""
    path = lock_path(home)
    try:
        raw = path.read_text(encoding="utf-8")
        document = json.loads(raw)
        pid = int(document["pid"])
        started_at = parse_iso(str(document["started_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if pid <= 0:
        return None
    return DaemonLock(pid=pid, started_at=started_at, path=path)


def daemon_alive(home: Path) -> bool:
    """True only when the lock names a live process."""
    lock = read_daemon_lock(home)
    return lock is not None and _pid_alive(lock.pid)


def clear_daemon_lock(home: Path) -> None:
    with contextlib.suppress(OSError):
        lock_path(home).unlink()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists but belongs to another user; the lock is still live.
        return True
    except OSError:
        return False
    return True


# --------------------------------------------------------------------------- offline posture


@dataclass(frozen=True, slots=True)
class OfflinePosture:
    offline_complete: bool
    external_channels: tuple[str, ...]
    detail: str


#: Channels that never leave the machine. Anything else is an external channel.
LOCAL_CHANNELS = frozenset({"terminal", "desktop"})


def offline_posture(config: Config) -> OfflinePosture:
    """Report whether the configured box is offline-complete (PRD 13 N-19)."""
    external = tuple(
        sorted(
            name
            for name, channel in config.channels.items()
            if channel.enabled and name not in LOCAL_CHANNELS
        )
    )
    if not external:
        return OfflinePosture(
            offline_complete=True,
            external_channels=(),
            detail="offline-complete: no external channels enabled",
        )
    return OfflinePosture(
        offline_complete=False,
        external_channels=external,
        detail=(
            f"external channel enabled ({', '.join(external)}); "
            "disable it for an offline day — local paths still work"
        ),
    )


# --------------------------------------------------------------------------- backup / restore


@dataclass(frozen=True, slots=True)
class BackupResult:
    path: Path
    created_at: datetime
    schema_version: int
    chain_head: str
    asks: int
    transitions: int
    audit_entries: int


@dataclass(frozen=True, slots=True)
class RestoreResult:
    home: Path
    asks: int
    transitions: int
    audit_entries: int
    expired: int


def backup_home(
    home: Path,
    out: Path,
    *,
    config_path: Path | None = None,
    now: Callable[[], datetime] = utcnow,
) -> BackupResult:
    """Write a WAL-safe archive of evidence + config references (never secret values)."""
    home = Path(home)
    database = home / "inbox.db"
    if not database.exists():
        raise OpsError(f"{database}: no store to back up; run `agentinbox init` first")
    config_path = Path(config_path) if config_path is not None else home / "config.toml"
    if not config_path.exists():
        raise OpsError(f"{config_path}: no config to back up")
    config = load_config(config_path)

    out = Path(out)
    _ensure_private_dir(out.parent)
    created_at = now()

    with tempfile.TemporaryDirectory(prefix="agentinbox-backup-") as staging_text:
        staging = Path(staging_text)
        _copy_database(database, staging / "inbox.db")
        entries = read_audit_entries(staging / "inbox.db")
        try:
            verify_audit_chain(entries)
        except StoreError as exc:
            raise OpsError(f"chain verification failed; refusing to back up: {exc}") from exc
        version = _schema_version(staging / "inbox.db")
        if version > SCHEMA_VERSION:
            raise OpsError(
                f"store schema v{version} is newer than this build (v{SCHEMA_VERSION}); "
                "downgrade is refused loudly"
            )
        counts = _counts(staging / "inbox.db")
        chain_head = entries[-1].entry_hash if entries else GENESIS_HASH
        manifest = {
            "contract": BACKUP_CONTRACT,
            "created_at": to_iso(created_at),
            "agentinbox_version": __version__,
            "schema_version": version,
            "chain_head": chain_head,
            "counts": counts,
            "files": list(BACKUP_MEMBERS),
            "secrets": "references only (env:/file:); no resolved values",
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        shutil.copyfile(config_path, staging / "config.toml")
        (staging / "keys").mkdir()
        (staging / "keys" / "slots.json").write_text(
            json.dumps(_key_slots(config), sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        for file in staging.rglob("*"):
            if file.is_file():
                os.chmod(file, 0o600)
        with tarfile.open(out, "w", format=tarfile.PAX_FORMAT) as tar:
            for name in BACKUP_MEMBERS:
                tar.add(staging / name, arcname=name)
    os.chmod(out, 0o600)
    return BackupResult(
        path=out,
        created_at=created_at,
        schema_version=version,
        chain_head=chain_head,
        asks=int(counts["asks"]),
        transitions=int(counts["transitions"]),
        audit_entries=int(counts["audit"]),
    )


def restore_home(
    archive: Path,
    home: Path,
    *,
    force: bool = False,
    now: Callable[[], datetime] = utcnow,
) -> RestoreResult:
    """Verify an archive, then install it into ``home``; a bad chain aborts untouched."""
    archive = Path(archive)
    home = Path(home)
    if not archive.exists():
        raise OpsError(f"{archive}: backup archive does not exist")
    if home.exists():
        if not home.is_dir():
            raise OpsError(f"{home}: home is not a directory")
        if any(home.iterdir()) and not force:
            raise OpsError(
                f"{home}: home is not empty; restore into a fresh AGENTINBOX_HOME "
                "or pass --force to replace it"
            )

    with tempfile.TemporaryDirectory(prefix="agentinbox-restore-") as staging_text:
        staging = Path(staging_text)
        _extract_archive(archive, staging)
        manifest = _read_manifest(staging)
        database = staging / "inbox.db"
        version = _schema_version(database)
        if version > SCHEMA_VERSION:
            raise OpsError(
                f"backup schema v{version} is newer than this build (v{SCHEMA_VERSION}); "
                "downgrade is refused loudly"
            )
        entries = read_audit_entries(database)
        try:
            verify_audit_chain(entries)
        except StoreError as exc:
            raise OpsError(f"chain verification failed; restore aborted: {exc}") from exc
        expected_head = str(manifest.get("chain_head", ""))
        actual_head = entries[-1].entry_hash if entries else GENESIS_HASH
        if expected_head and expected_head != actual_head:
            raise OpsError(
                "chain verification failed; restore aborted: manifest chain head does not "
                "match the archive"
            )
        counts = _counts(database)

        if force and home.exists():
            shutil.rmtree(home)
        home.mkdir(parents=True, exist_ok=True)
        os.chmod(home, 0o700)
        for name in BACKUP_MEMBERS:
            source = staging / name
            if not source.exists():
                raise OpsError(f"backup archive is missing {name}")
            destination = home / name
            _ensure_private_dir(destination.parent)
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o600)

        expired = _expire_overdue(home / "inbox.db", now=now())

    return RestoreResult(
        home=home,
        asks=int(counts["asks"]),
        transitions=int(counts["transitions"]),
        audit_entries=int(counts["audit"]),
        expired=expired,
    )


# --------------------------------------------------------------------------- internals


def _copy_database(source: Path, destination: Path) -> None:
    """SQLite online backup: consistent while the daemon keeps writing (WAL-safe)."""
    try:
        source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()
    except sqlite3.Error as exc:
        raise OpsError(f"store is unavailable for backup: {exc}") from exc
    os.chmod(destination, 0o600)


def _schema_version(database: Path) -> int:
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            exists = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            ).fetchone()
            if exists is None:
                return 0
            row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    except sqlite3.Error as exc:
        raise OpsError(f"store is unreadable: {exc}") from exc
    return int(row[0]) if row is not None and row[0] is not None else 0


def _counts(database: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            for table in ("asks", "transitions", "audit"):
                row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608 - fixed table names
                counts[table] = int(row[0]) if row is not None else 0
    except sqlite3.Error as exc:
        raise OpsError(f"store is unreadable: {exc}") from exc
    return counts


def _key_slots(config: Config) -> dict[str, object]:
    """Reference strings only — resolving a secret here would leak it into the archive."""
    slots: dict[str, object] = {
        "producers": {
            name: producer.key_ref for name, producer in sorted(config.producers.items())
        },
        "channels": {},
    }
    webhook = config.channels.get("webhook")
    if webhook is not None:
        channels = slots["channels"]
        assert isinstance(channels, dict)
        channels["webhook"] = {
            "url_ref": webhook.url_ref,
            "hmac_key_ref": webhook.hmac_key_ref,
        }
    return slots


def _extract_archive(archive: Path, staging: Path) -> None:
    try:
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                name = member.name
                if (
                    not member.isfile()
                    or Path(name).is_absolute()
                    or ".." in Path(name).parts
                    or name not in BACKUP_MEMBERS
                ):
                    raise OpsError(f"archive member is not allowed: {name!r}")
                handle = tar.extractfile(member)
                if handle is None:  # pragma: no cover - isfile() guarantees a body
                    raise OpsError(f"archive member is unreadable: {name!r}")
                destination = staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(handle.read())
                os.chmod(destination, 0o600)
    except (tarfile.TarError, OSError) as exc:
        raise OpsError(f"backup archive is unreadable: {exc}") from exc


def _read_manifest(staging: Path) -> dict[str, object]:
    path = staging / "manifest.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OpsError(f"backup manifest is unreadable: {exc}") from exc
    if not isinstance(document, dict):
        raise OpsError("backup manifest is not an object")
    if document.get("contract") != BACKUP_CONTRACT:
        raise OpsError(
            f"unsupported backup contract: {document.get('contract')!r} "
            f"(this build reads {BACKUP_CONTRACT})"
        )
    return document


def _expire_overdue(database: Path, *, now: datetime) -> int:
    """Scheduler-recovery semantics on restore: overdue pending asks expire once."""
    store = SqliteStore(database)
    expired = 0
    try:
        for pending in store.list_pending(now=now, limit=10_000):
            if pending.expires_at > now:
                continue
            won = store.cas_status(
                pending.ask_id,
                expected=AskStatus.PENDING,
                new=AskStatus.EXPIRED,
                transition=TransitionRecord(
                    ask_id=pending.ask_id,
                    at=now,
                    kind="expired",
                    from_status=AskStatus.PENDING,
                    to_status=AskStatus.EXPIRED,
                    detail={"reason": "ttl", "retryable": False, "restored": True},
                ),
            )
            if won:
                expired += 1
    finally:
        store.close()
    return expired


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _systemd_join(arguments: list[str]) -> str:
    """Quote arguments for a systemd ExecStart line (no shell interpretation)."""
    quoted: list[str] = []
    for argument in arguments:
        needs_quotes = any(character.isspace() for character in argument)
        if needs_quotes or '"' in argument or "\\" in argument:
            escaped = argument.replace("\\", "\\\\").replace('"', '\\"')
            quoted.append(f'"{escaped}"')
        else:
            quoted.append(argument)
    return " ".join(quoted)


__all__ = [
    "BACKUP_CONTRACT",
    "BACKUP_MEMBERS",
    "LAUNCHD_LABEL",
    "LOCAL_CHANNELS",
    "LOCK_NAME",
    "SERVICE_NAME",
    "BackupResult",
    "DaemonLock",
    "OfflinePosture",
    "OpsError",
    "RestoreResult",
    "ServiceUnit",
    "backup_home",
    "clear_daemon_lock",
    "daemon_alive",
    "install_service",
    "lock_path",
    "offline_posture",
    "read_daemon_lock",
    "render_service_unit",
    "restore_home",
    "write_daemon_lock",
]
