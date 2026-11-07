# Escalation reference (v0.1.0 · M11)

**BLUF:** unanswered asks move through a configured tier ladder. A tier change is routing: it changes who may
answer and revokes prior-tier claims. It never extends `expires_at`.

- Design of record: [`docs/design/v0.1.0/escalation.md`](../design/v0.1.0/escalation.md)
- Config: [`config.md`](config.md) (`ladder`, `ladder_delays`, `[roster.<tier>]`)

```toml
[classes.irreversible]
ttl_seconds = 600
ladder = ["tier-1", "on-call"]
ladder_delays = [0, 300]

[roster.tier-1]
terminal = ["alice"]

[roster.on-call]
terminal = ["bob"]
```

## Rules

| Rule | Behaviour |
|---|---|
| timers | tier advances when `escalate_at` arrives; the M4 scheduler fires it |
| no extension | `expires_at` is immutable after ingest |
| exhaustion | the last tier denies at the original deadline |
| claim revocation | every prior-tier claim is revoked atomically with the tier change |
| authorization | only the **current** tier's roster may answer |
| notification | one re-notify job/notification per tier; redelivery is a no-op |
| validation | unique tiers, a non-empty roster entry per tier, increasing delays inside the TTL |

## Events

`ask-escalated` carries `from_tier`, `to_tier`, `recipients`, and `remaining_s`. A sleeper approval is recorded
as `answer-rejected` with cause `revoked`.

## Configuration governance

Policy changes are reviewed like code. On daemon start the effective policy digest is compared with
`<home>/logs/config-digest`; a change appends one `inbox-config-changed` line to
`<home>/logs/inbox-config-changed.jsonl`. `doctor --explain` prints `ladder` and `ladder_delays`.

## Limits

Recipients are static config in v0.1.0. Calendars, rotations, and schedule lookups are the forward slate.
