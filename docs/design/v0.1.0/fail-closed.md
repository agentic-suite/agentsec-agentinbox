# Fail-closed fault matrix design — v0.1.0 (M20)

**BLUF:** every injected fault is **deny-or-pending**, explicit, and leaves evidence. No fault produces an allow,
and no fault is skipped silently. `doctor` is the operator's single red/green surface, and an invalid config
reload keeps the last-good policy in force while saying so.

- **Milestone:** M20 ([WBS Part 11](../../wbs/v0.1.0/wbs-v0.1.0-part11-failclosed-ops.md), issues #51–#61)
- **Requirements:** E9, D-1, N-27 · PRD 06 (failure = no allow), PRD 02 §failures · SC-24

---

## 1. Fault catalog

| Fault | Injection | Expected state | Evidence |
|---|---|---|---|
| store locked | exclusive SQLite transaction / locked wrapper | ingest refused; existing asks pending | producer `503` / exit `4` |
| store corrupt | non-database bytes at `inbox.db` | no decision is read | `doctor` schema fail |
| schema mismatch | `schema_version = 999` | downgrade refused; store untouched | `SchemaVersionError`, `doctor` fail |
| sink offline | failing event sink | decisions unaffected | buffered events, `event-gap` on overflow |
| channel 500 | failing channel | ask pending | `delivery-failed` records/events |
| scheduler killed | new scheduler after death | exactly-once recovery | `scheduler-recovered` + one `expired` |
| config invalid | reload a bad file | last-good config stays | `inbox-config-changed(failed)` |
| clock skew | future audit timestamp | TTL cannot extend | `doctor` clock-skew warning |

The machine-readable catalog lives in `agentinbox/faults.py` (`FAILURE_MATRIX`), with the allowed outcomes and the
expected state/events. Tests assert the catalog is complete and that no case allows by itself.

## 2. The invariant

- The scheduler's `allows_on_expiry` counter is `0` across the run.
- A locked/unreadable store never yields a decision: the API returns `503`; the CLI exits `4`.
- A channel failure never changes status or TTL; the ask stays pending.
- A sink failure never affects a decision; events buffer and gaps are marked.
- A bad reload changes nothing and is loud.
- A clock jump cannot extend a deadline (M4 monotonic clamp + doctor warning).

## 3. Store failures and the producer contract

`SqliteStore` wraps connection/migration failures in `StoreError`. The API maps `StoreError` to `503` with
`{ "error": { "field": "store", ... } }`. Producers must treat `503`/exit `4` as **deny at the enforcer** and use
bounded retry only. `ask --exec` exits `4` and never runs the command.

## 4. Doctor completion

Checks (stable ids): `platform`, `home`, `config`, `desktop`, `store-path`, `schema`, `chain`, `spool`, `keys`,
`clock`, `clock-skew`.

- `chain` recomputes the audit chain read-only and names the first bad seq.
- `spool` reports pending/done/staging counts; a missing lock or staging files is a warning.
- `keys` resolves producer/webhook references (missing key = red).
- `schema` fails when the store is newer than the build, warns when older.
- Healthy path is under two seconds (N-27); any `fail` exits `4`.

## 5. Last-good reload

`ConfigHolder.reload()` re-reads the file. On `ConfigError` it returns the previous config and the error; the
daemon (SIGHUP) applies the new escalation config and records the change on success, or records
`inbox-config-changed(failed)` and keeps everything on failure.

## 6. Tests

`tests/faults/test_matrix.py` injects each fault and asserts the expected state/evidence plus the zero-allow
counter. `tests/cli/test_doctor_m20.py` covers the new checks, the red cases, and the time budget.
