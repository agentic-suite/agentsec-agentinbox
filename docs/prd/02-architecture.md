# PRD 02 — Architecture

**BLUF:** agentinbox is a **local-first ask broker** with four responsibilities: **ingest** an ask
(agentpolicy or generic), **render + deliver** it to channels, **accept one authenticated answer** (or expire /
escalate / flood-deny), and **emit** every transition to the audit log and agentwatch. It is a single process
with a **pluggable store** (SQLite reference, per E11), a **pluggable bus** (in-proc + filesystem spool, per
E12), a scheduler, and channel adapters (terminal, desktop, CI, webhook — chat platforms optional); it exposes
a small JSON API on loopback plus a CLI. It owns no policy, no harness integration, and no secrets beyond its
own claim-signing key. **Queue moves; store decides** (D-13).

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Component view

```
┌──────────────────────────── producers ────────────────────────────┐
│ agentpolicy ask broker · harness hook · CI script · LangGraph     │
│ interrupt · OpenAI Agents SDK approval · MCP elicitation bridge   │
└──────────────────────────────┬───────────────────────────────────┘
                               │ POST /v1/asks  (idempotent, identity-bound)
┌──────────────────────────────▼───────────────────────────────────┐
│                        agentinbox core                            │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐  │
│  │  Ingest /  │→ │ Ask store  │← │ Scheduler  │→ │  Escalation │  │
│  │ validator  │  │ (SQLite,   │  │ (timers,   │  │   engine    │  │
│  │            │  │  WAL)      │  │  TTL/warn) │  │             │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └──────┬──────┘  │
│        │               │               │                │         │
│  ┌─────▼──────┐  ┌─────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐  │
│  │ Redactor / │  │ Throttle / │  │  Answer    │  │   Audit     │  │
│  │ context    │  │ flood guard│  │ verifier   │  │  emitter    │  │
│  │ packager   │  │            │  │ (tokens)   │  │ (hash chain)│  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └──────┬──────┘  │
│        │               │               │                │         │
│  ┌─────▼───────────────▼───────────────▼────┐    ┌──────▼──────┐  │
│  │           Delivery router                │    │ agentwatch  │  │
│  │  terminal · desktop · CI · webhook      │    │  sink       │  │
└──┴────────────────────┬─────────────────────┴────┴─────────────┴──┘
                        │ signed claim, rendered card
        ┌───────────────▼──────────────────┐
        │ approver surfaces                │
        │ TTY prompt · desktop alert ·     │
        │ CI exit · webhook (matrix/chat   │
        │ adapters optional)               │
        └───────────────┬──────────────────┘
                        │ answer (token + principal)
                        ▼
                 resolve → allow | deny
```

## Components and single responsibilities

| Component | Responsibility | Must never |
|---|---|---|
| **Ingest + validator** | Accept the ask contract, validate required fields, canonicalize the action identity, enforce idempotency, reject malformed/oversized payloads | Trust any field as safe for rendering; accept an ask without `action_identity` and `expires_at` |
| **Ask store** | Durable ask records + state machine + delivery/escalation history; survives restart | Lose a pending ask on crash; mutate a resolved ask's decision (append-only transitions) |
| **Scheduler** | Fire pre-expiry warning, escalation, and expiry at absolute UTC instants; recompute on restart | Assume it was running; extend a TTL implicitly |
| **Context packager** | Build the decision card: action, args (redacted/truncated), policy clause, criticality, blast radius, environment/data class, session tail, alternatives | Render agent/tool text as markdown/HTML; include secrets; exceed size budgets |
| **Redactor** | Pattern + shape based scrubbing of secrets/PII before storage, delivery, and audit; emit a receipt | Log the raw value anywhere; silently drop context without saying so |
| **Throttle / flood guard** | Per-agent/environment/project token buckets, duplicate-identity coalescing, digest notifications, auto-deny on flood | Notify per-ask during a flood; silently deny without an event |
| **Delivery router** | Pick channels from config + severity; record every attempt and failure; retry within a bounded budget | Block the ingest path on a slow channel; mark delivered when it failed |
| **Answer verifier** | Verify claim token (hash, expiry, one-time, ask binding), principal authentication, approver authorization, first-answer-wins | Accept an answer without both token and authenticated principal; accept text intent |
| **Escalation engine** | Advance a configured ladder (tier 2 → tier 3), re-issue claims, cancel superseded claims, emit events | Extend TTL; escalate a resolved ask |
| **Audit emitter** | Append-only local log (seq + prev_hash) and agentwatch security events for every transition | Write a secret; rewrite history |
| **CLI / TUI** | `serve`, `ask`, `inbox`, `answer`, `gate`, `doctor`, `export`, `channels` | Approve by default in non-interactive mode |
| **AskBus driver** | Move delivery/escalation/digest **jobs** (in-proc default; filesystem spool at v0.1.0; Redis/NATS later) — movement, never truth | Own authoritative state; answer asks; lose a job silently (E12) |
| **AskStore driver** | Persist asks/claims/transitions/chain (SQLite reference at v0.1.0; memory for tests; Postgres/embedded later) behind the conformance-gated E11 contract | Buffer acked writes; relax single-use claims; reorder the audit seq (E11) |

## Core lifecycle (state machine)

```
                    ┌──────────── expire (TTL) ────────────► expired ──┐
                    │                                                      │
created ──► pending ──► delivered ──► warned ──► escalated(tier 2..n)      │
                    │        │              │                             │
                    │        └──────────────┴──► approved ────────────────┤
                    │                              (allow)                │
                    ├──────────────────────────────► denied (deny) ──────┤
                    ├──────────────────────────────► cancelled ──────────┤
                    └──────────────────────────────► flood-denied ───────┘
                                                       (deny, event)
```

Terminal states: `approved`, `denied`, `expired`, `cancelled`, `flood_denied`. `delivered`, `warned`, and
`escalated` are delivery/escalation sub-states recorded as events, not a replacement for `pending`.

The **decision contract** is agentpolicy's:

| agentinbox terminal state | agentpolicy resolve result | Reason code |
|---|---|---|
| `approved` (bound identity matches) | `allow` | `allow_ask_approved` |
| `denied` | `deny` | `deny_ask_denied` |
| `expired` (no answer by `expires_at`) | `deny` | `human_gate_timeout` |
| `flood_denied` | `deny` | `ask_flood_throttled` (new) |
| unknown ask / identity mismatch | `deny` | `deny_ask_unknown` / `deny_action_identity_mismatch` |
| still pending | `deny` (non-blocking read) | `deny_ask_pending` |

## Interfaces (v0.1.0)

| Interface | Method / command | Notes |
|---|---|---|
| Ingest | `POST /v1/asks` | Idempotency key = `action_identity` + `session_id` within the dedupe window; returns existing ask id when duplicate |
| Read / await | `GET /v1/asks/{id}` · `GET /v1/asks/{id}?wait=25s` | Long-poll bounded (default 25 s) so producers do not busy-loop |
| Answer (channel → core) | `POST /v1/asks/{id}/answer` | Requires `claim` + authenticated principal from the adapter, never a raw client-supplied `approver` string |
| Chat adapter (optional) | `POST /v1/channels/{platform}/interactions` | Verifies the platform signature (Slack `v0` HMAC, Matrix event signatures, Teams callback auth) + timestamp window before parsing |
| CLI ask | `agentinbox ask --file ask.json --channel terminal` | Human-facing; also the integration seam for hooks |
| CLI gate | `agentinbox gate --ask <id> --wait --timeout 300` | CI checkpoint; exit code is the decision (see below) |
| CLI answer | `agentinbox answer <id> --approve \| --deny --reason "…"` | Local approver; principal = OS user + optional `--as` (rejected unless configured) |
| Ops | `agentinbox serve`, `agentinbox doctor`, `agentinbox inbox`, `agentinbox export` | `doctor` checks store, clock, key, channel reachability, schema version |

**Exit codes (reserved, stable):** `0` approved/allow · `2` denied · `3` expired/timeout (deny class) ·
`4` unavailable/fail-closed · `5` still pending (poll again) · `1` usage/internal error. CI treats `2/3/4` as
failure; `5` as retry.

## Delivery modes

| Mode | Shape | When |
|---|---|---|
| **Inline / blocking** | `agentinbox ask` blocks the calling terminal until answer or TTL | Interactive coding agent, local CLI |
| **Local daemon** | `agentinbox serve` owns the store + channels; producers POST and long-poll | Multi-session developer machine, channels connected |
| **CI checkpoint** | `agentinbox gate` blocks a pipeline job; exit code + summary annotation | Headless/CI agents |
| **Deferred / async** | Producer emits ask and continues; harness resumes on a later callback | Frameworks with interrupt/resume (e.g., durable workflow signals) |

All four share the same store and lifecycle; only the caller's wait strategy differs.

## Trust boundaries

| Boundary | Data crossing | Assumption | Control |
|---|---|---|---|
| Producer → ingest | Ask context, agent-supplied strings, args | **Untrusted**: agent/tool output may be attacker-shaped (prompt injection) | Schema validation, size caps, escaping, redaction, "untrusted content" labelling |
| Core → channel | Rendered card | Channel is honest transport, not an authenticator | Channel-specific signing (platform HMACs where chat adapters are configured), no auto-approving links, fingerprint of action shown |
| Channel → core | Answer + principal identity | Adapter authenticates the human; core trusts the adapter's statement only for its channel | Claim token + adapter signature + approver allowlist + first-answer-wins |
| Core → agentwatch / SIEM | Security events | Sink is append-only; may be unavailable | Bounded buffer + durable local log; never block the decision on the sink |
| Approver → audit export | Evidence | Export is read-only | Hash-chained log; export includes `prev_hash` chain and schema version |

**Invariant:** the core never accepts an `approver` or `decision` field that did not come from a channel
adapter that authenticated the principal. A producer calling `POST /v1/asks/{id}/answer` directly is rejected
unless it presents the claim **and** a principal credential configured for that channel.

## Failure semantics (fail-closed, explicit)

| Failure | Behavior |
|---|---|
| Store unavailable / corrupt | Reject new asks (`503`), producers treat as deny at the enforcer; `doctor` exits non-zero; never guess approvals |
| Scheduler down / restart | On start, recompute all due timers from `expires_at` in the store; overdue asks expire immediately; late warnings/escalations fire once, never skipped silently |
| Channel delivery fails | Record the failure, retry with bounded backoff, try the next configured channel; pending ask remains subject to TTL |
| External channel down | Ask stays pending; terminal/CI paths unaffected; expiry still fires; event `delivery-failed` |
| Clock skew / NTP jump | Absolute UTC timestamps; scheduler uses monotonic deltas with a UTC anchor; a backwards jump cannot extend a TTL |
| Duplicate ingest | Same `ask_id` returned; no second notification; recorded as `deduplicated` |
| Duplicate answer (race) | First valid answer wins; later answers recorded as `late-answer` with no state change; responder is told who won and when |
| Sink unavailable | Local audit remains authoritative; events buffered and flushed with a gap marker if the buffer overflows |

## Why local-first, and where a server fits

Local-first makes the solo developer path real (no account, no cloud, no data leaving the machine) and is the
same posture as agentwatch/agentpolicy. The server mode that enterprises need — SSO, SCIM, multi-tenant,
WORM audit, HA — is a **deployment of the same core**, not a fork: the store, claim format, and events are
identical ([PRD 22](22-operations-and-governance.md)).

## Out of scope for this document

Per-subsystem designs (channel SDK, escalation algorithm, flooding math, token format) live under
`docs/design/`; the ADRs that freeze these choices live under `docs/adr/`. This PRD fixes the component
boundaries and the contracts other tools code against.
