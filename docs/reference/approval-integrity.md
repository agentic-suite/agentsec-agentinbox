# Approval integrity reference (v0.1.0 · M6)

**BLUF:** An approval is a **claim + authenticated principal**, bound to the exact ask and channel, first-wins,
single-use, and expiring with the ask. No free-text approval exists, and no raw API call can answer.

- Design: [`docs/design/v0.1.0/claims.md`](../design/v0.1.0/claims.md)
- Requirements: E3, E4 · PRD 18 · PRD 06 T13/T14

## Claim lifecycle

```python
minted = mint_claim(store, ask, channel="terminal", tier="tier-1", now=now)
# minted.secret goes to the adapter only; only sha256(secret) is stored
```

| State | Meaning |
|---|---|
| `issued` | not used, not revoked, not expired |
| `used` | consumed by the winning answer (single use) |
| `revoked` | invalidated (escalation tier change in M11, governance) |
| `expired` | `expires_at <= now` |

Revocation: `store.revoke_claims(ask_id, at=now, tier="tier-1")` → those claims can never be consumed.

## Pipeline failures (internal cause → public surface)

| Cause | When | Public |
|---|---|---|
| `unknown_ask` | no such ask | 404 at the API layer |
| `bad_signature` | channel did not authenticate | 403 |
| `unknown_claim` / `bad_secret` / `expired_token` / `used` / `revoked` | claim invalid | `bad_claim` (uniform) |
| `guessing` | attempt ceiling exceeded | `bad_claim` |
| `identity_mismatch` | claim bound to another ask/channel/tier | `identity_mismatch` |
| `late` | ask already resolved | `late` (with winner/time) |
| `off_roster` | principal not authorized | `off_roster` |
| `self_review` | requester deciding own ask | `self_review` |
| `reason_required` | deny without a reason where required | `reason_required` |
| `confirmation` | irreversible approve without typed confirmation | `confirmation` |

Every failure appends an `answer-rejected` transition with the internal cause; the public message stays
uniform for credential failures so callers cannot probe claim existence.

## Rules

- **Both** a valid claim **and** an authenticated principal are required; either alone is refused.
- First valid answer wins (CAS); later answers are `late-answer` observations — the decision never changes.
- Claims expire with the ask; a claim cannot outlive its decision window.
- Approve on an `irreversible` class requires typing the action name (`run_command` in the fixtures).
- Deny on a class with `require_reason_on_deny` requires a non-empty reason.
- Raw `POST /v1/asks/{id}/answer` always returns 403: answers come from channel adapters (terminal, M7).
