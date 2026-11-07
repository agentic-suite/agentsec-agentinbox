# Ask contract design — v0.1.0 (M2)

**BLUF:** One versioned JSON document (`ask/1.0`) is the front door. It is validated strictly, its
**action identity is verified** (not trusted), its agent-supplied text is **redacted before anything is
persisted**, and its trusted fields are marked **unverified unless the producer is authenticated**.
Ingest is idempotent by `action_identity` + `session_id`; malformed asks are rejected with the failing field
named and **nothing partial is stored**.

- **Milestone:** M2 ([WBS Part 2](../../wbs/v0.1.0/wbs-v0.1.0-part2-contract-lifecycle.md), issues #124–#135)
- **Requirements:** E1, E6, T13 · PRD 15 §contract · PRD 18 §trust · PRD 06 §T13
- **Out of scope:** lifecycle/state machine (M3), scheduler (M4), cards (M5), claims/answers (M6). M2 stops at
  "a validated, redacted, classified ask is durably stored and readable".

---

## 1. Pipeline (order is the security property)

```
raw JSON ─► schema + type validation ─► size caps ─► identity verification (raw args)
        ─► expiry/ceiling check ─► redaction (receipts) ─► trust classification
        ─► AskRecord(payload=redacted + _trust + _redactions) ─► AskStore.create_or_get_by_identity
```

1. **Validate** the contract shape and types. Failure → `400` naming `field`.
2. **Caps** per field and total (256 KiB). Failure → `400` naming the field.
3. **Verify identity**: recompute the canonical hash from the **raw** `tool` + `action` + `arguments` and
   require it to equal the supplied `action_identity` (I-2). A mismatch is rejected — the server does not
   "fix" it.
4. **Expiry**: `expires_at` is mandatory, must be in the future, and may not exceed `now + class.ttl_seconds`.
5. **Redact** every string value (arguments, context, and any extra field). Receipts record
   `{field, class, count}`; raw values are never written anywhere.
6. **Classify** trusted fields (§4).
7. **Store** the redacted payload through the AskStore (idempotent; dedupe inside the window).

Identity is verified against the **raw** arguments and then those raw arguments are discarded. That is why
the stored payload carries the verified `action_identity` while its `arguments` are redacted: the binding is
to what the producer asked to do, not to what we chose to keep.

## 2. Schema (`ask/1.0`)

The shipped truth is [`agentinbox/contract/ask-1.0.schema.json`](../../../agentinbox/contract/ask-1.0.schema.json)
(JSON Schema 2020-12). Model and schema are kept in lock-step by a test.

| Field | Type | Rule |
|---|---|---|
| `contract` | string | exactly `ask/1.0` |
| `ask_id` | string | optional; producer ids accepted only if fresh and shaped `ask_<16 hex>`; otherwise server mints one |
| `action_identity` | string | `sha256:<64 hex>`; must equal the canonical hash of `tool`+`action`+`arguments` |
| `tool`, `action` | string | required, non-empty, ≤ 256 chars |
| `arguments` | object | required; untrusted; ≤ 64 KiB canonical |
| `agent_id`, `session_id` | string | required, non-empty (ecosystem join keys) |
| `environment`, `data_class` | string | required; trusted-class fields |
| `class` | string | required; must resolve in config |
| `reason_code` | string | required; trusted-class field |
| `policy_ref` | object | required; `rule_id`, `policy_version` required, `clause` optional; trusted-class |
| `criticality` | string | required (`low`/`medium`/`high`/`critical`? — v0.1.0 accepts free text ≤ 64, rendered as data) |
| `requested_by` | string | required, non-empty |
| `expires_at` | string | required, RFC 3339 UTC (`...Z`), future, ≤ class ceiling |
| `context` | object | required (may be `{}`); untrusted; ≤ 64 KiB canonical |
| `traceparent` | string | optional, ≤ 128 chars |

**Unknown fields are tolerated and preserved** (E18 posture): stored under the payload's `extra` so later
contract versions can carry additional context without breaking v0.1.0. They are still redacted and capped.

## 3. Size caps

| Scope | Cap |
|---|---|
| total canonical payload | 256 KiB (262 144 bytes) |
| single string field | 4 KiB |
| `arguments` / `context` canonical | 64 KiB each |
| `policy_ref.clause` | 8 KiB |

Caps are enforced **before** redaction so a hostile payload cannot force a large regex pass. Rejection names
the offending field.

## 4. Trusted vs untrusted (T13)

| Fields | Source | If producer is **not** authenticated |
|---|---|---|
| `reason_code`, `policy_ref`, `criticality`, `class`, `environment`, `data_class`, `requested_by` | trusted-class | rendered/flagged **unverified** |
| `arguments`, `context.*`, `traceparent`, any extra string | agent-supplied | always **untrusted** |
| `tool`, `action`, `agent_id`, `session_id`, `expires_at`, `action_identity` | protocol facts | not "trusted policy", but not agent-influenceable |

`requested_by` is the self-review anchor: an authenticated adapter's value is trusted, an unsigned producer's
value is unverified (so `self_review=deny` is best-effort for unsigned producers).

The stored payload carries:

```json
"_trust": {"trusted": ["class", "criticality"], "unverified": ["policy_ref", "reason_code"]},
"_redactions": [{"field": "context.blast_radius.resource", "class": "EMAIL", "count": 1}]
```

A producer cannot self-assert trust: `ProducerIdentity(authenticated=False)` marks every trusted-class field
unverified regardless of the request body. Only an adapter that verified the producer key (agentpolicy in
v0.1.0, M18) sets `authenticated=True`.

## 5. Identity canonicalization

```python
action_identity = "sha256:" + sha256(canonical_json({
    "tool": tool, "action": action, "arguments": arguments
})).hexdigest()
```

`canonical_json` = UTF-8, object keys sorted, separators `(",", ":")`, no ASCII escaping
(`agentinbox.store.canonical_json`). One form, one hash, everywhere.

## 6. Ingest API (loopback)

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/v1/asks` | `201` created · `200` duplicate (same ask id) · `400` named field · `401` missing/bad token · `413` over total cap · `503` store unavailable |
| `GET` | `/v1/asks/{id}` | `200` status snapshot · `404` unknown |
| `GET` | `/v1/asks/{id}?wait=25s` | bounded long-poll (≤ 30 s) — returns as soon as the ask leaves `pending` |

Auth: a per-process socket token (`Authorization: Bearer <token>` or `X-AgentInbox-Token`), compared in
constant time. Bind is loopback-only. The API records the remote address; **peer uid is not exposed on
loopback TCP**, so M2 records what it can and does not pretend to have credentials it lacks. The producer
identity used for trust is the adapter's, not a header the caller can spoof.

Long-poll: the server keeps per-ask `threading.Event`s. Ingest signals the event; M3/M6 signal it on resolve.
A waiter also stops at its deadline, so a lost signal degrades to a bounded poll, never a hang.

## 7. Error shape

```json
{"error": {"field": "expires_at", "message": "must be in the future"}}
```

Field names are stable (`arguments`, `context`, `policy_ref.rule_id`, …) so producers can fix payloads and
tests can assert the failing field.

## 8. Tests

| File | Covers |
|---|---|
| `tests/ask/test_contract.py` | schema/model lock-step, round-trip, unknown-field preservation |
| `tests/ask/test_validation.py` | required fields, types, caps, expiry ceiling |
| `tests/ask/test_identity.py` | canonical hash, 3× retry → one ask (SC-06) |
| `tests/ask/test_redaction.py` | seeded secrets/PII → 0 raw occurrences, receipts present |
| `tests/ask/test_trust.py` | authenticated vs unauthenticated trust flags |
| `tests/ask/test_api.py` | token auth, 201/200/400/404/413/503, long-poll timeout + wake |
