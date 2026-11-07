# AskBus design — v0.1.0 (M9)

**BLUF:** The bus is the **movement layer**: typed jobs (`deliver`, `renotify`, `escalate`, `digest`, `expire`)
carried at-least-once with **idempotent consumers**. Movement is never truth (D-13): a job can only cause a
delivery attempt; it can never answer an ask, reorder the store, or create a decision. The in-process driver is
the default; the filesystem spool is the single-box durable driver (atomic rename, fsync, `flock` single owner,
≤1 s bounded poll). The spool is honestly one box (D-14).

- **Milestone:** M9 ([WBS Part 5](../../wbs/v0.1.0/wbs-v0.1.0-part5-desktop-bus.md), issues #203–#214)
- **Requirements:** E12 · PRD 16 §C, PRD 15 §storage, PRD 13 N-3c · D-13, D-14

---

## 1. Job model

```text
Job
  job_id      stable id; republishing the same id is a dedupe, not a second job
  kind        deliver | renotify | escalate | digest | expire
  ask_id      the ask the job is about (digest: the first ask in the window)
  created_at  UTC instant (ordering key)
  not_before  optional earliest delivery instant
  payload     small, JSON-safe metadata (tier, window, counts) — never a decision
```

`job_id` is caller-assigned and deterministic where dedupe matters (for example
`digest:<window-start>`), so a retry of the publisher cannot double-publish.

## 2. Contract

| Method | Semantics |
|---|---|
| `publish(job) -> bool` | `True` when enqueued, `False` when the id was already published (dedupe). |
| `consume(handler) -> int` | Deliver every due job once; `handler` exceptions leave the job queued (at-least-once) and propagate. Returns the number consumed. |
| `run(handler, stop)` | Repeatedly consume and wait; bounded wait ≤1 s. |
| `close()` | Release resources (spool: release `flock`). |

A consumer is idempotent **by ask state**: a job arriving for a resolved/unknown ask is a logged no-op. The bus
itself has no idea what a decision is — it only moves bytes.

## 3. In-process driver (default)

Jobs are entries in an ordered dict; `publish` records the id, `consume` invokes the handler synchronously and
removes the job only after the handler returns. Zero moving parts; same semantics as the spool.

## 4. Filesystem spool driver

```text
<home>/spool/
  jobs/<job-id>.json     pending
  done/<job-id>.json     consumed (movement only; prunable)
  locks/bus.lock         flock LOCK_EX | LOCK_NB, held for the process lifetime
  tmp/                   staging; every *.tmp is swept on boot
```

- **Publish:** write `tmp/<job-id>.<rand>.tmp` with mode `0600`, `fsync` the file, `os.replace` into
  `jobs/<job-id>.json` (atomic rename; the target name is the CAS — an existing file is a dedupe), then
  `fsync` the `jobs/` directory.
- **Consume:** scan `jobs/*.json` in `(created_at, job_id)` order, skip `not_before > now`, call the handler,
  then `os.replace` into `done/<job-id>.json` + `fsync` the `done/` directory. A crash before the rename
  redelivers the job on boot (at-least-once); the consumer's ask-state check makes that safe.
- **Single owner:** the second daemon on the same spool raises `BusLockedError` ("another daemon owns the
  spool") rather than racing.
- **Wakeups:** the portable stdlib has no inotify/FSEvents; `run()` uses a bounded poll with
  `poll_interval = 0.5 s` (asserted ≤1 s). A broker driver (Redis/NATS) is the forward-slate upgrade.
- **Pruning:** `done/` is trimmed to the newest `keep` entries on boot and on demand. Movement is not
  evidence; the audit chain is (M15).
- **Crash safety:** `.tmp` files are removed on boot; a partially written file is never visible in `jobs/`.

## 5. Flood-before-bus rule

The flood guard (M12) must publish **one** digest job, never N deliveries. `publish_digest()` uses the
deterministic id `digest:<window-start>`, so the bus dedupes the 200th flood publication exactly like the
first. The rule is enforced at the contract level and pinned by a 200-ask fixture.

## 6. Delivery wiring

`DeliveryWiring.handle(job)`:

1. unknown ask → `delivery-skipped` observation; resolved ask → silent no-op (idempotent by state);
2. build the M5 card once;
3. try each configured channel in order, up to `max_attempts` each, recording a `DeliveryRecord` for **every**
   attempt (`delivered` / `failed`);
4. a successful attempt appends `ask-delivered` and stops; a failed one appends `delivery-failed`;
5. failover to the next channel; ingest and the bus never block on a slow channel.

`digest` jobs are handed to the desktop digest notifier; they never render individual asks.

## 7. Non-goals

- No broker, no network listeners, no cross-box delivery (D-14).
- No job can carry an answer, a principal, or a claim.
- No exactly-once promise: at-least-once + idempotent consumers is the honest contract.

## 8. Tests

`tests/bus/conformance.py` runs every driver through the same checks (dedupe, not-before, at-least-once on
handler failure, crash resume, lock refusal, poll latency). The spool adds filesystem-specific fixtures; a
deliberately broken driver must fail the conformance suite.
