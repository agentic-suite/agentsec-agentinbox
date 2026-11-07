# WBS v0.1.0 — Part 16: Grants, compression & policy learning (M30–M31)

> **Every milestone here is v0.1.0 work.** Standard exit criteria + closure apply (see the
> [index](wbs-v0.1.0-index.md)): design docs first (`.D0`), then implement one ticket at a time
> (test first, RED → GREEN), then close with **`.T` tests · `.C` coverage ≥95% · `.L` ruff +
> `mypy --strict` · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS checkpoint**.

## Milestone M30 — Repetitive approvals, grants & compression

**Goal:** Compress repeated asks as a view (never a group decision), add narrow timeboxed windows and session grants with ceilings, burn-down, repeated-deny escalation, and grant governance.

**CUJ:** CUJ-22, CUJ-41..CUJ-44 · **PRD:** PRD 36 — Repetitive Approvals, Grants & Compression · **Milestone:** 0.1.0 — M30 Repetitive approvals, grants & compression

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 30.D0 | Design docs first | Compression equivalence rules, window/grant shape + ceilings, burn-down fields, governance/revocation | docs | reviewed before code | #353 | CUJ-22..44 | R108–R114 |
| 30.1 | Repeated-ask compression | Group materially identical asks into one view with per-ask rows; each ask answered individually; export keeps every ask (SC-83) | card/inbox view | 12 asks → 1 group + 12 rows + 12 individual verifications; export complete | #354 | CUJ-22, CUJ-41 | R108, R112 |
| 30.2 | Timeboxed approval windows | Class-scoped, ceiling-bounded, expiring windows; answers carry `authorization.source=window-grant`; expiry reverts to per-ask (SC-84) | grants engine | expiry mid-burst reverts to per-ask with zero silent allows | #355 | CUJ-42 | R109 |
| 30.3 | Session grants | Session-scoped grant with one active grant per session, never outliving the session; standing-rules config governs owner/why/expiry/recert | grants engine | second grant for the same session refused; session end expires loudly | #356 | CUJ-42 | R110 |
| 30.4 | Grant burn-down UI | What the grant covers, uses used/ceiling, time remaining, issuing principal; `doctor --explain` lists active grants | renderer + doctor | burn-down on card + doctor; spent grant renders spent (SC-85) | #357 | CUJ-43 | R111 |
| 30.5 | Repeated-deny escalation | Repeated denies/non-decisionable clusters are NOT compressed; they surface as insight + optional class hardening (SC-86) | insight hook | 5 identical denials trigger the insight; nothing auto-approves/hardens | #358 | CUJ-44 | R113 |
| 30.6 | Grant governance + revocation | Owner/reason on issuance, chained events, owner/governance revocation is immediate and loud | governance | revoked window reverts covered asks instantly; every use is a chained event | #359 | CUJ-44 | R114 |
| 30.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #360 | — | — |
| 30.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #361 | — | — |
| 30.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #362 | — | — |
| 30.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #363 | — | — |
| 30.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #364 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Compress repeated asks as a view (never a group decision), add narrow timeboxed windows and session grants with ceilings, burn-down, repeated-deny escalation, and grant governance.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

## Milestone M31 — Policy learning & governance insights

**Goal:** Turn observed decisions into reviewed governance action: repetitive-approval, deny/rejection, escalation-hotspot, calibration, evidence-gap, and outcome-tuning insights with an insight-to-action workflow.

**CUJ:** CUJ-19, CUJ-45..CUJ-48 · **PRD:** PRD 37 — Policy Learning & Governance Insights · **Milestone:** 0.1.0 — M31 Policy learning & governance insights

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 31.D0 | Design docs first | Insight definitions, redaction/aggregation rules, calibration access model, insight-to-action path | docs | reviewed before code | #365 | CUJ-19..48 | R115–R122 |
| 31.1 | Repetitive-approval insight | Detect class+tool+shape patterns approved N times with low variance; propose a grant/rule/self-certification with counts and a redacted representative ask (SC-87) | insights | 20 similar approvals → one insight with redacted exemplar | #366 | CUJ-19, CUJ-45 | R115 |
| 31.2 | Deny/rejection clusters | Cluster denies and non-decisionable rejections by reason+shape; propose tuning (TTL, class split, evidence relaxation) (SC-88) | insights | 10 same-reason denies → one cluster naming the reason and a config change | #367 | CUJ-46 | R116 |
| 31.3 | Escalation hotspots | Correlate escalations/expiries by class×tier×hour; recommend roster/routing/TTL changes | insights | hotspot fixture names the pattern and a specific recommendation | #368 | CUJ-48 | R117 |
| 31.4 | Reviewer calibration | Aggregate-first variance across principals for similar asks; per-principal views gated + access-logged; never a ranking system (SC-89) | calibration view | aggregates render; per-principal access gated and logged | #369 | CUJ-47 | R118 |
| 31.5 | Evidence-gap reporting | Report which evidence dimensions block decisions/denials per class, feeding class evidence requirements | insights | class whose denies lack diffs gets a 'require diffs?' insight | #370 | CUJ-46 | R119 |
| 31.6 | Outcome-aware tuning | Divergence/closure patterns produce proposed hardening diffs (typed confirm, tier bump, shorter TTL) — never automatic (SC-90) | insights | divergence-heavy class yields a hardening proposal only | #371 | CUJ-45 | R120 |
| 31.7 | Insight-to-action | Export an insight as a proposed config diff / runbook task / grant proposal; record action, reviewer, origin (SC-88) | workflow | export produces the diff; applying is a git-reviewed PR | #372 | CUJ-45 | R121 |
| 31.8 | Insight hygiene | Redacted, aggregated payloads only; read-only queries; stale insights expire; scanner checks exports | privacy guard | insight export scanner finds zero secrets | #373 | CUJ-19 | R122 |
| 31.T | Tests | tests for this milestone's modules (unit + fixtures + corpus/conformance as applicable) | report/docs | milestone gate green (Tests) | #374 | — | — |
| 31.C | Coverage gate | enforce >=95% on this milestone's modules | report/docs | milestone gate green (Coverage gate) | #375 | — | — |
| 31.L | Lint & type gate | ruff zero; mypy --strict clean | report/docs | milestone gate green (Lint & type gate) | #376 | — | — |
| 31.CR | Code review | findings recorded in the v0.1.0 codereview log and resolved | report/docs | milestone gate green (Code review) | #377 | — | — |
| 31.D | Docs | reference/design docs for this milestone, linked from the WBS and PRD 12 | report/docs | milestone gate green (Docs) | #378 | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Turn observed decisions into reviewed governance action: repetitive-approval, deny/rejection, escalation-hotspot, calibration, evidence-gap, and outcome-tuning insights with an insight-to-action workflow.
- [ ] Committed & pushed; tracking issues closed or explicitly commented

---

Part 16 green ⇒ proceed to the next part / [index](wbs-v0.1.0-index.md).
