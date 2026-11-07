# Escalation ladder design — v0.1.0 (M11)

**BLUF:** an unanswered ask moves through a config-driven ladder (`tier-1 → on-call → …`) so a 3 a.m. ask
reaches the person who can decide it. Escalation is **routing only**: it changes who may answer, revokes
prior-tier claims, and re-notifies once per tier. It **never** extends `expires_at`; when the ladder is
exhausted the ask denies at the original deadline (D-11).

- **Milestone:** M11 ([WBS Part 6](../../wbs/v0.1.0/wbs-v0.1.0-part6-ci-escalation.md), issues #227–#237)
- **Requirements:** R4, D-11, E3, E9 · CUJ-5 · SC-11/SC-12

---

## 1. Model

```toml
[classes.irreversible]
ttl_seconds = 600
ladder = ["tier-1", "on-call", "incident-commander"]
ladder_delays = [0, 300, 900]      # absolute offsets from ingest

[roster.tier-1]
terminal = ["alice"]
[roster.on-call]
terminal = ["bob"]
[roster.incident-commander]
terminal = ["carol", "dave"]
```

- `ladder` is ordered and unique; every tier must resolve to a non-empty roster entry.
- `ladder_delays` has one entry per tier, starts at `0`, is strictly increasing, and ends before the TTL.
  Omitted delays spread the ladder over the TTL (`0, ttl/2, …`) — never past it.
- A class with no ladder keeps the pre-M11 behaviour: `tier = null`, no escalation timers.

## 2. Timers

Ingest stores `tier = ladder[0]` and `escalate_at = created_at + delays[1]` (or `null` for a single tier).
The M4 scheduler calls `Escalator.tick()` on every pass; a pending ask whose `escalate_at <= now` advances
exactly once. The new `escalate_at` is `created_at + delays[i+2]`, or `null` at the last tier. The store's
`escalate()` CAS (`pending` + expected tier) makes concurrent schedulers safe: the loser writes nothing.

## 3. The invariant: no deadline extension

`escalate()` updates only `tier` and `escalate_at`. `expires_at` is written once at ingest and never by any
escalation path. The last tier's card renders the remaining TTL; when the ladder is exhausted the ask expires
at the original instant, producing `tiers − 1` `ask-escalated` events and one `expired` transition. SC-12
pins this.

## 4. Claims and authorization

Advancing to tier *k* revokes every claim issued for tiers `< k` in the **same store transaction** as the tier
change. A sleeper tier-1 approval is therefore rejected as `revoked` (recorded as `answer-rejected`), and the
ask stays pending. Authorization is tier-aware: only principals in the **current** tier's roster for the
answering channel may decide. A channel that mints a claim at the current tier still cannot make a prior-tier
principal eligible.

## 5. Rendering and notification

The card's SESSION block gains `tier` and `escalations` (`tier-1 → on-call, …`), alongside the remaining TTL.
The engine publishes one deterministic `renotify:<ask>:<tier>` bus job per tier change; the desktop channel
dedupes by `(ask, tier)`, so each tier pings exactly once and a redelivered job is a no-op.

## 6. Config governance

Ladders, delays, and rosters are policy. Validation happens at load (non-empty tiers, unique, roster entry
present, non-zero delays, inside the TTL). On daemon start, the effective policy digest is compared with
`<home>/logs/config-digest`; a change appends one digested `inbox-config-changed` line (0600) with the previous
digest. `doctor --explain` prints the effective ladder and delays.

## 7. Honest limits

v0.1.0 resolves recipients from static config; schedule lookups, calendars, and on-call rotations are the
forward slate (PRDs 24–30). There is no per-tier message text and no chat platform.

## 8. Tests

`tests/escalation/` covers tier firing, once-per-tier, the no-extension invariant, exhaustion, revocation, the
sleeper-approval rejection, tier-context rendering, notification counts, and config refusals.
