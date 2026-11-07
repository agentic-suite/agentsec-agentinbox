# agentwatch event-set design — v0.1.0 (M16)

**BLUF:** every lifecycle fact is projected from the audit chain into the agentwatch security-event schema,
`event_version 0.2.0`, emitted by `agentinbox` with the shared join keys. Events are **facts** — no inference, no
enrichment, no untrusted text. A downed sink buffers; overflow leaves a gap marker; the decision path never waits
on it.

- **Milestone:** M16 ([WBS Part 9](../../wbs/v0.1.0/wbs-v0.1.0-part9-events-bridge.md), issues #282–#292)
- **Requirements:** R5, E9, E10, E5, N-1 · PRD 20 §A/§B, PRD 15 §events · D-10 · CUJ-10

---

## 1. Types and payloads

| event_type | Required payload | Source |
|---|---|---|
| `ask-raised` | `class`, `criticality`, `expires_at`, `requested_by` | `created` transition |
| `ask-delivered` | `channel`, `attempt` | delivery record |
| `ask-delivery-failed` | `channel`, `attempt`, `error` | delivery record |
| `ask-warned` | `remaining_s` | `warned` transition |
| `ask-escalated` | `tier`, `targets_count`, `revoked_claims` | `ask-escalated` transition |
| `ask-answered` | `outcome`, `principal`, `channel` (+ `reason`) | `answer` transition |
| `ask-expired` | `ttl_s` | `expired` transition |
| `ask-cancelled` | `by` | `cancelled` / `gate-cancelled` transition |
| `ask-flood` | `window`, `denied_count`, `first_ask_id` | flood record |
| `answer-rejected` | `cause` (+ internal `cause_detail`) | `answer-rejected` / `late-answer` |

The schema vocabulary for rejection causes is (`unknown_claim`, `bad_signature`, `expired_claim`, `used_claim`,
`revoked_claim`, `binding_mismatch`, `late`, `off_roster`, `self_review`). The internal cause is preserved in
`cause_detail`, so precision is never lost while the shared vocabulary stays stable.

`ask-delivered` / `ask-delivery-failed` / `ask-flood` have **mirrored transitions** in the chain; the event
projection reads the delivery/flood records (one event per fact), never both.

## 2. Envelope

```json
{
  "event_version": "0.2.0",
  "event_type": "ask-answered",
  "emitter": "agentinbox",
  "event_id": "agentinbox:42",
  "at": "2026-11-08T12:00:00.000000Z",
  "ask_id": "ask_…",
  "session_id": "sess_…",
  "agent_id": "agent://…",
  "action_identity": "sha256:…",
  "traceparent": "00-…-…-01",
  "payload": { "outcome": "approve", "principal": "alice", "channel": "terminal" }
}
```

`event_id` is `<emitter>:<audit seq>` — stable and dedupable. `traceparent` is carried only when the producer
supplied one (W3C Trace Context); it is never synthesized.

## 3. Derivation from evidence

`EventTracer.drain()` reads new audit entries (`seq > last`), maps each to at most one event, writes it to the
buffered sink, and advances. The audit chain remains authoritative; the event stream is a projection that can be
rebuilt at any time. This is why a sink outage cannot lose a decision or change a state.

## 4. Sink and degradation

`BufferedEventSink`:

- tries the inner sink; on failure it appends to a bounded queue (decision unaffected);
- on overflow it drops the **oldest** record and increments `dropped` (never silent);
- on recovery it flushes in order, then writes one `event-gap` marker with the dropped count;
- `serve` drains every second and after each `--once` pass.

`JsonlEventSink` writes `<home>/logs/events.jsonl` mode `0600`, append-only.

## 5. Versioning

The in-repo fixture `agentinbox/events/security-event.schema.json` pins `event_version 0.2.0`, the type enum,
the envelope, and the per-type payload allow-lists. Changes are **additive only** (new optional fields); a
breaking shape fails the fixture. A version bump follows agentwatch's stewardship process, recorded in the
schema's `$id` and this doc — never a silent in-place rewrite.

## 6. No-ML / no-drift guard

Event payloads are built from record fields and trusted codes. `arguments`, `context`, tool output, and any
agent-supplied text are excluded; a test serialises every emitted event and asserts marker secrets and
`arguments`/`context` never appear. There is no inference, scoring, or enrichment.

## 7. Tests

`tests/events/` runs one integration script that produces all ten event types, validates each against the
fixture, checks join keys/`traceparent`, asserts delivery events are not duplicated, and proves no untrusted
text escapes. Sink tests cover down/buffer/flush/overflow/gap and the non-blocking decision path.
