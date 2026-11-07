# Claims & answer verification design — v0.1.0 (M6)

**BLUF:** An answer is accepted only when **both** hold: a valid single-use claim and an **authenticated
principal from a channel adapter**. The pipeline has six fixed steps; every failure is an `answer-rejected`
event with a distinct internal cause, while the public error stays uniform (no claim-existence oracle).
First valid answer wins by CAS; everything later is a `late-answer` observation.

- **Milestone:** M6 ([WBS Part 4](../../wbs/v0.1.0/wbs-v0.1.0-part4-claims-terminal.md), issues #169–#180)
- **Requirements:** E3, E4 · PRD 18 §pipeline/§claim design/§guessing · PRD 06 T13/T14 · D-3

---

## 1. Claim format & storage

| Property | Value |
|---|---|
| `claim_id` | `cl_<16 hex>` (public handle) |
| secret | 128 bits from the OS CSPRNG (`secrets.token_hex(16)`) |
| stored | `sha256(secret)` only — no offline dictionary exists because the secret is high-entropy |
| binding | `ask_id` + `channel` + tier at issue; the ask's immutable `action_identity` at verify |
| expiry | exactly the ask's `expires_at` (claims never outlive the ask) |
| state | derived: `issued / used / revoked / expired` from timestamps |

Minting returns the secret **once** to the channel adapter. The API never returns it, logs it, or stores it.

## 2. Pipeline (order is the security property)

1. **Ask exists** (unknown → `unknown_ask`).
2. **Channel authenticity** — the adapter must have verified the human. Raw loopback API answers are refused
   (`bad_signature`); T14 is proved by the API test.
3. **Claim validity** — exists, secret matches (constant-time), unexpired, unused, unrevoked. Failures map to
   distinct causes (`unknown_claim`, `bad_secret`, `expired_token`, `used`, `revoked`) but a **uniform public
   cause** `bad_claim`.
4. **Binding** — claim's ask + channel (+ tier when both are set) must match (`identity_mismatch`). The
   `action_identity` is immutable on the ask, so it is verified by construction.
5. **Ask state** — pending only. A terminal ask yields a `late-answer` observation and `late`; state never
   changes.
6. **Authorization** — principal in the class ladder's roster for that channel (`off_roster`); requester
   cannot decide their own ask unless `self_review = allow` (`self_review`); deny on a class with
   `require_reason_on_deny` needs a reason (`reason_required`); approve on an `irreversible` class needs the
   typed action confirmation (`confirmation`).

Then: **first-wins commit** = CAS `pending → approved|denied` (transition carries principal, channel,
claim_id, reason) followed by claim consumption. The loser records `late-answer` with the winner and time and
is told it lost.

## 3. Guessing resistance

- Per-claim attempt counter with a configurable ceiling (default 5 → sixth attempt is `guessing`).
- A burst of bad claims is itself recorded (`answer-rejected[guessing]`), so brute force is noisy.
- Constant-time secret comparison; uniform public error for every credential failure.
- Deadlines bound the attack window: claims expire with the ask.

## 4. Revocation

`revoke_claims(ask_id, at, tier=...)` marks claims revoked; `consume_claim` refuses them. M11 uses this on
tier change (a sleeper tier-1 approval cannot answer after the ladder moved). Revocation is loud: revoked
claims are unusable, not deleted.

## 5. Raw-API guard (T13/T14)

`POST /v1/asks/{id}/answer` exists only to **refuse** raw answers: it always calls the verifier with
`channel_authenticated=False`, returns `403`, and records the attempt. The loopback socket token is
authentication of the *process*, not of a human — it never buys a decision.

## 6. Tests

| File | Covers |
|---|---|
| `tests/answers/test_claims.py` | mint/hash, expiry with ask, single use, tier revocation, reopen |
| `tests/answers/test_pipeline.py` | happy approve/deny, 10-attack matrix, confirm/reason, guessing lockout, race, late |
| `tests/answers/test_api_answer.py` | raw-API forge → 403, no state change; unknown ask; bad decision |
