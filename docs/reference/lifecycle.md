# Lifecycle reference (v0.1.0 · M3)

**BLUF:** Four entities and one edge table. `Ask` is the durable object, `Transition` is append-only history,
`Claim` and `Delivery` complete the audit join, and `resolve/1.0` maps state to allow/deny/pending. Terminal is
terminal; expiry is derived on read; nothing outside `agentinbox.lifecycle` writes a status.

- Design: [`docs/design/v0.1.0/lifecycle.md`](../design/v0.1.0/lifecycle.md)
- Requirements: PRD 15 §entities/§lifecycle · PRD 02 §lifecycle · D-4

## States

| State | Terminal | Meaning |
|---|---|---|
| `pending` | no | waiting for a human |
| `approved` | yes | authenticated answer + claim; only state that allows |
| `denied` | yes | authenticated answer |
| `expired` | yes | TTL elapsed → deny (`human_gate_timeout`) |
| `cancelled` | yes | producer withdrew |
| `flood_denied` | yes | throttle trip → deny (`ask_flood_throttled`) |

Legal edges: `pending → {approved, denied, expired, cancelled, flood_denied}`. Every other edge raises
`IllegalTransition`, and the attempt itself is recorded as an `illegal-transition-rejected` observation
(state unchanged). Post-terminal, the only allowed append is `late-answer` — it records the responder and
changes nothing.

```python
from agentinbox.lifecycle import transition, observe
from agentinbox.store import AskStatus

transition(store, ask_id, AskStatus.APPROVED, kind="answer", at=now,
           principal="alice", channel="terminal", claim_id=claim_id)
observe(store, ask_id, kind="late-answer", at=now, principal="mallory")
```

## Entities

| Entity | Where | Notes |
|---|---|---|
| `Ask` | `asks` + redacted `payload` | scheduling fields `warn_at`, `escalate_at`, `tier` are columns |
| `Transition` | `transitions` per-ask `seq` + audit chain | append-only; no update/delete API exists |
| `Claim` | `claims` | hash only; `state(at)` → issued/used/revoked/expired |
| `Delivery` | `deliveries` | `record_delivery` / `list_deliveries`, one row per attempt |

Descriptive fields (`tool`, `action`, `policy_ref`, `class`, …) live in the already-redacted payload. They are
never copied into an unredacted column.

## `resolve/1.0`

```json
{
  "contract": "resolve/1.0",
  "ask_id": "ask_9f2b7c31a4d0e5f6",
  "status": "deny",
  "reason_code": "human_gate_timeout",
  "explanation": "no answer before expiry",
  "retryable": false,
  "answered_by": null,
  "rescope_hint": "narrow the target, or request a standing approval for class irreversible (timeout is a deny, not a failure)",
  "action_identity": "sha256:..."
}
```

| Stored | At `now` | status | reason_code | retryable |
|---|---|---|---|---|
| pending, not due | pending | `pending` | `deny_ask_pending` | true |
| pending, overdue | **expired (derived)** | `deny` | `human_gate_timeout` | false |
| approved | approved | `allow` | `allow_ask_approved` | false |
| denied | denied | `deny` | `deny_ask_denied` | false |
| expired | expired | `deny` | `human_gate_timeout` | false |
| cancelled | cancelled | `deny` | `deny_ask_denied` | false |
| flood_denied | flood_denied | `deny` | `ask_flood_throttled` | false |
| unknown | — | `deny` | `deny_ask_unknown` | false |

A read never writes. A derived expiry is the scheduler's job to record exactly once (M4), so a crash between
"derived" and "recorded" simply derives again.
