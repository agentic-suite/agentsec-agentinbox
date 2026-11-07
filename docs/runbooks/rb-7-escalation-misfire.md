# RB-7 — Escalation ladder misfire

**Symptoms:** an ask did not reach the next tier, escalated too early, or a prior-tier claim still works.

**Steps**
1. `agentinbox doctor --explain` — check `ladder`, delays, and roster per tier (no zero delay, every
   tier has a roster).
2. Inspect the ask's transitions: `ask-escalated` records the tier, recipients, and revoked claims.
3. If a claim from a prior tier was used after escalation, it should have been revoked; treat a success
   as a security finding and preserve evidence (`export`), then fix.
4. Change the ladder only in a reviewed config PR; reload keeps `expires_at` immutable.

**Verify:** re-run the escalation drill (SC-11/SC-12): the configured tier is reached in the window,
prior-tier claims are revoked, and exhaustion denies with an unchanged TTL.
