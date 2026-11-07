# WBS v0.1.0 — Part 17: Field Tests & Release — the final two milestones (M32–M33)

> **Every milestone here is v0.1.0 work.** Standard exit criteria + closure apply (see the
> [index](wbs-v0.1.0-index.md)): design docs first (`.D0`), then implement one ticket at a time
> (test first, RED → GREEN), then close with **`.T` tests · `.C` coverage ≥95% · `.L` ruff +
> `mypy --strict` · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS checkpoint**.
>
> **Ordering:** M32 and M33 are the final two milestones. Nothing follows M33; it tags `v0.1.0`. M24/M25
> (core field tests and release rehearsal) are re-executed at M32/M33.

## Milestone M32 — Field tests — FINAL (SC-01–SC-90 + the 15-second study)

**Goal:** The **only** field-test pass (it absorbs M24): execute the core catalog (SC-01–SC-26) **and**
the expansion scenarios SC-68–SC-90 on the expanded build, run **one** zero-context study across all
CUJs, run the Claude Code / Codex CLI recipes live, and publish an honest report whose red verdicts
block release.

**CUJ:** CUJ-15..CUJ-48 · **PRD:** PRD 31 — 0.1.0 CUJ & Feature Gaps (field-test execution) · **Milestone:** 0.1.0 — M32 Field tests — FINAL (SC-01–SC-90 + the 15-second study)

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 32.D0 | Field-test plan | **One** plan covering SC-01–SC-90 + the single 15-second study protocol (box spec, clock/env, run order, frozen corpora with checksums, report template); authored before any run | plan | reviewed + frozen; corpus checksums recorded | #379 | all CUJs | SC-01–SC-90 |
| 32.1 | Execute SC-68–SC-74 | Readiness rejection, contradictions, constrained allows, repair-packet round trip, edits, unbindable advice | results | every scenario has evidence + verdict | #380 | CUJ-15..32 | SC-68..74 |
| 32.2 | Execute SC-75–SC-78 | Bundles, handoff, incident mode, decision narrative | results | verdicts with evidence | #381 | CUJ-17..21 | SC-75..78 |
| 32.3 | Execute SC-79–SC-86 | Outcome closure/packets/divergence, compression, windows, revocation | results | verdicts with evidence | #382 | CUJ-22..40 | SC-79..86 |
| 32.4 | Execute SC-87–SC-90 | Insights, calibration access, divergence tuning proposals | results | verdicts with evidence | #383 | CUJ-19..48 | SC-87..90 |
| 32.5 | Zero-context study (one cohort) | One corpus across core + expansion CUJs (12 + 12 degraded + 10 poisoned, extended for the new CUJs), pre-registered answers, checksummed; ≥10 participants who did not author cards; run once | study | raw timings + decisions + checksum published; bars met or the miss documented for M33 | #384 | CUJ-2..28 | R1, E5 |
| 32.7 | Execute core scenarios SC-01–SC-26 | SC-01–SC-26 on the expanded build against the **M23 core commit `ab94330` + PRD 17 expected behavior** (there is no separate M24 pass); attack packs release-blocking; regressions documented | verdicts + regression notes | every core scenario verdicted; any red blocks M33 | #401 | all | R1–R7, E1–E12 |
| 32.8 | **Harness recipe runs (absorbed 24.6)** | Claude Code `PreToolUse` + Codex CLI wrapper executed live; record harness version, date, transcript, OS/user, and the gate outcome | run journal | journal entries cite a real harness version + transcript; feeds the M33 matrix labels | #104 | — | PRD 19 |
| 32.6 | Publish the honest report | Every scenario verdict, found issues, and release-blocking reds | report | report published; red blocks M33 | #385 | — | — |
| 32.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #386 | — | — |
| 32.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #387 | — | — |
| 32.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #388 | — | — |
| 32.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #389 | — | — |
| 32.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #390 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-01–SC-90 all verdicted (core against the M23 baseline + PRD 17); one study cohort run; harness journal recorded; honest report published with reds blocking M33.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

## Milestone M33 — Release readiness — FINAL (tags `v0.1.0`)

**Goal:** Close the expanded v0.1.0 (**it absorbs M25**): claims lint, generated compatibility matrix, release notes + gap list, SBOM/signing, the Wave-0 demo, the security audit, and the tag — only after M32 is green.

**CUJ:** CUJ-14 · **PRD:** PRD 31 — 0.1.0 release gate (expanded) · **Milestone:** 0.1.0 — M33 Release readiness (tags `v0.1.0`)

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 33.D0 | Release plan | Scope, claims vocabulary, compatibility labels, artifact list for the expanded release | plan | reviewed before release work | #391 | CUJ-14 | PRD 20, PRD 19 |
| 33.1 | Compatibility matrix + honest labels | Update the matrix for all new surfaces; no claim beyond evidence | docs | every label is one of field-tested/conformance-tested/documented/not-supported | #392 | CUJ-14 | PRD 19 |
| 33.2 | Claims lint + evidence scanner | Claims lint vs PRD 20 §G; evidence scanner over store/channel/audit/packets | CI gates | both green; zero secrets in evidence | #393 | CUJ-14 | PRD 20/21 |
| 33.3 | Docs, quickstart, runbooks | Reference set + quickstart + runbooks for the expansion surfaces | docs | linked from README/WBS | #394 | CUJ-1 | PRD 23 |
| 33.4 | SBOM, signing, tag (absorbed 25.4/25.7) | SBOM, signed artifacts (SLSA/Sigstore), OpenSSF Scorecard recorded, `v0.1.0` tag + GitHub release + PyPI **only after M32 is green** | release | artifacts verify; `pip install` reproduces the quickstart | #395 | CUJ-14 | PRD 20 |
| 33.5 | **Wave-0 demo wiring (absorbed 25.5)** | agentpolicy rule fires → terminal + desktop alert → deny with reason → agentwatch events + audit reconstruction; run as the release smoke test and record it as evidence | demo | demo script green on the release commit; evidence recorded | #116 | — | PRD 01 §5 |
| 33.6 | **Security audit + risk re-grade (absorbed 25.6)** | PRD 06 non-claims restated against M32 evidence; PRD 08 risks re-graded; published under `docs/release/v0.1.0/` | audit note | published; no claim without evidence | #117 | CUJ-14 | PRD 06/08/21 |
| 33.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #396 | — | — |
| 33.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #397 | — | — |
| 33.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #398 | — | — |
| 33.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #399 | — | — |
| 33.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #400 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Claims lint green; compatibility matrix generated from M32 evidence; notes carry benches + gaps + verdicts; Wave-0 demo + security audit recorded.
- [ ] SBOM/signed artifacts/Scorecard done; `v0.1.0` tagged and published only after M32 green; fresh install reproduces the quickstart.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

Part 17 green ⇒ proceed to the next part / [index](wbs-v0.1.0-index.md).
