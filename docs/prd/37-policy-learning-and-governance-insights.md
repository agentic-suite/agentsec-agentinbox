# PRD 37 — Policy Learning & Governance Insights

**BLUF:** the product should get **quieter and sharper over time**. This PRD defines the feedback layer:
repetitive-approval insight ("these never needed a human"), noisy-policy insight ("this class always denies or
escalates"), reviewer calibration, evidence-gap reporting, escalation hotspots, and an **insight-to-action**
workflow that turns observed friction into reviewed policy changes. Governance becomes evidence-led instead of
anecdotal.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

Without a feedback layer, a human gate becomes **permanent friction** and operators tune it out. With one, the
inbox is a measurement instrument for the org's own decision-making: which asks are noise, which classes are
misconfigured, which evidence is never enough, and which humans disagree. This is the PRD that makes the
product *improve the organization*, not just police the agent.

**Honesty clauses:**

1. **Insights never act.** An insight can propose a policy change, a grant (PRD 36), or a class hardening —
   it can never apply one. Every change goes through PRD 22 §C's git-reviewed config path.
2. **Humans are not performance-ranked.** Calibration views exist to align standards and design systems, not
   to score reviewers. Data is aggregated by default; per-human views are access-controlled.

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-19** | "Tell us which asks should never have reached a human" — near-always-approved patterns surface as grant/rule candidates | P0 |
| **CUJ-45** | "Show the class that never needed this gate" — repetitive-approval insight with counts and variance | P0 |
| **CUJ-46** | "Show the policy that generates noise" — always-denied / always-missing-evidence clusters | P0 |
| **CUJ-47** | "Help us improve reviewer consistency" — variance across similar asks, aggregate by default | P1 |
| **CUJ-48** | "Turn escalation hotspots into action" — 3 a.m. tiers, timeout classes, routing recommendations | P0 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R115** | **Repetitive-approval insight.** Detect class+tool+argument-shape patterns approved ≥ N times with ≤ X outcome variance in a window; emit an insight proposing a window grant (PRD 36), standing rule (PRD 27), or producer self-certification. Insights carry counts, time range, and a representative ask id — never raw arguments (redacted per E6). | v0.1.0 | 20 similar approvals produce one insight; the insight links a representative redacted ask, not the full corpus |
| **R116** | **Repetitive-deny / rejection insight.** Cluster denials and PRD 32 non-decisionable rejections by reason code + shape; emit "this policy/class generates noise" insights with the dominant reason and a tuning suggestion (TTL change, class split, evidence requirement relaxation). | v0.1.0 | 10 same-reason denials produce one cluster insight naming the reason code and suggested config change |
| **R117** | **Escalation hotspot insight.** Correlate escalations and expiries by class × tier × hour; surface "3 a.m. tier-2 always answers / tier-1 never does" patterns with roster/routing recommendations. | v0.1.0 | Hotspot fixture renders the pattern + a specific roster or TTL recommendation |
| **R118** | **Reviewer calibration view.** For similar asks (same class+shape), expose decision variance across principals — approve rates, deny reasons, time-to-answer — **aggregated by default**; per-principal views require configured governance access. No rankings, no scores, no alerts on individual humans. | v0.1.0 | Calibration fixture renders aggregate stats; per-principal rows are gated and access-logged |
| **R119** | **Evidence-gap reporting.** From PRD 32 labels, report which evidence dimensions most often block decisions or accompany denials, per class — feeding the class's evidence requirements (R86). | v0.1.0 | A class whose denies always lack diffs gets a "require diffs?" insight |
| **R120** | **Outcome-aware tuning.** Include PRD 35 closures: patterns where approvals were followed by `exceeded/divergent` outcomes harden the class (mandatory typed confirm, tier bump, shorter TTL) via *proposed* config diffs. | v0.1.0 | Divergence-heavy class yields a hardening proposal, never an automatic change |
| **R121** | **Insight-to-action workflow.** An insight can be exported as a **proposed config diff** (PRD 22 §C path: branch, review, `inbox-config-changed` digest), a runbook task, or a grant proposal. The action, its reviewer, and the originating insight are all recorded. | v0.1.0 | One-click export produces the diff; applying it is a git-reviewed PR, not an inbox button |
| **R122** | **Insight hygiene.** Insights are computed from redacted, aggregated data only; raw arguments never leave the store into insight payloads; insight queries are read-only; insights expire (stale insights do not linger forever). | v0.1.0 | An insight payload scanner (PRD 22 evidence scanner extension) finds zero secrets in insight exports |

## Non-goals

- No ML in the decision path (PRD 14): insights are deterministic clustering over stored, redacted data.
- No auto-policy: insights propose; humans review; git records.
- No human surveillance product: calibration is for alignment, and it is aggregate-first by design.

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-87** | 20 repetitive approvals → one grant-proposing insight with redacted representative ask |
| **SC-88** | A noisy policy cluster → a named tuning suggestion exported as a config diff |
| **SC-89** | Calibration view renders aggregates; per-principal access is gated and logged |
| **SC-90** | Divergence-heavy class yields a hardening proposal that no path applies automatically |

## Traceability

| Requirement | Test |
|---|---|
| R115–R117 | `tests/insights/` (patterns, clusters, hotspots) |
| R118 | `tests/insights/test_calibration.py` (+ access gating) |
| R119–R120 | `tests/insights/test_evidence_gaps.py`, `test_outcome_tuning.py` |
| R121–R122 | `tests/insights/test_to_action.py`, `test_hygiene.py` |
