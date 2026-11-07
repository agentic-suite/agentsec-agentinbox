# RB-1 — External-channel outage

**Symptoms:** `ask-delivery-failed` events or delivery records with a growing attempt count; asks stay
pending; terminal/CI still show the card.

**Steps**
1. `agentinbox channels` — the unhealthy channel is named with the failing reference.
2. `agentinbox doctor` — `keys` red means the reference cannot resolve; `desktop` red means a headless
   session; `offline` warns when an external channel is enabled.
3. Keep the ask **pending**; do not answer for someone else. Terminal/CI answers still work and record
   normally.
4. Fix the reference (`env:`/`file:`) or the receiver, then let the delivery retry (bounded) or send
   a fresh notification; the ask's `expires_at` is unchanged.
5. For a planned outage, set the channel `enabled = false` and reload; TTL still denies.

**Verify:** `agentinbox doctor` green; a new ask shows `ask-delivered` on the channel; `verify-log`
passes. `ask-delivery-failed` never changes status or TTL.
