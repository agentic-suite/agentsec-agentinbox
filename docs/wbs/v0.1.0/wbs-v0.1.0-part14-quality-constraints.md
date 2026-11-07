# WBS v0.1.0 — Part 14: Ask readiness & constrained repair (M26–M27)

> **Every milestone here is v0.1.0 work.** Standard exit criteria + closure apply (see the
> [index](wbs-v0.1.0-index.md)): design docs first (`.D0`), then implement one ticket at a time
> (test first, RED → GREEN), then close with **`.T` tests · `.C` coverage ≥95% · `.L` ruff +
> `mypy --strict` · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS checkpoint**.

## Milestone M26 — Ask readiness & decision quality

**Goal:** Score every ask for readiness before delivery, bounce non-decisionable asks with machine-usable repair guidance, detect contradictions, label evidence sufficiency/freshness, and put a quality banner on every card.

**CUJ:** CUJ-25..CUJ-28 · **PRD:** PRD 32 — Decision Quality & Ask Readiness · **Milestone:** 0.1.0 — M26 Ask readiness & decision quality

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 26.D0 | Design docs first | Readiness model (six dimensions), rejection contract, contradiction rules, banner layout, class-owned expectations | docs | reviewed before code | #306 | CUJ-25..28 | R78–R86 |
| 26.1 | Readiness scorer | Deterministic six-dimension scorer (completeness, target specificity, reversibility clarity, evidence presence, trust provenance, contradiction) stored on the ask payload | readiness module | scored corpus produces the expected per-dimension breakdown; score is derived, never producer-asserted | #307 | CUJ-26 | R78 |
| 26.2 | Non-decisionable rejection + repair contract | Ingest rejects below-threshold asks with a structured `non-decisionable` response (dimension, fix, retry), storing nothing | ingest gate + contract | failing ask produces zero pending rows, zero deliveries, one structured response (SC-68) | #308 | CUJ-25 | R79, R84 |
| 26.3 | Contradiction detector | Detect staging-vs-prod resource, read-only-vs-destructive args, low criticality vs irreversible, unverified trust presented as fact; deliver-with-flag or reject per class (SC-69) | detector + fixtures | 12-case contradiction corpus labels every case; no silent unflagged delivery | #309 | CUJ-28 | R80 |
| 26.4 | Evidence sufficiency + freshness labels | Per-class evidence expectations; strong/partial/weak/absent labels naming the missing dimension; freshness markers with `unknown freshness` when no basis | scoring + renderer | same ask scores differently across classes; missing basis renders unknown (SC-70) | #310 | CUJ-26 | R81, R82 |
| 26.5 | Quality banner + similar-case guidance | Banner above the four blocks (band, missing dimensions, contradictions); up to 3 prior similar asks labelled precedent — never recommendation | card renderer | banner on 100% of delivered cards; guidance never recommends an outcome | #311 | CUJ-26 | R83, R85 |
| 26.6 | Class-owned readiness config | Per-class thresholds + evidence expectations in config; missing expectation config is a load error; `doctor --explain` prints them | config + doctor | absent expectations refuse to start naming the class | #312 | CUJ-26 | R86 |
| 26.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #313 | — | — |
| 26.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #314 | — | — |
| 26.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #315 | — | — |
| 26.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #316 | — | — |
| 26.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #317 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Score every ask for readiness before delivery, bounce non-decisionable asks with machine-usable repair guidance, detect contradictions, label evidence sufficiency/freshness, and put a quality banner on every card.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

## Milestone M27 — Constrained allows & denial repair

**Goal:** Let producers advertise safe alternatives, render them as one-click constrained allows, return machine-readable denial repair packets, and support human edits with provenance.

**CUJ:** CUJ-15, CUJ-16, CUJ-29..CUJ-32 · **PRD:** PRD 33 — Constrained Allows & Denial Repair · **Milestone:** 0.1.0 — M27 Constrained allows & denial repair

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 27.D0 | Design docs first | Alternatives schema, suggestion rules, repair-packet shape, edit re-fingerprinting, resolve vocabulary additions | docs | reviewed before code | #318 | CUJ-15/16 | R87–R93 |
| 27.1 | Producer alternatives + enforcer binding | `alternatives[]` with named scopes/constraints/fingerprints; offered only when the producer declares an enforcer binding (PRD 24 clause) (SC-71/SC-74) | contract + resolve | chosen alternative yields `allow_with_constraints` bound to its fingerprint; unbindable variants render as advice only | #319 | CUJ-15, CUJ-29 | R87, R93 |
| 27.2 | Constraint suggestion heuristics | Class-generic narrowings (environment demotion, dry-run, subset) rendered as labelled suggestions; unpicked suggestions leave no constraint | suggestions | unpicked variants leave zero constraints in the resolve | #320 | CUJ-32 | R88 |
| 27.3 | Denial repair packet | Structured deny guidance: violated invariant, missing evidence, suggested scope, safe alternative, retry-worthiness, required tier; carried in resolve + audit + redacted event (SC-72) | deny path | producer receives the packet without human parsing; `pointless` suppresses blind retries | #321 | CUJ-16, CUJ-30, CUJ-31 | R89 |
| 27.4 | Human edits + constraint provenance | Declared edit schemas; edits re-canonicalized and re-fingerprinted; edited action is the approved action; record who applied what and the narrowing diff (SC-73) | edit pipeline | edited approval executes the edited form; out-of-schema edits rejected with the field named | #322 | CUJ-29 | R90, R91 |
| 27.5 | Repair recall + resolve vocabulary | Prior denial reason/packet surfaced on resubmission; additive `allow_with_constraints` / `allow_with_edits` / `repair` fields in resolve/1.0 | resolve + card | resubmission shows prior objections; old clients see deny/allow unchanged | #323 | CUJ-16 | R92 |
| 27.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #324 | — | — |
| 27.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #325 | — | — |
| 27.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #326 | — | — |
| 27.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #327 | — | — |
| 27.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #328 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Let producers advertise safe alternatives, render them as one-click constrained allows, return machine-readable denial repair packets, and support human edits with provenance.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

Part 14 green ⇒ proceed to the next part / [index](wbs-v0.1.0-index.md).
