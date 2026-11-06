# Scheduler reference (v0.1.0 · M4)

**BLUF:** Timers are persisted absolute UTC instants, recovery recomputes them on boot, and firing is
exactly-once. **Timeout = deny**: expiry records a terminal `expired` and the resolver returns
`deny / human_gate_timeout` with a rescope hint. There is no configuration or retry path from expiry to allow.

- Design: [`docs/design/v0.1.0/scheduler.md`](../design/v0.1.0/scheduler.md)
- Requirements: R3, E2, E8, D-1

## Timers

| Timer | Set at ingest | Fires |
|---|---|---|
| `expires_at` | producer value, ≤ `class.ttl_seconds` | terminal `expired`, deny to the producer |
| `warn_at` | `expires_at - class.warn_seconds` (when configured) | `warned` observation once, with remaining seconds |
| `escalate_at` | M11 | — |

Every tick scans pending asks ordered by `expires_at`. The SQLite index `(status, expires_at)` keeps it cheap.
An ask at `expires_at` exactly is due (`<=`).

## Exactly-once and recovery

- Expiry uses CAS `pending → expired`, so concurrent schedulers and restarts write one transition.
- Warning is deduplicated by the persisted `warned` transition.
- `Scheduler.recover()` (`tick(recovered=True)`) fires overdue work once and records a
  `scheduler-recovered` observation with what it planned to do.
- A missed warning fires on the next boot — never silently skipped. An ask that expired while the process
  was down fires expiry only (a warning for an unreachable ask would be noise).

```python
from agentinbox.scheduler import Scheduler

scheduler = Scheduler(store)
scheduler.recover()                 # boot pass
thread, stop = scheduler.start()    # periodic ticks every second
...
stop.set()
```

## Clock rules

- Persisted times are UTC ISO-8601 with microseconds.
- The scheduler schedules against `max(now, last_seen)`; a backwards wall-clock jump cannot postpone a
  deadline. A forwards jump past the deadline fires immediately and cannot resurrect a resolved ask.
- **Expiry is a read-safe derivation**: `resolve()` on an overdue pending ask returns deny without writing.
  The scheduler is what records the terminal transition.
- `doctor` reports `clock-skew` when the newest audit entry is more than 300 s ahead of the wall clock (the
  machine's own evidence says it moved backwards). A warning does not change `doctor`'s exit code.

## Timeout = deny

| Path | Result |
|---|---|
| ask expired | `deny` · `human_gate_timeout` · `retryable=false` · rescope hint |
| ask pending | `pending` · `deny_ask_pending` · `retryable=true` |
| ask approved | `allow` · `allow_ask_approved` · `answered_by` |

`Scheduler.allows_on_expiry` is a runtime counter that must remain `0`; tests assert it after every expiry
fixture. A refactor that allowed on timeout would have to change this counter to hide, which is exactly the
review signal we want.
