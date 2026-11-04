# PRD 29 — Trust Maturity, Writeback & Human Performance

**BLUF:** The last layer that makes the inbox *infrastructure*: **rollback-aware approvals** (no rollback story,
no approve for the classes that need one), **confidence-labeled blast radius** (is "173 rows" an EXPLAIN guess
or a count?), a **structured deny taxonomy** that turns every rejection into policy-tuning data, **signed human
rationale** and **externally-verifiable approval attestations** (release evidence a third party can check),
**outbound status writeback** (GitHub checks, PR comments, tickets, CI annotations — integrated, not isolated),
**cross-ask correlation** (these 4 asks are rollout X; these 6 hit the same prod db), plus the human side:
**replay/training mode** for onboarding approvers and a built-in **red-team/chaos drill pack**. Trust matures,
evidence moves outward, and humans get better at the one job the whole ecosystem depends on.

**Status:** Draft — v0.1.x–v0.2.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

An approval is a *claim about the future* ("this will be fine") and an attestation is a *claim about the past*
("this was decided, by this person, with this evidence, at this time"). Enterprises buy the second claim —
release evidence, audit letters, postmortem packets. And the humans making the first claim need to get *better*
or the whole gate degenerates into rubber-stamping; training mode and structured feedback are how that
happens without a single ML anywhere.

## A. Trust maturity (evidence you can defend)

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R59** | **Rollback-aware approvals.** Classes may declare rollback evidence **mandatory**: rollback plan attached, rollback command preview, rollback owner named, rollback artifact digest. Missing rollback evidence on such a class is a **blocking** partial score (R23/R47) — the approver literally cannot approve blind. | v0.1.x | A prod-migrate ask without rollback evidence renders blocking-partial; with it, approves (SC-46); the rollback block renders on every surface and rides the packet |
| **R60** | **Confidence-labeled blast radius.** Every blast-radius number carries its source and confidence: `exact` (counted), `estimated` (EXPLAIN/plan-derived, low confidence), `modeled`, or `unknown` — plus size buckets (small/medium/large per class). A low-confidence "173 rows" renders as an estimate, visibly different from a counted 173. | v0.1.x | Fixture matrix: exact vs estimated vs unknown labels render distinctly (SC-47); estimates never silently display as facts; confidence is part of the delta block (R24) when magnitudes compare |
| **R61** | **Structured deny taxonomy.** Denies and needs_changes carry reason **codes**, not just prose: `missing-evidence`, `wrong-environment`, `outside-window`, `too-broad`, `wrong-owner`, `insufficient-provenance`, `stale`, `policy-unclear`, `rollback-missing`, + optional free text. Codes are first-class in analytics (R34), the tuning loop, and the packet — "what you deny most and why" becomes a report, not folklore. | v0.1.x | Every deny/needs_changes in the fixture corpus carries ≥ 1 code; the weekly report aggregates codes by class/agent/rule (SC-48); free text never replaces codes on mandatory classes |
| **R62** | **Signed human rationale.** Where an approver records a reason (required on irreversible denies, optional elsewhere): the rationale is **hash-bound into the decision record and the chain** — tamper-evident with the rest, exported with the packet, and mandatory-per-class by config. | v0.1.x | Rationale hash verifies with the chain; removing/altering it breaks `verify-log` (fixture); classes can require rationale on approve too |
| **R63** | **Signed approval attestations.** One-command export of a **detached, signed attestation** per decision (or per bundle): the decision, constraints/edits, provenance tier, rationale hash, evidence digests, chain proof — signed with the local key (Sigstore at release scale), **verifiable by a third party with zero agentinbox access**. This is release evidence: attach it to a deploy record, a compliance export, a vendor review. | v0.2.0 | External verification fixture: a verifier with only the attestation + public key confirms it matches the chain segment (SC-49); attestations attest **facts** (who/what/when/how-verified), never judgments ("was correct") |
| **E16** | **Attestation & rationale invariants.** Signatures cover canonical bytes; verification is offline; keys are local (0600) with rotation runbooks; an attestation is bound to the store's chain segment — a mismatch is detected, not ignored; rationale text is escaped, capped, and never executable. | v0.1.x | Tamper/rotate/rebind fixtures all fail closed; no path from attestation to a new permission (it describes, it never authorizes) |

## B. Writeback & correlation (integrated, not isolated)

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R64** | **Outbound status writeback.** Post-decision, best-effort writeback to where the work lives: **GitHub check runs** (pending → pass/fail with the ask id), PR comments/reviews (the decision as a review line), ticket status transitions, CI annotations, deployment-tool records. Writeback is R44's hook machinery with **named, idempotent targets**; failures are `writeback-failed` events — a dead GitHub token never blocks or rewrites a decision. | v0.1.x (annotations/comments) · v0.2.0 (checks/tickets) | A CI ask answered in the terminal completes its GitHub check (SC-50); writeback retries are idempotent (no double-comments); failure delays nothing |
| **R65** | **Cross-ask correlation / incident grouping.** Asks share correlation keys (rollout id, incident id, same effect target, same credential chain) and the queue/cards render the grouping: "4 asks in rollout X", "6 asks touch prod-db this hour", "3 asks follow the credential elevation from 14:02". Grouping is **display + analytics** (R27's rule: decisions stay per-ask). | v0.2.0 | Rollout/incident/target groupings render in fixtures (SC-51); grouped display states counts honestly; grouping never auto-approves or hides a decision |

## C. Human performance (the approver gets better)

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R66** | **Replay / training mode.** `agentinbox train` runs historical asks as **drills** for a new approver: render the card exactly as it appeared (R34's render digests), collect the trainee's decision, then reveal the pre-registered actual outcome + rationale + taxonomy code + what the blast radius turned out to be. Read-only against historical data; touches no live state; scores per class so onboarding is measurable. | v0.2.0 | A trainee session replays 10 historical asks with zero live-store mutation (SC-52); score report shows correctness + latency per class; the corpus is the field-test set, checksummed |
| **R67** | **Built-in red-team / chaos drills.** `agentinbox drill` runs the inbox's own attack pack locally, on demand: spoofed callback, flood, stale-ask, missing-evidence, dual-control failure, tier-confusion, suppression escape. Green drills are an operator's confidence check; red drills are findings. This is the agentdrill partnership made self-serve — the inbox ships its own pack and runs it in CI and on the ops box. | v0.1.x (subset) · v0.2.0 (full pack) | All 7 drills run green on a healthy box in < 2 min (SC-53); each red drill produces a named finding event; drills never touch real asks (sandboxed fixture mode) |

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-46 · Rollback-required approval.** `prod-migrate` without rollback evidence → blocking partial, approve
disabled, taxonomy code `rollback-missing` suggested; with rollback plan + owner + digest → approves and the
packet carries the rollback block.

**SC-47 · Confidence labeling.** Three sibling asks: exact file count (`exact·high`), EXPLAIN rows estimate
(`estimated·low`), unknown blast radius (`unknown`) — each renders its source distinctly; the delta block
compares magnitudes only within same-confidence fields.

**SC-48 · Deny taxonomy analytics.** A week of denies codes as: `too-broad` ×12, `outside-window` ×6,
`missing-evidence` ×5; the weekly report names rule R-9 + class external-send as the top sources; one free-text
rationale rides along, codes are mandatory.

**SC-49 · External attestation.** A release's 3 decisions exported as a signed attestation bundle; a verifier
with only the public key + bundle confirms chain-segment match, provenance tiers, and rationale hashes — no
agentinbox install, no store access, offline.

**SC-50 · Writeback.** CI ask answered from a terminal: GitHub check goes pending → completed with the ask id;
a PR comment lands with the decision summary; token revoked mid-run → `writeback-failed` event, decision
already recorded, zero delay to the agent.

**SC-51 · Correlation under pressure.** During a rollout, 4 asks share `rollout_id=RL-9` and 6 touch prod-db in
an hour: the queue shows both groupings with honest counts; each ask still answered individually; the incident
grouping feeds the postmortem packet.

**SC-52 · Training mode.** A new approver replays 10 historical asks; trainee decisions never touch the live
store (verified by store-digest before/after); score report: 8/10 correct, p50 21 s, weakest class prod-deploy.

**SC-53 · Chaos drill pack.** `agentinbox drill` runs all 7 attacks against a healthy sandboxed instance:
spoof, flood, stale, missing-evidence, dual-control failure, tier-confusion, suppression escape — all blocked,
all with named events, all green in < 2 min, zero real asks touched.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R59 | CUJ-2, CUJ-3 | SC-46 | `test_rollback_required.py` |
| R60 | CUJ-2 | SC-47 | `test_blast_confidence.py` |
| R61 | CUJ-8, CUJ-10 | SC-48 | `test_deny_taxonomy.py` |
| R62 | CUJ-10 | chain fixtures | `test_signed_rationale.py` |
| R63/E16 | CUJ-10, CUJ-14 | SC-49 | `test_attestations.py` |
| R64 | CUJ-7 | SC-50 | `test_writeback.py` |
| R65 | CUJ-6, CUJ-10 | SC-51 | `test_correlation.py` |
| R66 | CUJ-2 (onboarding) | SC-52 | `test_training_mode.py` |
| R67 | PRD 06 attack surface | SC-53 | `test_drill_pack.py` |

## Non-goals (this PRD's boundaries)

- **No ML scoring of approvers or asks** — training mode compares decisions to pre-registered outcomes; it
  never models, predicts, or ranks humans ([PRD 14 N-1](14-non-goals.md)).
- **Attestations describe, never authorize** — an attestation is evidence for auditors and release records; it
  cannot release, extend, or excuse any action (E16).
- **No writeback in the decision path** — outbound targets are strictly post-decision and best-effort; if
  writeback could block, a dead token would be a fail-open path.
- **No gamification/surveillance of approvers** — training scores are local, self-run, and never exported by
  default (the [PRD 26](26-approver-experience-operations.md) honesty rules apply).
