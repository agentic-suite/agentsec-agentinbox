# WBS v0.1.0 — Part 11: Fail-Closed Hardening & Operations (M20–M21)

**BLUF:** **M20 is the fault matrix**: store locked, corrupted schema, sink offline, external channel down,
scheduler killed mid-fire — every path is **deny-or-pending**, explicit events, `doctor` red, **zero** silent
allows and **zero** silent skips (E9, SC-24; the honesty behind "no path from any failure to an allow"). **M21
makes it operable**: service units (`serve --install` → launchd/systemd), WAL-safe backup/restore, forward
migrations with loud downgrade refusal, `report --json` (the PRD 07 metrics computed locally), retention
scheduling, the performance benches (N-1..N-7), and the offline day (CUJ-12/SC-26).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M20 — Fail-closed fault matrix + doctor hardening (E9)

**Goal:** prove the degradation table in [PRD 02 §failures](../../prd/02-architecture.md) row by row: every
injected fault produces the documented behavior — store down → 503 + producer denies at the enforcer; channel
down → pending + delivery-failed events + TTL still denies; sink down → buffered + gap markers; scheduler
crash → exactly-once recovery (M4) re-verified under full integration; config reload failure → last-good kept.
`doctor` becomes the operator's single red/green surface with exit codes for CI.

**CUJ:** CUJ-9 (failover leg), CUJ-12 groundwork · **Requirements:** E9, [PRD 06](../../prd/06-security-baseline.md)
(failure = no allow), [PRD 13](../../prd/13-non-functional-requirements.md) (N-27), D-1.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 20.D0 | **Design docs first** | Fault-injection design: the fault catalog (each with expected state + events), injection harness, doctor check completion | docs | reviewed before code | #51 | — | — |
| 20.1 | **Fault-injection harness** | Injectable faults: store lock/corrupt, schema mismatch, sink offline, external channel 500, scheduler kill mid-fire, config reload with invalid file, clock skew beyond signature window | harness | each fault triggers its documented path; harness reusable by agentdrill-style drills | #52 | — | E9 |
| 20.2 | **SC-24 matrix green** | Every fault → deny-or-pending + explicit events (delivery-failed / degradation / scheduler-recovered); the runtime zero-allow-on-expiry counter reads 0 across the whole run | fixtures | SC-24 verdicts recorded; **no** path produces allow or silent skip | #53 | CUJ-9 | E9, D-1 |
| 20.3 | 503 + producer contract | Store unavailable → ingest refuses (503) with a body producers can act on; producers documented to deny at the enforcer on 503/exit-4 (the fail-closed loop across tools) | API contract | producer fixture: 503 → producer treats as deny; no retry-storm | #54 | — | E9 |
| 20.4 | **Doctor completion** | All checks: store + chain, schema versions, clock skew, key presence, channel reachability, spool health (flock owner, `.tmp` sweep), config validity — exit-coded, scheduled in cron it becomes the health check | doctor | every injected fault turns `doctor` red with a named cause; healthy box green < 2 s (N-27) | #55 | — | E9, N-27 |
| 20.5 | Last-good config reload | Reload (SIGHUP/`reload`) with an invalid file → refuse to apply, keep last-good, emit `inbox-config-changed(failed)` + operator-visible error | reload | bad-reload fixture: behavior unchanged, failure loud | #56 | — | E9 |
| 20.T | Tests | The full matrix + doctor + reload | tests | coverage ≥ 95% | #57 | — | — |
| 20.C | Coverage gate | ≥95% | report | ≥95% | #58 | — | — |
| 20.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #59 | — | — |
| 20.CR | Code review | Findings resolved | log | no open findings | #60 | — | — |
| 20.D | Docs | Fail-closed reference (the degradation table, proven) + doctor guide | docs | updated + linked | #61 | — | — |
| 20.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 20.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-24 fully green; the zero-allow-on-expiry counter is 0 across every fault
- [ ] `doctor` red/green for every injected fault; invalid reloads keep last-good loudly

---

## Milestone M21 — Ops: service units, backup/restore, migrations, `report` (E10, PRD 22)

**Goal:** the tool runs like infrastructure: `serve --install` emits user-scoped launchd/systemd units (no
root); backup uses the SQLite online-backup path (WAL-safe, secrets stay refs) and restore verifies the chain
or aborts; upgrades migrate forward and **refuse downgrade loudly**; `report --json` computes the
[PRD 07](../../prd/07-success-metrics.md) metrics locally; the offline day passes end-to-end (CUJ-12/SC-26);
and the performance benches (N-1..N-7) are recorded in CI.

**CUJ:** CUJ-12 · **Requirements:** E10, [PRD 22 §A–E](../../prd/22-operations-and-governance.md),
[PRD 13](../../prd/13-non-functional-requirements.md) (N-1..N-19, N-26..N-30).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 21.D0 | **Design docs first** | Ops design: service units, backup/restore semantics (what's in, what stays a ref), migration policy, report metrics + on-event local hooks, offline posture | docs | reviewed before code | #62 | — | — |
| 21.1 | Service units | `agentinbox serve --install` → user-scoped launchd (macOS) / systemd (Linux) units; SIGTERM → stop accepting, flush, clean close; in-flight `gate` clients get exit 4 | units | install/start/stop cycle fixture; restart adopts pending asks | #63 | — | E2 |
| 21.2 | Backup / restore | `doctor --backup out.tar` via the SQLite online-backup path + config (secrets as refs only) + key-slot metadata; restore into a fresh `AGENTINBOX_HOME`, chain verifies or aborts; restored boxes never resurrect expired approvals | backup | backup→restore→`verify-log` fixture; secrets absent from the archive | #64 | — | E10, N-26 |
| 21.3 | Migrations + compatibility | Forward migrations per release (old-store fixture opens); **downgrade refuses loudly**; contract/exit codes additive-only within v0.x (E10/E18 posture) with a compatibility test matrix | migrations | old→new green; new→old refuses; contract fixtures validate across versions | #65 | — | E10 |
| 21.4 | `report --json` | Local metrics from the event stream: response-time p50/p99, expiry counts, escalation firings, flood events, `answer-rejected` causes, deny-rate by class — nothing leaves the machine | CLI | report fixture matches hand-computed values over a scripted corpus | #66 | — | N-26 |
| 21.5 | **Offline day** | Network disabled + external channels off: terminal + desktop + CI + audit + export all function; `doctor` reports offline mode green; no telemetry ever calls out | offline posture | SC-26 executed at milestone level (re-run at M24) | #67 | CUJ-12 | N-19, E9 |
| 21.6 | Performance benches | N-1..N-7 in CI: ingest p50<50ms/p99<250ms, terminal render <100 ms, external <2 s p50 (mocked), resolve p99<100 ms, scheduler jitter ≤1 s, 10k-ask load, startup <2 s | benches | recorded per release in the release notes ([PRD 20 §F](../../prd/20-standards-and-claims.md)) | #68 | — | N-1..N-7 |
| 21.T | Tests | Units, backup/restore, migrations, report, offline, benches | tests | coverage ≥ 95% | #69 | — | — |
| 21.C | Coverage gate | ≥95% | report | ≥95% | #70 | — | — |
| 21.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #71 | — | — |
| 21.CR | Code review | Findings resolved | log | no open findings | #72 | — | — |
| 21.D | Docs | Runbook-ready ops docs: install-as-service, backup/restore, upgrade, report, offline | docs | updated + linked | #73 | — | — |
| 21.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 21.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Backup/restore verify the chain; downgrades refuse; units install without root
- [ ] SC-26 offline day green; `report` matches hand-computed metrics; benches recorded

---

Part 11 green ⇒ failures are honest (M20) and the box is operable (M21); proceed to
[Part 12 (M22–M23)](wbs-v0.1.0-part12-security-docs.md).
