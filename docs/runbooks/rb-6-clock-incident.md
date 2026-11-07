# RB-6 — Clock incident

**Symptoms:** signature failures, `doctor` `clock-skew` warning, or approvals that appear to expire early.

**Steps**
1. Fix NTP/time sync on the box.
2. `agentinbox doctor` — `clock-skew` warns when evidence is ahead of the wall clock; the scheduler
   clamps backwards jumps so a TTL can only shrink, never extend.
3. Re-read the affected asks: expiry is derived from persisted absolute instants; a late answer is a
   visible no-op.
4. Re-run the relevant scenario fixture (SC-10) if the cause is unclear.

**Verify:** `doctor` clock/clock-skew green; no ask was approved after expiry; `verify-log` passes.
