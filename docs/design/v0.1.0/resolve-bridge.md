# agentpolicy resolve bridge design — v0.1.0 (M17)

**BLUF:** the producer gets a structured outcome in agentpolicy's own reason-code vocabulary. Every terminal
state maps to exactly one frozen code; expiry carries a **rescope hint** and `retryable=false`; flood carries
`retry_after`; a resolve call that presents a different action identity is denied (an approval for X never
releases Y).

- **Milestone:** M17 ([WBS Part 9](../../wbs/v0.1.0/wbs-v0.1.0-part9-events-bridge.md), issues #293–#303)
- **Requirements:** PRD 02 §lifecycle, PRD 15 §resolve/1.0, R3, R7, D-2 · CUJ-4, CUJ-8

---

## 1. Frozen mapping

| Ask state | `status` | `reason_code` | `retryable` | `retry_after` | hint |
|---|---|---|---|---|---|
| pending | `pending` | `deny_ask_pending` | true | — | — |
| approved | `allow` | `allow_ask_approved` | false | — | — |
| denied (human) | `deny` | `deny_ask_denied` | false | — | yes (reason echo) |
| cancelled | `deny` | `deny_ask_denied` | false | — | — |
| expired (stored or derived) | `deny` | `human_gate_timeout` | false | — | yes |
| flood-denied | `deny` | `ask_flood_throttled` | true | `retry_after_s` | — |
| unknown id | `deny` | `deny_ask_unknown` | false | — | — |
| identity mismatch | `deny` | `deny_action_identity_mismatch` | false | — | — |

The codes live in `agentinbox/reasons.py`; `resolve.py` imports them and re-exports the old names. A drift test
asserts the constants equal the frozen set, and the outcome matrix asserts each state's exact code.

## 2. Payload (`resolve/1.0`)

```json
{
  "contract": "resolve/1.0",
  "ask_id": "ask_…",
  "status": "deny",
  "reason_code": "human_gate_timeout",
  "explanation": "no answer before expiry",
  "retryable": false,
  "retry_after": null,
  "answered_by": null,
  "rescope_hint": "narrow the target … (human-authored hint, not policy)",
  "action_identity": "sha256:…"
}
```

`status` is the decision (`allow` / `deny` / `pending`), never the raw lifecycle word. Re-reads are idempotent:
the same ask returns byte-identical payloads.

## 3. Rescope hints

`ClassConfig.rescope_hint` (config) supplies class-specific advice; otherwise a class/environment-aware fallback
is authored ("narrow the target to a narrower target (for example staging), or request a standing approval for
class …"). On a human deny the deny reason is echoed. Hints are:

- capped at 400 characters and control-stripped;
- labelled `(human-authored hint, not policy)` so an agent never mistakes advice for policy;
- advisory only — never executed and never parsed by the inbox.

## 4. `retryable` / `retry_after`

Flood denials use the `flood-denied` transition's `retry_after_s` (falling back to `flood_window_seconds`).
Expiry is never retryable: a new ask with a narrower identity is the correct next step (SC-05).

## 5. Unknown and mismatch

- A vanished id resolves `deny_ask_unknown` (HTTP 404 with the same resolve body).
- A resolve call may present `action_identity`; if it differs from the stored identity the result is
  `deny_action_identity_mismatch` and the stored identity is returned. The ask stays untouched.

## 6. API and long-poll

`GET /v1/asks/{id}?wait=<s>&action_identity=<hash>` returns `resolve/1.0`. The long-poll waits only while the
ask is pending and returns immediately for a mismatch. The CLI `gate` prints the reason code; adapters consume
the same payload.

## 7. Tests

`tests/lifecycle/test_resolve.py` covers the mapping matrix, mismatch, retry semantics, hints, and idempotency.
`tests/ask/test_api.py` covers the resolve body, 404-unknown, mismatch, and idempotent re-reads.
`tests/config/test_hints.py` covers hint validation.
