# Operations design — v0.1.0 (M21)

**BLUF:** the inbox runs like infrastructure without becoming infrastructure: **user-scoped** service
units (no root), **WAL-safe** backups that carry evidence but never secrets, forward-only migrations
that refuse downgrade loudly, a **local-only** `report`, a proven **offline day**, and recorded
performance floors. Nothing in this milestone adds a network dependency or a telemetry path.

- **Milestone:** M21 ([WBS Part 11](../../wbs/v0.1.0/wbs-v0.1.0-part11-failclosed-ops.md), issues #62–#73)
- **Requirements:** E10, N-1..N-7, N-19, N-26, N-27, N-28 · PRD 22 §A–§E, PRD 07, PRD 13, PRD 20 §F

---

## 1. Service units (`serve --install`)

`agentinbox serve --install` writes a **user-scoped** unit and prints its path; it never calls
`sudo`, never writes outside the user's home, and never starts the service itself.

| Platform | File | Supervisor behaviour |
|---|---|---|
| macOS | `~/Library/LaunchAgents/com.agentsec.agentinbox.plist` | `RunAtLoad=true`, `KeepAlive=false` (launchd owns restarts), `SIGTERM` on stop |
| Linux | `~/.config/systemd/user/agentinbox.service` | `Restart=on-failure`, `WantedBy=default.target`, `KillSignal=SIGTERM` |

The rendered `ProgramArguments`/`ExecStart` is the **absolute interpreter + module** form
(`/path/to/python -m agentinbox --home <home> --config <config> serve`) so the unit does not depend
on the caller's shell or `PATH`. Logs go to `<home>/logs/serve.log` and `<home>/logs/serve.err`
(0600 files, 0700 directories).

**Shutdown contract.** `serve` handles `SIGTERM`/`SIGINT` by setting the stop event: it stops
accepting work (the API closes, the bus stops consuming), flushes the buffered event sink, and closes
the store cleanly. The daemon writes `<home>/serve.lock` (JSON: `pid`, `started_at`) while running and
removes it on exit. A `gate --wait` that started while the daemon was alive but sees the daemon gone
returns **exit 4** (unavailable), never a hang and never an approval.

**Restart.** On start the scheduler runs its recovery pass (M4): persisted absolute deadlines are
recomputed, overdue transitions fire exactly once, and pending asks are adopted. A restart never
changes an ask's `expires_at`.

## 2. Backup and restore

### Backup — `agentinbox doctor --backup out.tar`

The archive is a plain (uncompressed) tar, mode `0600`, containing exactly:

| Member | Contents |
|---|---|
| `manifest.json` | `backup/1.0`, created_at, agentinbox version, schema version, chain head hash, counts (asks/transitions/audit), file list |
| `inbox.db` | a **SQLite online-backup** copy (`Connection.backup`) — WAL-safe, consistent without stopping the daemon |
| `config.toml` | the config file as written; secrets are references (`env:`/`file:`) by construction |
| `keys/slots.json` | key **slot metadata**: reference strings only (producer/webhook), never resolved values |

Never in the archive: resolved secret values, `api-token`, the spool, exports, or event logs. The
backup does not modify the source store and does not append an audit entry (a backup is not a
decision).

### Restore — `agentinbox doctor --restore in.tar` into a fresh `AGENTINBOX_HOME`

1. Refuse a non-empty home unless `--force`.
2. Extract into a sibling staging directory; reject absolute paths, `..`, and unknown members.
3. Verify `manifest.json` (contract, schema version not newer than this build).
4. Open the restored store and **verify the audit chain**; any gap/hash mismatch aborts the restore
   loudly and leaves the destination untouched.
5. Move the staging tree into the home with `0700`/`0600` modes.
6. Expire overdue pending asks **once** (scheduler recovery semantics). A restored box never
   resurrects an expired approval: expiry is derived from the persisted `expires_at`, not from the
   backup's age, and an approved/denied decision is never rewritten.

`doctor` then runs its normal checks on the restored home; the chain check is the acceptance gate.

## 3. Migrations and compatibility

- **Forward only.** `MIGRATIONS[from_version]` is applied in order inside one transaction; a failed
  step rolls back to the old version. Every released version has an old-store fixture.
- **Downgrade refuses loudly.** A store newer than the build raises `SchemaVersionError` with the
  exact versions and the next action; `doctor` reports it red. No migration is guessed backwards.
- **Additive-only within v0.x.** The frozen surface is versioned in `agentinbox/compat.py`:
  `ask/1.0`, `resolve/1.0`, `webhook/1.0`, `export/1.0`, `backup/1.0`, the exit-code integers
  (`0/1/2/3/4/5`), and the agentwatch event vocabulary. New optional fields/events may be added;
  removing or repurposing one is a breaking change and is refused by the compatibility test matrix.

## 4. `report --json`

`report` computes PRD 07 metrics from the owner's own store/audit stream and prints JSON (or a short
human summary). It never opens a socket and never writes an export.

| Field | Definition |
|---|---|
| `response_time_s.p50` / `.p99` | answered asks only: first successful delivery → answer transition; `created_at` is the fallback when no delivery exists. Nearest-rank percentile. |
| `expiries` | asks that reached `expired` |
| `escalation_firings` | `ask-escalated` transitions |
| `flood_events` | distinct flood windows in the audit chain |
| `answer_rejected_causes` | normalized causes (`bad_signature`, `late`, `off_roster`, …) from rejected/late answers |
| `deny_rate_by_class` | per class: `(denied + flood_denied + expired) / resolved` |
| `pending`, `total_asks` | current pending count and distinct asks seen in the chain |

`local_only: true` is part of the contract: the artifact is shareable by choice, never emitted.

## 5. Offline posture (CUJ-12 / SC-26)

Offline-complete means: with the network down and external channels disabled, `ingest → card →
answer → gate → audit → export → verify-log → doctor` all work, and nothing calls out.

- `doctor` gains an `offline` check: green when no external channel is enabled (or all are disabled
  in config); a warning naming the enabled channel otherwise. It never probes the network.
- The only network code in the package is the webhook adapter (enabled explicitly). Terminal,
  desktop, CI, audit, export, report, backup, and restore are local.
- No telemetry, ever: there is no analytics module, endpoint, or background sender.

## 6. Performance floors (N-1..N-7)

`agentinbox/bench.py` measures the floors with the real store and channels; a test runs the set and
asserts the documented thresholds. Results are recorded in the release notes at M33.

| NFR | Floor | Bench |
|---|---|---|
| N-1 ingest | p50 < 50 ms, p99 < 250 ms | 200 sequential ingests |
| N-2 terminal render | < 100 ms | card render after ingest |
| N-3a desktop | < 1 s p99 | adapter call (skipped when unavailable) |
| N-3b external | < 2 s p50 | mock webhook over loopback |
| N-3c bus pickup | ≤ 1 s | spool publish → consume |
| N-4 resolve | p99 < 100 ms | resolve after answer |
| N-5 scheduler jitter | ≤ 1 s | warn/expire at a configured instant |
| N-6 load | floors hold at 10k resolved + 100 pending | seeded load fixture |
| N-7 startup + doctor | < 2 s cold | open store + run checks |

## 7. Tests

| Area | File |
|---|---|
| units, shutdown, gate availability | `tests/ops/test_units.py` |
| backup/restore/secret absence/expiry | `tests/ops/test_backup.py` |
| compatibility matrix + migrations | `tests/ops/test_compat.py` |
| report metrics | `tests/ops/test_report.py` |
| offline day | `tests/ops/test_offline.py` |
| performance floors | `tests/ops/test_bench.py` |

## 8. Non-goals

- No root/system-wide install, no Windows service wrapper (POSIX only, N-17).
- No backup encryption in v0.1.0; the archive is `0600` inside the user's home and the operator owns
  key custody. Secrets remain references, so a stolen archive does not hand over signing keys.
- No cloud upload, no scheduled backup daemon, no remote report.
