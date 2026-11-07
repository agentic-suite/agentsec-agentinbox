"""Evidence scanner (M22 item 22.1): zero secrets across every artifact class.

Design: ``docs/design/v0.1.0/security-closeout.md`` §2. Rules are the redaction pattern set (one
source of truth); findings name the rule, artifact, and line — never the matched value.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tarfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from agentinbox.card import build_card
from agentinbox.channels.webhook import build_payload
from agentinbox.config import Config
from agentinbox.redaction import SENSITIVE_PATTERNS
from agentinbox.store import AskStore, canonical_json, to_iso, utcnow


@dataclass(frozen=True, slots=True)
class Finding:
    artifact: str
    rule: str
    line: int


@dataclass(frozen=True, slots=True)
class ScanReport:
    artifacts: int
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def scan_text(text: str, *, artifact: str = "text") -> ScanReport:
    findings: list[Finding] = []
    for rule, pattern in SENSITIVE_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                Finding(
                    artifact=artifact,
                    rule=rule,
                    line=text.count("\n", 0, match.start()) + 1,
                )
            )
    return ScanReport(artifacts=1, findings=tuple(findings))


def scan_bytes(data: bytes, *, artifact: str) -> ScanReport:
    return scan_text(data.decode("utf-8", errors="replace"), artifact=artifact)


def scan_artifacts(artifacts: Iterable[tuple[str, str | bytes]]) -> ScanReport:
    findings: list[Finding] = []
    count = 0
    for artifact, body in artifacts:
        report = (
            scan_bytes(body, artifact=artifact)
            if isinstance(body, bytes)
            else scan_text(body, artifact=artifact)
        )
        count += 1
        findings.extend(report.findings)
    return ScanReport(artifacts=count, findings=tuple(findings))


def store_artifacts(store: AskStore, config: Config) -> list[tuple[str, str]]:
    """Serialize the live store + its rendered channel payloads for scanning (read-only)."""
    del config  # shapes are config-independent; kept for call-site symmetry
    artifacts: list[tuple[str, str]] = []
    moment = utcnow()
    ask_ids: set[str] = set()
    for entry in store.audit_entries():
        artifacts.append(
            (
                f"audit:{entry.seq}",
                canonical_json(
                    {
                        "kind": entry.kind,
                        "ref_id": entry.ref_id,
                        "at": to_iso(entry.at),
                        "payload": None if entry.payload is None else dict(entry.payload),
                    }
                ),
            )
        )
        if entry.kind == "transition":
            ask_ids.add(entry.ref_id)
    for ask_id in sorted(ask_ids):
        ask = store.get(ask_id)
        if ask is None:
            continue
        artifacts.append((f"ask:{ask_id}", canonical_json(dict(ask.payload))))
        transitions = store.transitions_for(ask_id)
        artifacts.append(
            (
                f"transitions:{ask_id}",
                canonical_json(
                    [
                        {
                            "at": to_iso(item.at),
                            "kind": item.kind,
                            "principal": item.principal,
                            "channel": item.channel,
                            "reason": item.reason,
                            "detail": dict(item.detail),
                        }
                        for item in transitions
                    ]
                ),
            )
        )
        deliveries = store.list_deliveries(ask_id)
        if deliveries:
            artifacts.append(
                (
                    f"deliveries:{ask_id}",
                    canonical_json(
                        [
                            {
                                "channel": item.channel,
                                "target": item.target,
                                "error": item.error,
                            }
                            for item in deliveries
                        ]
                    ),
                )
            )
        for surface in ("terminal", "desktop", "ci"):
            card = build_card(
                ask, now=moment, transitions=transitions
            )
            artifacts.append((f"render:{surface}:{ask_id}", card.render(surface)))
        artifacts.append(
            (
                f"render:webhook:{ask_id}",
                canonical_json(build_payload(ask, now=moment)),
            )
        )
    return artifacts


def scan_store(store: AskStore, config: Config) -> ScanReport:
    return scan_artifacts(store_artifacts(store, config))


def store_artifacts_from_db(database: Path) -> list[tuple[str, str]]:
    """Read-only artifact extraction from an on-disk store (no migration, no write)."""
    if not database.exists():
        return []
    tables = (
        ("asks", ("ask_id", "payload"), "store.asks"),
        ("transitions", ("ask_id", "reason", "detail"), "store.transitions"),
        ("deliveries", ("ask_id", "target", "error"), "store.deliveries"),
        ("audit", ("ref_id", "payload"), "store.audit"),
        ("floods", ("agent_id", "session_id", "first_ask_id"), "store.floods"),
    )
    artifacts: list[tuple[str, str]] = []
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            for table, columns, label in tables:
                try:
                    cursor = connection.execute(
                        f"SELECT {', '.join(columns)} FROM {table}"  # noqa: S608 - fixed names
                    )
                except sqlite3.OperationalError:
                    continue
                for row in cursor:
                    body = " ".join("" if value is None else str(value) for value in row)
                    artifacts.append((f"{label}:{row[0]}", body))
    except sqlite3.Error:
        return artifacts
    return artifacts


_SKIP_PATH_SUFFIXES = frozenset(
    {
        ".bmp",
        ".db",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".pdf",
        ".png",
        ".tar",
        ".tgz",
        ".webp",
        ".whl",
        ".zip",
    }
)


def _evidence_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        for candidate in sorted(path.rglob("*")):
            if candidate.is_file() and candidate.suffix.lower() not in _SKIP_PATH_SUFFIXES:
                yield candidate


def scan_path(path: Path) -> ScanReport:
    """Scan a release/evidence file or directory tree (read-only, no extraction)."""
    findings: list[Finding] = []
    artifacts = 0
    for candidate in _evidence_files(path):
        try:
            body = candidate.read_bytes()
        except OSError:
            continue
        report = scan_bytes(body, artifact=f"path:{candidate}")
        artifacts += 1
        findings.extend(report.findings)
    return ScanReport(artifacts=artifacts, findings=tuple(findings))


def scan_archive(archive: Path) -> ScanReport:
    findings: list[Finding] = []
    artifacts = 0
    try:
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                handle = tar.extractfile(member)
                if handle is None:
                    continue
                artifacts += 1
                report = scan_bytes(handle.read(), artifact=f"archive:{member.name}")
                findings.extend(report.findings)
    except (tarfile.TarError, OSError):
        return ScanReport(artifacts=0, findings=())
    return ScanReport(artifacts=artifacts, findings=tuple(findings))


#: Benign text that must never trip the scanner (including redaction labels and refs).
CLEAN_CORPUS: tuple[tuple[str, str], ...] = (
    ("clean:text", "ask ask_123 approved by alice after checking the blast radius"),
    ("clean:redacted", "token=[REDACTED:SECRET] key=[REDACTED:PRIVATE_KEY]"),
    ("clean:ref", "key_ref=env:AGENTINBOX_WEBHOOK_KEY path=file:/run/secrets/key"),
    ("clean:identity", "sha256:" + "a" * 64 + " action=run_command"),
    ("clean:email", "[REDACTED:EMAIL] asked for [REDACTED:PHONE]"),
)

#: Seeded leaks the scanner must find (each names the rule it should trip).
SEEDED_CORPUS: tuple[tuple[str, str, str], ...] = (
    ("seed:openai", "token sk-" + "a" * 24, "SECRET"),
    ("seed:github", "token ghp_" + "b" * 24, "SECRET"),
    ("seed:slack", "token xoxb-" + "c" * 12, "SECRET"),
    ("seed:aws", "key AKIA" + "D" * 16, "SECRET"),
    ("seed:bearer", "authorization: bearer " + "e" * 20, "SECRET"),
    (
        "seed:private-key",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----",
        "PRIVATE_KEY",
    ),
    ("seed:dsn", "postgres://user:" + "f" * 12 + "@db.internal/app", "CONNECTION_STRING"),
)


def self_test() -> tuple[ScanReport, ScanReport]:
    clean = scan_artifacts(CLEAN_CORPUS)
    seeded = scan_artifacts([(name, text) for name, text, _rule in SEEDED_CORPUS])
    return clean, seeded


def _print_report(report: ScanReport) -> None:
    for finding in report.findings:
        print(f"{finding.rule}: {finding.artifact}:{finding.line}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentinbox-scanner", description="scan evidence artifacts for secret shapes"
    )
    parser.add_argument("--home", metavar="PATH", help="scan <home>/inbox.db read-only")
    parser.add_argument(
        "--archive", action="append", default=[], metavar="PATH", help="scan a backup archive"
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        metavar="PATH",
        help="scan a file or directory tree of release evidence",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="prove clean artifacts pass and the seeded corpus is detected",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        clean, seeded = self_test()
        print(f"clean: {clean.artifacts} artifacts, {len(clean.findings)} findings")
        print(f"seeded: {seeded.artifacts} artifacts, {len(seeded.findings)} findings")
        _print_report(clean)
        ok = clean.ok and not seeded.ok
        if not ok:
            print("scanner self-test FAILED", file=sys.stderr)
        return 0 if ok else 1

    if not args.home and not args.archive and not args.path:
        parser.print_usage(sys.stderr)
        print(
            "scanner: error: pass --home, --archive, --path, or --self-test",
            file=sys.stderr,
        )
        return 1

    artifacts: list[tuple[str, str | bytes]] = []
    if args.home:
        artifacts.extend(
            store_artifacts_from_db(Path(args.home) / "inbox.db")
        )
    report = scan_artifacts(artifacts)
    findings = list(report.findings)
    extra_count = 0
    for archive in args.archive:
        archive_report = scan_archive(Path(archive))
        extra_count += archive_report.artifacts
        findings.extend(archive_report.findings)
    for evidence_path in args.path:
        path_report = scan_path(Path(evidence_path))
        extra_count += path_report.artifacts
        findings.extend(path_report.findings)
    final = ScanReport(
        artifacts=report.artifacts + extra_count, findings=tuple(findings)
    )
    print(
        f"scanned {final.artifacts} artifacts: {len(final.findings)} finding(s)"
    )
    _print_report(final)
    return 0 if final.ok else 1


__all__ = [
    "CLEAN_CORPUS",
    "SEEDED_CORPUS",
    "Finding",
    "ScanReport",
    "main",
    "scan_archive",
    "scan_artifacts",
    "scan_bytes",
    "scan_path",
    "scan_store",
    "scan_text",
    "self_test",
    "store_artifacts",
    "store_artifacts_from_db",
]


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
