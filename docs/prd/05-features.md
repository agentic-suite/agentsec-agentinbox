# PRD 05 — What (Features)

**BLUF:** agentinbox v0.1.0 is the **complete ask lifecycle**: ingest any `ask` (agentpolicy first, any producer
via a stable JSON contract), render a zero-context **decision card**, deliver to **terminal + desktop
notifications + CI + signed webhooks** (Matrix next; chat platforms optional),
accept exactly one **authenticated, identity-bound answer**, enforce **timeout = deny** with pre-expiry warning
and a configurable **escalation ladder**, neutralize **ask floods**, and record everything in a **hash-chained
audit log + agentwatch events**. Local-first, one binary, five minutes to first approval.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## v0.1.0 scope (one sentence)

Everything an `ask` needs after the policy engine says *"a human must decide"* — and nothing that decides on the
human's behalf.

## Requirement IDs and how to read them

- **R#** — product requirements, inherited and expanded from the consolidated PRD (Appendix A). R1–R7 are the
  v1.0 P0 set; R8–R10 are v1.x. **R13–R46 are the forward product-depth slate, specified in
  [PRDs 24–27](24-constrained-approvals-and-effects.md)** (§D below is the index).
- **E#** — engineering requirements: the security/protocol/ops properties without which the product is unsafe to
  ship (these are P0 for v0.1.0). E13/E14 are the forward engineering clauses defined in PRDs 24–25.
- Priority: **P0** v0.1.0 · **P1** v0.1.x–v0.2.0 · **P2** v0.3.0+.

## A. Core requirements (R1–R10, from the consolidated PRD)

### R1 — Decision-ready notifications (P0)

| | |
|---|---|
| **Requirement** | Every `ask` arrives as a **decision card** with full context: what the agent wants to do, which policy clause fired, the action's blast radius, and the session so far. |
| **The four context blocks** | (1) **Action**: tool, verb, canonical arguments (redacted, truncated with receipts), environment, data class. (2) **Policy**: matched rule id, reason code, policy version, criticality, freeze/posture flags. (3) **Blast radius**: resource scope, affected counts where derivable, reversibility label (`reversible`/`irreversible`/`unknown`), credential class involved. (4) **Session**: agent id, session id, the last N tool calls (titles only), cumulative counters, prior asks in this session and their outcomes. |
| **Missing context rule** | A missing field renders as **`unknown`** and is visually distinct — never blank, never guessed, never defaulted to a safe-looking value. |
| **Untrusted content rule** | Any agent- or tool-supplied string (arguments, tool output, agent "intent") is labeled **untrusted**, escaped, and length-capped. Trusted fields (policy clause, reason code) come only from a signed producer adapter or render as **unverified**. |
| **Acceptance** | Zero-context test: ≥ 9/10 approvers make the pre-registered correct call in < 15 s on the scenario corpus ([PRD 07](07-success-metrics.md)); missing-context corpus renders `unknown` in 100% of cases; injection corpus produces 0 approval-cause-by-embedded-text. |
| **Test** | `tests/test_card_context.py`, `tests/test_card_untrusted.py`, user study protocol in [PRD 21](21-evidence-register.md). |

### R2 — Answer from anywhere, one truth (P0)

| | |
|---|---|
| **Requirement** | The approver answers from **terminal/TUI**, **desktop-notification → terminal**, or **CI checkpoint**; remote reach rides **signed webhooks** (display-only at v0.1.0) with **Matrix** next and chat platforms (Slack/Teams) as optional adapters — every channel records the identical decision in the identical audit record. |
| **Channel parity rule** | The same ask rendered in N channels resolves **once**; the record names the winning channel, principal, and timestamp; losing surfaces show the outcome within their poll interval. |
| **Answer action** | A structured action only: terminal keypress pair (`a`/`d` with a typed confirm for irreversible), CI exit, or a platform-signed chat button (Matrix/Slack/Teams, **when an adapter is configured**). **No free-text approvals** ([PRD 14](14-non-goals.md)). |
| **Acceptance** | Cross-channel parity test: the same ask answered on each of 3 channels yields byte-identical decision records modulo channel/principal fields; a second-channel answer after resolution is a logged no-op (`late-answer`). |
| **Test** | `tests/test_channel_parity.py`, `tests/test_late_answer.py`. |

### R3 — Timeout = deny, configurable, warned (P0)

| | |
|---|---|
| **Requirement** | Unanswered asks **deny** at expiry. TTL configurable **per action class** (e.g., irreversible 5 min, external-send 15 min, bulk 30 min), with a floor and ceiling. A **pre-expiry warning** fires at `T-warn` (default `T-60s`) on every active channel. |
| **Hard rules** | Escalation and delivery retries **never extend the TTL**. The agent receives a structured outcome, not a hang: `decision=deny`, `reason_code=human_gate_timeout`, `retryable=false`, plus a **rescope hint** (e.g., "narrow scope to staging, or request a standing approval for this class"). |
| **Persistence** | Expiry survives restart: on boot, any ask past `expires_at` is expired exactly once; late warnings fire once with a `scheduler-recovered` marker. Clock jumps cannot extend a TTL (absolute UTC + monotonic deltas). |
| **Acceptance** | Timeout demonstrated, logged (`ask-expired`), producer receives rescope-not-failure; restart and clock-skew fixtures pass; no code path turns expiry into allow. |
| **Test** | `tests/test_expiry.py`, `tests/test_expiry_restart.py`, `tests/test_clock_skew.py`. |

### R4 — Escalation ladder (P0)

| | |
|---|---|
| **Requirement** | Unanswered asks escalate up a **configurable ladder**: tier 1 → tier 2 → … (e.g., buddy → on-call → channel). Per-tier delay, per-tier channel, per-tier re-notification. |
| **Semantics** | Escalation is **notification routing, not a decision**: it changes who is asked, never the outcome or the deadline. Each escalation: emits `ask-escalated` with tier + recipients, re-renders the card with the remaining time and "tier N did not answer", and **cancels superseded single-use claims** so an earlier tier cannot answer after escalation. |
| **Terminal** | The final tier sees "last tier — this expires in mm:ss"; if still unanswered, expiry = deny (R3). |
| **Acceptance** | 3 a.m. drill: the ask reaches the configured tier within the configured window; events reconstruct the ladder; the ladder never lengthens the TTL. |
| **Test** | `tests/test_escalation.py`, drill SC-11/SC-12 in [PRD 17](17-scenarios.md). |
| **v0.1.x** | Native PagerDuty/Opsgenie schedule lookup and business-hours calendars ([PRD 09](09-roadmap.md)). |

### R5 — Full audit trail in agentwatch (P0)

| | |
|---|---|
| **Requirement** | Every ask/answer/timeout/escalation/flood/delivery attempt is recorded: (a) in the **agentwatch security-event schema** (the ask lifecycle event set defined in [PRD 20](20-standards-and-claims.md), added under the schema's additive process), and (b) in a local **append-only, hash-chained** log. |
| **Join keys** | `ask_id`, `session_id`, `agent_id`, `action_identity` — an ask record and an agentwatch record join on a common id, so the gate history reconstructs next to the session trace. |
| **Reconstruction** | `agentinbox export --session <id>` emits an ordered JSONL timeline: every transition with principal, channel, timestamps, reason codes, redaction receipts, and the hash chain. |
| **Acceptance** | Full gate history reconstructable per session; the chain verifies (`verify-log`); a corrupted row is detected, not skipped. |
| **Test** | `tests/test_audit_chain.py`, `tests/test_export.py`. |

### R6 — CI/headless checkpoints (P0)

| | |
|---|---|
| **Requirement** | Headless agents surface asks as **pipeline checkpoints** (`agentinbox gate`), not push notifications alone: the pipeline job blocks, prints the ask id + card summary + deep link, and exits with a **reserved, stable exit code**. |
| **Exit codes** | `0` approved → proceed · `2` denied → fail · `3` expired → fail (deny class) · `4` inbox unavailable → fail closed · `5` still pending → poll again · `1` usage/internal error. CI treats `2/3/4` as failure; `5` as retry. |
| **Resume** | The gate is **answerable from any channel** while the job waits (Slack approves; CI continues). Job cancellation marks the ask `cancelled`, never orphaned. |
| **Acceptance** | An irreversible CI action halts the pipeline on an ask and never proceeds on `2/3/4`; retries are idempotent (same ask id, no duplicate notification). |
| **Test** | `tests/test_gate_exit_codes.py`, `tests/test_ci_resume.py`, SC-15/SC-16. |

### R7 — Rate protection: throttling + flood auto-deny (P0)

| | |
|---|---|
| **Requirement** | A misbehaving agent cannot spam the inbox: per-agent/session/environment **token-bucket throttling**, **duplicate-identity coalescing**, and **flood auto-deny** as a first-class event. |
| **Behavior** | Bucket trip → new asks auto-denied with `ask_flood_throttled` → **one** `ask-flood` event (counts, window, offending agent/session) → **one digest notification** ("N asks denied; first ask shown"). Pre-flood pending asks stay answerable. Legitimate bursts stay under the threshold (dedupe + batching first). |
| **Config** | Per action class + per agent; threshold, burst, and window in config; `doctor` explains the effective limits. |
| **Acceptance** | Flood pack (200 asks / 30 s) → 200 denies, 1 event, 1 notification, approver sees a digest; a 20-action migration burst remains fully answerable. |
| **Test** | `tests/test_flood.py`, `tests/test_burst_legitimate.py`, SC-13/SC-14. |

### R8–R10 (v1.x, scoped not built)

| # | Requirement | Design notes |
|---|---|---|
| **R8** | **Mobile push** — the 3 a.m. scenario done right: native push with the four context blocks, one-tap deny, approve requires the confirm step; delivered-via-push is recorded like any channel | v0.1.0 covers the away-from-desk case with desktop notifications + signed webhook push recipes (ntfy/Pushover) + Matrix (v0.1.x); native push adds an APNs/FCM dependency and its own spoofing surface |
| **R9** | **Delegated approvals** — certain ask classes delegatable to a second agent/automation under a **narrower policy**, logged as `approved-by-machine` with the delegate policy id | Requires agentpolicy's approval-policy decision (its R41 dual-control space); the inbox must render and audit machine decisions distinctly, never silently |
| **R10** | **Standing approvals** — "always allow this class from this project" **with mandatory expiry**, hit-count and last-used surfaced, recertification flow | The dangerous convenience: every standing rule is an audited, expiring artifact with an owner; expiry re-gates automatically; a standing approval answers an ask with `authorization.source=human-remembered` in the agentwatch schema |

## B. Engineering requirements (E1–E10, all P0 for v0.1.0)

### E1 — Stable ask contract + idempotent ingest

A small, versioned JSON contract (`ask/1.0`): required `ask_id?` (or server-minted), `action_identity`,
`tool`, `action`, `arguments` (redaction at ingest), `agent_id`, `session_id`, `environment`, `data_class`,
`reason_code`, `policy_ref`, `criticality`, `expires_at`, `requested_by`, `context`. Ingest is
**idempotent** keyed by `action_identity` + `session_id` within the dedupe window: a retry returns the same
ask id and re-notifies nothing. Contract fixture + JSON Schema shipped; producers validated against it.
*Acceptance:* a duplicate producer POST returns the same ask id; malformed asks are rejected with a
diagnostic that names the failing field.

### E2 — Durable store + crash-safe scheduler

SQLite (WAL) as the reference **AskStore driver** (pluggable per E11); ask records, delivery attempts, claims,
and the audit chain in one file. All timers derive from persisted absolute instants (`expires_at`, `warn_at`,
`escalate_at`); on boot the scheduler recomputes — overdue transitions fire **exactly once**, with a
`scheduler-recovered` marker.
*Acceptance:* kill -9 mid-wait → restart → expiry at the correct instant, one event, no lost asks.

### E3 — Unforgeable, single-use claim tokens

Every rendered card carries a **claim token**: 256-bit secret, stored **hashed**, bound to `ask_id` +
`action_identity` + channel + tier, expiring with the ask, **single-use**, invalidated on escalation tier
change and on resolution. A forwarded link, a replayed request, or a token answered late does nothing.
*Acceptance:* replay/forward/late/stale-token fixtures all fail closed and log `answer-rejected` with reason.

### E4 — Answer authentication + authorization

An answer requires (1) a valid claim and (2) an **authenticated principal** from the channel adapter — never a
client-supplied `approver` string. The principal must be in the **approver allowlist** for the ask's action
class; `self_review=deny` rejects the requester approving their own ask for irreversible classes;
chat-platform callbacks (Matrix/Slack/Teams, **when an adapter is configured**) are **signature-verified**
(platform HMAC with timestamp window) before parsing. First valid answer wins.
*Acceptance:* unsigned chat callback → rejected; off-roster principal → rejected + logged; self-approval →
rejected per config; winner + loser recorded on race.

### E5 — Injection-resistant rendering

All agent/tool-derived text is data, never markup: plain-text rendering (or escaped HTML) with length caps,
clear **untrusted-source labeling**, and no link auto-expansion inside untrusted fields. Trusted fields are
never taken from unauthenticated producers. No "approve" affordance inside untrusted content; buttons exist
only in the trusted chrome. *Acceptance:* the injection corpus (markdown, links, fake buttons, CISO-impersonation,
"ignore previous instructions") renders as inert text — 0 approvals, 0 auto-navigation.

### E6 — Redaction-by-default across store, channel, audit

A pattern + shape redactor (API keys, bearer tokens, private keys, connection strings, PII classes) runs
**before** storage, rendering, and audit; every redaction emits a receipt (field, class, count). Config
`off` requires explicit, loud config; raw values are never persisted anywhere. *Acceptance:* the evidence
scanner finds 0 secrets in store/channel payloads/audit dumps; receipts present on every redacted field.

### E7 — Notification hygiene + delivery accounting

Every delivery attempt is an event (`delivered`/`delivery-failed` + retry). Bounded retry with backoff, then
fail over to the next channel — **ingest never blocks on delivery**. Per-channel quiet behavior (chat
threading when an adapter is configured, CI annotation vs. desktop alert) is config. Floods coalesce (R7);
the inbox must get **quieter** under attack,
not louder. **Unroutable-class rule:** an ask whose class resolves to *no enabled channel* is a **config
error, not a quiet timeout** — ingest rejects it with a diagnostic (the producer denies at the enforcer) and
`doctor` flags the class; a channel that is *configured but down* is different (accepted, pending,
`delivery-failed` events, TTL still applies). *Acceptance:* channel outage → fallback fires, ask still
answerable, `delivery-failed` logged; unroutable class → rejected at ingest, never a silent 5-minute deny; a
flood produces 1 digest.

### E8 — Time correctness

All persisted times are UTC ISO-8601; scheduling uses absolute instants + monotonic deltas. A backwards clock
jump cannot extend a TTL; a forwards jump cannot resurrect an expired ask. `doctor` warns on clock skew beyond
the signature window. *Acceptance:* clock-skew fixtures (jump back mid-TTL, jump forward past expiry) behave
fail-closed; late Slack signatures rejected by the window.

### E9 — Fail-closed degradation, everywhere

Store down/corrupt → no new asks (503), `doctor` non-zero, producers deny at the enforcer. Channel down →
pending + TTL. agentwatch sink down → local log remains authoritative, buffered with a gap marker. Export
read-only. No path from any failure to an allow. *Acceptance:* fault-injection matrix (store locked, schema
migrated, channel 500, sink offline) — every path is deny-or-pending, never allow, never silent.

### E10 — Versioning, migration, and compatibility

Store schema is **forward-compatible** with a version table + migration path; the ask contract and exit codes
are **stable** within v0.x (additive only); events carry `event_version` per the agentwatch schema process.
*Acceptance:* an old store opens under a new binary (migrates or refuses loudly, never guesses); a 0.1.0
producer payload validates under 0.2.0's schema.

### E11 — Pluggable store behind a conformance-gated contract (P0)

One **AskStore** interface is the only way the core touches state:
`create_or_get_by_identity`, `get`, `cas_status`, `issue_claim`, `consume_claim`, `list_pending`,
`append_event`, `export_session` — with semantics every driver MUST provide: idempotent create, CAS on status
(first-answer-wins), atomic single-use claim consumption, monotonic gapless audit seq, exactly-once timer
recovery, durable-commit-before-ack, and declared **capability flags** (`single_writer`, `multi_writer`,
`cluster_safe`) so the core **refuses configurations a driver cannot guarantee**. Drivers: SQLite (reference,
v0.1.0), memory (tests/embedded), Postgres + embedded-lib (server mode, v0.2.0); third-party drivers via entry
points, admitted only by passing the conformance suite.
*Acceptance:* every driver passes the full semantic suite (crash, race, redelivery, chain fixtures); a
failing driver is rejected at load, never at runtime; capability-failing configs refuse to start.

### E12 — Pluggable bus: movement is not truth (P0)

One **AskBus** interface for delivery/escalation/digest **jobs** (`deliver`, `renotify`, `escalate`, `digest`,
`expire`) — at-least-once with **idempotent consumers** (a redelivered job against a resolved ask is a logged
no-op, never a second notification or state change). Jobs are **never** authoritative state (the store is —
D-13). Drivers: **in-proc** (default; jobs are function calls), **filesystem spool** (v0.1.0: atomic
tmp→rename writes, fsync'd, `flock` single-owner, inotify/FSEvents with a ≤1 s bounded-poll fallback, JSONL
inspectable with standard tools, **one box only**), Redis streams / NATS JetStream (server mode, v0.2.0).
The flood guard throttles **before jobs are published** — a flood becomes one digest job, never 200
deliveries (R7).
*Acceptance:* conformance fixtures per driver (at-least-once + idempotent-consumer, crash mid-job, spool
atomicity/locking/rename-CAS); no driver can answer an ask or reorder the store.

## C. Feature catalog (v0.1.0)

| # | Feature | Requirement | Origin / note |
|---|---|---|---|
| F1 | Ask ingest + validation + idempotency (`POST /v1/asks`, CLI `ask`) | E1 | agentpolicy's `Ask` record is the reference producer payload |
| F2 | Ask store + lifecycle state machine (5 terminal states) | E2, R1 | mirrors agentpolicy `AskStatus` + delivery sub-states |
| F3 | Scheduler: TTL / warn / escalate timers, crash-safe recovery | E2, R3, R4 | small durable-timer engine (Temporal-shaped, local) |
| F4 | Decision-card renderer (4 blocks + unknown-labeling + receipts) | R1, E5 | every channel shares one renderer core |
| F5 | Redactor + receipts (store/channel/audit) | E6 | reuses the ecosystem's redaction vocabulary |
| F6 | Terminal channel (TTY prompt, non-interactive fallback) | R2 | `a`/`d` + typed confirm for irreversible |
| F7 | Remote surfaces: desktop notifications (P0) + signed webhook, display-only (P0) | R2, E4 | no third-party account, no network trust; answers still via terminal/CLI |
| F7b | Chat adapters — Matrix (v0.1.x), Slack/Teams (optional community) | R2, E4 | one InboxChannel contract; signature verify before parse; no free-text |
| F8 | CI checkpoint (`agentinbox gate`) + reserved exit codes | R6 | the headless path |
| F9 | Escalation engine (tiers, re-notify, claim invalidation) | R4 | routing, not deciding |
| F10 | Throttle + flood guard + digest notification | R7 | one event, one digest |
| F11 | Answer verifier (claims, principals, rosters, first-wins) | E3, E4 | the anti-spoofing core |
| F12 | Audit emitter + hash chain + `export` / `verify-log` | R5 | local-first evidence |
| F13 | agentwatch sink + event set (ask lifecycle) | R5 | added under the schema's additive process |
| F14 | Producer adapters: agentpolicy (reference), generic HTTP/CLI | E1 | the plugin seam ([PRD 16](16-channel-and-harness-adapters.md)) |
| F15 | Config: channels, TTLs per class, rosters, ladders, throttle | R2–R4, R7 | one file, `doctor` explains the effective config |
| F16 | `doctor` (store, clock, key, channels, schema versions) | E9 | self-check with exit codes |
| F17 | Long-poll read API (`GET /v1/asks/{id}?wait=`) | E1, R6 | producers don't busy-loop |

## D. Forward requirements — the product-depth slate (PRDs 24–27)

The v0.1.0 set above is the *complete ask lifecycle*. The features that turn it from a gate into an
**approval control plane** are specified, with acceptance criteria, in four dedicated PRDs — this section is
the index (full definitions, honesty clauses, data-model deltas, and scenarios live there):

| PRD | Theme | Requirements |
|---|---|---|
| [PRD 24](24-constrained-approvals-and-effects.md) | **Constrained approvals, effects & ask semantics** — approve the effect not just the call; approve narrower; approve edited; stale-context detection; bundles; gate dependencies; agent-readable outcomes | R13 effect identity · R14 constrained approvals · R15 edits (`allow_with_edits`) · R16 staleness · R17 re-auth on drift · R18 bundles · R19 dependencies · R20 structured outcomes · E13 enforcement-honesty clause |
| [PRD 25](25-evidence-and-decision-quality.md) | **Evidence, previews & decision quality** — diffs/plans/digests on the card; previews bound to identity; deterministic evidence-quality scores; "why this ask" deltas; trust block; replayable decision packets | R21 evidence · R22 previews · R23 quality score · R24 delta block · R25 trust block · R26 decision packet · E14 evidence invariants |
| [PRD 26](26-approver-experience-operations.md) | **Approver experience, teams & operations** — grouped review, claim/assign/handoff, quiet hours, incident/freeze mode, persona views, saved filters, precedent (advisory), SLA accountability, search/replay, local web UI | R27 grouped review · R28 mode-tuned views · R29 saved views · R30 claim/assign · R31 workload controls · R32 incident mode · R33 SLA accountability · R34 search/replay · R35 local web UI · R36 precedent |
| [PRD 27](27-governance-identity-extensibility.md) | **Governance, identity & extensibility** — governed standing approvals, quorum variants, provenance tiers, local identity plugins, rule simulation, policy packs, approval templates, event hooks, typed SDKs, native CI/Git surfaces | R37 standing approvals governed · R38 quorum variants · R39 provenance tiers · R40 identity plugins · R41 rule simulation · R42 policy packs · R43 approval templates · R44 event hooks · R45 typed SDKs · R46 CI/Git surfaces · R47 risk-tier drivers |
| [PRD 28](28-review-loops-and-orchestration.md) | **Review loops & operational orchestration** — `needs_changes` + clarification cycles, session grants, future-effective windows, incident suppression, class-shaped routing, parallel notify, trust profiles, environment overlays, change calendars | R48 needs_changes · R49 clarification cycle · R50 resolution summary · R51 session grants · R52 approval windows · R53 incident suppression · R54 class routing · R55 parallel notify · R56 trust profiles · R57 environment overlays · R58 change calendars · E15 loop/grant invariants |
| [PRD 29](29-trust-maturity-writeback-performance.md) | **Trust maturity, writeback & human performance** — rollback-aware approvals, confidence-labeled blast radius, structured deny taxonomy, signed rationale, signed attestations, outbound writeback, cross-ask correlation, training mode, built-in chaos drills | R59 rollback-required · R60 confidence labels · R61 deny taxonomy · R62 signed rationale · R63 signed attestations · R64 writeback · R65 correlation · R66 training mode · R67 drill pack · E16 attestation invariants |
| [PRD 30](30-correctness-conflict-abuse-hardening.md) | **Correctness, conflict & abuse hardening — the final layer that makes PRDs 24–29 safe to ship**: the precedence lattice (which rule wins), the formal state machine, idempotent never-authoritative side effects, frozen schema-evolution policy, computed-not-asserted trust, review-loop abuse limits, monotonic-narrowing edits, shared-machine provenance, sleep/wake time semantics, derivative redaction, the no-advisory-allows rule, revocation semantics, corpus governance, web-UI security, dead-man detection | R68 precedence lattice · R69 state machine · R70 review limits · R71 scope-escape protection · R72 shared-machine provenance · R73 no-advisory-allows · R74 revocation · R75 corpus governance · R76 web-UI security · R77 dead-man · E17–E21 |

## E. What is deliberately small

No web dashboard in v0.1.0 (terminal TUI + desktop notifications are the surfaces; chat cards optional); no
multi-node sync (single store,
single principal — server/HA mode is [PRD 22](22-operations-and-governance.md)); no plugin marketplace
(adapters are code + docs, the seam is the contract); no policy editing (agentpolicy owns policy; the inbox
links to the clause, it does not rewrite it).

## F. Requirement priority table

| Req | Title | Pri | Req | Title | Pri |
|---|---|---|---|---|---|
| R1 | Decision-ready notifications | P0 | E1 | Ask contract + idempotent ingest | P0 |
| R2 | Any-channel answers, one truth | P0 | E2 | Durable store + crash-safe scheduler | P0 |
| R3 | Timeout = deny + warning | P0 | E3 | Unforgeable single-use claims | P0 |
| R4 | Escalation ladder | P0 | E4 | Answer authN/authZ | P0 |
| R5 | Audit trail (agentwatch + chain) | P0 | E5 | Injection-resistant rendering | P0 |
| R6 | CI checkpoints | P0 | E6 | Redaction-by-default | P0 |
| R7 | Flood protection | P0 | E7 | Notification hygiene | P0 |
| R8 | Mobile push | P1 | E8 | Time correctness | P0 |
| R9 | Delegated (machine) approvals | P1 | E9 | Fail-closed degradation | P0 |
| R10 | Standing approvals + expiry | P1 | E10 | Versioning + compatibility | P0 |
| — | — | — | **E11** | Pluggable store (conformance-gated) | P0 |
| — | — | — | **E12** | Pluggable bus (movement ≠ truth) | P0 |
