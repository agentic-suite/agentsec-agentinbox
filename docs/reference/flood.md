# Flood protection reference (v0.1.0 · M12)

**BLUF:** duplicate coalescing first, then per-key token buckets, then a **decision**: over-threshold asks are
denied with `ask_flood_throttled`. One window produces one `ask-flood` event and one digest job.

- Design of record: [`docs/design/v0.1.0/flood.md`](../design/v0.1.0/flood.md)

## Configuration

```toml
[throttle]
per_agent_burst = 20
per_agent_rate_per_min = 10
flood_window_seconds = 30

[classes.irreversible]
ttl_seconds = 300
flood_burst = 20            # optional per-class override
flood_rate_per_min = 10     # optional per-class override
```

Non-positive thresholds and unknown keys refuse at load. `doctor --explain` prints the effective values.

## Key

```text
agent_id | session_id | environment | producer-uid
```

`producer-uid` is the authenticated principal; for unauthenticated producers it is the loopback remote address.

## Behaviour

| Situation | Result |
|---|---|
| retry of the same ask inside the dedupe window | the existing ask; no token, no notification |
| first 20 distinct actions in a burst | pending and answerable |
| 21st action in the window | created then `flood_denied`/`ask_flood_throttled` |
| 200-ask pack | 180 denies, **one** `ask-flood` event, **one** digest job |
| pre-flood pending ask | untouched, answerable, original TTL |
| answer after flood denial | late-answer rejection; status never changes |

## Producer semantics

`resolve` returns:

```json
{
  "status": "deny",
  "reason_code": "ask_flood_throttled",
  "retryable": true,
  "explanation": "denied by flood protection; retry after the flood window"
}
```

The retry window is `flood_window_seconds`; the denied ask's `flood-denied` transition carries
`detail.retry_after_s`.

## Evidence

- one `ask-flood` event per window (window bounds, count, first ask id, agent/session, bucket key);
- one `flood_<digest>` record with the running denied count;
- one digest bus job (`digest:<window-start>`) with the rolling count;
- `flood-denied` transition per denied ask.

## Honest limits

Buckets are in-process (a restart resets the counters); the flood records and events are durable. Thresholds are
static config in v0.1.0 — adaptive/behavioral tuning is the forward slate.

**Burst vs pack:** a new key starts with `per_agent_burst` tokens, so the first `burst` asks are allowed and the
rest of a pack are denied. With the defaults (burst 20, 200 asks in 30 s) the pack yields **180 denies plus the
20-ask burst capacity**, one event, and one digest. This is deliberate: the same mechanism must keep a legitimate
20-action migration answerable (SC-14). A literal "200 asks → 200 denies" would deny the legitimate burst too;
the SC-13 verdict is therefore "N denies, one event, one digest, and no more than the burst capacity reaches the
approver".
