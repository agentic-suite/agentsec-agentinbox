# Foundation design — v0.1.0 (M0)

**BLUF:** M0 builds the skeleton only: an installable `agentsec-agentinbox` distribution exposing the
`agentinbox` package, console script, and `python -m agentinbox`; the **frozen CLI surface**; the **reserved
exit-code contract**; and a **fail-closed TOML config model** rooted at `AGENTINBOX_HOME` (default
`~/.agentinbox`). Nothing asks, answers, schedules, or persists yet — every unimplemented command refuses
honestly with exit `4` rather than pretending to work. The store layer is sketched here and frozen in M1
(`1.D0`); this document fixes only its layout, permissions, and version contract.

- **Milestone:** M0 Foundation & identity ([WBS Part 1](../../wbs/v0.1.0/wbs-v0.1.0-part1-foundation-store.md), issue #4)
- **Requirements:** PRD 02 §interfaces, PRD 13 N-13/N-16/N-18/N-20/N-36..N-39, PRD 15 §config/§storage, PRD 22 §C
- **Out of scope:** ask ingestion, lifecycle, scheduler, claims, channels, bus, audit chain (M1–M23). Config keys
  belonging to the forward slate (PRD 24–30) are rejected as unsupported, never silently ignored.

---

## 1. Identity & packaging

| Concern | Decision |
|---|---|
| Distribution name | `agentsec-agentinbox` (PyPI/SBOM identity) |
| Import package | `agentinbox` |
| Console script | `agentinbox` |
| Module invocation | `python -m agentinbox` (must behave identically — N-16) |
| Python | 3.11, 3.12, 3.13 (N-20) |
| Platform | POSIX only. **Windows is explicitly unsupported** and must say so on invocation, not fail obscurely |
| Runtime dependencies | **None** beyond the stdlib (`tomllib` for config, `argparse` for the CLI). Dev-only pins: `pytest`, `coverage`, `ruff`, `mypy` |
| Build backend | `hatchling`; single source of version in `agentinbox/version.py`, read by `pyproject.toml` |
| Console/`-m` parity | Both entry points call the same `agentinbox.cli.main(argv) -> int`; no logic in `__main__.py` or the script shim |

`pip install -e .` must succeed on a clean interpreter, and `agentinbox --help` plus
`python -m agentinbox --help` must list the full surface below.

> **Decision D-M0-1 — stdlib CLI.** M0 uses `argparse`, not a third-party CLI framework: zero runtime
> dependencies keeps the supply chain and the offline install honest (N-13). The TUI milestone (M7) may add
> `prompt_toolkit`/`rich` for interactive rendering only; the command surface and exit codes defined here do
> not change.

---

## 2. CLI surface (frozen in M0)

Global form: `agentinbox [global options] <command> [command options]`.
Global options are parsed once, before dispatch: `--help`, `--version`, `--config PATH`, `--home PATH`
(explicit override, wins over `AGENTINBOX_HOME`), `--json` (machine-readable output where a command emits
structured data), `--no-color`.

| Command | v0.1.0 intent (later milestone) | **M0 behavior** |
|---|---|---|
| `init` | Scaffold config + home layout (M1/M21) | Creates the doc's commented config scaffold only; refuses if a config exists unless `--force` |
| `doctor` | Validate store/config/schema/clock/channels (grows M1/M20/M21) | Real checks: home writable, config parses + validates, store path/permissions, schema version present-if-store-exists, system clock readable. Exit-coded per §3 |
| `version` | Print version + exit | Real: prints `agentinbox <version>`; `--json` emits `{name, version, python, platform}` |
| `channels` | List configured channels + health (M13/M14) | Stub → refuse `4` (except `--help`) |
| `ask` | Propose an ask, block or defer (M18) | Stub → refuse `4` |
| `inbox` | List/answer pending asks interactively (M7) | Stub → refuse `4` |
| `answer` | Answer a pending ask (M7) | Stub → refuse `4` |
| `serve` | Run the local daemon (M9/M21) | Stub → refuse `4` |
| `gate` | CI checkpoint; exit code is the decision (M10) | Stub → refuse `4` (never `0`, never a guessed decision) |
| `export` | Export asks/audit as JSONL (M15) | Stub → refuse `4` |
| `verify-log` | Verify the audit hash chain (M15) | Stub → refuse `4` |
| `report` | Success-metric report (M21) | Stub → refuse `4` |

Rules for the stubs (this is a security property, not politeness):

1. `--help` always exits `0` and never touches config or state.
2. A stub prints a one-line, actionable message to **stderr** — `agentinbox: <command> is not implemented in
   v0.1.0 (scheduled: <milestone>)` — and exits **`4`** (unavailable/fail-closed). It never exits `0` and never
   prints a decision-looking success.
3. An unknown command or invalid option prints usage to stderr and exits **`1`**.
4. No command auto-approves in a non-interactive context (PRD 02 §CLI); an absent TTY can only produce `4`
   (unavailable) or `5` (pending), never `0`.
5. `--json` switches structured output only; it never changes exit codes.

---

## 3. Exit-code contract (frozen; compatibility fixture)

The enum below is PRD 02 §"Exit codes (reserved, stable)". It is a **public compatibility contract** consumed
by CI and producers; it is asserted in exactly one test fixture and every command maps its result through the
same module (`agentinbox.exit_codes`).

| Code | Name | Meaning | CI treatment |
|---|---|---|---|
| `0` | `APPROVED` | Approved / allow | success |
| `2` | `DENIED` | Denied by a human | failure |
| `3` | `EXPIRED` | Expired / timeout (deny class) | failure |
| `4` | `UNAVAILABLE` | Unavailable / fail-closed (no decision possible) | failure |
| `5` | `PENDING` | Still pending; poll again | **retry** |
| `1` | `USAGE` | Usage error or internal error | failure |

Mapping rules:

- Terminal ask states map one-to-one (`approved→0`, `denied→2`, `expired→3`, `flood_denied→2`); pending maps
  to `5`. Unknown ask / identity mismatch must surface as `2` (deny) when a decision is being requested — never
  `0` (PRD 02 §decision contract). That mapping lives in the lifecycle module (M3/M6) and reuses the enum.
- `4` is the **only** code for "we could not produce a decision": missing/invalid config, unreadable or
  unwritable home, store unavailable, unsupported platform, unimplemented command.
- `1` is reserved for the caller's mistake (bad flags/subcommand) and for internal invariant violations. A
  fail-closed condition must never be reported as `1`, so operators can distinguish misuse from environment.
- Exit codes are `int`-valued; `IntEnum` is used in-process but the contract test asserts literal integers, so a
  future renumbering cannot slip in silently.

Fixture: `tests/contract/test_exit_codes.py` asserts the exact `{name: code}` map in one place; every other
test imports it (`from tests.contract.exit_codes import EXIT_CODES`) instead of re-listing numbers.

---

## 4. Home layout & `AGENTINBOX_HOME`

Resolution order (first hit wins; no implicit fallback after an explicit value is set):

1. `--home PATH` (CLI flag, M0)
2. `AGENTINBOX_HOME` environment variable
3. `~/.agentinbox` (default)

An empty string or a non-absolute path is a **config error** (`4`) — never silently expanded into a surprise
directory. `AGENTINBOX_HOME` is the supported multi-instance seam (servers, test matrices), and per-user homes
are the supported pattern until server mode (PRD 22 §C).

```
<home>/                     # 0700
  config.toml               # 0600; parsed, never rewritten by the daemon
  inbox.db                  # 0600; SQLite WAL (M1; created on first write)
  spool/                    # 0700; filesystem AskBus (M9)
    jobs/ done/ locks/
  keys/                     # 0700; claim-key slot (M6)
  logs/                     # 0700; rotating local logs (M20/M21)
  exports/                  # 0700; `export` output (never auto-written)
```

M0 creates only what it needs and never invents files: `init` creates `<home>` (0700), `config.toml` (0600),
and the empty directory skeleton; `doctor` reports what is missing or mis-permissioned. Directory-mode
normalization (`umask`-independent) and store-file permissions are asserted in tests.

**Store sketch (layout only — contract frozen in M1 `1.D0`):** one SQLite database, WAL, synchronous commits,
`0600`; tables `asks`, `transitions`, `claims`, `deliveries`, `floods`, `audit`; a `schema_version` table; the
indexes from PRD 15 §storage (pending-by-expiry, asks-by-session, asks-by-agent, transitions-by-ask-seq,
chain-by-seq). M0 must not create or migrate the store; `doctor` only reports whether it exists and whether its
schema version is readable. Forward migrations and loud downgrade refusal are M1.

`doctor --explain` prints the effective config (paths, driver selection, class resolution inputs) with secret
**references** shown, never resolved values.

---

## 5. Config model (TOML, fail-closed)

### 5.1 Loading & validation

- Parser: stdlib `tomllib` (read-only; config is never rewritten by the daemon).
- Validation target: typed, frozen dataclasses (`agentinbox.config`), parsed once at command start except for
  `--help` and `version`.
- **Fail closed:** any of the following exits `4` with a message naming the file, the key path, and the fix —
  never a silent default, never a partial config:
  - file missing (where the command requires config), unreadable, not valid UTF-8 TOML, duplicate keys;
  - unknown section or key (a typo must not silently disable a control). Keys for the forward slate are
    **known-unsupported** and produce "not supported in v0.1.0" rather than being ignored;
  - wrong type, negative/zero TTL, empty roster, delay ≥ TTL, invalid port or non-loopback bind, unknown driver
    name;
  - a literal secret where a `*_ref` is required (§5.3).
- World-writable config files and symlink policy are *deferred* to M20 hardening (`SC-24`, open question §8.3);
  M0 enforces `0600` and same-user ownership only.
- Unknown **environment** variables are irrelevant; only the explicit `AGENTINBOX_HOME` is read.

### 5.2 Schema (M0 subset, PRD 15 §config / PRD 22 §C)

```toml
# <home>/config.toml

[classes.<name>]              # ask classes; resolution rules land in M2/M3
ttl_seconds = 300             # required, > 0
warn_seconds = 60             # optional, 0 < warn < ttl
self_review = "deny"          # deny | allow | escalate  (default: deny)
require_reason_on_deny = true # optional, bool
ladder = ["tier-1"]           # optional, ordered, non-empty strings

[roster.<tier>]               # named approvers per channel
terminal = ["alice"]          # M0: shape/type validation only
desktop  = ["alice"]
# chat tiers (slack/matrix) are parsed for shape but inert until their adapters exist

[throttle]
per_agent_burst = 20
per_agent_rate_per_min = 10
flood_window_seconds = 30

[channels.desktop]
enabled = true

[channels.webhook]
enabled = false
url_ref    = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "env:AGENTINBOX_WEBHOOK_HMAC"

[channels.terminal]
enabled = true

[bus]
driver = "filesystem"         # in-proc | filesystem

[store]
driver = "sqlite"             # sqlite | memory

[limits]                      # defaults shown; ceilings are enforced later (M20+)
max_hold_rounds = 2
max_evidence_revisions = 4
max_thread_entries = 20

[webui]
enabled = false
bind = "127.0.0.1:8377"       # loopback only; anything else is a config error + doctor warning
```

Forward-slate sections from PRD 15 (`[quiet_hours]`, `[incident]`, `[hooks.*]`, `[standing_rules]`,
`[calendars]`, `[writeback.*]`, `[drills]`, `[deadman]`, `[channels.matrix]`, `[channels.slack]`) are
recognized by name and rejected with "not supported in v0.1.0" (they arrive with PRDs 24–30).

### 5.3 Secret references only

Secrets never appear as literals. A secret-valued key must end in `_ref` (or be declared in the secret-key
registry) and must match one of:

- `env:NAME` — read from the environment at use time, never stored;
- `file:/absolute/path` — read at use time, `0600` file, never stored.

A literal value in a `*_ref` position, or a plausible secret under a non-`_ref` key (reusing the M22 detector
shape), is a **lint/validation error** (PRD 22 §C) — not a warning. Error messages quote the key path, never
the value.

### 5.4 Loopback default

`webui.bind` defaults to `127.0.0.1`; `serve`'s future HTTP bind follows the same rule. A non-loopback bind is
accepted only with an explicit config value **and** produces a `doctor` warning (N-18); the design forbids
widening silently.

---

## 6. `doctor` checks (M0 set, exit-coded)

Each check reports `ok | warn | fail` with a stable id so M20/M21 can extend the set without renumbering.
Overall exit code: `0` if all checks pass (warnings allowed), `4` if any check fails, `1` on usage errors.

| Check id | Verifies | Fail example |
|---|---|---|
| `platform` | POSIX; unsupported OS named plainly | "Windows is not supported in v0.1.0" |
| `home` | resolved home exists/creatable and is `0700`-writable | "cannot write `<path>` (permission denied)" |
| `config` | file exists, parses, validates (§5) | "config.toml: unknown key `classes..name.ttl`" |
| `store-path` | `<home>/inbox.db` path is inside home; perms `0600` if present | "inbox.db is world-readable" |
| `schema` | if the store exists, its `schema_version` is readable | "unreadable schema version" |
| `clock` | a UTC clock is readable and monotonic time advances | "system clock unavailable" |
| `explain` | `--explain` prints the effective config with refs unexpanded | — |

`doctor` must return `0` on a healthy fresh install (`init` then `doctor`) — that is an acceptance test.

---

## 7. Test & fixture plan for M0

| Fixture | Asserts |
|---|---|
| `tests/contract/test_exit_codes.py` | exact integer map §3; single source reused everywhere |
| `tests/cli/test_surface.py` | every command appears in `--help`; stubs exit `4` with the honest message; unknown command exits `1`; `--help` exits `0` |
| `tests/cli/test_doctor.py` | fresh home exits `0`; each failing check names itself and exits `4` |
| `tests/config/test_fail_closed.py` | missing / malformed / unknown key / secret literal / non-loopback bind / bad TTL each exit `4` with an actionable message |
| `tests/config/test_home_resolution.py` | flag > env > default; relative/empty home rejected |
| `tests/test_packaging.py` | console script and `python -m agentinbox` produce identical `--help` and version output |

Coverage is enforced at ≥95% on `agentinbox/` at the milestone gate only (one full run, `.T`/`.C`), not per
ticket.

---

## 8. Open questions (owned by later milestones)

1. **Default-config semantics** — whether `init` writes a fully commented, minimal, or class-complete file goes
   to M0 implementation; the requirement is only "scaffolds a commented file" (PRD 22 §C).
2. **Class resolution defaults** — "config that resolves to nothing is an error" (PRD 15) is a runtime rule for
   M2/M3; M0 validates shape and types without inventing inheritance.
3. **Symlink / ownership policy** on config and store paths — M20 (fail-closed matrix) unless a security review
   pulls it earlier.
4. **Windows message** — explicitly unsupported (PRD 14 scope guard); the CLI must say so instead of raising
   `OSError` (M0 acceptance).

## 9. Traceability

| Requirement | Where satisfied |
|---|---|
| PRD 02 §interfaces (CLI + reserved exit codes) | §2, §3 |
| PRD 13 N-13 (zero external services) | §1 (stdlib-only runtime, no network) |
| PRD 13 N-16 (`-m` + console script) | §1, §7 packaging test |
| PRD 13 N-18 (loopback default) | §5.4 |
| PRD 13 N-20 (3.11–3.13) | §1 |
| PRD 13 N-36..N-39 (gates, DCO, in-repo fixtures, docs versioned) | §7 + `.github/workflows/ci.yml` (0.5) |
| PRD 15 §storage / PRD 22 §C (layout, config governance, secret refs) | §4, §5 |
| PRD 06 invariants | I-3/I-5 upheld by fail-closed stubs (§2) and secret-refs-only (§5.3) |
