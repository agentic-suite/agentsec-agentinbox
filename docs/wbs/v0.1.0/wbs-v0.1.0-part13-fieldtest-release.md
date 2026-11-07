# WBS v0.1.0 — Part 13: Core Field Tests & Release Rehearsal (M24–M25)

**BLUF:** **M24 proves it on the field-test box**: the plan authored first, then all **26 v0.1.0 scenarios**
(SC-01–SC-26) executed with per-scenario verdicts, the **zero-context 15-second study** (Method B) run with
its frozen corpus, the harness recipes field-tested (Claude Code + Codex CLI), and the honest report published
under `docs/field-test/v0.1.0/` — misses documented, never smoothed, and **no automation overwrites the
hand-maintained report**. **M25 ships it**: claims lint vs the [PRD 20 §G](../../prd/20-standards-and-claims.md)
vocabulary, release notes + the honest compatibility matrix, SBOM + Sigstore/SLSA, the Wave-0 demo wiring, and
the `v0.1.0` tag + PyPI publish.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).
>
> **Ordering:** M24/M25 are the **core** field-test pass and release rehearsal. After the 0.1.0 expansion
> (M26–M31), the **final two milestones are M32 (field tests, SC-01–SC-90) and M33 (release readiness)**;
> M33 tags `v0.1.0`. Nothing follows M33.

> **AMENDED 2026-11-07 — M24 and M25 are ABSORBED into M32 and M33.**
> The two-pass design is replaced by **one field-test pass (M32) and one release pass (M33)**. M24 was a
> strict subset of M32's SC-01–SC-26 re-run; M25 was a rehearsal of the same release M33 performs. Every
> M24/M25 work item maps to an M32/M33 item (see the
> [absorption map](wbs-v0.1.0-index.md#m24m25-absorption-into-m32m33-amended-2026-11-07)); two items with
> no counterpart became new work items: **32.8 harness recipe runs (#402)** and
> **33.5 Wave-0 demo wiring (#403)**. Issues #98–#123 are closed as *absorbed* (each names its target).
> **Consequence:** the core is not hardware-tested before M26–M31; the M32 regression baseline is the M23
> core commit `ab94330` + PRD 17 expected behavior, not a measured M24 verdict set.

---

## Milestone M24 — Core field tests (SC-01–SC-26 + the 15-second study) — **ABSORBED into M32**

> **Status: absorbed (2026-11-07).** Execute these items inside **M32** (32.D0/32.5/32.6/32.7); do not
> run a separate pass. Issue targets: #98→32.D0, #99–#102/#106→32.7/32.T, #103→32.5, #104→32.8, #105→32.6,
> #107–#110→32.C/L/CR/D.

**Goal:** execute [PRD 17](../../prd/17-scenarios.md)'s v0.1.0 catalog on real hardware with real harnesses:
lifecycle (SC-01–06), expiry (09–10), cross-channel truth (07/18/19), escalation (11/12), flood (13/14), CI
(15/16), evidence (20/21), attacks (17/22/23/24), plugin (25), offline (26) — plus the **study** (SC-03/04/05
corpora with pre-registered answers, ≥ 9/10 approvers correct in < 15 s) and live recipe runs for Claude Code
and Codex CLI. The report is the evidence register's EV-2..EV-14 made real.

**CUJ:** all (the catalog exercises every CUJ) · **Requirements:** [PRD 17](../../prd/17-scenarios.md),
[PRD 21 §B/§C](../../prd/21-evidence-register-and-method.md), [PRD 07 §B](../../prd/07-success-metrics.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 24.D0 | **Field-test plan first** | `docs/field-test/v0.1.0/FIELD_TEST_PLAN.md`: box spec, clock/env recording, scenario run order, study protocol (participants, corpus checksum, pass bars), report template — authored **before** any run | plan | plan reviewed + frozen; corpus checksums recorded | #98 | — | — |
| 24.1 | Lifecycle + expiry runs | SC-01..06, SC-09/10: ingest→card→answer, malformed rejects, coalescing, expiry with warning, crash-restart, clock jumps | verdicts | all green or honestly documented with causes + owners | #99 | CUJ-1/4 | R1, R3, E1, E2, E8 |
| 24.2 | Cross-channel + escalation runs | SC-07/08/11/12/18/19: parity, races, ladder drills (incl. the 3 a.m. drill with named tiers), failover, late answers | verdicts | ladder reaches the configured tier in window; races resolve once | #100 | CUJ-3/5/9 | R2, R4, E3, E7 |
| 24.3 | Flood + CI + evidence + attacks | SC-13/14 (flood + legitimate burst), SC-15/16 (CI matrix), SC-20/21 (reconstruction + scanner), SC-17/22/23/24 (self-review, spoof/inject/faults) | verdicts | attack packs **release-gating**: any red blocks M25 | #101 | CUJ-6/7/10/11 | R5, R6, R7, E3..E9 |
| 24.4 | Plugin + offline runs | SC-25 (LangGraph crash-resume) + SC-26 (offline day) | verdicts | offline green with network disabled; plugin resumes exactly-once | #102 | CUJ-12/13 | E1, E9 |
| 24.5 | **Zero-context study (Method B)** | ≥ 10 participants, randomized frozen corpus (12 + 12 degraded + 10 poisoned cards), worst-case surface, pre-registered pass bars (≥9/10 ≥10/12 correct, median < 15 s, 0 approvals-from-injection) | study report | raw timings + decisions + corpus checksum published; bars met or the miss is documented and M25 gates on it | #103 | CUJ-2 | R1, E5 |
| 24.6 | Harness recipe runs | Claude Code `PreToolUse` + Codex CLI wrapper recipes executed live (the "field-tested" labels for the M25 matrix) | run journal | versions, dates, transcripts recorded per [PRD 21 §D](../../prd/21-evidence-register-and-method.md) | #104 | — | PRD 19 |
| 24.7 | **The report (hand-maintained)** | `FIELD_TEST_REPORT.md`: master verdict table + per-scenario notes + study + journal + **misses section**; the no-automation-overwrite guard verified (temp-copy test only) | report | every SC-01..26 row has an honest verdict; automation never writes the report | #105 | all | R1..R7, E1..E12 |
| 24.T | Tests | Field-test fixtures re-runnable (`make fieldtest-v010` style target; distinct log filenames) | runner | runner reproduces verdicts from the report's commands | #106 | — | — |
| 24.C | Coverage gate | No new code expected; fixture coverage maintained | report | no regression | #107 | — | — |
| 24.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #108 | — | — |
| 24.CR | Code review | Findings resolved | log | no open findings | #109 | — | — |
| 24.D | Docs | The report itself + plan; risk re-grade ([PRD 08](../../prd/08-risks.md) section) | docs | published under `docs/field-test/v0.1.0/` | #110 | — | — |
| 24.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 24.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Plan authored and frozen **before** the run; corpus checksums recorded
- [ ] All 26 scenarios graded with published verdicts; attack packs green (or the release is blocked)
- [ ] Study bars met (or honestly missed with a documented decision at M25); report is hand-maintained

---

## Milestone M25 — Release readiness (tags `v0.1.0`) — **ABSORBED into M33**

> **Status: absorbed (2026-11-07).** Execute these items inside **M33**; there is one release pass.
> Issue targets: #111→33.D0, #112→33.2, #113→33.1, #114→33.3, #115→33.4, #116→33.5, #117→33.D,
> #118→33.4, #119–#123→33.T/C/L/CR/D.

**Goal:** ship honestly: the **claims lint** enforces the [PRD 20 §G](../../prd/20-standards-and-claims.md)
vocabulary against every public doc (no over-claim ships), release notes carry the measured benches + the
**honest compatibility matrix** (labels: field-tested / conformance-tested / documented / not-supported) +
the explicit v0.1.0 gap list, SBOM + Sigstore-signed artifacts + SLSA provenance, the Wave-0 demo wiring
verified end-to-end, and the tag + PyPI publish.

**CUJ:** CUJ-14 (the honest-buyer milestone) · **Requirements:** [PRD 20 §E–H](../../prd/20-standards-and-claims.md),
[PRD 21](../../prd/21-evidence-register-and-method.md), [PRD 23 §C](../../prd/23-enterprise-adoption-and-governance-hardening.md),
[PRD 19](../../prd/19-harness-compatibility.md), [PRD 07](../../prd/07-success-metrics.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 25.D0 | **Design docs first** | Release plan: claims-lint vocabulary mapping, matrix generation from evidence, signing pipeline, demo script, rollback plan | plan | reviewed before execution | #111 | — | — |
| 25.1 | **Claims lint** | Machine-check published docs/READMEs against the [PRD 20 §G](../../prd/20-standards-and-claims.md) vocabulary (forbidden/restricted claims: no "blocks all injection", no "enterprise-ready", no unproven perf numbers); a claim without its evidence row fails CI | lint + CI | green on every public doc; a seeded over-claim fixture fails | #112 | CUJ-14 | PRD 20 §G |
| 25.2 | Compatibility matrix (generated) | The [PRD 19](../../prd/19-harness-compatibility.md) table generated **from evidence**: field-tested rows cite the M24 journal; conformance rows cite fixtures; unsupported rows state reasons | matrix | no row lacks a label; no ✅ without a citation | #113 | CUJ-14 | PRD 19 |
| 25.3 | Release notes + gap list | Notes: what shipped (R1–R7 + E1–E12 each named), measured benches (M21), the honest gap list (no SSO/quorum/standing-approvals/mobile-push at v0.1.0 — [PRD 23 §A](../../prd/23-enterprise-adoption-and-governance-hardening.md)), field-test verdict summary | notes | every claim traceable; gaps listed before features | #114 | CUJ-14 | PRD 20 §H |
| 25.4 | Supply chain | SBOM (CycloneDX), Sigstore signing, SLSA provenance on artifacts; OpenSSF Scorecard run + badge recorded | artifacts | verification recipe documented; scorecard grade in the notes | #115 | — | PRD 20 §D/E |
| 25.5 | **Wave-0 demo wiring** | The ecosystem demo end-to-end: agentpolicy's Replit rule fires → terminal + desktop alert → deny with a reason → agentwatch events + audit reconstruction — verified as the release's smoke test | demo | demo script runs green on the release commit; recorded as EV evidence | #116 | — | PRD 01 §5 |
| 25.6 | Security audit + risk re-grade | The [PRD 06](../../prd/06-security-baseline.md) non-claims re-stated against evidence; [PRD 08](../../prd/08-risks.md) risks re-graded post-field-test (tripwire values recorded) | audit note | published under `docs/release/v0.1.0/` | #117 | — | PRD 06/08/21 |
| 25.7 | **Tag + publish** | `v0.1.0` tag → GitHub release (notes + artifacts + matrix) → PyPI `agentsec-agentinbox==0.1.0`; README links go live | release | `pip install agentsec-agentinbox` works from the public index; install→approval reproduces on a fresh box | #118 | CUJ-1 | — |
| 25.T | Tests | Release smoke: fresh-box install → quickstart → demo → export/verify | tests | smoke green on the release commit | #119 | — | — |
| 25.C | Coverage gate | Final ≥95% confirmed on the release commit | report | ≥95% | #120 | — | — |
| 25.L | Lint & type gate | `ruff` zero; `mypy --strict` clean on the tag | CI | zero violations | #121 | — | — |
| 25.CR | Code review | Findings resolved | log | no open findings | #122 | — | — |
| 25.D | Docs | Release notes, verifier instructions, the evidence index (EV-1..EV-14 → artifacts) | docs | published under `docs/release/v0.1.0/` | #123 | — | PRD 21 |
| 25.CI | Commit & push | Feature branch → main; tag pushed | git | tagged `v0.1.0` | — | — | — |
| 25.W | Update WBS | Final checkpoint; milestone issues closed | WBS | recorded; set complete | — | — | — |

**Exit criteria**

- [ ] Claims lint green; compatibility matrix generated from evidence; notes carry benches + gaps + verdicts
- [ ] SBOM/signed artifacts/Scorecard done; Wave-0 demo green on the release commit
- [ ] `v0.1.0` tagged and published; fresh-box install → first approval reproduces; **M25 tags `v0.1.0`**

---

Part 13 green ⇒ **v0.1.0 is shipped**: the gate has a consumer, the consumer has evidence, and the evidence
has a release. The forward slate (PRDs 24–30) starts its own WBS at v0.1.x.
