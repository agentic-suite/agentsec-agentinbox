# Ask contract & ingest reference (v0.1.0 · M2)

**BLUF:** Producers submit one JSON document, `ask/1.0`, to `POST /v1/asks` (loopback + token). It is
validated, capped, identity-verified, redacted, classified, and stored idempotently. Malformed asks are
rejected with the failing field named and nothing stored. Agent-supplied text is redacted before it is
persisted.

- Design: [`docs/design/v0.1.0/ask-contract.md`](../design/v0.1.0/ask-contract.md)
- Shipped schema: [`agentinbox/contract/ask-1.0.schema.json`](../../agentinbox/contract/ask-1.0.schema.json)
- Requirements: E1, E6 · PRD 15 §contract · PRD 18 §trust

## Minimal ask

```json
{
  "contract": "ask/1.0",
  "action_identity": "sha256:<64 hex>",
  "tool": "shell",
  "action": "run_command",
  "arguments": {"command": "psql prod -c 'DROP TABLE customers'"},
  "agent_id": "agent://ops-agent/7f31",
  "session_id": "sess_20261106T030412Z",
  "environment": "production",
  "data_class": "customer-pii",
  "class": "irreversible",
  "reason_code": "human_gate_required",
  "policy_ref": {"rule_id": "irreversible-ask-gate", "policy_version": "v0.4.2"},
  "criticality": "critical",
  "requested_by": "maya@team",
  "expires_at": "2026-11-06T12:05:00.000000Z",
  "context": {}
}
```

`action_identity` is **not** a free label. Compute it as:

```python
"sha256:" + sha256(canonical_json({
    "tool": tool, "action": action, "arguments": arguments
})).hexdigest()
```

canonical JSON = sorted keys, `(",", ":")` separators, UTF-8, no ASCII escaping. The server recomputes and
rejects a mismatch (`action_identity`) — it never "fixes" the identity.

## Required fields

`contract` · `action_identity` · `tool` · `action` · `arguments` · `agent_id` · `session_id` ·
`environment` · `data_class` · `class` · `reason_code` · `policy_ref` (`rule_id`, `policy_version`) ·
`criticality` · `requested_by` · `expires_at` · `context`.

Optional: `ask_id` (`ask_<16 hex>`, accepted if fresh), `traceparent`.

**Unknown fields are tolerated and preserved** (redacted and capped like everything else), so future
contract versions can add context without breaking v0.1.0 producers.

## Rules and limits

| Rule | Value | Rejection field |
|---|---|---|
| total payload | ≤ 256 KiB | `body` (HTTP 413) |
| any string | ≤ 4 KiB | the nested path, e.g. `arguments.command` |
| `arguments` / `context` | ≤ 64 KiB each | `arguments` / `context` |
| `policy_ref.clause` | ≤ 8 KiB | `policy_ref.clause` |
| `expires_at` | must be in the future and ≤ `now + class.ttl_seconds` | `expires_at` |
| `class` | must resolve in config | `class` |
| duplicate `ask_id` | only for the same action identity + session | `ask_id` |

## Idempotency

The key is `action_identity` + `session_id` inside the dedupe window (default 900 s). A retry returns the
same `ask_id`, stores nothing new, and records a `deduplicated` transition. Three retries ⇒ one ask and two
dedupe transitions.

## Redaction (before persistence)

Every string value in `arguments`, `context`, and unknown fields is scanned for:

| Class | Examples |
|---|---|
| `PRIVATE_KEY` | `-----BEGIN ... PRIVATE KEY-----` blocks |
| `SECRET` | `sk-…`, `ghp_…`, `xox…`, `AKIA…`, `Bearer …` |
| `CONNECTION_STRING` | `postgres://user:password@host/…` |
| `EMAIL` | `user@example.com` |
| `PHONE` | formatted phone numbers |

Matches become `[REDACTED:<CLASS>]`; receipts ride the stored payload:

```json
"_redactions": [{"field": "arguments.command", "class": "SECRET", "count": 1}]
```

The raw value is never written to the store, the audit chain, or logs. Receipts are rendered on the card
(M5).

## Trust

Trusted-class fields — `class`, `criticality`, `data_class`, `environment`, `policy_ref`, `reason_code` — are
stored as **unverified** unless an authenticated producer adapter submitted the ask. Agent-supplied text
(`arguments`, `context`, extras) is always untrusted. Booking fields in the body (`_trust`, `_redactions`,
`_producer`) cannot self-assert trust; the server overwrites them.

```json
"_trust": {"trusted": [], "unverified": ["class", "criticality", ...], "untrusted": ["arguments", "context"]}
```

## API

| Call | Result |
|---|---|
| `POST /v1/asks` | `201` created · `200` duplicate · `400` named field · `401` token · `413` over cap · `503` store down |
| `GET /v1/asks/{id}` | `200` snapshot · `404` unknown |
| `GET /v1/asks/{id}?wait=25s` | bounded long-poll (≤ 30 s) until the ask leaves `pending` |

Auth: `Authorization: Bearer <token>` or `X-AgentInbox-Token: <token>`, compared in constant time. The bind is
loopback-only. Errors are `{"error": {"field": "...", "message": "..."}}`.

## Producer checklist

1. Build the ask, compute `action_identity` with the canonical form above.
2. Set `expires_at` inside the class TTL; do not extend it to wait longer.
3. Retry with the **same** payload on timeouts — idempotency makes it safe.
4. Treat `200` and `201` identically; poll or long-poll `GET` for the decision.
5. Never put secrets in `arguments`/`context` and expect them to survive — they will be redacted, and the
   approver will see the receipt, not the value.
