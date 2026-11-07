# WBS v0.1.0 — Part 15: Operations, handoff & outcome closure (M28–M29)

> **Every milestone here is v0.1.0 work.** Standard exit criteria + closure apply (see the
> [index](wbs-v0.1.0-index.md)): design docs first (`.D0`), then implement one ticket at a time
> (test first, RED → GREEN), then close with **`.T` tests · `.C` coverage ≥95% · `.L` ruff +
> `mypy --strict` · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS checkpoint**.

## Milestone M28 — Operation bundles, handoff & incident review

**Goal:** Group related asks into derived operation bundles, add claim/assign/handoff, a bounded incident-mode overlay, decision narratives, and an operation timeline.

**CUJ:** CUJ-17, CUJ-18, CUJ-20, CUJ-21, CUJ-33..CUJ-36 · **PRD:** PRD 34 — Operation Bundles, Handoff & Incident Review · **Milestone:** 0.1.0 — M28 Operation bundles, handoff & incident review

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 28.D0 | Design docs first | Bundle derivation rules, handoff payload, incident-mode scope + limits, narrative/timeline shapes | docs | reviewed before code | #329 | CUJ-17..21 | R94–R100 |
| 28.1 | Bundle derivation + phase/critical path | Derived-on-read bundles from `operation_id` (or labelled heuristic); phases, aggregate blast radius, critical path; no bundle-level decision (SC-75) | bundle module | 20-ask bundle renders grouped, answers as 20 decisions, no one-tap-approve-all path | #330 | CUJ-17, CUJ-33 | R94, R95 |
| 28.2 | Claim / assign | Routing-only claim/assign recorded as observations with acknowledgement; status, TTL, eligibility unchanged | lifecycle observations | claimed ask answers identically; claim/assign appear in the timeline | #331 | CUJ-34 | R96 |
| 28.3 | Shift handoff note | Handoff carries remaining TTL, prior context, open questions, evidence gathered, outgoing principal (SC-76) | handoff | incoming approver sees the note before the card; TTL unchanged | #332 | CUJ-21 | R97 |
| 28.4 | Incident-mode overlay | One bounded, config-declared, audited mode changing urgency/routing without extending TTLs or converting denies to allows (SC-77) | config + scheduler + card | irreversible asks still deny on timeout; every mode change is chained | #333 | CUJ-20 | R98 |
| 28.5 | Decision narrative | Readable story from stored transitions: ask, evidence labels, rule, principal, alternatives, constraints, outcome (SC-78) | narrative renderer | a third party reconstructs the decision with only the rendered packet | #334 | CUJ-18 | R99 |
| 28.6 | Operation timeline | Causal order of ask/answer/deny/escalate/handoff/incident events, exportable with the bundle | timeline | ordering matches transition seqs; export includes it | #335 | CUJ-36 | R100 |
| 28.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #336 | — | — |
| 28.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #337 | — | — |
| 28.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #338 | — | — |
| 28.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #339 | — | — |
| 28.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #340 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Group related asks into derived operation bundles, add claim/assign/handoff, a bounded incident-mode overlay, decision narratives, and an operation timeline.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

## Milestone M29 — Outcome closure & execution proof

**Goal:** Close the loop after the decision: closure states, execution receipts, approved-vs-executed comparison, divergence alerting, and a portable decision packet.

**CUJ:** CUJ-24, CUJ-37..CUJ-40 · **PRD:** PRD 35 — Outcome Closure & Execution Proof · **Milestone:** 0.1.0 — M29 Outcome closure & execution proof

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 29.D0 | Design docs first | Closure state model, receipt schema, comparison semantics, packet format + offline verification | docs | reviewed before code | #341 | CUJ-24..40 | R101–R107 |
| 29.1 | Outcome closure states | Post-decision observations: executed/failed/cancelled/rolled_back/superseded; unresolved renders `outcome: unknown`; terminal decisions immutable (SC-81) | lifecycle observations | closure never alters the decision; ignored approvals stay unknown | #342 | CUJ-38 | R101 |
| 29.2 | Execution receipts | Redacted, capped receipt attachments (run URLs, digests, job ids, changed resources); receipts are evidence, never credentials (SC-79) | receipts | scanner finds zero secrets; receipt renders on card + narrative | #343 | CUJ-39 | R102 |
| 29.3 | Approved-vs-executed comparison | Derived `match/partial/exceeded/divergent` comparison of approved fingerprint/constraints vs executed manifest (producer claim untrusted) (SC-80) | comparison module | exceeding manifest reads `exceeded` with resources named | #344 | CUJ-24, CUJ-37 | R103 |
| 29.4 | Divergence alerting | `outcome-divergence` chained event surfaced on inbox, narrative, export; class config may require acknowledgement | events + card | divergence alerts without opening any approval path | #345 | CUJ-40 | R104 |
| 29.5 | Portable decision packet | Self-contained export: ask, redacted evidence, decision, principal, constraints/edits, narrative, outcome, chain segment + verify instructions (SC-79/SC-82) | export | packet-only reviewer verifies the chain segment offline | #346 | CUJ-39 | R105 |
| 29.6 | Outcome traceability + SLA | Join closure to ask/policy/writeback; per-class closure SLA surfaces in doctor/insights, never auto-closes (SC-82) | traceability + doctor | ask→decision→execution→divergence walk works; ignored irreversible approval shows outcome-pending-past-sla | #347 | CUJ-24 | R106, R107 |
| 29.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #348 | — | — |
| 29.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #349 | — | — |
| 29.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #350 | — | — |
| 29.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #351 | — | — |
| 29.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #352 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Close the loop after the decision: closure states, execution receipts, approved-vs-executed comparison, divergence alerting, and a portable decision packet.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

Part 15 green ⇒ proceed to the next part / [index](wbs-v0.1.0-index.md).
