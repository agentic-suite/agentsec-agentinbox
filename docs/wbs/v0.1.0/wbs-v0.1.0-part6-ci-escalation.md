# WBS v0.1.0 — Part 6: CI Checkpoint & Escalation (M10–M11)

**BLUF:** **M10 makes headless real**: `agentinbox gate` — the blocking CI step with the frozen exit-code
contract (`0` approved / `2` denied / `3` expired / `4` unreachable fail-closed / `5` pending), cancellation →
`cancelled` (never an orphan), idempotent retries (same ask, no second notification), answerable from any
interactive channel while the job waits (R6, CUJ-7; SC-15/16). **M11 routes what nobody answers**: the
configurable escalation ladder — per-tier delays, per-tier re-notify, claim invalidation on tier change, and
the rule that escalation changes routing, **never the deadline** (R4, D-11; SC-11/12).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M10 — CI checkpoint (R6)

**Goal:** an irreversible CI action halts on an ask and **never proceeds** on deny/expiry/unreachable; the
pipeline log and the audit share the ask id; the gate is answerable from Slack-less surfaces (terminal /
desktop wake-up / webhook display) so on-call is never blocked by CI UI.

**CUJ:** CUJ-7 · **Requirements:** R6, [PRD 16 §B.3](../../prd/16-channel-and-harness-adapters.md),
[PRD 02 §interfaces](../../prd/02-architecture.md) (exit codes), E9 (unreachable = exit 4).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 10.D0 | **Design docs first** | Gate design: wait loop (long-poll), exit mapping, cancellation (SIGTERM/SIGINT) → `cancelled`, retry idempotency, job-log output (ask id + card summary + deep link) | docs | reviewed before code | #215 | — | — |
| 10.1 | `agentinbox gate` command | `--ask <id> --wait --timeout <s>`; blocks on the resolve long-poll; prints ask id + card summary; exit `0/2/3/5` per outcome | CLI | exit-code matrix fixture green (SC-16) | #216 | CUJ-7 | R6 |
| 10.2 | Fail-closed unavailability | Daemon down / store locked / API unreachable → exit **4**, never 0, never a hang; `--timeout` lapses → exit 3 path | failure path | SC-16 unreachable fixture; M20 fault matrix re-verifies | #217 | — | E9, R6 |
| 10.3 | Cancellation → `cancelled` | SIGTERM/cancel maps to a `cancelled` transition (producer withdrew); audit says who/what, never an orphan | signal handling | cancelled-job fixture: transition recorded, no orphan pending | #218 | — | E2 |
| 10.4 | Idempotent retries | Re-running the gate for the same ask: same id, no second notification, same eventual outcome | idempotency | SC-16 retry fixture green | #219 | — | E1 |
| 10.5 | Cross-channel resume | While the job waits, an answer from terminal (or any configured channel) resolves it; job continues on `0` | wiring | SC-15: answered from a second surface → exit 0 → pipeline continues | #220 | — | R2, R6 |
| 10.6 | CI recipes | Documented recipes (docs/adapters/): GitHub Actions step + `GITHUB_STEP_SUMMARY` annotation, GitLab manual-job/protected-env mapping, Jenkins, Argo suspend template | recipes | each recipe reproduced in fixtures/docs; nothing vendor-specific in the core | #221 | CUJ-7 | R6 |
| 10.T | Tests | Exit matrix, cancellation, retries, cross-channel resume, recipes' CLI contracts | tests | coverage ≥ 95% | #222 | — | — |
| 10.C | Coverage gate | ≥95% | report | ≥95% | #223 | — | — |
| 10.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #224 | — | — |
| 10.CR | Code review | Findings resolved | log | no open findings | #225 | — | — |
| 10.D | Docs | Gate reference (exit codes, recipes, cancellation) | docs | updated + linked | #226 | — | — |
| 10.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 10.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] The irreversible step never runs on exit 2/3/4; retries idempotent; cancellations recorded, not orphaned
- [ ] SC-15/SC-16 green; recipes documented for the four CI systems

---

## Milestone M11 — Escalation ladder (R4)

**Goal:** a 3 a.m. ask reaches the configured tier **within the configured window** — or denies: per-tier delay
and channel config, re-notify with tier context ("tier 1 did not answer · expires in mm:ss"), prior-tier
claims **revoked** (a sleeper approval cannot answer after the ladder moved), and the hard rule: escalation
never extends the TTL; the last tier sees exactly how long is left.

**CUJ:** CUJ-5 · **Requirements:** R4, D-11, [PRD 02 §lifecycle](../../prd/02-architecture.md),
[PRD 22 §governance](../../prd/22-operations-and-governance.md) (ladder config ownership).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 11.D0 | **Design docs first** | Ladder design: tier model (config-driven, non-empty, sane delays — validated at load), claim revocation on tier change, tier-context rendering, honest v0.1.0 limits (config-driven recipients, not schedule lookups) | docs | reviewed before code | #227 | — | — |
| 11.1 | Tier engine | Per-class ladder (`tier-1` → `on-call` → …): `escalate_at` timers via the M4 scheduler, per-tier delay + channel, `ask-escalated` events with tier + recipient counts | escalation engine | SC-11: tier-2 reached at T+300s per config; events reconstruct the ladder | #228 | CUJ-5 | R4 |
| 11.2 | **No-TTL-extension rule** | Escalation is routing only: `expires_at` immutable after ingest; the last tier renders remaining time; no path extends a deadline | invariant | SC-12: full-ladder exhaustion → deny at the original T; ladder events = tiers−1 | #229 | — | R4, D-11 |
| 11.3 | Claim revocation on tier change | Escalating to tier k revokes all tier <k claims; a late tier-1 answer → `answer-rejected(revoked)` | revocation | SC-11 revocation fixture: sleeper approval rejected + logged | #230 | — | E3 |
| 11.4 | Tier-context rendering | The escalated card carries escalation history + remaining time; escalations update the **same** desktop notification/message (no re-ping per tier beyond the configured re-notify) | rendering | once-per-tier notify fixture (M8 interplay) | #231 | CUJ-5 | R4, E7 |
| 11.5 | Roster resolution + config governance | Tier → roster/channel resolution from config; changes are git-reviewed + `inbox-config-changed` digested events; `doctor --explain` prints the effective ladder | config | empty-tier/zero-delay config = load error, not runtime surprise | #232 | — | E9 |
| 11.T | Tests | Tier firing, immutability, revocation, rendering counts, config validation | tests | coverage ≥ 95% | #233 | — | — |
| 11.C | Coverage gate | ≥95% | report | ≥95% | #234 | — | — |
| 11.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #235 | — | — |
| 11.CR | Code review | Findings resolved | log | no open findings | #236 | — | — |
| 11.D | Docs | Escalation reference (tiers, rules, config, the no-extension invariant) | docs | updated + linked | #237 | — | — |
| 11.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 11.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-11/SC-12 green: tiers fire in order and in window; exhaustion denies; TTL never extends
- [ ] Superseded-tier claims revoked; ladders validated at load; drill documented for M24

---

Part 6 green ⇒ headless agents gate (M10) and silence routes (M11); proceed to
[Part 7 (M12–M13)](wbs-v0.1.0-part7-flood-webhook.md).
