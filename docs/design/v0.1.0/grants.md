# Repeated-ask compression & bounded grants design — v0.1.0 (M30)

**BLUF:** repetition should cost attention once, not N times — but only via **bounded, audited,
revocable** windows. Compression is a view; grants never silently allow past their ceiling, expiry,
rate, or revocation.

- **Milestone:** M30 (WBS Part 16, issues #353–#364) · **Requirements:** PRD 36 R108–R114, SC-83..86
- **Module:** `agentinbox/grants.py` · **Tests:** `tests/grants/`

## 1. Compression (R108/R112)

`compress(store, ask)` groups asks by canonical `{class, tool, action, arguments}` (minus an explicit
ignore list) within a 300 s window. `Compression.render()` prints `COMPRESSED xN` and every row; each
ask keeps its own record, claim, status, and audit rows. There is no group decision. Exports still
contain every ask and the chain is untouched.

## 2. Windows and session grants (R109/R110)

`issue_grant` requires scope (`class`/`session`), class, owner, reason, issuer, TTL, `max_uses`, and
`max_per_minute`; session grants also require `session_id` and at most one active per session. Issuing
writes a chained `grant-issued` event.

`consume_grant` (called at ingest) covers a matching ask when the grant is active, under both ceilings,
and rate-eligible: it writes `grant-used` and transitions the ask to approved with
`authorization.source=window-grant` and a burn-down snapshot. No grant → normal per-ask approval. A
mid-burst expiry/revocation/ceiling reverts the next ask to pending; there is no silent allow.

## 3. Burn-down (R111)

`grant_for_card` returns the covering grant (or the spent/revoked grant whose window contained the ask)
with `uses/max_uses`, `remaining_s`, owner, issuer, and status. The card renders a `GRANT` block;
`doctor` reports active grants.

## 4. Revocation and session end (R110/R114)

`revoke_grant` (reason required) and `end_session` write chained `grant-revoked`/`grant-expired` events;
the next covered ask is per-ask. `expire_due_grants` records time expiry once.

## 5. Repeated denies (R113)

`repeated_denials` groups stored human denies by the same canonical intent and returns items at or above
the threshold (default 5). It only reports — nothing auto-approves or auto-hardens; a class can be
hardened separately by config.

## 6. Tests

`tests/grants/test_grants.py`: ceilings and rate, expiry/revocation/session-end reverts, one active
session grant, burn-down card rendering (including spent), 12-ask compression with every row, repeated
denials as an insight only, and invalid-grant refusal.
