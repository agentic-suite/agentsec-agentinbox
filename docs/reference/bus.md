# AskBus reference (v0.1.0 · M9)

**BLUF:** the bus moves work between the ingest side and the channel side. It is **at-least-once** with
**idempotent consumers**, and it is never the source of truth: a job cannot answer an ask, change its status, or
lose evidence. Two drivers ship: `in-proc` (default, no disk) and `filesystem` (durable, one box).

- Design of record: [`docs/design/v0.1.0/bus.md`](../design/v0.1.0/bus.md)
- Config: `[bus] driver = "filesystem" | "in-proc"`

## Jobs

| Kind | Meaning |
|---|---|
| `deliver` | deliver the ask on the configured channels |
| `renotify` | tier change re-notification |
| `escalate` | escalation routing step |
| `digest` | one flood digest for a window |
| `expire` | expiry follow-up |

A job is JSON with `job_id`, `kind`, `ask_id`, `created_at`, optional `not_before`, a small `payload`, and
`attempts`. It never carries a principal, a claim, or a decision.

Publishing the same `job_id` twice is a **dedupe**, not a second job. `publish_digest()` uses the deterministic
id `digest:<window-start>`, so a 200-ask flood yields exactly one digest job whose payload is updated to the
rolling count.

## Drivers

### `in-proc` (default)

Jobs live in process memory and `consume()` invokes the handler synchronously. Nothing survives a restart; the
store still does.

### `filesystem`

```text
<home>/spool/
  jobs/<job-id>.json
  done/<job-id>.json
  locks/bus.lock
  tmp/
```

- publish = write `tmp/*.tmp` (mode `0600`) → `fsync` → atomic rename into `jobs/` → `fsync` the directory;
- consume = call the handler, then move the file to `done/` (crash before the move ⇒ redelivery);
- one owner: a second daemon on the same spool exits `4` with `another daemon owns the spool`;
- wakeups are a bounded poll (`0.5 s`, never above `1 s`); the stdlib has no portable inotify/FSEvents;
- `done/` is pruned aggressively (default 1000 newest). Movement is not evidence — the M15 chain is.

## Idempotent consumers

`DeliveryWiring` treats a job for an unknown or resolved ask as an evidence-only no-op. It records a
`DeliveryRecord` for **every** attempt and emits `ask-delivered`, `delivery-failed`, or `delivery-skipped`.
Retries are bounded (3 by default) with injectable backoff; after a channel is exhausted, the next configured
channel is tried (failover). Ingest and the bus never block on delivery.

## `agentinbox serve`

```sh
agentinbox serve            # daemon loop: scheduler + bus consumer
agentinbox serve --once     # drain once and exit (tests, cron, unit files)
```

Exit `0` after a clean drain/stop; `4` for config, store, or spool-lock failures. A second daemon on the same
filesystem spool fails closed with exit `4`.

## One-box honesty

The filesystem spool is a same-machine queue. It is not a broker, has no network listener, and makes no
cross-box guarantee. Redis/NATS drivers are the forward-slate upgrade path; they inherit the same conformance
suite.
