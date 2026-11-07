# agentwatch events reference (v0.1.0 · M16)

**BLUF:** the inbox emits the agentwatch security-event set (`event_version 0.2.0`) from its audit chain. Events
are facts with shared join keys; a downed sink buffers and marks gaps.

- Design of record: [`docs/design/v0.1.0/events.md`](../design/v0.1.0/events.md)
- Schema fixture: [`agentinbox/events/security-event.schema.json`](../../agentinbox/events/security-event.schema.json)

## Where they go

`agentinbox serve` drains new audit entries every second (and after `--once`) to
`<home>/logs/events.jsonl` (mode `0600`). The tracer is a projection of the audit chain; the chain remains
authoritative. Its delivered cursor lives in `<home>/logs/events.seq`, so a normal restart does not replay the
whole chain. If the sink is down the cursor stays behind and buffered facts are replayed (at-least-once, stable
`event_id = agentinbox:<audit seq>`) rather than lost.

## Envelope

| Field | Value |
|---|---|
| `event_version` | `0.2.0` |
| `event_type` | one of the ten types below |
| `emitter` | `agentinbox` |
| `event_id` | `agentinbox:<audit seq>` |
| `at` | UTC ISO-8601 from the audit entry |
| `ask_id`, `session_id`, `agent_id`, `action_identity` | join keys |
| `traceparent` | carried when the producer supplied one |
| `payload` | per-type evidence |

## Types

| Type | Payload |
|---|---|
| `ask-raised` | `class`, `criticality`, `expires_at`, `requested_by` |
| `ask-delivered` | `channel`, `attempt` |
| `ask-delivery-failed` | `channel`, `attempt`, `error` |
| `ask-warned` | `remaining_s` |
| `ask-escalated` | `tier`, `targets_count`, `revoked_claims` |
| `ask-answered` | `outcome`, `principal`, `channel`, `reason?` |
| `ask-expired` | `ttl_s` |
| `ask-cancelled` | `by` |
| `ask-flood` | `window`, `denied_count`, `first_ask_id` |
| `answer-rejected` | `cause`, `cause_detail` |

Rejection causes: `unknown_claim`, `bad_signature`, `expired_claim`, `used_claim`, `revoked_claim`,
`binding_mismatch`, `late`, `off_roster`, `self_review`.

## Joins

An agentwatch record joins the agentpolicy decision and the inbox ask on `ask_id` + `action_identity`, and the
whole run on `session_id` + `traceparent`. The inbox never re-writes a legacy record shape.

## Sink degradation

| Situation | Behaviour |
|---|---|
| sink up | one JSONL line per event |
| sink down | bounded in-memory buffer; decisions unaffected |
| buffer overflow | oldest records dropped and counted |
| recovery | buffer flushed in order, then one `event-gap` marker with `dropped` |

The decision path never waits on the sink, and the audit chain is unaffected either way.

## Versioning

Additive only: new optional fields, a documented `event_version` bump, and schema fixtures. A breaking shape
fails the fixture; never write back legacy shapes.
