# Operations reference (v0.1.0 · M21)

**BLUF:** install as a user service, back up without stopping the daemon, restore with a verified
chain, upgrade forward only, read metrics locally, and run the offline day with no network. Nothing
here adds a cloud dependency or a telemetry path.

- Design of record: [`docs/design/v0.1.0/ops.md`](../design/v0.1.0/ops.md)
- Runbook: [`docs/runbooks/ops.md`](../runbooks/ops.md)
- Compatibility matrix: [`agentinbox/compat.py`](../../agentinbox/compat.py)

## Install as a service (no root)

```sh
agentinbox --home "$HOME/.agentinbox" serve --install
```

Writes a **user-scoped** unit and prints its path:

| Platform | Path | Start |
|---|---|---|
| macOS | `~/Library/LaunchAgents/com.agentsec.agentinbox.plist` | `launchctl bootstrap gui/$(id -u) <path>` |
| Linux | `~/.config/systemd/user/agentinbox.service` | `systemctl --user daemon-reload && systemctl --user enable --now agentinbox` |

The unit runs `python -m agentinbox --home <home> --config <config> serve`, starts at login, and
lets the supervisor own restarts. Logs: `<home>/logs/serve.log`, `<home>/logs/serve.err` (mode
`0600`). An invalid config is refused — no unit is written.

**Stop:** SIGTERM. The daemon stops accepting work (API closes, bus stops), flushes the buffered
event sink, and closes the store. The `<home>/serve.lock` disappears; a `gate --wait` that started
while the daemon was alive returns **exit 4** (unavailable) instead of hanging.

## Backup

```sh
agentinbox --home "$HOME/.agentinbox" doctor --backup /secure/agentinbox-2026-11-07.tar
```

- Uses the **SQLite online-backup** path: consistent while the daemon is writing (WAL-safe).
- Contains `manifest.json`, `inbox.db`, `config.toml`, and `keys/slots.json`.
- `keys/slots.json` is **reference metadata only** (`env:NAME`, `file:/path`). Resolved secrets,
  `api-token`, the spool, exports, and logs are never included.
- The archive is `0600`; the backup refuses to package a store whose audit chain does not verify.

## Restore

```sh
agentinbox --home /fresh/agentinbox doctor --restore /secure/agentinbox-2026-11-07.tar
agentinbox --home /fresh/agentinbox doctor --restore /secure/backup.tar --force   # replace
```

Restore extracts to a staging directory first, verifies the manifest contract, refuses a schema
newer than the build, and **verifies the audit chain**; any mismatch aborts and leaves the target
untouched. Then it installs the files `0700`/`0600`, expires overdue pending asks once (scheduler
recovery semantics), and runs the normal `doctor` checks.

A restored box never resurrects an expired approval: expiry is derived from the persisted
`expires_at`, and approved/denied decisions are never rewritten.

## Upgrade / migrations

- Store schema migrates **forward on open** inside one transaction; a failed step rolls back.
- A store newer than the build **refuses loudly** (`SchemaVersionError`, `doctor` schema red).
- `ask/1.0`, `resolve/1.0`, `webhook/1.0`, `export/1.0`, `backup/1.0`, `report/1.0`, the exit codes
  `0/1/2/3/4/5`, and the event vocabulary are additive-only within v0.x. The matrix and its
  additive check live in `agentinbox/compat.py`; `tests/ops/test_compat.py` fails on a breaking
  change.

## `report --json` (local only)

```sh
agentinbox --home "$HOME/.agentinbox" report --json
```

Computed from your own audit chain, never emitted anywhere:

| Field | Meaning |
|---|---|
| `response_time_s.p50` / `.p99` / `.samples` | answered asks: first delivery (or create) → answer; nearest-rank |
| `expiries` | asks that reached `expired` |
| `escalation_firings` | `ask-escalated` transitions |
| `flood_events` | distinct flood windows |
| `answer_rejected_causes` | normalized causes (`bad_signature`, `late`, `off_roster`, …) |
| `deny_rate_by_class` | `(denied + flood_denied + expired) / resolved` per class |
| `pending`, `total_asks` | current pending and distinct asks in the chain |

`local_only: true` is part of the contract. There is no telemetry module, endpoint, or sender.

## Offline day

Disable external channels (`[channels.webhook] enabled = false`, the scaffold default) and run with
the network down. Terminal, desktop, CI checkpoint, audit, export, `verify-log`, `report`, backup,
and restore are local. `doctor` reports `offline-complete`; if an external channel is enabled it
warns and names it but never probes the network. See [SC-26](../prd/17-scenarios.md) (re-run at
M24/M32).

## Performance floors (N-1..N-7)

`agentinbox/bench.py` measures the floors with the real store/channel paths; the recorded results
belong in the release notes at M33.

| NFR | Floor | Bench |
|---|---|---|
| N-1 | ingest p50 < 50 ms, p99 < 250 ms | 200 sequential ingests |
| N-2 | terminal render < 100 ms | card render |
| N-3b | external delivery p50 < 2 s (mocked) | webhook channel |
| N-3c | spool pickup ≤ 1 s | publish → consume |
| N-4 | resolve p99 < 100 ms | resolve after answer |
| N-5 | scheduler tick ≤ 1 s | 100 pending asks |
| N-6 | 10k resolved + 100 pending holds N-1 | in-memory load fixture |
| N-7 | startup + doctor < 2 s cold | open store + checks |
