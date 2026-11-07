# Webhook channel reference (v0.1.0 · M13)

**BLUF:** a signed, display-only outbound POST. It reaches ntfy/Pushover/Discord/Teams/email bridges; it cannot
answer an ask.

- Design of record: [`docs/design/v0.1.0/webhook.md`](../design/v0.1.0/webhook.md)
- Recipes: [`docs/adapters/webhook-recipes.md`](../adapters/webhook-recipes.md)

```toml
[channels.webhook]
enabled = true
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "file:/etc/agentinbox/webhook.key"
```

## Contract

| Item | Value |
|---|---|
| contract | `webhook/1.0` |
| method | `POST` |
| content type | `application/json` |
| signature | `X-AgentInbox-Signature: sha256=<HMAC-SHA256 hex over the exact body>` |
| contract header | `X-AgentInbox-Contract: webhook/1.0` |
| body | canonical JSON (sorted keys, no whitespace) |

The body contains `ask_id`, `class`, `action`, `fingerprint`, `status`, `ttl_seconds`, `expires_at`,
`answer_command`, `answer_channel` (`terminal`), and `decision` (always `null`). It never contains `arguments`,
tool output, blast-radius text, or credentials.

## Behaviour

| Situation | Result |
|---|---|
| channel disabled | no POST |
| missing/unresolvable `url_ref` or `hmac_key_ref` | `ChannelError` (delivery failure) |
| non-http(s) URL | `ChannelError` |
| receiver error/timeout | `ChannelError`; a Delivery `failed` record + `delivery-failed` event |
| success | a Delivery `delivered` record + `ask-delivered` event |

Retries are bounded (3) with backoff; after exhaustion the next configured channel is tried (failover). Ingest
never blocks on delivery.

## Health

`agentinbox channels` verifies the references resolve and exits `4` when an enabled webhook is unhealthy. A
configured-but-down receiver is not a config error; it is a delivery failure, and the ask stays pending.

## Security

The channel has `deliver()` only; `authenticate()` returns `None`, and there is no answer/submit/decide method.
A receiver-side "response" has no inbox counterpart: answers require a claim minted by an interactive channel and
the M6 verifier. The HMAC key is resolved at delivery time and never logged or persisted.
