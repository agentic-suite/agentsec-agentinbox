# agentinbox PRD

The product requirements for **agentinbox** — the human half of every agent `ask`-gate: decision-ready
notifications, any-channel answers, timeout = deny, escalation, flood protection, and evidence-grade audit.
Part of the [agentic-suite](https://github.com/agentic-suite).

> **Status: planned — PRD set 00–30 complete (plan of record).** Code has not started; everything here is the
> design of record the WBS, tests, and field test are built from. PRDs 00–23 define the v0.1.0 core plus the
> OSS-first plugin architecture (channels/bus/store/producers); **PRDs 24–29 are the forward product-depth
> slate** (constrained approvals, evidence, operator experience, governance, review loops & orchestration,
> trust maturity & writeback) that turns the gate into an **approval control plane**; **PRD 30 is the
> correctness/conflict/abuse hardening layer that gates it**. The consolidated source
> PRD is retained
> verbatim as [Appendix A](appendix-a-consolidated-prd.md); every line of it is traced into the numbered set
> in [PRD 12](12-traceability.md).

## Documents

| # | Document | Scope |
|---|---|---|
| 00 | [Press release / FAQ](00-press-release.md) | The one-page story and the honest FAQ |
| 01 | [Why](01-why.md) | Problem, four failure modes, evidence, why now, what success looks like |
| 02 | [Architecture](02-architecture.md) | Components, lifecycle, interfaces, trust boundaries, failure semantics |
| 03 | [Landscape](03-landscape.md) | What OSS and enterprises already solve (CI/ITSM/on-call/PAM/chat/SOAR/protocols), the whitespace, honest v0.1.0 gaps |
| 04 | [Users, stories & CUJs](04-users-and-cujs.md) | 7 personas, 26 user stories, 14 critical journeys with unhappy paths |
| 05 | [Features](05-features.md) | R1–R10 product requirements + E1–E10 engineering requirements, with acceptance criteria |
| 06 | [Security baseline](06-security-baseline.md) | Invariants, STRIDE threats, channel security, privacy, own posture, non-claims |
| 07 | [Success metrics](07-success-metrics.md) | Headline + spine + gate-trust + product-health metrics, anti-metrics, measurement infra |
| 08 | [Risks](08-risks.md) | Risk register with mitigations and tripwires; dismissed risks |
| 09 | [Roadmap](09-roadmap.md) | v0.1.0 → v0.1.x → v0.2.0 → v0.3.0 sequencing and principles |
| 10 | [Feature parity](10-feature-parity.md) | Gap-closure matrix vs harness prompts, HITL SDKs, OSS HITL products, commercial approval products, protocols |
| 11 | [Decisions](11-decisions.md) | The 12 frozen design decisions + deferred decisions with defaults |
| 12 | [Traceability](12-traceability.md) | Requirement → story → CUJ → scenario → test; consolidated-PRD coverage check |
| 13 | [NFRs](13-non-functional-requirements.md) | Performance, durability, size, portability, security NFRs, observability, usability, accessibility, maintainability |
| 14 | [Non-goals](14-non-goals.md) | Hard boundaries (security properties) and product boundaries, with disambiguations |
| 15 | [Data model](15-data-model.md) | Entities, lifecycle, ask/resolve contracts, agentwatch event set, storage, integrity, config |
| 16 | [Adapters: channels, bus, store & producers](16-channel-and-harness-adapters.md) | The plugin surfaces — **four adapter families**: inbox channels (terminal/desktop/CI/webhook; Matrix next; chat optional), the AskBus (in-proc/filesystem/Redis/NATS), the AskStore (SQLite/memory/Postgres/embedded), and producers (agentpolicy, harness hooks, framework interrupts, MCP, Temporal) + the OSS-first rationale and the filesystem-bus hard rules |
| 17 | [Scenarios](17-scenarios.md) | The 26-scenario field-test catalog incl. attack packs and scoring |
| 18 | [Approval integrity](18-approval-integrity.md) | The answer-acceptance pipeline, claim design, per-channel assurance, confused-deputy defenses, anti-injection rules, guessing resistance |
| 19 | [Harness compatibility](19-harness-compatibility.md) | REQUIRED: the agnostic-by-construction model, Tier 1/2/3 matrices, honest labels, verification & governance |
| 20 | [Standards & claims](20-standards-and-claims.md) | Standards implemented/aligned, the agentwatch event proposal, compliance mappings, certification ladder, claims vocabulary |
| 21 | [Evidence & method](21-evidence-register-and-method.md) | Evidence register, the zero-context study protocol, field-test method, reproducibility kit, non-evidence honesty |
| 22 | [Operations & governance](22-operations-and-governance.md) | Deployment modes, lifecycle, config-as-code, retention/backup/upgrade, monitoring, runbooks, gate-governance |
| 23 | [Enterprise adoption](23-enterprise-adoption-and-governance-hardening.md) | Honest starting point, staged hardening (step-up → server mode → certifications), buyer packet, topologies, hardening principles |
| 24 | [Constrained approvals, effects & ask semantics](24-constrained-approvals-and-effects.md) | **Shape the action**: effect identity, constrained approvals (`allow_with_constraints`), human edits (`allow_with_edits`), staleness + re-auth on drift, bundles, gate dependencies, agent-readable outcomes — R13–R20, E13 |
| 25 | [Evidence, previews & decision quality](25-evidence-and-decision-quality.md) | **Make decisions real**: evidence attachments, previews bound to identity, deterministic evidence-quality scores, "why this ask" delta block, trust block, replayable decision packets — R21–R26, E14 |
| 26 | [Approver experience, teams & operations](26-approver-experience-operations.md) | **The muting defense**: grouped review (no bulk-approve), claim/assign/handoff, quiet hours, incident/freeze mode, persona views, saved filters, precedent (advisory), SLA accountability, search/replay, local web UI — R27–R36 |
| 27 | [Governance, identity & extensibility](27-governance-identity-extensibility.md) | **Trust infrastructure**: governed standing approvals, quorum variants, provenance tiers, local identity plugins (no chat platform ever required), rule simulation, policy packs, approval templates, event hooks, typed SDKs + conformance kit, native CI/Git surfaces, risk-tier drivers — R37–R47 |
| 28 | [Review loops & operational orchestration](28-review-loops-and-orchestration.md) | **The middle path**: `needs_changes` + clarification cycles, timeboxed session grants, future-effective approval windows, incident-scoped suppression, class-shaped routing, parallel notify, per-agent trust profiles, environment overlays, change calendars — R48–R58, E15 |
| 29 | [Trust maturity, writeback & human performance](29-trust-maturity-writeback-performance.md) | **Evidence you can defend**: rollback-required approvals, confidence-labeled blast radius, structured deny taxonomy, signed rationale, externally-verifiable attestations, outbound writeback (GitHub checks/PRs/tickets), cross-ask correlation, training mode, built-in chaos drills — R59–R67, E16 |
| 30 | [Correctness, conflict & abuse hardening](30-correctness-conflict-abuse-hardening.md) | **The final layer that makes 24–29 safe**: the precedence lattice, the formal state machine, idempotent never-authoritative side effects, frozen schema-evolution, computed-not-asserted trust, review-loop limits, monotonic-narrowing edits, shared-machine provenance, sleep/wake semantics, derivative redaction, no-advisory-allows, revocation, corpus governance, web-UI security, dead-man detection — R68–R77, E17–E21 |
| 31 | [CUJ & feature gaps (0.1.0 expansion)](31-cuj-and-feature-gaps-next-slate.md) | CUJ-15..48 + F31–F45 umbrella → PRDs 32–37 |
| 32 | [Decision quality & ask readiness](32-decision-quality-and-ask-readiness.md) | Readiness scoring, non-decisionable rejection, contradictions, evidence sufficiency, quality banner — R78–R86 |
| 33 | [Constrained allows & denial repair](33-constrained-allows-and-denial-repair.md) | Alternatives, constrained allow, repair packets, human edits — R87–R93 |
| 34 | [Operation bundles, handoff & incident review](34-operation-bundles-handoff-and-incident-review.md) | Bundles, claim/assign/handoff, incident mode, narrative, timeline — R94–R100 |
| 35 | [Outcome closure & execution proof](35-outcome-closure-and-execution-proof.md) | Closure states, receipts, approved-vs-executed, packets — R101–R107 |
| 36 | [Repetitive approvals, grants & compression](36-repetitive-approvals-grants-and-compression.md) | Compression, windows, session grants, burn-down, governance — R108–R114 |
| 37 | [Policy learning & governance insights](37-policy-learning-and-governance-insights.md) | Repetition/deny/hotspot insights, calibration, insight-to-action — R115–R122 |
| A | [Appendix A — consolidated PRD](appendix-a-consolidated-prd.md) | The source PRD (PRD 11 from the research vault), verbatim, fully traced into the set |

## Reading order

- **You want the pitch:** 00 → 01.
- **You want to build it:** 02 → 05 → 15 → 16 → 18 (then 17 for how it's proven).
- **You want the product vision beyond v0.1.0:** 24 → 25 → 26 → 27 → 28 → 29 (the approval-control-plane slate).
- **You're a security reviewer:** 06 → 18 → 21 → 20.
- **You're an enterprise buyer:** 03 → 23 → 14 (what we refuse to pretend).
- **You're an integrator:** 16 → 19 → 15 → 27 R44–R46 (the contract + the hooks/SDK surfaces).
