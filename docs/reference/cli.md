# CLI reference (v0.1.0 · M0–M21)

**BLUF:** `agentinbox` is one binary surface with two entry points (`agentinbox` and
`python -m agentinbox`), one **reserved exit-code contract**, and thirteen commands. Every command is
implemented as of M21; nothing in the CLI can approve by default.

- Design of record: [`docs/design/v0.1.0/foundation.md`](../design/v0.1.0/foundation.md)
- Config reference: [config.md](config.md)

## Invocation

```sh
agentinbox [global options] <command> [command options]
python -m agentinbox [global options] <command> [command options]
```

Both forms are identical (same parser, same exit codes, same output).

| Global option | Meaning |
|---|---|
| `--help` | usage, exit `0` |
| `--version` | version, exit `0` |
| `--config PATH` | config file (absolute); default `<home>/config.toml` |
| `--home PATH` | home directory (absolute); overrides `AGENTINBOX_HOME` |
| `--json` | machine-readable output where the command emits structured data |
| `--no-color` | disable color output |

Global options are parsed before the command. Unknown commands and unknown global options are
usage errors (exit `1`).

## Exit codes (reserved, stable)

| Code | Name | Meaning | CI treatment |
|---|---|---|---|
| `0` | `APPROVED` | approved / allow — the **only** approval code | success |
| `2` | `DENIED` | denied by a human | failure |
| `3` | `EXPIRED` | expired / timeout (deny class) | failure |
| `4` | `UNAVAILABLE` | unavailable / fail-closed — no decision was possible | failure |
| `5` | `PENDING` | still pending; poll again | **retry** |
| `1` | `USAGE` | usage error or internal error | failure |

Two rules matter in practice:

- `4` is used for every fail-closed condition (bad/missing config, unwritable home, unsupported
  platform, unimplemented command). It is **not** `1`; `1` means the caller made a mistake.
- `2` is never produced by the CLI's own argument parsing (argparse's default of `2` is
  overridden), so a pipeline cannot mistake a typo for a denial.

The mapping lives in `agentinbox.exit_codes`; `tests/contract/exit_codes.py` pins the literal
integers so the contract cannot drift.

## Commands

| Command | Status |
|---|---|
| `init` | **works** — creates the private home skeleton and a valid `config.toml`; refuses an existing config unless `--force` |
| `doctor` | **works** — exit-coded install checks; `--explain` prints the effective config; `--json` emits records |
| `version` | **works** — prints `agentinbox <version>` (or JSON with `--json`) |
| `inbox`, `answer` | **works** (M7) — list pending asks; answer via the terminal channel |
| `serve` | **works** (M9) — scheduler + bus consumer; `--once` drains and exits; see [bus.md](bus.md) |
| `gate` | **works** (M10) — CI checkpoint with the reserved exit codes; see [gate.md](gate.md) |
| `channels` | **works** (M13) — configured channels and health |
| `export`, `verify-log` | **works** (M15) — ordered evidence + chain verification; see [audit.md](audit.md) |
| `ask` | **works** (M18) — `--file` / `--exec`; only executes on allow; see [producer-guide.md](../adapters/producer-guide.md) |
| `conformance` | **works** (M19) — contract conformance kit; see [conformance.md](conformance.md) |
| `report` | **works** (M21) — local PRD 07 metrics; `--json`; see [ops.md](ops.md) |

No command is a stub in v0.1.0. `--help` always exits `0` and never reads config or state; a command
never exits `0` except for a real approval (or a successful non-decision operation such as
`doctor`/`export`/`report`).

## `init`

```sh
agentinbox init [--force]
agentinbox --home /srv/inbox init
AGENTINBOX_HOME=/srv/inbox agentinbox init
```

Creates `<home>` (mode `0700`), `<home>/config.toml` (mode `0600`), and the empty
`spool/{jobs,done,locks}`, `keys`, `logs`, `exports` directories. The scaffold parses and
validates with the real loader — it is a working config, not a decoration.

Exit codes: `0` written; `4` existing config without `--force`, relative/empty home, or an
unwritable location.

## `doctor`

```sh
agentinbox doctor
agentinbox doctor --explain
agentinbox doctor --backup /secure/backup.tar
agentinbox doctor --restore /secure/backup.tar [--force]
agentinbox --json doctor
```

| Check | Verifies | Fail example |
|---|---|---|
| `platform` | POSIX; Windows named as unsupported | `Windows is not supported in v0.1.0` |
| `home` | exists, is a directory, writable; warns on modes looser than `0700` | `home does not exist; run agentinbox init` |
| `config` | parses and validates ([config.md](config.md)) | `[classes.x].ttl_seconds: required positive integer` |
| `store-path` | `inbox.db` is `0600` when present | `mode 644 exposes the store; expected 600` |
| `schema` | `schema_version` is readable when a store exists | `unreadable schema version` |
| `clock` | UTC clock and monotonic time are sane | `system clock unavailable` |
| `desktop` | enabled desktop channel is reachable (disabled is `ok`) | `headless SSH session` |
| `offline` | no external channel enabled (warning names one) | — |
| `chain` | the audit hash chain verifies read-only | `audit seq 7: entry_hash does not verify` |
| `spool` | pending/done/staging counts; missing lock or staging is a warning | — |
| `keys` | producer/webhook references resolve | `env reference … is not set` |

Overall exit: `0` when no check fails (warnings allowed), `4` when any check fails. `--explain`
prints the effective config with secret **references** shown and never resolved.

`--backup PATH` writes a WAL-safe archive (chain-verified, secrets as references only) and exits
`0`/`4`. `--restore PATH` installs a backup into the current (fresh) home, verifies the chain, expires
overdue pending asks once, then runs the checks. A non-empty home requires `--force`. See
[ops.md](ops.md).

## `report`

```sh
agentinbox report
agentinbox report --json
```

Local PRD 07 metrics computed from your own audit chain: response-time p50/p99, expiries,
escalation firings, flood events, `answer-rejected` causes, deny rate by class, pending/total.
`local_only: true`; nothing leaves the machine. See [ops.md](ops.md).

## `conformance`

```sh
agentinbox conformance
agentinbox --json conformance
```

Runs the contract kit against a fresh in-memory store and exits `0` when every check passes, `4` otherwise. See
[conformance.md](conformance.md).

## `serve`

```sh
agentinbox serve                    # loopback API + scheduler + bus consumer
agentinbox serve --once             # tick the scheduler, drain the bus, exit
agentinbox serve --api-port 9000    # choose the loopback API port (default 8377)
agentinbox serve --no-api           # consumer only
agentinbox serve --install          # write a user-scoped launchd/systemd unit and exit
```

The daemon starts the loopback ingest API (127.0.0.1) and writes its bearer token to `<home>/api-token` (mode
`0600`); the token is never printed. `AGENTINBOX_API_TOKEN` overrides a generated token. Exit `0` on a clean
drain/stop; `4` for a bad config, an unavailable store, an occupied API port, or a spool already owned by another
daemon. SIGTERM stops accepting work, flushes events, closes the store, and removes `<home>/serve.lock`; a
waiting `gate` then exits `4`. See [bus.md](bus.md), [ops.md](ops.md), and
[producer-guide.md](../adapters/producer-guide.md).

## Environment

| Variable | Effect |
|---|---|
| `AGENTINBOX_HOME` | home directory (absolute); `--home` wins |
| `AGENTINBOX_WEBHOOK_URL`, `AGENTINBOX_WEBHOOK_HMAC` | example secret **references** used by the scaffold's webhook channel (`env:` refs); values are read only when the channel is implemented |

## Platform

POSIX (macOS, Linux). Python 3.11–3.13. Windows is not supported in v0.1.0 and says so.
