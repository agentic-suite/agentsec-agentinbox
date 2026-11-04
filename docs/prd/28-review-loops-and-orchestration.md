# PRD 28 — Review Loops & Operational Orchestration

**BLUF:** Binary approve/deny is too blunt for real review, and a single ladder is too rigid for real ops. This
PRD adds the **review loop** — `needs_changes`, request-more-evidence, clarification cycles, reviewer notes,
auto-attached resolution summaries — and the **orchestration layer**: timeboxed **session grants** (safer than
standing approvals), **future-effective approval windows** ("deploy, but only after 22:00"), **incident-scoped
suppression** ("don't ask again for *this* target during *this* incident, expiring in 30 min"),
**class/severity-shaped routing** (security asks go to security first; per-agent trust profiles and
per-environment overlays), **parallel notify / parallel quorum** (owner + security together), and **change
calendar integration** (maintenance windows, freezes, business hours, holidays). Every convenience here is
scoped, expiring, and audited — the anti-rubber-stamp and the anti-nagging in one PRD.

**Status:** Draft — v0.1.x–v0.2.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

Real reviewers say three things approve/deny can't express: *"change it and come back"*,
*"not at 2 p.m. — after the freeze"*, and *"stop asking me about this table while I'm firefighting"*. Every
existing gate forces those sentences into a raw deny (teaching the agent nothing) or a standing approval
(over-granting for days). This PRD makes the middle path first-class — and every middle path **expires**.

## A. The review loop

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R48** | **`needs_changes` — request changes as a first-class outcome.** Between deny and approve: the approver selects structured change requests ("reduce recipient set", "attach rollback plan", "rerun with dry-run evidence", "bring owner approval") + optional free text. Two bounded modes: **(a) hold-and-clarify** — the ask stays open, the producer may supply changes/evidence within the *remaining* TTL (never extended); **(b) resolve-and-reask** — terminal `needs_changes`, the producer re-asks; both asks share a `review_thread_id`. The agent receives an actionable `needs_changes` outcome (R20 vocabulary) — not a denial pretending to be feedback. | v0.1.x | Both modes demonstrated (SC-41); TTL never extends across a clarification cycle; the re-ask renders prior-thread context ("v2 of an ask changed twice"); deny-reason taxonomy (R58) codes the request |
| **R49** | **Request-evidence / clarification cycle.** The approver can ask the producer for more evidence (missing diff, dry-run output, owner sign-off) without deciding; the producer's response lands on the card as a **new, labeled evidence revision** (digest-bound, untrusted-labeled where agent-authored); every reviewer note ("checked RB-7, need rows estimate") is a recorded transition visible to the next tier. | v0.1.x | The card shows the full review thread (requests → responses → notes) with authors and timestamps; an evidence revision does not silently refresh the freshness basis (R16 interplay is explicit) |
| **R50** | **Resolution summary, auto-attached.** When an ask resolves, the approver's structured rationale + chosen taxonomy codes + constraints/edits compile into a canonical **resolution summary** bound into the record and the decision packet — the postmortem doesn't require re-reading the thread. | v0.1.x | Packet includes the summary; a reviewer with zero context reconstructs the decision (SC-36 extension) |

## B. Operational orchestration

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R51** | **Timeboxed session grants.** The middle ground between one-shot and standing: "allow this class for this agent/session for 15 minutes / for this rollout window" — minted by an approver *at* an ask, auto-expiring, hit-counted, and rendered on every card it answers (`authorization.source=human-remembered`, grant id shown). Narrower than standing rules (R37) by construction: session- or incident-scoped, short ceiling, no recert ceremony because they die on their own. | v0.1.x | A 15-min grant auto-answers matching asks and expires mid-rollout with zero cleanup (SC-42); a grant can never outlive its ceiling; every auto-answer names the grant + approver |
| **R52** | **Future-effective approval windows.** Approve now, effective later: "deploy, but only after 22:00", "credential elevation starting 01:00 UTC", "maintenance task only inside this freeze-exception window". The window is part of the binding — the enforcer denies execution outside it. | v0.2.0 | Pre-window execution is denied by the enforcer naming the window (SC-43); the card shows the effective window; expiry semantics compose with TTL (whichever ends first) |
| **R53** | **Incident-scoped suppression.** "Do not ask again for *this* effect target / class / incident-id during *this* incident" — a tight, expiring suppression (default 30 min, hard ceiling) created at an ask, audited on/off, and **never** applicable outside its declared scope or to a class configured `suppression=false`. This is the firefight tool that replaces the dangerous "just approve everything" reflex — and it is a first cousin of session grants, not of standing approvals. | v0.1.x | Suppression covers only its declared scope for its TTL (SC-44); an out-of-scope or expired match still gates; on/off are events; irreversible classes are excluded unless explicitly configured |
| **R54** | **Class/severity-shaped routing.** Routing beyond one ladder: security-class asks hit the security roster first; deploy asks hit owner+on-call; credential asks hit platform; `critical` asks notify **two tiers in parallel from t=0**. Per-class ladder selection is config (packs ship sensible defaults, R42). | v0.1.x | A security ask reaches the security tier first in fixtures; a critical ask notifies two tiers at once (SC-45); routing rules are visible in `doctor --explain` |
| **R55** | **Parallel notify / parallel quorum.** Notify owner + security simultaneously with first-valid-answer-wins, or require one-from-each (compromise with R38 role-pair quorum at smaller risk). | v0.2.0 | Both rosters receive the same card at t=0; race resolves once; quorum variant requires both groups |
| **R56** | **Per-agent trust profiles.** Defaults shaped by agent class (coding agent, deploy agent, research/scraping agent, finance/workflow agent): TTL defaults, mandatory evidence, escalation path, minimum provenance tier, suppression eligibility. Profiles are inbox-side renderings of agentpolicy's agent classes — the inbox consumes, never re-derives. | v0.2.0 | The same ask scores different TTL/evidence/roster behavior per profile in a fixture matrix; `doctor` explains the effective profile |
| **R57** | **Per-environment overlays.** Inbox behavior per environment (local/dev/staging/prod/regulated-prod): who is asked, how fast, what evidence is mandatory — layered over class defaults, **narrow-only** like agentpolicy's R44 layering: an overlay may tighten, never loosen. | v0.2.0 | A prod overlay tightening TTL/roster applies; a loosening overlay is a config error (loud, `doctor` red) |
| **R58** | **Change calendar integration.** Calendar-aware behavior beyond quiet hours (R31): maintenance windows (irreversible asks deliverable *inside* them only), code-freeze calendars (asks during freeze route to the freeze-exception approver), business-hours TTLs, holiday routing. Calendars are local ICS/JSON files — no SaaS dependency. | v0.2.0 | A maintenance-window ask outside the window is denied-by-window at the enforcer; freeze-calendar routing sends the ask to the configured exception approver; DST/rollover fixtures pass |
| **E15** | **Loop & grant invariants.** `needs_changes` never extends a TTL; clarification responses are new evidence *revisions* (digests change, freshness interplay explicit); session grants and suppressions are expiring artifacts with hard ceilings, audited on/off, and can never answer an ask outside their declared scope; review-thread content from agents is untrusted-labeled. | v0.1.x | Invariant fixtures: TTL-extension attempts fail; grant/suppression scope escapes deny; untrusted thread content renders inert |

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-41 · needs_changes round trip.** Approver requests "reduce recipients + attach rollback" (hold mode);
producer responds within remaining TTL; approver approves the revised ask — or the TTL lapses → deny (no
extension ever). Re-ask variant: terminal `needs_changes`, producer re-asks, thread renders as v2.

**SC-42 · Session grant.** Approver grants "db-migration class, this agent, 15 min" at an ask → 6 matching
asks auto-answer with grant provenance → minute 16: the 7th gates again. Zero cleanup; every auto-answer
recorded `human-remembered` + grant id.

**SC-43 · Future-effective approval.** Deploy approved at 21:40 effective 22:00; a 21:55 execution attempt is
denied by the enforcer naming the window; 22:05 executes. The approval is inert, not just unrecorded.

**SC-44 · Incident suppression.** During incident INC-7, approver suppresses `db.stats.*` reads on prod-db for
30 min: matching asks auto-answer (suppressed, recorded); an ask for a *different* table still gates; minute 31
gates again; on/off + scope are events.

**SC-45 · Parallel notify.** A `critical` security-class ask notifies security + owner rosters at t=0; security
answers first; owner's late answer is a logged no-op; quorum variant requires one from each before release.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R48–R50 | CUJ-8 | SC-41 | `test_needs_changes.py`, `test_review_thread.py` |
| R51 | CUJ-8, CUJ-6 | SC-42 | `test_session_grants.py` |
| R52 | CUJ-3 | SC-43 | `test_approval_windows.py` |
| R53 | CUJ-6 | SC-44 | `test_suppression.py` |
| R54/R55 | CUJ-5 | SC-45 | `test_class_routing.py`, `test_parallel_notify.py` |
| R56/R57 | CUJ-2, CUJ-12 | profile/overlay matrix | `test_trust_profiles.py`, `test_env_overlays.py` |
| R58 | CUJ-5, CUJ-4 | calendar fixtures | `test_calendars.py` |
| E15 | — | invariant fixtures | `test_loop_invariants.py` |

## Non-goals (this PRD's boundaries)

- **No open-ended conversation**: the review loop is structured requests → labeled evidence revisions →
  recorded notes — never a free chat surface ([PRD 14 N-2](14-non-goals.md) holds on chat).
- **No workflow engine**: windows, grants, and calendars modify *routing and gating*, not orchestration — there
  is still no branching/retry/scheduling engine (N-14).
- **No suppression of the irreversible class** unless explicitly, loudly configured — the default answer to
  "stop asking me" for irreversible actions is the deny that already exists.
- **No inbox-side agent classification**: trust profiles consume agentpolicy's agent classes; the inbox never
  invents its own taxonomy (N-8 pattern).
