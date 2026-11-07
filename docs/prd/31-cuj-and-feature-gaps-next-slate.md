# PRD 31 — CUJ & Feature Gaps: the 0.1.0 expansion

**BLUF:** PRDs 24–30 deepen the existing control plane; what is still missing is **operator leverage**:
constrain instead of deny, teach the agent on every denial, review operations rather than isolated asks, close
the loop after the decision, compress repetition safely, and let governance learn from observed outcomes. This
PRD is the umbrella for the 0.1.0 expansion: it defines the **new CUJs (CUJ-15..CUJ-48)** and the
**feature-gap requirement space (F31–F45)** that PRDs 32–37 specify in depth.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026

---

## Why this PRD exists

The published set (00–30) specifies a **correct** control plane: unforgeable answers, timeout=deny, audit
chains, conformance-gated drivers. Correctness is necessary but not *compelling*. The gaps below are the ones a
team feels in week two of real use — the difference between "we trust it" and **"we would fight to keep it."**

| Gap felt by the operator | Today | The 0.1.0 expansion |
|---|---|---|
| "This ask is too broad, not wrong" | deny, or hand-write instructions | **constrained allows + suggested safe variants** (PRD 33) |
| "The agent will just retry the same thing" | deny and hope | **machine-readable denial repair packets** (PRD 33) |
| "This deploy is 14 asks" | 14 isolated cards | **operation bundles + phase views** (PRD 34) |
| "Why was this denied at 3 a.m.?" | read the chain | **decision narratives** (PRD 34) |
| "Half these asks are junk" | deliver them anyway | **ask readiness scoring + non-decisionable rejection** (PRD 32) |
| "Did what ran match what we approved?" | unknown | **outcome closure + execution proof** (PRD 35) |
| "I approved the same safe thing ten times" | rubber-stamp risk | **repeated-ask compression + narrow grants** (PRD 36) |
| "Which of our classes are misconfigured?" | anecdotes | **policy learning insights** (PRD 37) |

## Reading this PRD

- **CUJ-1..CUJ-14** are specified in [PRD 04](04-users-and-cujs.md) and delivered by the v0.1.0 WBS.
- **CUJ-15..CUJ-48 and the requirement space F31–F45/R78–R115 are specified here** and expanded by
  [PRD 32](32-decision-quality-and-ask-readiness.md) through [PRD 37](37-policy-learning-and-governance-insights.md).
- Every requirement in the 0.1.0 expansion keeps the **ecosystem honesty clause**: the inbox records and returns;
  the enforcer enforces; nothing is offered that no enforcer can honor.

---

## The new compelling CUJs (summary register)

| CUJ | One-line story | PRD |
|---|---|---|
| **CUJ-15** | Approve safely in 5 s because the system already narrowed the blast radius | 33 |
| **CUJ-16** | I denied it once; the agent resubmits correctly without re-teaching | 33 |
| **CUJ-17** | Review the whole operation, not 14 fragmented asks | 34 |
| **CUJ-18** | Explain a decision to a new approver without reading logs | 34 |
| **CUJ-19** | The product tells us which asks should never have reached a human | 37 |
| **CUJ-20** | Incident mode without disabling accountability | 34 |
| **CUJ-21** | Hand off a waiting ask across time zones without losing intent | 34 |
| **CUJ-22** | Approve one thing, not the next ten that look similar | 36 |
| **CUJ-23** | Catch ambiguous or low-quality asks before they waste attention | 32 |
| **CUJ-24** | Prove the human approved exactly what was executed | 35 |
| **CUJ-25..28** | Ask-readiness, quality banners, safe-vs-poorly-explained, pre-delivery contradictions | 32 |
| **CUJ-29..32** | One-move constrained approval, deny-once-teach-permanently, machine-shaped fixes, narrow-beats-easy | 33 |
| **CUJ-33..36** | Deploy-as-one-operation, shift handoff, incident mode, blocked-operation view | 34 |
| **CUJ-37..40** | Approved==executed, outcome closure, one packet for CAB/postmortem, drift detection | 35 |
| **CUJ-41..44** | Compression, tiny windows, burn-down, no policy drift | 36 |
| **CUJ-45..48** | Never-needed-a-human, noisy-policy, reviewer consistency, escalation hotspots | 37 |

## The feature-gap space (F31–F45 → PRDs 32–37)

| ID | Feature theme | PRD |
|---|---|---|
| F31 | Constraint suggestion engine | 33 |
| F32 | Denial repair packets | 33 |
| F33 | Review bundles / operation views | 34 |
| F34 | Decision quality scoring | 32 |
| F35 | Post-decision outcome capture | 35 |
| F36 | Human handoff / shared ownership | 34 |
| F37 | Incident-mode UX + policy overlay | 34 |
| F38 | Repeated-ask compression | 36 |
| F39 | Similar-case guidance | 32 |
| F40 | Ask quality gate before delivery | 32 |
| F41 | Approval window / grant burn-down | 36 |
| F42 | Outcome-aware policy tuning insights | 37 |
| F43 | Cross-system decision packet export | 35 |
| F44 | Ambiguity / contradiction detector | 32 |
| F45 | Human learning / calibration views | 37 |

## Product themes

1. **Constrain instead of deny** — the gate becomes a steering wheel (PRD 33).
2. **Teach the agent** — every human decision improves future asks (PRDs 32/33).
3. **Think in operations** — bundles, handoffs, incident mode (PRD 34).
4. **Raise decision quality** — readiness scoring, evidence sufficiency (PRD 32).
5. **Close the loop** — approved vs executed, portable proof (PRD 35).
6. **Compress repetition safely** — narrow grants, visible burn-down (PRD 36).
7. **Let governance learn** — insights from observed outcomes (PRD 37).

## Relationship to PRDs 24–30 (sharpening, not replacing)

- **PRD 24** (constrained approvals) gains its most compelling frame from PRD 33: suggested variants + repair packets.
- **PRD 25** (evidence & decision quality) is generalized by PRD 32 into readiness scoring and contradiction detection.
- **PRD 26** (approver experience) gains operation bundles, handoff, and incident UX from PRD 34.
- **PRD 27** (governance) gains grant burn-down and delegation ergonomics from PRD 36.
- **PRD 28** (review loops) gains incident-mode choreography from PRD 34.
- **PRD 29** (writeback) gains outcome closure and execution proof from PRD 35.
- **PRD 30** (hardening) absorbs PRD 32's contradiction checks and PRD 35's approved-vs-executed proof.

## Milestone posture

Everything in PRDs 31–37 lands **inside v0.1.0** as milestones **M26–M33**, after the core (M0–M25). The
original field-test (M24) and release (M25) gates are re-executed after the expansion (M32/M33) so the `v0.1.0`
tag covers the expanded scope. The core was built so this expansion is additive: the resolve vocabulary, the
append-only transition log, the audit chain, and the conformance-gated store/bus contracts already carry the
fields these PRDs need.
