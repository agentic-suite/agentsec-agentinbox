# Configuration reference (v0.1.0 · M0)

**BLUF:** One TOML file at `<home>/config.toml`. The loader is **strict and fail-closed**:
unknown keys are errors, forward-slate keys are rejected as unsupported, secrets are
references only (`env:NAME` / `file:/absolute/path`), and the bind is loopback. Nothing
silently falls back to a default after an explicit value is set.

- Design of record: [`docs/design/v0.1.0/foundation.md`](../design/v0.1.0/foundation.md)
- CLI reference: [cli.md](cli.md)

## Location and home

```text
--home PATH          (highest)
AGENTINBOX_HOME
~/.agentinbox        (default)
```

The value must be an **absolute** path; empty or relative values are rejected (exit `4`).
`--config PATH` (absolute) points at a different file for commands that read config.

```
<home>/                 # 0700
  config.toml           # 0600
  inbox.db              # 0600, created by the M1 store driver
  spool/{jobs,done,locks}/
  keys/
  logs/
  exports/
```

`agentinbox init` creates this skeleton; `agentinbox doctor` reports what is missing, loose, or
unreadable.

## Validation rules (all are errors, exit `4`)

- missing, unreadable, non-UTF-8, or malformed TOML;
- unknown section or key (**typos never silently disable a control**);
- forward-slate sections (`[quiet_hours]`, `[incident]`, `[hooks]`, `[standing_rules]`,
  `[calendars]`, `[writeback]`, `[drills]`, `[deadman]`) — "not supported in v0.1.0";
- `ttl_seconds` missing, non-integer, or `<= 0`; `warn_seconds` not a positive integer or
  `>= ttl_seconds`;
- `self_review` not one of `deny`, `allow`, `escalate`;
- empty roster, or roster principals that are not non-empty strings;
- unknown store/bus driver; unknown channel; non-boolean `enabled`;
- a secret literal where a `*_ref` is required, or a bad reference scheme;
- a non-loopback `webui.bind`, a bad port, or `webui.enabled = true` (the web UI does not exist
  in v0.1.0).

## Sections

### `[audit]` — retention

| Key | Type | Default | Notes |
|---|---|---|---|
| `retention` | `never` \| `1y` \| `<n>d` | `never` | detail older than the cutoff is pruned with a chain marker |

```toml
[audit]
retention = "90d"
```

### `[producers.<name>]` — signed producer adapters

| Key | Type | Notes |
|---|---|---|
| `key_ref` | `env:NAME` \| `file:/abs/path` | **required**; HMAC key for `X-AgentInbox-Signature` |

```toml
[producers.agentpolicy]
key_ref = "env:AGENTINBOX_ADAPTER_KEY"
```

A signed adapter makes the trusted fields (`class`, `criticality`, `data_class`, `environment`, `policy_ref`,
`reason_code`, `requested_by`) verified for rendering and for the self-review anchor. Unknown adapters and bad
signatures are `401`.

### `[classes.<name>]` — ask classes

| Key | Type | Default | Notes |
|---|---|---|---|
| `ttl_seconds` | int > 0 | **required** | how long an ask stays pending |
| `warn_seconds` | int > 0 | unset | must be `< ttl_seconds` |
| `self_review` | `deny` \| `allow` \| `escalate` | `deny` | self-approval policy |
| `require_reason_on_deny` | bool | `false` | deny must carry a reason |
| `ladder` | list[str] | `[]` | escalation tiers, ordered; each must resolve to a `[roster.<tier>]` entry |
| `ladder_delays` | list[int] | spread over the TTL | absolute offsets from ingest, one per tier; first is `0`, strictly increasing, last `< ttl_seconds` |
| `require_signed_producer` | bool | `false` | reject unsigned producers for this class (makes the self-review anchor enforceable) |

```toml
[classes.irreversible]
ttl_seconds = 300
warn_seconds = 60
self_review = "deny"
require_reason_on_deny = true
ladder = ["tier-1", "on-call"]
ladder_delays = [0, 150]

[roster.tier-1]
terminal = ["alice"]

[roster.on-call]
terminal = ["bob"]
```

Escalation is **routing only**: it changes the answering tier and revokes prior-tier claims, but never
changes `expires_at`. The default delays spread the ladder over the TTL (`0, ttl/2, …`).

Class **resolution** rules (what an ask with no class inherits, and "config that resolves to
nothing is an error") arrive with the lifecycle in M2/M3. M0 validates shape and types only.

### `[roster.<tier>]` — named approvers

Each key is a channel name; the value is a non-empty list of principal names. M0 validates
shape only; authorisation semantics arrive with the answer verifier (M6).

```toml
[roster.tier-1]
terminal = ["alice"]
desktop = ["alice"]
```

### `[throttle]`

| Key | Default |
|---|---|
| `per_agent_burst` | `20` |
| `per_agent_rate_per_min` | `10` |
| `flood_window_seconds` | `30` |

All must be positive integers. Enforcement arrives with M12.

### `[channels.<name>]` — `terminal`, `desktop`, `webhook`

| Key | Applies to | Default |
|---|---|---|
| `enabled` | all | `false` |
| `url_ref` | webhook | unset |
| `hmac_key_ref` | webhook | unset |

Unknown channel names are errors (chat adapters arrive in v0.1.x).

```toml
[channels.webhook]
enabled = true
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "env:AGENTINBOX_WEBHOOK_HMAC"
```

### `[bus]` / `[store]`

| Section | Key | Values | Default |
|---|---|---|---|
| `[bus]` | `driver` | `filesystem`, `in-proc` | `filesystem` |
| `[store]` | `driver` | `sqlite`, `memory` | `sqlite` |

Drivers are contract-gated in M1 (store) and M9 (bus); selecting an unsupported driver is an
error, never a silent fallback.

### `[limits]`

| Key | Default |
|---|---|
| `max_hold_rounds` | `2` |
| `max_evidence_revisions` | `4` |
| `max_thread_entries` | `20` |

Positive integers; enforcement arrives in M20+.

### `[webui]`

| Key | Default | v0.1.0 |
|---|---|---|
| `enabled` | `false` | `true` is rejected (not implemented) |
| `bind` | `127.0.0.1:8377` | loopback only (`127.0.0.1`, `[::1]`) |

## Secrets

Secrets are **references only**:

| Scheme | Meaning |
|---|---|
| `env:NAME` | read from the environment at use time; never stored |
| `file:/absolute/path` | read from a `0600` file at use time; never stored |

A literal value in a `*_ref` position, or a secret-looking key without `_ref`, is an error.
The daemon never writes secrets into the store, logs, exports, or `doctor --explain` output —
`--explain` shows the reference, not the value.

## Minimal valid file

```toml
[classes.irreversible]
ttl_seconds = 300
```

Everything else takes the documented defaults. `agentinbox init` writes a fuller, commented
scaffold that validates as-is.
