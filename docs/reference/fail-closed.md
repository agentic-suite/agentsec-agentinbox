# Fail-closed reference (v0.1.0 · M20)

**BLUF:** the degradation table, proven. Every fault is deny-or-pending and explicit; `doctor` is red/green.

- Design of record: [`docs/design/v0.1.0/fail-closed.md`](../design/v0.1.0/fail-closed.md)
- Catalog: [`agentinbox/faults.py`](../../agentinbox/faults.py)

## Degradation table

| Fault | What the operator sees | What the producer gets |
|---|---|---|
| store locked | `doctor` store/schema red; ingest refused | `503` / exit `4` — deny at the enforcer |
| store corrupt | `doctor` schema red | no decision |
| schema newer than build | `doctor` red: downgrade refused | exit `4` |
| event sink offline | events buffered; gap marker on overflow | decisions unaffected |
| channel 500 | `delivery-failed` records/events | ask pending |
| scheduler killed | `scheduler-recovered` + one expiry | expired (deny) |
| invalid reload | `inbox-config-changed(failed)`; old policy active | unchanged |
| clock skew | `doctor` clock-skew warning | TTL cannot extend |

**No fault produces an allow.** The scheduler's zero-allow-on-expiry counter stays `0`.

## `doctor` checks

| Check | Red when |
|---|---|
| `chain` | audit seq gap or hash mismatch (names the seq) |
| `schema` | store newer than the build (downgrade refused) |
| `keys` | an enabled producer/webhook reference cannot resolve |
| `spool` | never red; warns on a missing lock or staging files |
| `desktop` | enabled but unreachable (headless) |
| `clock-skew` | never red; warns on evidence ahead of the clock |

Healthy path exits `0` in under two seconds; any red check exits `4`.

## Reload

Send `SIGHUP` to the daemon. A valid file is applied (escalation policy) and recorded; an invalid file is refused,
the last-good config stays, and the failure is recorded with the error. No in-flight ask changes.

## Producer rule

On `503` or exit `4`, **deny at the enforcer**. Do not treat an unavailable inbox as approval and do not retry in a
tight loop. The irreversible step is guarded by a non-zero exit.
