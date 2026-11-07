# PRD 12 — Traceability

**BLUF:** Every requirement traces to a user story, a CUJ, a scenario in the field-test catalog, and an
acceptance test. No requirement is orphaned; no test exists without a requirement; every consolidated-PRD
(P0/P1/P2) line has a home. This table is the contract the WBS and the field test are built from.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Requirement → story → CUJ → scenario → test

| Req | Requirement (short) | Stories | CUJ | Scenarios ([PRD 17](17-scenarios.md)) | Acceptance test |
|---|---|---|---|---|---|
| **R1** | Decision card: 4 context blocks, unknown-labeling | US-01, US-06, US-07, US-11 | CUJ-1, CUJ-2, CUJ-3, CUJ-11 | SC-01, SC-03, SC-04, SC-05, SC-22, SC-23 | `tests/card/test_card.py` + corpus + user study (M32) |
| **R2** | Any-channel answer, one record | US-06, US-07, US-17 | CUJ-3, CUJ-9 | SC-06, SC-18, SC-19 | `test_channel_parity.py`, `test_late_answer.py` |
| **R3** | Timeout=deny, per-class TTL, warning, rescope | US-03, US-08, US-15 | CUJ-4 | SC-09, SC-10 | `tests/scheduler/test_expiry.py`, `tests/scheduler/test_recovery.py`, `tests/scheduler/test_clock.py` |
| **R4** | Escalation ladder (routing, not deciding) | US-13, US-14 | CUJ-5 | SC-11, SC-12 | `test_escalation.py` + 3 a.m. drill |
| **R5** | Audit trail: chain + agentwatch + export | US-19, US-20, US-21, US-22 | CUJ-8, CUJ-10 | SC-20, SC-21 | `test_audit_chain.py`, `test_export.py` |
| **R6** | CI checkpoints + reserved exit codes | US-16, US-17, US-18 | CUJ-7 | SC-15, SC-16 | `test_gate_exit_codes.py`, `test_ci_resume.py` |
| **R7** | Flood throttling + auto-deny + digest | US-04, US-12 | CUJ-6 | SC-13, SC-14 | `test_flood.py`, `test_burst_legitimate.py` |
| **R8** | Mobile push (v1.x) | US-13 | CUJ-5 | — (v1.x) | deferred |
| **R9** | Delegated/machine approvals (v1.x) | US-02 | — | — | deferred; depends on agentpolicy R41 |
| **R10** | Standing approvals with expiry (v1.x) | US-03 | CUJ-4 variant | — (v1.x) | deferred |
| **E1** | Ask contract + idempotent ingest | US-23, US-24 | CUJ-1, CUJ-13 | SC-01, SC-25, SC-26 | `tests/ask/test_contract.py`, `tests/ask/test_identity.py`, `tests/ask/test_api.py` |
| **E2** | Durable store + crash-safe scheduler | US-03 | CUJ-4, CUJ-13 | SC-09, SC-25 | `tests/store/test_durability.py`, `tests/scheduler/test_recovery.py` |
| **E3** | Unforgeable single-use claims | US-09 | CUJ-3, CUJ-9 | SC-07, SC-08 | `test_claims.py` |
| **E4** | Answer authN/authZ (signature, roster, self-review) | US-06, US-09, US-11 | CUJ-3, CUJ-8, CUJ-11 | SC-17, SC-22 | `test_answer_verify.py`, `test_slack_signature.py` |
| **E5** | Injection-resistant rendering | US-11 | CUJ-11 | SC-22, SC-23 | `tests/card/test_card.py` (poisoned corpus) |
| **E6** | Redaction-before-persistence + receipts | US-05 | CUJ-3, CUJ-10 | SC-21 | `tests/ask/test_redaction.py` + evidence scanner (M22) |
| **E7** | Delivery accounting + hygiene | US-12 | CUJ-6, CUJ-9 | SC-13, SC-19 | `test_delivery_events.py` |
| **E8** | Time correctness (UTC + monotonic) | US-08, US-15 | CUJ-4, CUJ-5 | SC-09, SC-10, SC-12 | `tests/scheduler/test_clock.py`, `tests/cli/test_doctor_skew.py` |
| **E9** | Fail-closed degradation | US-18, US-02 | CUJ-7, CUJ-12 | SC-24 | `test_failclosed_matrix.py` |
| **E10** | Versioning + compatibility | US-23 | CUJ-13 | fixture-level (conformance suite) | `test_schema_migration.py`, `test_contract_version.py` |
| **E11** | Pluggable store (conformance-gated contract) | US-23, US-24 | CUJ-1, CUJ-13 | SC-02, SC-24, SC-25 | `tests/store/conformance.py` (race/claim/chain/crash fixtures) + `tests/store/test_loader.py` |
| **E12** | Pluggable bus (movement ≠ truth) | US-04, US-12 | CUJ-6, CUJ-9 | SC-13, SC-18, SC-19 | `test_bus_conformance.py`, `test_spool.py` (atomicity/locking/idempotent consumers) |

## M0 foundation (shipped tests, v0.1.0)

The foundation milestone freezes the contracts every later test builds on. Rows below are **green
today** (they run in CI), not planned:

| Req / NFR | What M0 ships | Acceptance test |
|---|---|---|
| **R6** (reserved exit codes) | frozen `0/1/2/3/4/5` enum + CI failure/retry classification | `tests/contract/test_exit_codes.py` |
| **E9** (fail-closed degradation) | strict config loader; `doctor` exits `4` on any failed check | `tests/config/test_load.py`, `tests/config/test_load_edges.py`, `tests/cli/test_doctor.py` |
| **E10** (versioning) | single version source; dist `agentsec-agentinbox` | `tests/test_packaging.py` |
| **N-13** (no external services) | zero runtime dependencies; stdlib-only config/CLI | `tests/test_packaging.py` |
| **N-16** (`-m` + console script) | both entry points share one parser | `tests/test_packaging.py`, `tests/cli/test_surface.py` |
| **N-18** (loopback default) | loopback bind enforced in v0.1.0 | `tests/config/test_load.py` |
| **N-36..N-39** (gates, DCO, in-repo fixtures, versioned docs) | CI runs ruff/mypy/pytest/coverage; DCO check; fixtures in-repo | `tests/ci/test_workflows.py`, `tests/test_identity.py` |

## M21 operations (shipped tests, v0.1.0)

| Req / NFR | What M21 ships | Acceptance test |
|---|---|---|
| **E10** (versioning + compatibility) | forward-only migrations, loud downgrade refusal, frozen contract/exit/event matrix | `tests/ops/test_compat.py`, `tests/store/test_migrations.py` |
| **N-1..N-7** (performance) | executable floors for ingest, render, external, spool, resolve, scheduler, 10k load, startup/doctor | `tests/ops/test_bench.py` |
| **N-19** (offline-complete) | external channels off; terminal/CI/audit/export/report/doctor run with non-loopback sockets blocked | `tests/ops/test_offline.py` |
| **N-26 / N-28** (no telemetry; local report) | `report --json` from the owner's chain; no analytics module/endpoint; `local_only: true` | `tests/ops/test_report.py`, `tests/ops/test_offline.py` |
| **N-27** (doctor completion) | added `offline`; backup/restore keep chain/schema/keys checks central | `tests/ops/test_offline.py`, `tests/cli/test_doctor_m20.py` |
| **PRD 22 §B/§E** (lifecycle + backup/restore) | user-scoped units, SIGTERM flush/close, daemon lock, WAL-safe backup, chain-verified restore | `tests/ops/test_units.py`, `tests/ops/test_backup.py` |

## M22 security close-out (shipped tests, v0.1.0)

| Req / invariant | What M22 ships | Acceptance test |
|---|---|---|
| **PRD 06 I-1..I-5** | store-level invariant checks shared by packs and negative fixtures | `tests/security/test_invariants.py` |
| **E6 / EV-9** (no secrets in evidence) | evidence scanner over store dumps, renders, audit exports, backup archives; seeded leak fails | `tests/security/test_scanner.py` |
| **E3/E4/E5/R7** (attack packs) | spoof/replay/forge, injection, and flood packs; a broken gate fixture fails | `tests/security/test_packs.py`, `tests/ci/test_workflows.py` |
| **E3/E4** (timing + uniform errors) | constant-time comparisons, collapsed public causes, guessing lockout | `tests/security/test_timing.py` |
| **N-22..N-25** (input/log/permission) | log sanitization, caps, forced private modes, no approval shortcut | `tests/security/test_hardening.py` |
| **PRD 20 §D** (own posture) | zero-runtime-dependency/no-ML manifest, CycloneDX SBOM dry run, RFC 9116 security.txt | `tests/security/test_posture.py` |

## M26 ask readiness (shipped tests, v0.1.0)

| Req / invariant | What M26 ships | Acceptance test |
|---|---|---|
| **R78** readiness score | six deterministic dimensions, derived and stored | `tests/readiness/test_scorer.py` |
| **R79/R84** rejection + repair | structured `ask_not_decisionable`, zero writes, API/CLI repair body | `tests/readiness/test_rejection.py` |
| **R80** contradictions | 12-case corpus, deliver-with-flag or reject per class | `tests/readiness/test_contradictions.py` |
| **R81/R82** evidence + freshness | per-class expectations, labels name the gap, no inferred freshness | `tests/readiness/test_evidence.py` |
| **R83/R85** banner + precedent | banner above ACTION, up to 3 prior cases labelled precedent | `tests/readiness/test_banner.py` |
| **R86** class config | opt-in enforcement, load error without a threshold, `doctor --explain` | `tests/readiness/test_class_config.py` |

## M27 constrained allows & denial repair (shipped tests, v0.1.0)

| Req | What M27 ships | Acceptance test |
|---|---|---|
| **R87/R93** | alternatives with canonical fingerprints; selectable only with an enforcer binding | `tests/constraints/test_alternatives.py` |
| **R88** | class-generic suggestions, labelled, never recorded unless picked | `tests/constraints/test_suggestions.py` |
| **R89** | deny repair packet on resolve + audit (`pointless` suppresses retries) | `tests/constraints/test_repair.py` |
| **R90/R91** | edit schema, re-fingerprinted approval, provenance | `tests/constraints/test_edits.py` |
| **R92** | repair recall on resubmission; additive resolve vocabulary | `tests/constraints/test_recall.py`, `test_resolve_vocab.py` |

## M28 operation bundles, handoff & incident review (shipped tests, v0.1.0)

| Req | What M28 ships | Acceptance test |
|---|---|---|
| **R94/R95** | derived-on-read bundles, phases, environments, critical path, no approve-all | `tests/bundles/test_operations.py` |
| **R96/R97** | claim/assign routing observations; handoff note with TTL and questions | `tests/bundles/test_operations.py` |
| **R98** | bounded config overlay, chained `incident-on/off`, denies unchanged | `tests/bundles/test_operations.py` |
| **R99/R100** | narrative from stored transitions; ordered exportable timeline | `tests/bundles/test_operations.py` |

## M29 outcome closure & execution proof (shipped tests, v0.1.0)

| Req | What M29 ships | Acceptance test |
|---|---|---|
| **R101** | closure observations on approved asks; unknown until closed; decision immutable | `tests/outcomes/test_outcomes.py` |
| **R102** | whitelisted, capped receipts; credential shapes refused; card + narrative | `tests/outcomes/test_outcomes.py` |
| **R103** | derived match/partial/exceeded/divergent comparison; exceeding resources named | `tests/outcomes/test_outcomes.py` |
| **R104** | chained `outcome-divergence`, card alert, acknowledgement observation | `tests/outcomes/test_outcomes.py` |
| **R105** | self-contained `decision-packet/1.0`, offline chain verification, CLI `--packet` | `tests/outcomes/test_outcomes.py` |
| **R106/R107** | ask→decision→execution→divergence trace; closure SLA + doctor finding | `tests/outcomes/test_outcomes.py` |

## M30 repetitive approvals, grants & compression (shipped tests, v0.1.0)

| Req | What M30 ships | Acceptance test |
|---|---|---|
| **R108/R112** | 12-ask compressed view with every row; no group decision; exports intact | `tests/grants/test_grants.py` |
| **R109/R110** | class/session windows with use+rate ceilings; auto-allow only while live; one session grant | `tests/grants/test_grants.py` |
| **R111** | card burn-down (uses/ceiling/remaining/owner/status) + doctor active grants | `tests/grants/test_grants.py` |
| **R113** | repeated-deny insight at threshold; no auto-approve or auto-harden | `tests/grants/test_grants.py` |
| **R114** | owner+reason issuance; chained issued/used/expired; immediate revocation | `tests/grants/test_grants.py` |

## M31 policy learning & governance insights (shipped tests, v0.1.0)

| Req | What M31 ships | Acceptance test |
|---|---|---|
| **R115** | repetitive-approval insight at threshold with redacted representative | `tests/insights/test_insights.py` |
| **R116** | deny clusters by reason+shape with tuning suggestions | `tests/insights/test_insights.py` |
| **R117** | class × tier × hour hotspots with routing/TTL recommendation | `tests/insights/test_insights.py` |
| **R118** | aggregate calibration; gated per-principal view + access log; no rankings | `tests/insights/test_insights.py` |
| **R119/R120** | evidence-gap and divergence-hardening proposals (never automatic) | `tests/insights/test_insights.py` |
| **R121/R122** | reviewable action export with origin; scanner-clean redacted payloads; stale expiry | `tests/insights/test_insights.py` |

## Forward slate traceability (R13–R47, PRDs 24–27)

The product-depth requirements are traced **inside their own PRDs** (each carries a
requirement → CUJ → scenario → test table); this register holds the summary so no requirement is orphaned:

| Range | Theme | PRD | Scenarios |
|---|---|---|---|
| R13–R20, E13 | Constrained approvals, effects, staleness, edits, bundles, dependencies, agent-readable outcomes | [PRD 24](24-constrained-approvals-and-effects.md) | SC-27, SC-28, SC-30, SC-34, SC-35, SC-39 |
| R21–R26, E14 | Evidence attachments, previews, quality scores, delta/trust blocks, decision packets | [PRD 25](25-evidence-and-decision-quality.md) | SC-29, SC-36 |
| R27–R36 | Grouped review, claim/assign, quiet hours, incident mode, views, SLA, search/replay, local web UI, precedent | [PRD 26](26-approver-experience-operations.md) | SC-31, SC-32 (+ SC-13/SC-34 hard mode) |
| R37–R47 | Standing approvals governed, quorum variants, provenance tiers, identity plugins, rule simulation, packs, templates, hooks, SDKs, CI/Git surfaces, risk-tier drivers | [PRD 27](27-governance-identity-extensibility.md) | SC-33, SC-37, SC-38, SC-40 |
| R48–R58, E15 | Review loop (needs_changes, clarifications, resolution summaries), session grants, approval windows, incident suppression, class routing, parallel notify, trust profiles, env overlays, change calendars | [PRD 28](28-review-loops-and-orchestration.md) | SC-41, SC-42, SC-43, SC-44, SC-45 |
| R59–R67, E16 | Rollback-required approvals, confidence labels, deny taxonomy, signed rationale, attestations, writeback, correlation, training mode, drill pack | [PRD 29](29-trust-maturity-writeback-performance.md) | SC-46, SC-47, SC-48, SC-49, SC-50, SC-51, SC-52, SC-53 |
| R78–R86 | Decision quality & ask readiness | [PRD 32](32-decision-quality-and-ask-readiness.md) | SC-68, SC-69, SC-70 |
| R87–R93 | Constrained allows & denial repair | [PRD 33](33-constrained-allows-and-denial-repair.md) | SC-71, SC-72, SC-73, SC-74 |
| R94–R100 | Operation bundles, handoff & incident review | [PRD 34](34-operation-bundles-handoff-and-incident-review.md) | SC-75, SC-76, SC-77, SC-78 |
| R101–R107 | Outcome closure & execution proof | [PRD 35](35-outcome-closure-and-execution-proof.md) | SC-79, SC-80, SC-81, SC-82 |
| R108–R114 | Repetitive approvals, grants & compression | [PRD 36](36-repetitive-approvals-grants-and-compression.md) | SC-83, SC-84, SC-85, SC-86 |
| R115–R122 | Policy learning & governance insights | [PRD 37](37-policy-learning-and-governance-insights.md) | SC-87, SC-88, SC-89, SC-90 |
| R68–R77, E17–E21 | Precedence lattice, formal state machine, review-loop limits, scope-escape protection, shared-machine provenance, no-advisory-allows, revocation, corpus governance, web-UI security, dead-man detection | [PRD 30](30-correctness-conflict-abuse-hardening.md) | SC-54, SC-55, SC-56, SC-57, SC-58, SC-59, SC-60, SC-61, SC-62, SC-63, SC-64, SC-65, SC-66, SC-67 |

## Consolidated-PRD coverage check (Appendix A → this PRD set)

| Appendix A line | Where it lives now |
|---|---|
| R1 receive with full context | **05 §R1** + CUJ-2 + SC-03/04/05 |
| R2 answer from terminal/desktop/Slack | **05 §R2** + CUJ-3/9 |
| R3 timeout=deny + warning + rescope | **05 §R3** + CUJ-4 |
| R4 escalation ladder | **05 §R4** + CUJ-5 |
| R5 agentwatch schema events | **05 §R5** + [PRD 20 §C](20-standards-and-claims.md) |
| R6 CI/headless checkpoints | **05 §R6** + CUJ-7 |
| R7 flood throttling + auto-deny event | **05 §R7** + CUJ-6 |
| R8 mobile push (v1.x) | **05 §A** + [PRD 09](09-roadmap.md) |
| R9 approval policies / delegation | **05 §A** + agentpolicy R41 dependency noted |
| R10 standing approvals with expiry | **05 §A** + [PRD 09](09-roadmap.md) |
| R11 approver analytics | [PRD 09 v0.2.0](09-roadmap.md) |
| R12 shared inbox | [PRD 09 v0.2.0](09-roadmap.md) |
| Non-requirements (no ML, no chat-bot, no harness-UI replacement) | [PRD 14](14-non-goals.md) |
| Standards (agentwatch, agentpolicy contract, escalation timing as a security property) | [PRD 20](20-standards-and-claims.md) + E8 |
| Success metrics | [PRD 07](07-success-metrics.md) |
| Open questions (timeout default, anti-spoofing) | **resolved/owned**: D-1 (timeout), [PRD 18](18-approval-integrity.md) (anti-spoofing) |

## Non-requirement coverage (things we promise not to do, and where that's tested)

| Non-goal | Guard test |
|---|---|
| No ML in decision path | code review gate + no ML deps in the dependency manifest (CI check) |
| No free-text approvals | fuzz: free-text "approve" in every channel surface is a no-op (`test_render_inert.py`) |
| No auto-approving links | link fixtures answer nothing without a POST + claim (`test_claims.py`) |
| No `--force`/`--yes` on answers | CLI surface test asserts the flags don't exist |
| No unredacted persistence | evidence scanner over store/channel/audit dumps |

## WBS alignment

The WBS (v0.1.0) is generated from this table: one milestone per requirement cluster (core lifecycle, terminal,
Slack, CI, escalation, flood, audit, adapters, ops), each milestone's acceptance tests named here. No WBS item
without a requirement ID; no requirement ID without a WBS item.
