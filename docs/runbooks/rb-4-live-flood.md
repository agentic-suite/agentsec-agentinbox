# RB-4 — Live flood

**Symptoms:** one `ask-flood` event, one digest notification, many `flood_denied` asks from one
agent/session; the inbox is quieter, not louder.

**Steps**
1. Read the flood event (`agentinbox export --ask <first_ask_id>` or the event log): note the
   agent/session/environment bucket and `denied_count`.
2. Pause the offending agent at the enforcer (agenthalt). Denials are decisions — do not resurrect them.
3. Confirm legitimate asks from other buckets still work (SC-14).
4. If the threshold is wrong, change `[throttle]`/class overrides in a reviewed PR; the next `report`
   shows the changed rate.
5. Re-run the flood drill pack: `python -m agentinbox.packs` (green expected).

**Verify:** exactly one `ask-flood` event and one digest per window; retries never consume tokens;
the zero-allow counter stays 0.
