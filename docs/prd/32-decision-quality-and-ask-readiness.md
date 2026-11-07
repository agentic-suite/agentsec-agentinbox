# PRD 32 — Decision Quality & Ask Readiness

**BLUF:** agentinbox decides whether an ask is **ready to burden a human at all**. Every ask is scored for
readiness (completeness, target specificity, reversibility clarity, evidence sufficiency, trust provenance,
contradiction), low-quality asks are **rejected back to the producer** with machine-usable reasons, and every
delivered card carries a visible **quality banner**. Ambiguous asks never reach an approver silently.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

A human gate that forwards junk is just moving the junk upstream. This PRD makes the inbox the **quality
gate before the trust gate**: approvers see fewer, better asks; producers get structured feedback instead of
mystery denials; contradictions are caught *pre-approval*, where they are cheap, instead of post-mortem, where
they are expensive.

**Honesty clause:** scoring is *advisory to delivery*, never to the decision. A high readiness score never
approves anything; a low score never silently allows. Only humans approve.

---

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-25** | "Don't send me asks that aren't ready for a human" — an incomplete ask is bounced to the producer with structured reasons, before any approver is interrupted | P0 |
| **CUJ-26** | "Tell me why this ask is hard to decide before I read all of it" — a quality banner names the gaps up front | P0 |
| **CUJ-27** | "Distinguish *low-quality* from *high-risk*" — a harmless ask with weak context must not look more urgent than a dangerous ask with strong context | P0 |
| **CUJ-28** | "Block ambiguous approvals before they become incidents" — `staging` field + `prod` resource, or `read-only` claim + destructive args, are flagged loudly and rejectably | P0 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R78** | **Ask readiness score.** Every ask receives a readiness score across six dimensions: completeness (required fields present), target specificity (named resource, not "the database"), reversibility clarity (label, not blank), evidence presence (fresh artifacts attached where the class demands them), trust provenance (authenticated vs unverified fields), and contradiction checks. The score and its per-dimension breakdown ride the stored payload. | v0.1.0 | A corpus of scored asks produces the expected dimension breakdown; the score is derived, never producer-asserted |
| **R79** | **Non-decisionable rejection.** Below a configured per-class threshold, ingest returns `non-decisionable` — a structured rejection listing each failing dimension and what would fix it — and **stores nothing**, exactly like malformed asks (SC-02 posture). The ask never reaches a channel. | v0.1.0 | A readiness-failing ask produces zero pending rows, zero deliveries, one structured producer response |
| **R80** | **Contradiction detection.** The scorer flags contradictory signals before delivery: environment (`staging`) vs resource (`prod`), claimed mode (`read-only`) vs destructive arguments, low criticality vs irreversible class, unverified trust fields presented as authoritative. Flagged asks are **delivered with the flag** (the human may still approve) or rejected per class config. | v0.1.0 | Contradiction corpus (12 cases) → every case labelled with its contradiction; zero silent deliveries of contradicting asks without the flag visible on the card |
| **R81** | **Evidence sufficiency labels.** Cards label evidence as `strong / partial / weak / absent` and name the missing dimension ("no diff attached", "policy version unverified"). Sufficiency expectations are **per class** (an irreversible class demands more than a read-only one). | v0.1.0 | The same ask scored against two classes yields different sufficiency expectations; the label names the gap, never a bare "insufficient" |
| **R82** | **Freshness visibility.** Evidence-bearing asks carry freshness markers (age of the artifact, digest pinned vs drifted) rendered on the card; a stale-but-present artifact is never silently treated as fresh. Absent basis renders `unknown freshness` (inferred freshness is forbidden). | v0.1.0 | Freshness labels match the producer-pinned data; absence renders unknown |
| **R83** | **Quality banner on card.** Every delivered card renders a banner line summarizing readiness: score band, the top missing dimensions, and any contradictions — above the four context blocks, never below. | v0.1.0 | Banner present on 100% of delivered cards; hidden only when readiness is fully green |
| **R84** | **Producer repair contract.** `non-decisionable` and low-band responses are machine-parseable: `{"reason_code": "ask_not_decisionable", "dimensions": [{"name": "target_specificity", "fix": "name the exact resource"}], "retry": "after-repair"}` — so the agent repairs and resubmits instead of guessing. | v0.1.0 | A demo agent converts a rejection into a passing ask with no human parsing step |
| **R85** | **Similar-case guidance.** The card surfaces up to 3 prior asks with the same class+tool, their outcomes, their differing fields, and the reason they were allowed or denied. Guidance is labelled as precedent, **not** as a recommendation. | v0.1.0 | Similar-case fixture: differing fields highlighted; the renderer never says "you should approve" |
| **R86** | **Scoring config is class-owned.** Readiness thresholds and evidence expectations live in class config (reviewed like policy, PRD 22 §C); `doctor --explain` prints the effective expectations. A class with no expectations configured is a load error, not a silent default. | v0.1.0 | Missing expectation config refuses to start, naming the class |

## Non-goals

- No ML in the decision path (PRD 14); readiness scoring is deterministic rules over producer-declared fields.
- The score never appears on a path to allow.
- No silent dropping of delivered-but-poor asks: rejection is loud and structured, or the ask ships with its banner.

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-68** | A readiness-failing ask bounces pre-delivery, stores nothing, and returns a machine-usable repair contract |
| **SC-69** | A contradicting ask renders with the contradiction visible, and can be configured to reject at ingest |
| **SC-70** | The same weak ask scores differently against a read-only vs irreversible class |

## Traceability

| Requirement | Test |
|---|---|
| R78–R83 | `tests/readiness/` (scorer, banner, corpus fixtures) |
| R79 | `tests/readiness/test_rejection.py` |
| R84 | `tests/readiness/test_repair_contract.py` |
| R85 | `tests/readiness/test_similar_cases.py` |
| R86 | `tests/readiness/test_class_config.py` |
