# Scheduler design — v0.1.0 (M4)

**BLUF:** The scheduler makes **timeout = deny** real. Timers are derived from persisted absolute UTC instants
(`expires_at`, `warn_at`), recovery recomputes them on boot, and every firing is recorded exactly once through
the lifecycle guard. A backwards clock jump cannot extend a TTL, a forwards jump cannot resurrect an expired
ask, and **no configuration path converts expiry into allow** — the zero-allow-on-expiry counter exists to prove
that in tests.

- **Milestone:** M4 ([WBS Part 3](../../wbs/v0.1.0/wbs-v0.1.0-part3-scheduler-card.md), issues #147–#157)
- **Requirements:** R3, E2, E8, D-1

---

## 1. Timer model

| Timer | Source | Fires |
|---|---|---|
| `expires_at` | ingest: producer-supplied, ≤ class TTL | terminal `expired` at the instant |
| `warn_at` | ingest: `expires_at - class.warn_seconds` | `warned` observation (once) |
| `escalate_at` | M11 (ladder) | escalation (not in v0.1.0 M4) |

Nothing is stored as a "timer": the scheduler scans `list_pending` ordered by `expires_at` every tick. A tick
is O(pending), and the SQLite index `(status, expires_at)` makes due work cheap.

`Scheduler.tick(recovered=False)`:

1. `now = effective_now()` (monotonic-guarded wall clock, §3);
2. for each pending ask: if `expires_at <= now`, CAS `pending → expired` (`kind="expired"`); elif
   `warn_at <= now` and no `warned` transition yet, append `warned` with `remaining_s`;
3. in recovery mode, append a `scheduler-recovered` observation (with the planned outcomes) before firing,
   so the evidence shows the boot pass happened.

The guard/CAS does the deduplication: a second scheduler, a restarted process, or a duplicate tick loses the
race and writes nothing.

## 2. Timeout = deny (D-1)

- Expiry resolves through `agentinbox.resolve`: `status=deny`, `reason_code=human_gate_timeout`,
  `retryable=false`, plus a **rescope hint** the producer can act on.
- There is no config flag, channel retry, or fallback that maps expiry to allow. The only allow code
  (`allow_ask_approved`) requires an approved status with an authenticated principal.
- `Scheduler.allows_on_expiry` is a runtime counter that is **never incremented**; tests assert it is `0`
  after every expiry fixture and assert `resolve()` denies. A future refactor that allows on timeout would
  have to change this counter to hide — an obvious review signal.

## 3. Clock correctness (E8)

- All persisted times are UTC ISO-8601 with microseconds (lexicographically comparable).
- The scheduler keeps `last_seen` wall time and schedules against `max(now, last_seen)`. A backwards jump
  therefore cannot postpone an expiry: the deadline was already reached from the process's point of view.
- A forwards jump past `expires_at` fires immediately; an expired ask is never resurrected because the status
  transition is one-way.
- `doctor` gains a `clock-skew` check: if the newest audit timestamp is more than **300 s** ahead of the
  current clock, the machine moved backwards relative to its own evidence — warn (exit stays `0`; a warning is
  not a failed install).

## 4. Crash recovery (E2)

- On boot, `recover()` = `tick(recovered=True)`: every overdue ask fires once, with a `scheduler-recovered`
  marker; warnings whose instant passed while the process was down fire once, not silently skipped.
- Adopted-pending semantics: a CLI-created pending ask (M7) is a normal pending row, so it is recovered by the
  same pass — no separate path.
- Idempotency comes from persisted transitions (`warned`) and CAS (`expired`), not from in-memory state.

## 5. Tests

| File | Covers |
|---|---|
| `tests/scheduler/test_timers.py` | warn at `T-60`, expiry at `T`, once-only, no status change before due |
| `tests/scheduler/test_expiry.py` | terminal expired, deny resolve, rescope hint, zero-allow counter |
| `tests/scheduler/test_recovery.py` | restart/crash recovery, marker, overdue warning, concurrent ticks |
| `tests/scheduler/test_clock.py` | backwards jump cannot extend, forwards jump cannot resurrect |
| `tests/cli/test_doctor_skew.py` | `clock-skew` warn on evidence ahead of the clock |
