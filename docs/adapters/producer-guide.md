# Producer guide (v0.1.0 · M18)

**BLUF:** any process can ask for a human decision in three ways: the `ask` CLI (file or exact command), the
loopback HTTP API, or the agentpolicy reference adapter. Every path uses one contract (`ask/1.0`), one outcome
(`resolve/1.0`), and the reserved exit codes.

- Design of record: [`docs/design/v0.1.0/adapters.md`](../design/v0.1.0/adapters.md)
- Contracts: [ask/1.0](../reference/ask-contract.md) · [resolve/1.0](../reference/resolve.md) · [exit codes](../reference/cli.md)

## 1. Five-minute path (CUJ-1)

```sh
python -m venv .venv && . .venv/bin/activate
pip install agentsec-agentinbox
agentinbox init                 # terminal-only scaffold; home is 0700
agentinbox ask --exec "deploy --prod"   # blocks; answer in another terminal
agentinbox inbox
agentinbox answer <ask-id> --approve
```

The command runs only after the answer is recorded; deny/expiry exits without executing it.

## 2. `ask --exec` / `ask --file`

| Flag | Meaning |
|---|---|
| `--exec COMMAND` | gate this exact command (tool `shell`, action `run_command`) |
| `--file PATH` | ingest a validated `ask/1.0` JSON object |
| `--class C` | class name (default `irreversible`) |
| `--environment E` | environment label (default `local`) |
| `--agent-id A` | agent identity recorded on the ask |
| `--requested-by R` | requester recorded for self-review (defaults to the agent id / `agent://agentinbox-cli`, never the human OS user) |
| `--ttl S` | requested TTL, at most the class ceiling |
| `--timeout S` | CI-style wait budget (independent of the ask TTL) |

Exit codes: `0` approved, `2` denied, `3` expired, `4` unavailable/contract error, `5` still pending (not used
by `ask`, which waits). On `0`, the command's own exit status is returned.

## 3. HTTP: create

```http
POST /v1/asks
Authorization: Bearer <token>
Content-Type: application/json

{ "contract": "ask/1.0", ... }
```

- The token is the daemon's API token: `agentinbox serve` writes it to `<home>/api-token` (mode `0600`) and never
  prints it. `AGENTINBOX_API_TOKEN` overrides a generated token. The API binds loopback only.
- Optional adapter signature for trusted fields:

```http
X-AgentInbox-Adapter: agentpolicy
X-AgentInbox-Principal: maya@team
X-AgentInbox-Signature: sha256=<HMAC-SHA256 over the exact body bytes>
```

The key is configured in the daemon (`[producers.agentpolicy].key_ref = "env:…"`). An unknown adapter or a bad
signature is `401`; nothing is stored. A valid signature makes `class`, `criticality`, `data_class`,
`environment`, `policy_ref`, and `reason_code` trusted for rendering.

Responses: `201` created / `200` coalesced duplicate, `{ "ask_id", "status", "created" }`. Errors are field-named:

| Status | Meaning |
|---|---|
| `400` | invalid field (`{ "error": { "field", "message" } }`) |
| `401` | bad token or adapter signature |
| `413` | payload over the cap |
| `503` | store unavailable — **deny at the enforcer**, do not proceed |

## 4. HTTP: resolve

```http
GET /v1/asks/{ask_id}?wait=30&action_identity=sha256:…
Authorization: Bearer <token>
```

Returns `resolve/1.0` (see the reference). Long-poll while pending; a different `action_identity` returns
`deny_action_identity_mismatch` immediately. Unknown ids return `404` with `deny_ask_unknown`.

## 5. Error taxonomy

| Situation | Producer action |
|---|---|
| `400 field=…` | fix the body; do not retry unchanged |
| `401` | fix the token/key; do not retry |
| `413` | shrink the payload |
| `503` / connection refused | deny at the enforcer (fail closed); bounded retry only |
| `deny_ask_pending` | poll again / long-poll |
| `human_gate_timeout` | do not retry the same action; use `rescope_hint` |
| `ask_flood_throttled` | wait `retry_after`, then re-ask |
| `deny_ask_denied` | respect the reason; do not auto-retry |
| `deny_action_identity_mismatch` | the id does not authorize this action |

## 6. Throttling and identity

Requests are keyed by agent/session/environment and the authenticated principal (or remote address). A flood is
a decision (`ask_flood_throttled`), not a silent drop. Retries of the same action identity coalesce inside the
dedupe window and never re-notify.
