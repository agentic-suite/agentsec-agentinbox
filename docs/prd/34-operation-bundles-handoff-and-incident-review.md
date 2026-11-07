# PRD 34 — Operation Bundles, Handoff & Incident Review

**BLUF:** humans think in **operations** — a deploy, a migration, an incident shift — not isolated asks. This
PRD adds the operator layer: **review bundles** (one operation, many asks, per-ask truth intact), **decision
narratives** (why it was decided, readable without the chain), **shift handoff** (pending asks move between
humons without losing intent), **incident mode** (faster routing, same accountability), and the **operation
timeline** that reconstructs the story.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

Fourteen isolated cards for one deploy is a *reading comprehension test* with a deadline attached. This PRD
makes the inbox match how change management actually works: grouped review with shared evidence, handoff that
preserves urgency, and crisis mode that is *faster but not sloppier* — the exact moments where gates get
bypassed today.

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-17** | "Review the deploy as one operation" — phase summary, shared blast radius, per-ask truth beneath | P0 |
| **CUJ-18** | "Explain this decision to a new approver without reading logs" — the decision narrative renders on demand | P0 |
| **CUJ-20** | "Incident mode without disabling accountability" — bounded, audited, loud | P0 |
| **CUJ-21** | "Hand off a waiting ask across time zones without losing intent" | P0 |
| **CUJ-33** | "One screen shows which ask is blocking the operation" — critical path, not 14 tabs | P1 |
| **CUJ-34** | "A night-shift approver inherits state, not vibes" — remaining TTL, prior notes, unanswered questions | P0 |
| **CUJ-36** | "See the sequence: which ask triggered which escalation" — timeline reconstruction | P1 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R94** | **Review bundle object.** A bundle groups asks by producer-declared `operation_id` (or session+window heuristic, labelled as derived). Bundle state is **derived-on-read** — never stored as truth; every child ask keeps its own status, claims, and audit rows. Extends PRD 24 R18 (per-ask answers hold: **no one-tap-approve-all**). | v0.1.0 | A 20-ask bundle renders grouped; 20 individual decisions; no path to a bundle-level approve exists |
| **R95** | **Bundle summary & phase view.** The bundle view shows phases (declared or inferred from transitions), aggregate blast radius (environments touched), counts by status, and the **critical path** — which pending ask blocks the operation. | v0.1.0 | Blocked-operation fixture renders the critical path; no inferential claim renders without its "derived" label |
| **R96** | **Claim / assign / handoff.** A pending ask may be claimed by (or assigned to) a principal — recorded as a non-state-changing observation with acknowledgement. Claim does **not** change status, TTL, or answer eligibility; it changes routing/attention only. | v0.1.0 | A claimed ask answers identically to an unclaimed one; claim/assign/handoff render in the timeline |
| **R97** | **Shift handoff note.** A handoff carries: remaining TTL, prior decision context, unanswered questions, evidence gathered so far, and the outgoing approver's identity. The incoming approver sees it before the card. | v0.1.0 | Handoff fixture: the incoming approver's first render shows the note; TTL is unchanged by handoff |
| **R98** | **Incident-mode overlay.** One bounded incident state (config-declared classes, TTL scaling, routing overrides) that **never** converts a deny path to allow, never extends TTLs beyond PRD 28 R32's rules, and records `incident-on/off` with owner + reason per audit. | v0.1.0 | Incident fixture: irreversible asks still deny on timeout; every mode change is a chained event |
| **R99** | **Decision narrative.** For any resolved ask, render a readable story: the ask, evidence present/missing (PRD 32 labels), the rule that fired, who answered (or why it expired/escalated), alternatives offered, constraints applied, and the outcome — sourced entirely from stored transitions. | v0.1.0 | Narrative fixture: a third party reconstructs the decision without store access beyond the rendered packet |
| **R100** | **Operation timeline.** The bundle timeline reconstructs ask/answer/deny/escalate/handoff/incident events in causal order, exportable with the bundle. | v0.1.0 | Timeline ordering matches transition seqs; export carries it |

## Non-goals

- No bundle-level decisions (each ask answers individually — N-20).
- No workflow engine: dependencies stay PRD 24 R19's lightweight gates.
- No unbounded incident mode: it is declared, audited, and timeboxed by config.

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-75** | A 20-ask bundle reviews as one screen, answers as 20 decisions, exports as one packet |
| **SC-76** | A handoff across approvers preserves TTL, notes, and acknowledgement |
| **SC-77** | Incident mode shortens review loops without a single silent allow or TTL extension |
| **SC-78** | A decision narrative reproduces a 3 a.m. denial for a reviewer who wasn't there |

## Traceability

| Requirement | Test |
|---|---|
| R94–R95 | `tests/bundles/` (derivation, phase view, critical path) |
| R96–R97 | `tests/bundles/test_handoff.py` |
| R98 | `tests/bundles/test_incident_mode.py` |
| R99–R100 | `tests/bundles/test_narrative.py`, `test_timeline.py` |
