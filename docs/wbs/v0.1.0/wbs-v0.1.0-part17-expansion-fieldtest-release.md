# WBS v0.1.0 — Part 17: Field Tests & Release — the final two milestones (M32–M33)

> **Every milestone here is v0.1.0 work.** Standard exit criteria + closure apply (see the
> [index](wbs-v0.1.0-index.md)): design docs first (`.D0`), then implement one ticket at a time
> (test first, RED → GREEN), then close with **`.T` tests · `.C` coverage ≥95% · `.L` ruff +
> `mypy --strict` · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS checkpoint**.
>
> **Ordering:** M32 and M33 are the final two milestones. Nothing follows M33; it tags `v0.1.0`. M24/M25
> (core field tests and release rehearsal) are re-executed at M32/M33.

## Milestone M32 — Field tests — FINAL (SC-01–SC-90 + the 15-second study)

**Goal:** The **final** field-test pass: re-execute the core catalog (SC-01–SC-26) on the expanded build, execute the expansion scenarios SC-68–SC-90, extend the zero-context study to the new CUJs, and publish an honest report whose red verdicts block release.

**CUJ:** CUJ-15..CUJ-48 · **PRD:** PRD 31 — 0.1.0 CUJ & Feature Gaps (field-test execution) · **Milestone:** 0.1.0 — M32 Field tests — FINAL (SC-01–SC-90 + the 15-second study)

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 32.D0 | Field-test plan | Plan for SC-68–SC-90 + extended 15-second study (new CUJ corpus with pre-registered answers) | plan | reviewed before execution | #379 | all expansion CUJs | SC-68–SC-90 |
| 32.1 | Execute SC-68–SC-74 | Readiness rejection, contradictions, constrained allows, repair-packet round trip, edits, unbindable advice | results | every scenario has evidence + verdict | #380 | CUJ-15..32 | SC-68..74 |
| 32.2 | Execute SC-75–SC-78 | Bundles, handoff, incident mode, decision narrative | results | verdicts with evidence | #381 | CUJ-17..21 | SC-75..78 |
| 32.3 | Execute SC-79–SC-86 | Outcome closure/packets/divergence, compression, windows, revocation | results | verdicts with evidence | #382 | CUJ-22..40 | SC-79..86 |
| 32.4 | Execute SC-87–SC-90 | Insights, calibration access, divergence tuning proposals | results | verdicts with evidence | #383 | CUJ-19..48 | SC-87..90 |
| 32.5 | Extend the 15-second study | New card corpus across expansion CUJs, pre-registered answers, checksummed; run the study | study | results reproducible from the frozen corpus | #384 | CUJ-2..28 | R1, CUJ-2 |
| 32.7 | Re-run core scenarios SC-01–SC-26 | SC-01–SC-26 on the expanded build vs the M24 baseline; attack packs release-blocking; regressions documented | verdicts + regression notes | every core scenario verdicted; any red blocks M33 | #401 | all | R1–R7, E1–E12 |
| 32.6 | Publish the honest report | Every scenario verdict, found issues, and release-blocking reds | report | report published; red blocks M33 | #385 | — | — |
| 32.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #386 | — | — |
| 32.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #387 | — | — |
| 32.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #388 | — | — |
| 32.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #389 | — | — |
| 32.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #390 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Execute the expansion scenarios SC-68–SC-90 and extend the zero-context study to the new CUJs; publish an honest report with red verdicts blocking release.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

## Milestone M33 — Release readiness — FINAL (tags `v0.1.0`)

**Goal:** Close the expanded v0.1.0: compatibility matrix, claims lint, evidence scanner, docs, SBOM/signing, and the tag — only after M32 is green.

**CUJ:** CUJ-14 · **PRD:** PRD 31 — 0.1.0 release gate (expanded) · **Milestone:** 0.1.0 — M33 Release readiness (expanded v0.1.0)

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 33.D0 | Release plan | Scope, claims vocabulary, compatibility labels, artifact list for the expanded release | plan | reviewed before release work | #391 | CUJ-14 | PRD 20, PRD 19 |
| 33.1 | Compatibility matrix + honest labels | Update the matrix for all new surfaces; no claim beyond evidence | docs | every label is one of field-tested/conformance-tested/documented/not-supported | #392 | CUJ-14 | PRD 19 |
| 33.2 | Claims lint + evidence scanner | Claims lint vs PRD 20 §G; evidence scanner over store/channel/audit/packets | CI gates | both green; zero secrets in evidence | #393 | CUJ-14 | PRD 20/21 |
| 33.3 | Docs, quickstart, runbooks | Reference set + quickstart + runbooks for the expansion surfaces | docs | linked from README/WBS | #394 | CUJ-1 | PRD 23 |
| 33.4 | SBOM, signing, tag | SBOM, signed artifacts (SLSA/Sigstore), tag v0.1.0 after M32 green | release | artifacts verify; tag only after the gate | #395 | CUJ-14 | PRD 20 |
| 33.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #396 | — | — |
| 33.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #397 | — | — |
| 33.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #398 | — | — |
| 33.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #399 | — | — |
| 33.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #400 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Close the expanded v0.1.0: compatibility matrix, claims lint, evidence scanner, docs, SBOM/signing, and the tag — only after M32 is green.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

Part 17 green ⇒ proceed to the next part / [index](wbs-v0.1.0-index.md).
