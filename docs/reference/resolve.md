# `resolve/1.0` reference (v0.1.0 · M17)

**BLUF:** the producer-facing outcome in agentpolicy's vocabulary, with retry and rescope semantics.

- Design of record: [`docs/design/v0.1.0/resolve-bridge.md`](../design/v0.1.0/resolve-bridge.md)

```http
GET /v1/asks/{ask_id}?wait=30&action_identity=sha256:…
```

```json
{
  "contract": "resolve/1.0",
  "ask_id": "ask_…",
  "status": "deny",
  "reason_code": "human_gate_timeout",
  "explanation": "no answer before expiry",
  "retryable": false,
  "retry_after": null,
  "answered_by": null,
  "rescope_hint": "narrow the target … (human-authored hint, not policy)",
  "action_identity": "sha256:…"
}
```

## Codes

| State | status | reason_code | retryable | retry_after |
|---|---|---|---|---|
| pending | `pending` | `deny_ask_pending` | true | — |
| approved | `allow` | `allow_ask_approved` | false | — |
| denied | `deny` | `deny_ask_denied` | false | — |
| cancelled | `deny` | `deny_ask_denied` | false | — |
| expired | `deny` | `human_gate_timeout` | false | — |
| flood-denied | `deny` | `ask_flood_throttled` | true | seconds |
| unknown id | `deny` | `deny_ask_unknown` | false | — |
| identity mismatch | `deny` | `deny_action_identity_mismatch` | false | — |

## Agent behaviour

- `allow` → proceed, exactly once.
- `deny` + `human_gate_timeout` → do not retry the same action; use `rescope_hint` to build a narrower ask.
- `deny` + `ask_flood_throttled` → wait `retry_after` seconds, then re-ask (the bucket refills).
- `deny` + `deny_ask_denied` → respect the human's reason; do not auto-retry.
- `deny` + `deny_action_identity_mismatch` → the id does not authorize this action; do not retry with the same id.
- `pending` → poll again (the long-poll already waited).

## Rescope hints

Advisory text only, capped at 400 characters, control-stripped, and labelled
`(human-authored hint, not policy)`. It echoes the deny reason when there is one. Never execute it; use it to
shape the next ask.

## Idempotency

Re-reading the same ask returns byte-identical payloads. The long-poll waits only while pending.
