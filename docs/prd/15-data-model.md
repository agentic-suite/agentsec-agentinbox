# PRD 15 — Data Model & Lifecycle

**BLUF:** The core entity is the **Ask** — a durable, stateful record that is *the approval object* (D-4), the
same role a ServiceNow approval record plays, but agent-shaped and seconds-fast. Around it: **Transition**
(the append-only history), **Claim** (single-use answer tokens), **Delivery** (per-channel attempts), and the
**AuditChain** (hash-linked entries). Everything joins to the ecosystem on `session_id` / `agent_id` /
`action_identity`, and everything time-bearing is UTC.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Entities

| Entity | Role | Key fields |
|---|---|---|
| **Ask** | The approval object: one proposed action needing a human decision | `ask_id` (server-minted `ask_<16 hex>`; producer ids accepted if fresh), `action_identity`, `tool`, `action`, `arguments` (redacted), `agent_id`, `session_id`, `environment`, `data_class`, `reason_code`, `policy_ref` (rule id + version), `criticality`, `class` (action class → TTL/roster/ladder resolution), `requested_by`, `expires_at`, `warn_at`, `escalate_at`, `tier`, `status`, `created_at` |
| **Transition** | Append-only lifecycle event on an ask | `seq` (per-ask), `from`, `to`, `at` (UTC), `principal?`, `channel?`, `claim_id?`, `reason?`, `detail` (structured, redacted) |
| **Claim** | A single-use answer token for one ask+channel+tier | `claim_id`, `secret_hash`, `ask_id`, `channel`, `tier`, `issued_at`, `expires_at`, `used_at?`, `revoked_at?`, `state` (`issued`/`used`/`revoked`/`expired`) |
| **Delivery** | One delivery attempt on one channel | `delivery_id`, `ask_id`, `channel`, `target` (user/channel/thread), `attempt`, `status` (`delivered`/`failed`), `at`, `error?` |
| **EscalationStep** | One ladder firing | `ask_id`, `tier`, `fired_at`, `targets[]`, `claims_revoked[]` |
| **Approver** (config, not a table) | Channel principal + class roster membership | `channel`, `principal` (e.g., Slack user id), `classes[]`, `self_review` policy |
| **FloodEvent** | Aggregate record of one throttle trip | `flood_id`, `agent_id`, `session_id?`, `window`, `denied_count`, `first_ask_id`, `at` |
| **AuditEntry** | The hash-chained evidence row | `seq`, `prev_hash`, `entry_hash`, `kind` (transition/delivery/flood/…), `ref_id`, `at`, `payload_digest` |
| **SessionSummary** (derived) | The tail context for cards + export | derived from the last N transitions/asks by `session_id` — never stored separately (no drift) |
| **Evidence** (v0.1.x, [PRD 25](25-evidence-and-decision-quality.md)) | One attachment on an ask | `kind`, `title`, `body \| ref`, `digest`, `size`, `trusted` — digest-bound to the ask (E14) |
| **Constraint** (v0.1.x, [PRD 24](24-constrained-approvals-and-effects.md)) | A producer-offered / approver-applied scope limit | `kind`, `params`, `enforcer_ref`; applied constraints ride the answer + resolve |
| **StandingRule** (v0.1.x, [PRD 27](27-governance-identity-extensibility.md)) | An expiring, owned auto-answer policy | `scope`, `owner`, `why`, `expiry`, `recert_at`, `hit_count`, `last_used` — answers carry `authorization.source=human-remembered` |
| **ReviewThread** (v0.1.x, [PRD 28](28-review-loops-and-orchestration.md)) | A clarification/change loop across ask versions | `thread_id`, `entries[]` (request/evidence-revision/note, each with author + digest), links ask v1..vN |
| **Grant** (v0.1.x, [PRD 28](28-review-loops-and-orchestration.md)) | A timeboxed auto-answer artifact (session grant / incident suppression / approval window) | `kind`, `scope`, `ceiling`, `issued_at`, `expires_at`, `hit_count`, `minted_by` — one shape, three kinds, all expiring |
| **Attestation** (v0.2.0, [PRD 29](29-trust-maturity-writeback-performance.md)) | A detached, signed, externally verifiable statement of a decision's facts | `signature`, `chain_segment_proof`, `provenance_tier`, `rationale_hash`, `evidence_digests` — describes, never authorizes (E16) |

## Ask lifecycle (states and legal transitions)

```
created ──► pending ──┬──► approved   (terminal: answer, claim used, principal recorded)
                     ├──► denied    (terminal: answer, principal + reason recorded)
                     ├──► expired   (terminal: TTL elapsed — deny to producer, human_gate_timeout)
                     ├──► cancelled (terminal: producer withdrew / CI job cancelled)
                     └──► flood_denied (terminal: throttle trip — deny to producer, ask_flood_throttled)

pending (delivery/escalation observations, non-state-changing):
   delivered(channel) · warned · escalated(tier k, claims revoked ≤ k-1) · read? (no — we do not track reads)
```

**Rules:**

- Terminal is terminal: the only *append* after terminal is a `late-answer` observation (someone answered a
  resolved ask — recorded, state unchanged, responder informed).
- `approved` carries `approver` principal + channel + claim_id + resolved_at; nothing else may ever carry the
  semantics of "this may proceed".
- Expiry is computed from `expires_at`, never from "last activity".
- **Forward state set (v0.1.x+, gated by [PRD 30 R69](30-correctness-conflict-abuse-hardening.md)):** the graph
  extends additively with `claimed`, `needs_changes`, `revised`, `stale`, `waiting_on_dependency`,
  `auto_answered_by_rule`, `suppressed` — as **one versioned state machine with explicit legal edges**
  ([PRD 30 §2](30-correctness-conflict-abuse-hardening.md)); every non-edge is an `illegal-transition-rejected`
  event, and conflicts between mechanisms resolve through the **precedence lattice**
  ([PRD 30 §1](30-correctness-conflict-abuse-hardening.md)) — deny-shapes outrank allow-shapes, human answers
  outrank convenience rules but lose to freshness/provenance/window/dependency failures.

## JSON — the ask contract (`ask/1.0`)

```json
{
  "contract": "ask/1.0",
  "ask_id": "ask_9f2b7c31a4d0e5f6",
  "action_identity": "sha256:5c1f…",
  "tool": "shell",
  "action": "run_command",
  "arguments": {
    "command": "psql prod -c 'DROP TABLE customers'",
    "timeout_s": 30
  },
  "agent_id": "agent://ops-agent/7f31",
  "session_id": "sess_20261104T030412Z",
  "environment": "production",
  "data_class": "customer-pii",
  "class": "irreversible",
  "reason_code": "human_gate_required",
  "policy_ref": {
    "rule_id": "irreversible-ask-gate",
    "policy_version": "v0.4.2",
    "clause": "permit … advice { human_gate = \"required\" }"
  },
  "criticality": "critical",
  "requested_by": "maya@team",
  "expires_at": "2026-11-04T03:09:12Z",
  "context": {
    "blast_radius": {
      "resource": "db:prod/customers",
      "reversibility": "irreversible",
      "affected_estimate": "unknown"
    },
    "session_tail": [
      {"tool": "read_file", "action": "read", "at": "2026-11-04T03:03:55Z"}
    ],
    "flags": ["code_freeze_window"],
    "alternatives": ["staging database", "request standing approval"]
  },
  "traceparent": "00-4bf9…-01"
}
```

**Field rules:** `arguments`, `context.blast_radius.resource`, `session_tail[*]`, and any `intent`-like string
are **untrusted** (rendered inert, redacted, capped). `reason_code`, `policy_ref`, `criticality`, `class`,
`environment`, `data_class` are **trusted fields**: accepted as-trusted only from authenticated producer
adapters (agentpolicy by default), otherwise displayed **unverified**. `expires_at` is mandatory; producers
cannot set it beyond the class ceiling.

## The decision returned to the producer (`resolve/1.0`)

```json
{
  "contract": "resolve/1.0",
  "ask_id": "ask_9f2b7c31a4d0e5f6",
  "status": "deny",
  "reason_code": "human_gate_timeout",
  "explanation": "no answer before expiry",
  "retryable": false,
  "rescope_hint": "narrow to db:staging/customers, or request a standing approval for class irreversible",
  "answered_by": null,
  "action_identity": "sha256:5c1f…"
}
```

`status` ∈ `allow|deny|pending` at v0.1.0; the forward slate ([PRD 24](24-constrained-approvals-and-effects.md)
R20, [PRD 28](28-review-loops-and-orchestration.md) R48) extends it additively to `allow_with_constraints`,
`allow_with_edits`, `needs_changes` (structured change requests + `review_thread_id`), and a `stale` advice
flag — each carrying its payload (`constraints[]`, `edits[]`, `change_requests[]`, `freshness`), so the agent
can act instead of guess. The
mapping to agentpolicy reason codes is fixed in
[PRD 02 §lifecycle](02-architecture.md) (`allow_ask_approved`, `deny_ask_denied`, `human_gate_timeout`,
`deny_ask_pending`, `deny_ask_unknown`, `deny_action_identity_mismatch`, `ask_flood_throttled`).

## agentwatch events (the ask lifecycle set)

Emitted for every state change, per the schema's additive process (owner: agentwatch; version bump required —
see [PRD 20 §C](20-standards-and-claims.md)):

| Event type | Carries (evidence) |
|---|---|
| `ask-raised` | ask_id, agent_id, session_id, action_identity, class, criticality, expires_at |
| `ask-delivered` / `ask-delivery-failed` | ask_id, channel, attempt |
| `ask-warned` | ask_id, remaining_s |
| `ask-escalated` | ask_id, tier, targets (counts/ids per privacy policy), revoked_claims |
| `ask-answered` | ask_id, outcome (approved/denied), principal, channel, reason? |
| `ask-expired` | ask_id, ttl_s |
| `ask-cancelled` | ask_id, by |
| `ask-flood` | flood_id, agent_id, window, denied_count |
| `answer-rejected` | ask_id, channel, cause (bad_signature/expired_token/unknown_claim/off_roster/identity_mismatch/late/self_review) |

All carry `emitter: "agentinbox"`, `session_id`, `traceparent` when known, and `event_version`.

## Storage layout (v0.1.0)

```
~/.agentinbox/
  inbox.db          # SQLite (WAL) — the reference AskStore driver (pluggable per E11):
                    #   asks, transitions, claims, deliveries, floods, audit chain
  config.toml       # channels, bus/store drivers, classes (TTL/roster/ladder), throttle, key refs
  spool/            # the filesystem AskBus driver (E12): jobs/ (tmp→rename), done/, locks/
  keys/
    claims.key      # HMAC key for claim derivation (0600)
  exports/          # `agentinbox export` output (never auto-written)
```

**Why two homes:** the store holds **truth** (asks, claims, the chain); the spool holds **movement**
(delivery/escalation/digest jobs, at-least-once, idempotently consumed). A crashed or replayed job is
harmless; a replayed truth-write is not — so they are different drivers with different semantics
([PRD 16 §C/§D](16-channel-and-harness-adapters.md), D-13/D-14).

**Indexes:** pending-by-expiry (scheduler scan), asks-by-session, asks-by-agent, transitions-by-ask-seq,
chain-by-seq. **Retention:** resolved asks + transitions retained until the owner prunes (compliance mode
config: never/90d/1y); pruning produces a pruned-chain marker (the chain stays verifiable); **spool jobs are
pruned aggressively** (they are movement, not evidence).

## Integrity model

- Every Transition and FloodEvent appends an **AuditEntry**: `entry_hash = H(prev_hash ‖ seq ‖ kind ‖ ref_id ‖
  at ‖ payload_digest)` where `payload_digest` is the canonical-JSON digest of the transition detail.
- `verify-log` recomputes the chain; a mismatch names the first bad seq. Exported JSONL carries the chain so
  verification works offline.
- `Ask.status` is *derived-on-read* for expiry (past `expires_at` reads as expired) and *recorded-on-transition*
  for answers — crash between "decided" and "recorded" resolves safely to deny on recovery (the decision was
  never delivered, so it can be re-asked; idempotency by `action_identity` prevents double-execution).

## Config sketch

```toml
[classes.irreversible]
ttl_seconds = 300
warn_seconds = 60
self_review = "deny"
require_reason_on_deny = true
ladder = ["tier-1", "on-call"]

[classes."external-send"]
ttl_seconds = 900

[roster.tier-1]
slack = ["U012ABC", "U045DEF"]   # named approvers

[roster."on-call"]
slack = ["#agent-oncall"]         # channel tier (explicitly configured, audited)

[throttle]
per_agent_burst = 20
per_agent_rate_per_min = 10
flood_window_seconds = 30

[channels.desktop]         # P0 — the no-chat remote path (macOS Notification Center / notify-send)
enabled = true

[channels.webhook]         # P0 — display-only reach (recipes: ntfy, Pushover, Discord, email bridges)
enabled = false
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "env:AGENTINBOX_WEBHOOK_HMAC"

[bus]                      # E12 — movement, not truth
driver = "filesystem"      # in-proc | filesystem (v0.1.0); redis/nats arrive with server mode

[store]                    # E11 — truth (conformance-gated)
driver = "sqlite"          # sqlite (reference) | memory; postgres arrives with server mode

[channels.matrix]          # v0.1.x — the second interactive surface (open protocol)
enabled = false

[channels.slack]           # optional community adapter (v0.1.x) — never required for correctness
enabled = false
signing_secret_ref = "env:SLACK_SIGNING_SECRET"

# ---- forward slate (PRDs 24–27; config lands with the features) ----

[quiet_hours]              # R31 — low-tier asks queue silently for the window; irreversible never silences
window = "22:00-08:00"
classes = ["low"]

[incident]                 # R32 — one audited toggle; owner + reason recorded on on/off events
ttl_scale = 0.5           # irreversible 300s -> 150s
deny_only_classes = ["external-send"]

[hooks.on_ask_answered]   # R44 — post-decision, signed, never blocking; failures are events
type = "webhook"
url_ref = "env:AGENTINBOX_HOOK_URL"

[standing_rules]           # R37 — every rule: scope, owner, why, expiry, recert_at (mandatory)
retention_days = 7
recert_days = 30

# ---- review loop & orchestration (PRD 28) ----

[calendars]                 # R58 — local ICS/JSON files; no SaaS dependency
freeze = "calendars/freeze.ics"
maintenance = "calendars/maintenance.ics"

[writeback.github]          # R64 — post-decision, best-effort, idempotent; failures are events
token_ref = "env:GITHUB_TOKEN"
checks = true               # v0.2.0 (pending → completed with ask id)

[drills]                     # R67 — sandboxed; never touches real asks
pack = "builtin"            # spoof, flood, stale, missing-evidence, dual-control, tier-confusion, suppression-escape

# ---- hardening (PRD 30) ----

[limits]                     # R70 — review-loop abuse ceilings (defaults shown)
max_hold_rounds = 2
max_evidence_revisions = 4
max_thread_entries = 20

[deadman]                     # R77 — systemic human-coverage failure: N critical expiries in a window
threshold = 3
window_hours = 24
on_fire = "hook:incident"    # or "agenthalt" — the gate nobody answers is the product's own failure mode

[webui]                       # R76/R35 — loopback-only bind enforced in code; claim doubles as CSRF secret
enabled = false
bind = "127.0.0.1:8377"
```

`doctor --explain` prints the *effective* class resolution for a sample ask — config that resolves to nothing
is an error, not a silent default.
