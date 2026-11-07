# Flood guard design — v0.1.0 (M12)

**BLUF:** flood protection is a **decision**, not a suppression (D-12). Duplicate coalescing runs first; then
per-key token buckets; then an over-threshold ask is auto-denied with `ask_flood_throttled`, the window records
**one** `ask-flood` event and publishes **one** digest job. The inbox gets quieter under attack while
pre-flood pendings stay answerable and a legitimate 20-action migration survives (R7, SC-13/SC-14).

- **Milestone:** M12 ([WBS Part 7](../../wbs/v0.1.0/wbs-v0.1.0-part7-flood-webhook.md), issues #238–#248)
- **Requirements:** R7, D-12, E1, E12 · PRD 06 T5 · CUJ-6

---

## 1. Order of defenses

1. **Duplicate coalescing** (M2): the same `action_identity` + `session_id` inside the dedupe window returns
   the existing ask (`created=False`). Retries never consume tokens, never re-notify, never add a deny.
2. **Token buckets** (this milestone): one bucket per key.
3. **Auto-deny**: the ask is created, then `pending → flood_denied` with kind `flood-denied`, reason
   `ask_flood_throttled`, and `detail.retry_after_s`. The producer learns a deny, not a timeout.
4. **Aggregation**: one `ask-flood` event per window and one rolling digest job.

## 2. Keys and limits

Bucket key = `agent_id | session_id | environment | producer-uid`, where producer-uid is the authenticated
principal (or the loopback remote address when the producer is unauthenticated). This stops a single agent from
laundering a flood through sessions or environments.

| Limit | Source | Default |
|---|---|---|
| burst (tokens) | `[throttle].per_agent_burst`, overridable per class | `20` |
| refill | `[throttle].per_agent_rate_per_min` | `10`/min |
| window | `[throttle].flood_window_seconds` | `30` |

A class may set `flood_burst` / `flood_rate_per_min` (validated positive at load). A 20-action migration with
distinct action identities fits exactly in the default burst; the 21st action is denied. This is the
SC-13/SC-14 discriminator: behaviour, not volume.

## 3. One event, one digest

A trip opens a window (`window_start = first denial`, `window_end = start + window`). The window record is
`flood_<digest>`, upserted with the running `denied_count`. The **creating** call appends the single
`ask-flood` event (window bounds, count, first ask id, offending agent/session, bucket key) to the first denied
ask (while it is still pending). Every denial calls `publish_digest()`, which upserts the deterministic
`digest:<window_start>` job with the rolling count — so 200 denials produce one digest job, not 200.

The digest is delivered once by the bus/desktop (M8/M9). Individual flood-denied asks never notify.

## 4. Deny semantics

- `resolve` returns `status=deny`, `reason_code=ask_flood_throttled`, `retryable=true`; the explanation tells the
  producer to retry after the flood window.
- The flood-denied ask is terminal: an answer attempt is a late-answer rejection, never a resurrection. The
  guard exposes `resurrections` and it stays `0`.
- Pre-flood pending asks are untouched and answerable; their TTL is unchanged.

## 5. Config governance

Thresholds are security-relevant policy. They are validated at load, shown by `doctor --explain`, and covered by
the digested `inbox-config-changed` evidence (M11). A typo cannot silently disable the guard: unknown keys are
errors, and non-positive values refuse.

## 6. Runtime counters

The guard keeps in-memory buckets and windows (restart resets the counters; the store keeps the flood records
and evidence). `resurrections` is the release-gate counter that proves the flood path never undoes a denial.

## 7. Tests

`tests/flood/` covers coalescing, bucket capacity/refill/isolation, class overrides, 20-vs-21 burst, the
200-ask pack (180 denies, 1 event, 1 digest), retryable-after-window, no resurrection, and the legitimate
migration.
