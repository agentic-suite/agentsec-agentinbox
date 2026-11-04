# PRD 09 — Roadmap

**BLUF:** v0.1.0 is the **complete lifecycle on zero-dependency channels** (terminal/TUI, desktop
notifications, CI, signed webhooks — **no chat platform required**) plus the pluggable bus + store spine
(filesystem spool + SQLite), with the security core
(claims, redaction, flood control, hash-chained audit). v0.1.x hardens the human side (step-up, on-call sync,
standing approvals, mobile push). v0.2.0 goes **multi-approver and enterprise-shaped** (quorum/dual-control,
delegation, SSO server mode). v0.3.0 completes the **ecosystem matrix** (Tier-1 harness adapters, ≥3 framework
adapters, marketplace-adjacent community adapters).

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Release philosophy

1. **Lifecycle before reach.** A smaller set of channels with correct claims, expiry, and audit beats more
   channels with weaker guarantees.
2. **Every version stays local-first.** Enterprise features are additive modes, never replacements for the
   single-machine path.
3. **Compatibility is a versioned claim.** Each release's notes carry the harness/producer matrix with what was
   actually field-tested ([PRD 19](19-harness-compatibility.md)) — never a hope.
4. **PRD-first.** A requirement ships when its acceptance test and its scenario in [PRD 17](17-scenarios.md)
   pass — not when the code exists.

## v0.1.0 — "The gate has a consumer" (Wave 0 co-release)

**Theme:** agentpolicy can say `ask` and *something safe and usable happens*.

| Area | Ships |
|---|---|
| Core | Ask contract `ask/1.0` + idempotent ingest; store + 5-state lifecycle; crash-safe scheduler; decision card renderer (4 blocks, unknown-labeling); redactor + receipts |
| Channels | Terminal/TUI (TTY + non-interactive fallback), **desktop notifications** (macOS/Linux, no third-party account), CI checkpoint (`gate` + reserved exit codes), **signed webhook** (display-only, recipes for ntfy/Pushover/Discord/email bridges) — **no chat platform required** |
| Bus + store | **AskBus** drivers: in-proc (default) + **filesystem spool** (atomic rename, fsync, flock, inotify/poll); **AskStore** driver: SQLite (reference) + memory, behind the conformance-gated contract (E11/E12) |
| Decisions | Claim tokens (single-use, hashed, bound); principal authN + rosters + self-review deny; first-answer-wins; typed confirm for irreversible |
| Time | Per-class TTLs, pre-expiry warning, timeout = deny + rescope hint; UTC + monotonic correctness |
| Escalation | Configurable tier ladder, claim invalidation on tier change, no-TTL-extension rule |
| Protection | Token-bucket throttle + duplicate coalescing + flood auto-deny event + digest notification |
| Evidence | Hash-chained audit log; `export` / `verify-log`; agentwatch event set (ask lifecycle); agentpolicy resolve bridge |
| Producers | agentpolicy adapter (reference); generic HTTP/CLI + contract fixtures; example adapter for one framework (LangGraph interrupt) |
| Ops | `init`, `doctor`, `report`; zero-cloud mode; file-permission defaults |

**Definition of done:** R1–R7 + E1–E12 acceptance tests green; SC-01–SC-26 field-test scenarios run with the
report published (misses included); harness matrix honest; docs complete.

## v0.1.x — "The 3 a.m. human" (hardening, one-to-two weeks of iteration each)

| Feature | Requirement | Notes |
|---|---|---|
| **Matrix interactive channel** | [PRD 16 §B.5](16-channel-and-harness-adapters.md) | The open-protocol remote/phone surface — same InboxChannel contract, homeserver event signatures, roster check; the honest OSS answer to the 3 a.m. case |
| **Chat-platform adapters (Slack/Teams)** | [PRD 16 §B.6](16-channel-and-harness-adapters.md) | Optional community adapters behind the same contract — never load-bearing |
| Step-up re-auth for critical classes | [PRD 18](18-approval-integrity.md) | Platform-verified user + a second factor for `irreversible` (config per class) |
| On-call schedule sync | PRD 03 §C | PagerDuty/Opsgenie lookup: tier = "whoever is on call", not a static list |
| Business-hours TTLs | PRD 03 §B | Calendar-aware deadlines (a 4-hour TTL at 2 a.m. ≠ 4 hours at 10 a.m.) |
| Standing approvals **with mandatory expiry + recert** | R10 | `authorization.source=human-remembered`; auto re-gate at expiry; usage counters surfaced |
| Mobile push | R8 | Native push with the four blocks; one-tap deny, confirm-to-approve |
| Delegated (machine) approvals | R9 | Narrower-policy delegate, logged `approved-by-machine` (depends on agentpolicy R41 decisions) |
| Ticket/incident linkage | PRD 03 §B | `correlation_id` + resolve webhooks → ServiceNow/Jira/GitHub issue |
| **Effect identity + constrained approvals** | [PRD 24](24-constrained-approvals-and-effects.md) R13/R14/R20 | Approve the effect, approve narrower, agent-readable structured outcomes — the "shape the action" release |
| **Staleness detection** | [PRD 24](24-constrained-approvals-and-effects.md) R16 | Changed-context asks degrade to re-confirm; delayed approvals never release silently |
| **Evidence + previews + quality scores + trust block + decision packets** | [PRD 25](25-evidence-and-decision-quality.md) R21–R26 | Diffs/plans/previews on cards; deterministic evidence scores; portable packets |
| **Grouped review + claim/assign/handoff** | [PRD 26](26-approver-experience-operations.md) R27/R30 | Clustered display, per-ask decisions; team work handling |
| **Quiet hours + incident/freeze mode** | [PRD 26](26-approver-experience-operations.md) R31/R32 | Workload controls; one audited tighten-everything toggle |
| **Standing approvals, governed** | [PRD 27](27-governance-identity-extensibility.md) R37 | Scope/owner/expiry/recert/hit-counts/shadow simulation |
| **Approval provenance tiers** | [PRD 27](27-governance-identity-extensibility.md) R39 | Every decision records how strongly it was verified |
| **Event hooks** | [PRD 27](27-governance-identity-extensibility.md) R44 | Post-decision outbound automation (tickets, SIEM, PR annotations) |
| **Typed SDKs + conformance kit + policy packs** | [PRD 27](27-governance-identity-extensibility.md) R42/R45 | JSON Schema/Pydantic/TS + self-verify harness + prebuilt class packs |
| **`needs_changes` + clarification cycles + resolution summaries** | [PRD 28](28-review-loops-and-orchestration.md) R48–R50 | The review loop between deny and approve — inside the running TTL, never extending it |
| **Session grants + incident suppression** | [PRD 28](28-review-loops-and-orchestration.md) R51/R53 | Timeboxed "stop asking me" — the firefight scalpel, expiring by construction |
| **Class-shaped routing + parallel notify** | [PRD 28](28-review-loops-and-orchestration.md) R54/R55 | Security asks reach security first; critical asks notify two tiers at t=0 |
| **Rollback-required approvals + confidence labels + structured deny taxonomy** | [PRD 29](29-trust-maturity-writeback-performance.md) R59–R61 | No rollback story, no approve; estimates never render as facts; every deny codes up for tuning |
| **Signed rationale + writeback (annotations/comments)** | [PRD 29](29-trust-maturity-writeback-performance.md) R62/R64 | Rationale hash-bound into the chain; decisions land in GitHub/PR/ticket surfaces |
| **Built-in chaos drill subset** | [PRD 29](29-trust-maturity-writeback-performance.md) R67 | `agentinbox drill`: self-serve spoof/flood/stale drills on the ops box |
| **PRD 30 hardening gates ship with their features, not after** | [PRD 30](30-correctness-conflict-abuse-hardening.md) | Precedence lattice, state machine, review limits, scope-escape, revocation, and no-advisory-allows are the *definition of done* for every PRD 24–29 feature they gate |
| Multi-select / queue UX | — | `inbox` TUI: answer a digest of pending asks efficiently |

## v0.2.0 — "Teams and enterprise shape"

| Feature | Requirement | Notes |
|---|---|---|
| Quorum / dual-control approvals (incl. role-pairs, veto, quorum deadlines) | agentpolicy R41 + [PRD 27](27-governance-identity-extensibility.md) R38 | N-of-M distinct approvers; single approval never releases; veto is terminal |
| **Human edits the action** (`allow_with_edits`) | [PRD 24](24-constrained-approvals-and-effects.md) R15 | Approve the edited form; the edit is what executes |
| **Approval bundles + gate dependencies** | [PRD 24](24-constrained-approvals-and-effects.md) R18/R19 | Grouped review without bulk-approve; blocked gates |
| **Persona views, saved filters, SLA analytics, search/replay, precedent** | [PRD 26](26-approver-experience-operations.md) R28/R29/R33/R34/R36 | The operator cockpit |
| **Local web UI (localhost-only)** | [PRD 26](26-approver-experience-operations.md) R35 | Loopback-served; a channel, not a bypass |
| **Rule simulation** | [PRD 27](27-governance-identity-extensibility.md) R41 | Replay history against candidate inbox config before changing it |
| **Approval templates + native CI/Git surfaces (GitHub Checks)** | [PRD 27](27-governance-identity-extensibility.md) R43/R46 | Per-class card contracts; check-run approval path |
| **Identity plugins (OIDC device flow, passkey step-up)** | [PRD 27](27-governance-identity-extensibility.md) R40 | Principals without any chat platform |
| **Future-effective windows + trust profiles + environment overlays + change calendars** | [PRD 28](28-review-loops-and-orchestration.md) R52/R56–R58 | Approve-now-effective-later; per-agent-class and per-env inbox behavior; freeze/maintenance calendars |
| **Parallel quorum + cross-ask correlation** | [PRD 28 R55](28-review-loops-and-orchestration.md) + [PRD 29 R65](29-trust-maturity-writeback-performance.md) | One-from-each rosters; rollout/incident grouping for humans under pressure |
| **Signed attestations + writeback (checks/tickets) + training mode + full drill pack** | [PRD 29](29-trust-maturity-writeback-performance.md) R63/R64/R66/R67 | Externally verifiable release evidence; integrated status surfaces; measurable approver onboarding; self-serve red-team |
| Delegation & out-of-office | PRD 03 §D | Time-boxed delegate windows |
| Server mode (headless host) | [PRD 22](22-operations-and-governance.md) | Same core, deployable: SSO (OIDC/SAML), SCIM rosters, multi-tenant, WORM/external-notarized audit, HA — plus the **Postgres AskStore** and **Redis/NATS AskBus** drivers, admitted by the same conformance suites (E11/E12) |
| Approver analytics (what you approve most) | R11 | Feeds policy refinement: "these classes need better rules, not more approvals" |
| Shared inbox | R12 | Round-robin ask distribution across a team |
| Access reviews for standing approvals | PRD 03 §D | Recertification campaigns — standing grants decay |

## v0.3.0 — "The ecosystem matrix closes"

| Feature | Requirement |
|---|---|
| All 5 Tier-1 coding-agent harnesses (or documented lower-layer coverage) | [PRD 19](19-harness-compatibility.md) |
| ≥ 3 Tier-2 framework adapters shipped | [PRD 19](19-harness-compatibility.md) |
| MCP elicitation bridge (approval-aware) | PRD 03 §G |
| A2A / agent-to-agent task-gate bridging | PRD 03 §G (as it stabilizes) |
| Community adapter guide + conformance kit | "any harness can add itself" |

## Post-v1.0 candidates (parking lot, not committed)

Intelligent digesting of near-duplicate asks (deterministic clustering, **not** ML-deciding); approval SLA
reporting for compliance exports; agentdrill-authored *inbox attack packs* shipped to other tools; approver
workload balancing across time zones; voice-answer flow ("approve ask ending 7f3a" — probably never: spoofable
surface, documented as such).

## Sequencing principles (the "why this order")

1. **Claims and audit before channels** — a new channel on a weak binding model multiplies exposure.
2. **Terminal first** (no external dependency), **desktop + webhook second** (reach without any platform),
   **CI third** (proves headless), **Matrix fourth** (proves remote-interactive + spoof resistance on an open
   protocol), chat adapters and native push after — every step leaves a product that is complete without the
   next one.
3. **Flood control ships in v0.1.0**, not later — it is a P0 because R7 is a security property.
4. **Enterprise = server mode of the same core** — the moment the local and server cores fork, both rot.
