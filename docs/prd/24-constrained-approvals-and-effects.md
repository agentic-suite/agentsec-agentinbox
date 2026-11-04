# PRD 24 — Constrained Approvals, Effects & Ask Semantics

**BLUF:** agentinbox grows from **approve/deny** to **shape the action**: approve the **effect** a human
understands (not just the tool call), approve **narrowed** (`staging only`, `dry-run only`, `max_rows=100`,
`ttl=1h`), approve **edited** (the human changes the recipient list and the edited action is what executes),
detect **stale context** before an answer lands, and return the agent a **structured, readable outcome** it can
act on. Constraints are **recorded by the inbox, enforced by the enforcer** — the same PDP/PEP split that keeps
the ecosystem honest.

**Status:** Draft — v0.1.x–v0.2.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

A binary gate has three bad exits: a blind approve, a blocking deny, or a rubber stamp. Real reviewers say a
fourth thing — **"yes, but smaller"** — and every existing approval surface makes that sentence impossible to
express. Once the human can *shape* the action, the gate stops being an interruption and becomes the
steering wheel. This PRD is the difference between a permission popup and an **approval control plane**.

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R13** | **Effect identity & envelope.** Producers may attach an effect envelope — `effect_type`, `effect_target`, `effect_scope`, `effect_fingerprint` — the human-readable statement of *what will change in the world* ("drop table `prod.customers`", "deploy `abc123` to prod", "email 172 recipients"). Cards render the effect first, tool details second; the approval binds to **both** `action_identity` and `effect_identity`. | v0.1.x | Card leads with the effect; an approval for effect E cannot release a call claiming E with a different fingerprint (SC-35); harness/tool renames don't orphan the approval |
| **R14** | **Constrained approvals** (`allow_with_constraints`). The producer may advertise **alternative scopes** (per class: staging-only, dry-run-only, row/file/recipient caps, time-boxed); the approver picks one instead of raw approve. Constraints return to the agent as a first-class outcome and to the enforcer as the binding the call must satisfy. | v0.1.x | Approve-with-constraint produces `allow_with_constraints` + the constraint set; a call exceeding the constraint denies at the enforcer (agentpolicy argument validation); SC-27 passes |
| **R15** | **Human edits the action** (`allow_with_edits`). For classes that declare editable fields (recipient list, target env, command flags, scope cap), the approver may edit within the producer-declared edit schema; the **edited action is the approved action** — re-canonicalized, re-fingerprinted, and what the enforcer executes. | v0.2.0 | An edited approval executes exactly the edited form (SC-30); edits outside the declared schema are rejected; the original and edited forms are both recorded |
| **R16** | **Staleness & changed-context detection.** Asks carry a `freshness_basis` (repo rev, artifact digest, DB state token, recipient-list digest, policy version — whatever the producer can pin). At answer time the core re-checks what it can; a changed basis marks the ask **stale**: the card visibly degrades ("context changed since ask"), and answering requires an explicit **re-confirm** of the new basis (or a re-ask). | v0.1.x | Delayed approval on a changed basis cannot release silently: stale + re-confirm flow in SC-28; no staleness check is ever *inferred* (absent basis = "unknown freshness", displayed) |
| **R17** | **Re-auth on drift.** Staleness plus class-criticality can require **step-up** (a stronger principal check) before the re-confirm is accepted — long-lived asks get *more* friction as they age and drift, never less. | v0.2.0 | A stale `irreversible` ask requires step-up re-auth; the requirement is config-per-class and audited |
| **R18** | **Approval bundles.** One logical change that fans out into many asks (a migration touching 20 tables) may be presented as a **bundle**: one summary, shared evidence, shared rationale — with **every child ask still answered individually** (N-20 holds). Bundle state is derived, never a decision of its own. | v0.2.0 | A 20-ask bundle renders as one grouped review; 20 individual decisions; one bundle outcome; no path to one-tap-approve-all (SC-34 hard mode) |
| **R19** | **Ask dependencies.** Producers may declare lightweight blocking relationships (`deploy` depends on `db-migration` approval) — a small DAG of *gates*, not a workflow engine: a blocked ask renders "waiting on X" and its claims do not issue until the blocker resolves. | v0.2.0 | A dependent ask cannot be answered before its blocker; cycle-declared dependencies are a loud config error; no scheduling/executive logic lives here |
| **R20** | **Agent-readable structured outcomes.** `resolve/1.0` grows from allow/deny/pending to the full vocabulary: `allow`, `allow_with_constraints`, `allow_with_edits`, `deny`, `constrained` (advice, not decision), `stale`, `expired`, `pending` — each with `reason_code`, `retryable`, `retry_after`, `rescope_hint`, and the exact constraint/edit payload, so the agent can **act** instead of guessing. | v0.1.x | Outcome matrix consumed by a demo agent: every status produces a distinct, correct agent behavior; no status is "a deny pretending to be a pause" |

## The enforcement honesty clause (why this doesn't become vaporware)

Every constraint, edit, and effect binding is **only as real as the enforcer's enforcement of it**:

1. The inbox **records** constraints and edits and returns them in the resolve — it does not sandbox anything.
2. The enforcer (agentpolicy argument validation / agentgate / agentkeys TTL issuance / the harness hook)
   **enforces** them — a `max_rows=100` constraint denies call 101 at the policy layer, with the constraint id
   named in the reason code.
3. A constraint that no enforcer can honor is **not offered** — the producer declares which constraints its
   enforcement path supports, and the card shows only those. Advertising an unenforceable "dry-run only"
   would be a security lie, and this PRD forbids it.
4. `effect_identity` is verified where the producer can prove containment (same tool path, argument-derived
   fingerprint); where it cannot, the effect renders as **unverified** — the same honesty rule as trusted
   fields ([PRD 18](18-approval-integrity.md)).

This is the ecosystem's PDP/PEP split applied one more time: **the inbox decides what the human meant; the
enforcer makes the world match it.**

## Data model deltas ([PRD 15](15-data-model.md))

| Addition | Shape |
|---|---|
| `Ask.effect` | `{effect_type, effect_target, effect_scope, effect_fingerprint, verified: bool}` |
| `Ask.constraints_offered[]` / `Answer.constraints_applied[]` | producer-advertised vs approver-selected constraint objects `{kind, params, enforcer_ref}` |
| `Ask.edit_schema` / `Answer.edits` | declared editable fields vs applied edits; `edited_identity` = re-canonicalized identity of the edited action |
| `Ask.freshness` | `{basis, pinned_at, checked_at, stale: bool, changed_fields[]}` |
| `Ask.bundle_id`, `Ask.depends_on[]` | bundle membership; blocking gate ids (validated acyclic) |
| `Answer.provenance_tier` | per [PRD 27 R39](27-governance-identity-extensibility.md) |
| `resolve/1.0` statuses | `allow_with_constraints`, `allow_with_edits`, `stale` (advice on re-confirm), plus `constraints[]` / `edits[]` payloads |

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-27 · Constrained approval round-trip.** Approver picks "staging only" on a prod DB ask →
`allow_with_constraints` → agent re-asks scoped to staging → allow; the original prod identity never
executes; the enforcer's denial of a constraint-exceeding call is demonstrated (call 101 of `max_rows=100`).

**SC-28 · Stale ask, delayed answer.** Ask pinned to repo rev `a1b2`; approver answers 40 min later; rev moved to
`c3d4` → card degrades to **stale**, answer rejected as `stale_reconfirm_required`; after re-confirm (of the new
basis) the decision binds to the re-validated context; audit shows both the drift event and the re-confirm.

**SC-30 · Edit-in-flight.** Approver edits a 172-recipient send down to the 2 maintainers (edit schema allows
the list) → executes exactly the edit; the original list is recorded but never sent; an edit outside the
schema is refused loudly.

**SC-34 (hard mode) · Bundle without bulk-approve.** 20-ask migration bundle: one grouped review, 20 individual
decisions, one rationale applied per ask; the UI offers **no** approve-all, and a scripted attempt to
bulk-answer is rejected ([PRD 14 N-20](14-non-goals.md) is the regression test).

**SC-35 · Effect identity mismatch.** An approval bound to effect E1 (fingerprint F) cannot release a call that
claims E1 with different arguments → `deny_action_identity_mismatch`'s effect-level twin; card shows both
fingerprints side-by-side.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R13 | CUJ-2, CUJ-3 | SC-35 | `test_effect_identity.py` |
| R14 | CUJ-3, CUJ-8 | SC-27 | `test_constraints.py`, `test_enforcer_honors_constraints.py` |
| R15 | CUJ-3 | SC-30 | `test_edits.py` |
| R16/R17 | CUJ-4, CUJ-9 | SC-28 | `test_staleness.py`, `test_stepup_on_drift.py` |
| R18 | CUJ-6 | SC-34 | `test_bundles.py` |
| R19 | CUJ-7 | SC-39 | `test_dependencies.py` |
| R20 | CUJ-4, CUJ-13 | outcome matrix | `test_resolve_matrix.py` |

## Non-goals (this PRD's boundaries)

- **No constraint execution in the inbox** — ever; it is the record, the enforcer is the muscle.
- **No bulk approval** — bundles group *display*, never decisions (N-20 is permanent).
- **No general workflow engine** — dependencies are gate-blocking only; there is no branching, no retries, no
  scheduling ([PRD 14 N-14](14-non-goals.md) holds).
- **No ML suggesting "similar past approvals" as decisions** — precedent is advisory display only
  ([PRD 26 R36](26-approver-experience-operations.md)); nothing auto-answers.
