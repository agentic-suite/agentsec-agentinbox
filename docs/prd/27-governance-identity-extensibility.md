# PRD 27 — Governance, Identity & Extensibility

**BLUF:** The trust infrastructure around decisions: **standing approvals with real governance** (scope, owner,
expiry, recert, hit counters, shadow simulation — convenience that decays loudly), **quorum variants** beyond
2-of-N (role pairs, veto, quorum deadlines), **approval provenance tiers** (every decision records *how
strongly* it was verified — terminal / desktop / chat / step-up / quorum), **local identity plugins** (OS user,
SSH principal, git signer, OIDC device flow, passkey later — no Slack required, ever), **rule simulation**
(replay history against candidate TTLs/rosters/ladders before you change them), **inbox policy packs &
approval templates** (prebuilt, versioned class definitions that make adoption a config file), **event hooks**
(outbound automation on every lifecycle event), and **typed SDKs + conformance kit** (JSON Schema, Pydantic,
TypeScript, fixtures — so any harness can integrate in an afternoon). This is the PRD that makes agentinbox
pluggable into *other* agentic systems as infrastructure, not as an app.

**Status:** Draft — v0.1.x–v0.2.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

Two buyers, one need: the **platform engineer** wants to wire approvals into everything they already run
(agents, CI, tickets, pagers) without bespoke glue; the **security owner** wants convenience features
(standing approvals!) that don't rot into standing privilege, and wants to know *how strongly* any given
approval was verified. Governance is what makes the convenience *survivable*; extensibility is what makes the
tool *load-bearing* across the ecosystem.

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R37** | **Standing approvals, governed** (deepens R10). Every standing rule is a first-class, owned artifact: `scope` (class+agent+target pattern), `owner`, `created_by`, `why` (recorded rationale), `expiry` (mandatory) + `recert_at`, `hit_count` + `last_used` (surfaced on cards and in reports), `references` (where it's cited). **Shadow simulation**: "here are the asks this rule *would have* auto-answered this week" — shown before activation and at recert. Auto re-gate at expiry; recert is a decision, not a formality. | v0.1.x | A rule auto-answers a matching ask with `authorization.source=human-remembered` in the audit; expiry re-gates with zero manual action; the shadow report matches replay exactly; recert requires an owner action |
| **R38** | **Quorum variants** (extends agentpolicy R41). Beyond any-one and 2-of-N: **role-pair quorum** (one security + one service owner), **on-call + owner**, **deny-veto** (a named role can kill an ask outright), and a **quorum deadline** (unmet quorum at deadline = deny — quorum never extends the TTL). | v0.2.0 | Card shows "1 of 2 approvals (security ✓, owner pending)"; a single approval never releases a dual-control ask; veto is terminal and audited; deadline-miss = deny |
| **R39** | **Approval provenance tiers.** Every decision records an assurance tier: `T1 local-terminal` · `T2 desktop+terminal` · `T3 chat-verified` · `T4 step-up` · `T5 quorum`. The tier is displayed on cards (footer), stored on the answer, and exported with the decision packet — the audit answers not just *who approved* but **how strongly they were verified**. Policy can require a minimum tier per class (`irreversible` → min T3). | v0.1.x | Every answer carries a tier; a below-minimum-tier answer is rejected (`insufficient_provenance`); reports break decisions down by tier |
| **R40** | **Local identity plugins.** Principals come from pluggable verifiers — no chat platform ever required: OS user (default), **SSH principal** (for gates answered over SSH), **git commit signer** (an approval recorded via a signed commit/tag — the git-native approver), **OIDC device flow** (local-friendly, no web callback), **passkey/WebAuthn** (later, as the strongest local step-up). Each plugin maps to a provenance tier (R39). | v0.1.x (OS/SSH/git) · v0.2.0 (OIDC/passkey) | Each verifier authenticates a principal and lands in the tier table; unauthenticated principals cannot answer (E4 unchanged); a git-signed approval verifies against the configured keyring |
| **R41** | **Rule simulation.** Before changing TTLs/rosters/ladders/thresholds, replay **recorded ask history** against the candidate config and show the diff: what would have escalated, expired, flood-denied, or routed elsewhere — the policy-backtest pattern (agentpolicy R43) applied to *inbox* config. Read-only; watermarked output; states coverage + limits. | v0.2.0 | A simulated change reproduces the exact flip set over the fixture history; the report is read-only and watermarked; a config change PR can attach its simulation |
| **R42** | **Inbox policy packs.** Versioned, reviewable packs of class definitions + TTLs + rosters + ladders + thresholds for the common cases: **prod-deploy**, **destructive-db**, **external-send**, **credential-elevation**, **mass-file-rewrite**, **package-publish**. `agentinbox init --pack prod-deploy` yields a working, commented inbox config — never blank, never guessed ([PRD 05 F15](05-features.md) pattern). | v0.1.x | Each pack installs via one file + passes its bundled pack test; pack provenance (version, hash) recorded in `inbox-config-changed` events |
| **R43** | **Approval templates (per-class card contracts).** Templates declare, per class: required context fields, **required evidence kinds** (feeds R23's quality score), required deny reasons, default TTL/roster/ladder, offered constraints (R14), editable fields (R15) — so producers integrate against a *published shape*, not vibes, and missing pieces score visibly. | v0.2.0 | A producer validating against the template gets field-level errors; a card missing required evidence renders partial-score per R23 |
| **R44** | **Event hooks / outbound automation.** Configurable, signed local webhooks/commands on every lifecycle event (raised, delivered, warned, escalated, answered, expired, cancelled, flood): open a ticket, annotate a PR/commit, write to a SIEM, trigger a pipeline, page on flood — **after** the state change, never in the decision path; failures are events, never blocks. | v0.1.x | Hook fixture fires post-resolution with the event payload; a dead hook does not delay or fail any decision; hook output is untrusted input to the receiver |
| **R45** | **Typed SDKs + conformance kit.** The `ask/1.0` contract ships as: JSON Schema, **Pydantic models**, **TypeScript types**, CLI fixtures, and a `agentinbox conformance` harness that any integration runs to self-verify (ingest → answer → resolve → event round-trips, redaction, idempotency). Community adapters enter the matrix by passing it ([PRD 19](19-harness-compatibility.md)). | v0.1.x | The kit runs green against the reference adapters in CI; a third-party integration can prove compatibility without our involvement |
| **R46** | **Native CI/Git surfaces.** Beyond the generic `gate`: a **GitHub Checks/deployment** integration (an ask surfaces as a check run; approval via the GitHub **environment reviewer** path, recorded with the GitHub principal and tier), GitLab manual-job/approval mapping, `pre-push`/release-script gating recipes, systemd/cron task-runner gating. | v0.1.x (recipes) · v0.2.0 (GitHub Checks) | A release pipeline halts on an ask, is answered via the GitHub reviewer path, and the audit joins the check run to the ask id |

| **R47** | **Class risk tiers as behavior drivers.** The inbox normalizes every ask's class into a tier
(`low` · `elevated` · `high` · `critical` — consumed from agentpolicy's `criticality`, never re-derived) and the
tier **drives behavior coherently** across the whole slate: TTL floor/ceiling, **required evidence** (the R23
checklist items become mandatory at `high`+), **minimum provenance tier** (R39's `min_tier` config), self-review
bans, and whether escalation starts immediately. A tier is rendered on the card footer next to the class so the
approver sees the same shape everywhere. | v0.1.x | A `high`-tier ask missing mandatory evidence renders a
**blocking** partial score (not merely informational); a below-min-provenance answer rejects (SC-37); a
`critical` ask escalates from t=0 in fixtures |

## Ecosystem wiring (how this plugs into other agentic systems)

| Surface | What they get |
|---|---|
| **agentpolicy** | Consumes R20's structured outcomes; enforces R14 constraints (its argument validation is the enforcement point); standing approvals (R37) ride its decision contract with `human-remembered` provenance |
| **agentwatch** | New events: `ask-claimed`, `ask-assigned`, `ask-handoff`, `incident-mode-changed`, `standing-approval-applied`, `hook-fired` — all additive, all carrying provenance tiers |
| **agentdrill** | New attack packs: constraint-bypass (exceed the cap), staleness-bypass (mutate context after render), precedent-poisoning (fake history), bulk-answer attempt, tier-confusion (answer a T4-required ask with T1) |
| **agenthalt** | Incident mode (R32) is the inbox-side counterpart of the kill-switch posture: tighten, don't only stop |
| **agentkeys** | Credential-elevation pack (R42) + time-boxed constraints (R14) give the broker a governed "issue for 1 h" path |
| **Temporal / CI / ticketing** | R44 hooks + R46 surfaces make the inbox the approval primitive other workflow tools call, not a competitor to them |

## Honesty rules

- **Standing approvals are the most dangerous convenience in the product** — R37 exists to make them loudly
  expiring, owned, simulated, and recertified; the shadow report exists so nobody activates one blind.
- **Provenance tiers describe what we verified, not what is true** — a T3 chat-verified approval says "the
  platform vouched for the user", nothing more ([PRD 18](18-approval-integrity.md) residual-risk table).
- **Simulation is advisory** — it replay-scores history; it cannot predict tomorrow's asks, and its report says
  so.
- **Hooks are fire-and-forget by design** — if outbound automation could block a decision, a dead webhook
  would become a fail-open path; forbidden.

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-33 · Standing approval, end to end.** Ravi grants "this project's `external-send` to
`registry.example` for 7 days": the next matching ask auto-answers `human-remembered` with the rule id, hit
count increments, the card footer shows the standing rule + expiry; day 8 the same ask gates again, zero
manual cleanup.

**SC-37 · Tier enforcement.** An `irreversible` ask configured `min_tier=T3` is answered from a bare terminal
session (T1) → rejected `insufficient_provenance`; answered via a chat-verified principal (T3) → allowed; the
audit and the packet both carry the tier.

**SC-38 · Rule simulation before a config change.** A PR shortening `irreversible` TTL 300→180 s attaches a
simulation: 3 historical asks would have expired instead of being answered — the reviewer reads the flip set
before merging; the simulation is read-only and cannot touch the store.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R37 | CUJ-8 | SC-33 | `test_standing_approvals.py`, `test_shadow_report.py` |
| R38 | CUJ-3 (dual) | quorum fixtures | `test_quorum.py` |
| R39 | CUJ-3, CUJ-10 | SC-37 | `test_provenance_tiers.py` |
| R40 | CUJ-1, CUJ-12 | verifier fixtures | `test_identity_plugins.py` |
| R41 | CUJ-14-adjacent (ops) | SC-38 | `test_rule_simulation.py` |
| R42/R43 | CUJ-1 | pack fixtures | `test_policy_packs.py`, `test_templates.py` |
| R44 | CUJ-7, CUJ-10 | SC-40 | `test_event_hooks.py` |
| R47 | CUJ-2 | SC-32/SC-37 (tier-driven fixtures) | `test_risk_tiers.py` |
| R45 | CUJ-13 | conformance suite | `test_conformance_kit.py` |
| R46 | CUJ-7 | CI-recipe fixtures | `test_github_checks.py` |
