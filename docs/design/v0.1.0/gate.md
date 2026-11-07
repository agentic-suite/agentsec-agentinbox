# CI checkpoint (`gate`) design — v0.1.0 (M10)

**BLUF:** `agentinbox gate` makes headless irreversible steps answerable by a human and **never proceed without
an explicit allow**. It blocks on the ask, prints the card summary, and maps the decision to the frozen exit
contract: `0` approved · `2` denied/cancelled · `3` expired (ask TTL or gate budget) · `4` fail-closed
unavailable · `5` still pending. A signal (`SIGTERM`/`SIGINT`) records a `cancelled` transition, so a killed
pipeline never leaves an orphan pending ask.

- **Milestone:** M10 ([WBS Part 6](../../wbs/v0.1.0/wbs-v0.1.0-part6-ci-escalation.md), issues #215–#226)
- **Requirements:** R6, E9, E1, E2, E4 · PRD 02 §interfaces · CUJ-7 · SC-15/SC-16

---

## 1. Command

```sh
agentinbox gate --ask <ask-id> [--wait] [--timeout <seconds>]
```

- **`--ask`** (required): the ask id printed by the ingest response.
- **`--wait`**: block until the ask resolves or its TTL / `--timeout` lapses. Without it, the command
  performs one resolve read and reports `5` while pending.
- **`--timeout`**: the **CI budget**, independent of the ask TTL. The effective deadline is
  `min(budget, ask.expires_at)`. A lapsed budget returns `3` and does **not** mutate the ask; a lapsed ask TTL is
  derived deny and also returns `3`. Retrying is safe.

The command reads the local store (the same store the daemon writes); it does not require the HTTP API to be up.
A locked/unreadable store is `4`, never `5`, never `0`.

## 2. Exit mapping

| Resolve outcome | Exit | CI treatment |
|---|---|---|
| `approved` | `0` | proceed |
| `denied` (human or flood) | `2` | fail |
| `cancelled` | `2` | fail; the producer withdrew |
| `expired` / gate budget lapsed | `3` | fail |
| unknown ask / store unavailable / bad config | `4` | fail closed |
| pending (no `--wait`, or budget not yet lapsed) | `5` | retry |

The irreversible step is guarded with `gate ... && deploy`; every non-zero code fails the job. There is no path
on which a failure becomes `0`.

## 3. Waiting

The wait loop is a bounded poll (`0.25 s`) over the store's resolve path, with the ask's derived expiry
evaluated each pass. A staged/rolled-back clock cannot extend the ask's TTL; the M4 scheduler still records the
expiry transition exactly once. The gate never writes a decision: only the answer pipeline can.

## 4. Cancellation

While waiting, `SIGTERM`/`SIGINT` sets a cancel flag. The loop then attempts one `pending → cancelled`
transition (kind `gate-cancelled`, channel `ci`, the OS principal, and a signal detail). If another writer won
the race first, the transition is skipped and the real outcome is reported. Evidence: no orphan pending ask, and
the audit says who cancelled and why.

## 5. Idempotent retries

Re-running `gate` for the same ask is read-only and returns the same terminal outcome. It never mints a claim,
never publishes a notification, and never re-asks. A CI retry after `5` is safe; a retry after `0/2/3` is a
stable no-op.

## 6. Recipes

`docs/adapters/` carries the four supported recipes (GitHub Actions, GitLab, Jenkins, Argo). The core stays
vendor-neutral: every recipe is just `gate` plus the exit code. The GitHub recipe also writes the ask id and
card summary to `$GITHUB_STEP_SUMMARY`.

## 7. Fail-closed matrix

| Fault | Result |
|---|---|
| missing/invalid config | `4` |
| store cannot be opened/locked | `4` |
| unknown ask id | `4` |
| ask TTL elapsed | `3` |
| gate budget elapsed, ask still pending | `3` (no mutation) |
| signal during wait | `cancelled` transition, `2` |
| clock moved backwards | derived expiry may not un-expire; `now` is monotonic in the loop |

## 8. Tests

`tests/ci/test_gate.py` pins every exit code, the wait/budget paths, cancellation evidence, and retry
idempotency. `tests/cli/test_gate_cli.py` pins the CLI wiring and the printed summary.
