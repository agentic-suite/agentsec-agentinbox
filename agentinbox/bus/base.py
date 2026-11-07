"""AskBus contract and the two v0.1.0 drivers (M9, E12).

Design: ``docs/design/v0.1.0/bus.md``. Jobs move work at-least-once; the store remains the only
source of truth (D-13). A job can cause a delivery attempt and nothing else.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from agentinbox.store import canonical_json, parse_iso, to_iso, utcnow

DEFAULT_POLL_INTERVAL = 0.5
MAX_POLL_INTERVAL = 1.0
DEFAULT_DONE_KEEP = 1000


class BusError(Exception):
    """Base class for bus failures."""


class BusLockedError(BusError):
    """Another daemon already owns this filesystem spool."""


class JobKind(StrEnum):
    DELIVER = "deliver"
    RENOTIFY = "renotify"
    ESCALATE = "escalate"
    DIGEST = "digest"
    EXPIRE = "expire"


@dataclass(frozen=True, slots=True)
class Job:
    """A movement job. It carries no answer, principal, or claim — ever."""

    job_id: str
    kind: JobKind
    ask_id: str
    created_at: datetime
    not_before: datetime | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    attempts: int = 0

    def due(self, at: datetime) -> bool:
        return self.not_before is None or self.not_before <= at

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind.value,
            "ask_id": self.ask_id,
            "created_at": to_iso(self.created_at),
            "not_before": None if self.not_before is None else to_iso(self.not_before),
            "payload": dict(self.payload),
            "attempts": self.attempts,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Job:
        raw_kind = data.get("kind")
        try:
            kind = JobKind(str(raw_kind))
        except ValueError:
            raise BusError(f"unknown job kind: {raw_kind!r}") from None
        not_before = data.get("not_before")
        payload = data.get("payload") or {}
        if not isinstance(payload, Mapping):
            raise BusError("job payload must be an object")
        return cls(
            job_id=str(data["job_id"]),
            kind=kind,
            ask_id=str(data["ask_id"]),
            created_at=parse_iso(str(data["created_at"])),
            not_before=None if not_before is None else parse_iso(str(not_before)),
            payload=payload,
            attempts=int(data.get("attempts", 0)),
        )

    @classmethod
    def from_json(cls, text: str) -> Job:
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise BusError(f"invalid job JSON: {exc}") from None
        if not isinstance(data, Mapping):
            raise BusError("job must be a JSON object")
        return cls.from_dict(data)


Handler = Callable[[Job], None]


class JobPublisher(Protocol):
    """Anything a producer may publish through (a bus or a lock-free spool writer)."""

    def publish(self, job: Job) -> bool: ...

    def upsert(self, job: Job) -> bool:
        """Publish, replacing an existing job with the same id (rolling digests)."""
        ...

    def close(self) -> None: ...


class AskBus(JobPublisher, Protocol):
    name: str

    def consume(self, handler: Handler) -> int: ...

    def run(self, handler: Handler, stop: threading.Event) -> None: ...

    def close(self) -> None: ...


def new_job(
    kind: JobKind,
    *,
    ask_id: str,
    now: datetime,
    not_before: datetime | None = None,
    payload: Mapping[str, Any] | None = None,
    job_id: str | None = None,
) -> Job:
    return Job(
        job_id=job_id or uuid.uuid4().hex,
        kind=kind,
        ask_id=ask_id,
        created_at=now,
        not_before=not_before,
        payload=dict(payload or {}),
    )


def publish_digest(
    bus: JobPublisher,
    *,
    window_start: datetime,
    first_ask_id: str,
    count: int,
    now: datetime,
    agent_id: str | None = None,
) -> bool:
    """The flood-before-bus rule: one deterministic digest job per window."""
    return bus.upsert(
        Job(
            job_id=f"digest:{to_iso(window_start)}",
            kind=JobKind.DIGEST,
            ask_id=first_ask_id,
            created_at=now,
            payload={
                "window_start": to_iso(window_start),
                "count": count,
                "agent_id": agent_id,
            },
        )
    )


# --------------------------------------------------------------------------- in-proc driver


class InProcBus:
    """Default driver: jobs are function calls with the same semantics."""

    name = "in-proc"

    def __init__(self, *, now: Callable[[], datetime] = utcnow) -> None:
        self._now = now
        self._jobs: dict[str, Job] = {}
        self._seen: set[str] = set()
        self._closed = False

    def publish(self, job: Job) -> bool:
        self._require_open()
        if job.job_id in self._seen:
            return False
        self._seen.add(job.job_id)
        self._jobs[job.job_id] = job
        return True

    def upsert(self, job: Job) -> bool:
        self._require_open()
        self._seen.add(job.job_id)
        self._jobs[job.job_id] = job
        return True

    def consume(self, handler: Handler) -> int:
        self._require_open()
        now = self._now()
        count = 0
        for job in sorted(self._jobs.values(), key=lambda item: (item.created_at, item.job_id)):
            if not job.due(now):
                continue
            handler(job)
            del self._jobs[job.job_id]
            count += 1
        return count

    def run(self, handler: Handler, stop: threading.Event) -> None:
        while not stop.is_set():
            self.consume(handler)
            stop.wait(DEFAULT_POLL_INTERVAL)

    def close(self) -> None:
        self._closed = True
        self._jobs.clear()

    def _require_open(self) -> None:
        if self._closed:
            raise BusError("bus is closed")


# --------------------------------------------------------------------------- filesystem spool


class SpoolBus:
    """Durable single-box driver: atomic rename, fsync, flock, bounded poll."""

    name = "filesystem"

    def __init__(
        self,
        root: Path | str,
        *,
        now: Callable[[], datetime] = utcnow,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        done_keep: int = DEFAULT_DONE_KEEP,
    ) -> None:
        if poll_interval <= 0 or poll_interval > MAX_POLL_INTERVAL:
            raise BusError(
                f"poll_interval must be >0 and <={MAX_POLL_INTERVAL}s (got {poll_interval})"
            )
        self.root = Path(root)
        self.jobs_dir = self.root / "jobs"
        self.done_dir = self.root / "done"
        self.locks_dir = self.root / "locks"
        self.tmp_dir = self.root / "tmp"
        for directory in (self.root, self.jobs_dir, self.done_dir, self.locks_dir, self.tmp_dir):
            directory.mkdir(parents=True, exist_ok=True)
            _chmod(directory, 0o700)

        self.poll_interval = poll_interval
        self._now = now
        self._done_keep = done_keep
        self._closed = False
        self._lock_path = self.locks_dir / "bus.lock"
        self._lock_handle = open(self._lock_path, "a+", encoding="utf-8")  # noqa: SIM115
        _chmod(self._lock_path, 0o600)
        try:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock_handle.close()
            raise BusLockedError(
                f"another daemon owns the spool: {self.root}"
            ) from None

        self.sweep_tmp()
        self.prune_done()

    # ------------------------------------------------------------------ contract

    def publish(self, job: Job) -> bool:
        self._require_open()
        target = self.jobs_dir / f"{job.job_id}.json"
        if target.exists() or (self.done_dir / target.name).exists():
            return False
        return self._write(job, replace=False)

    def upsert(self, job: Job) -> bool:
        self._require_open()
        target = self.jobs_dir / f"{job.job_id}.json"
        if (self.done_dir / target.name).exists():
            return False
        return self._write(job, replace=True)

    def consume(self, handler: Handler) -> int:
        self._require_open()
        now = self._now()
        count = 0
        for job in self._pending():
            if not job.due(now):
                continue
            handler(job)
            self._complete(job.job_id)
            count += 1
        return count

    def run(self, handler: Handler, stop: threading.Event) -> None:
        while not stop.is_set():
            self.consume(handler)
            stop.wait(self.poll_interval)

    def close(self) -> None:
        if self._closed:
            return
        try:
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._lock_handle.close()
            self._closed = True

    # ------------------------------------------------------------------ maintenance

    def sweep_tmp(self) -> None:
        for path in self.tmp_dir.glob("*.tmp"):
            path.unlink(missing_ok=True)

    def prune_done(self, keep: int | None = None) -> None:
        limit = self._done_keep if keep is None else keep
        files = sorted(
            self.done_dir.glob("*.json"), key=lambda path: path.stat().st_mtime_ns
        )
        doomed = files if limit <= 0 else files[:-limit]
        for path in doomed:
            path.unlink(missing_ok=True)

    # ------------------------------------------------------------------ internals

    def _write(self, job: Job, *, replace: bool) -> bool:
        return _write_job_file(
            self.jobs_dir, self.tmp_dir, job, replace=replace
        )

    def _pending(self) -> list[Job]:
        jobs = []
        for path in self.jobs_dir.glob("*.json"):
            try:
                jobs.append(Job.from_json(path.read_text(encoding="utf-8")))
            except (OSError, KeyError, ValueError) as exc:
                raise BusError(f"unreadable job {path}: {exc}") from None
        jobs.sort(key=lambda item: (item.created_at, item.job_id))
        return jobs

    def _complete(self, job_id: str) -> None:
        source = self.jobs_dir / f"{job_id}.json"
        destination = self.done_dir / f"{job_id}.json"
        if source.exists():
            os.replace(source, destination)
            _fsync_dir(self.done_dir)
        self.prune_done()

    def _require_open(self) -> None:
        if self._closed:
            raise BusError("bus is closed")


class SpoolPublisher:
    """Lock-free producer side of the filesystem spool (the daemon owns the consume lock)."""

    name = "filesystem"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.jobs_dir = self.root / "jobs"
        self.done_dir = self.root / "done"
        self.tmp_dir = self.root / "tmp"
        for directory in (self.root, self.jobs_dir, self.done_dir, self.tmp_dir):
            directory.mkdir(parents=True, exist_ok=True)
            _chmod(directory, 0o700)

    def publish(self, job: Job) -> bool:
        target = self.jobs_dir / f"{job.job_id}.json"
        if target.exists() or (self.done_dir / target.name).exists():
            return False
        return _write_job_file(self.jobs_dir, self.tmp_dir, job, replace=False)

    def upsert(self, job: Job) -> bool:
        target = self.jobs_dir / f"{job.job_id}.json"
        if (self.done_dir / target.name).exists():
            return False
        return _write_job_file(self.jobs_dir, self.tmp_dir, job, replace=True)

    def close(self) -> None:
        return None


def _write_job_file(
    jobs_dir: Path, tmp_dir: Path, job: Job, *, replace: bool
) -> bool:
    staging = tmp_dir / f"{job.job_id}.{uuid.uuid4().hex}.tmp"
    target = jobs_dir / f"{job.job_id}.json"
    data = job.to_json().encode("utf-8")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        if replace:
            os.replace(staging, target)
        else:
            # rename-CAS: link() is atomic and fails loudly if the id already exists.
            os.link(staging, target)
            os.unlink(staging)
    except FileExistsError:
        staging.unlink(missing_ok=True)
        return False
    _fsync_dir(jobs_dir)
    return True


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _chmod(path: Path, mode: int) -> None:
    with contextlib.suppress(OSError):  # pragma: no cover - exotic filesystems
        os.chmod(path, mode)


__all__ = [
    "DEFAULT_DONE_KEEP",
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "AskBus",
    "BusError",
    "BusLockedError",
    "Handler",
    "InProcBus",
    "Job",
    "JobKind",
    "JobPublisher",
    "SpoolBus",
    "SpoolPublisher",
    "new_job",
    "publish_digest",
]
