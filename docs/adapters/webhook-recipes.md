# Webhook recipes (v0.1.0 · M13)

**BLUF:** the webhook is one signed outbound POST. Point `url_ref` at any receiver that accepts JSON and verify
`X-AgentInbox-Signature` with the shared key. The payload is display-only: it says "answer in your terminal" and
carries **no** arguments and **no** answer affordance.

- Design of record: [`docs/design/v0.1.0/webhook.md`](../design/v0.1.0/webhook.md)
- Reference: [`docs/reference/webhook.md`](../reference/webhook.md)

## Configuration

```toml
[channels.webhook]
enabled = true
url_ref = "env:AGENTINBOX_WEBHOOK_URL"
hmac_key_ref = "file:/etc/agentinbox/webhook.key"
```

`url_ref`/`hmac_key_ref` are references only. The resolved URL must be `http(s)`. Enable a class route to the
webhook in the roster:

```toml
[roster.tier-1]
webhook = ["ops-channel"]
```

## Payload

```json
{
  "contract": "webhook/1.0",
  "ask_id": "ask_…",
  "class": "irreversible",
  "action": "run_command",
  "fingerprint": "sha256:…",
  "status": "pending",
  "ttl_seconds": 240,
  "expires_at": "2026-11-08T12:05:00.000000Z",
  "answer_command": "agentinbox answer ask_…",
  "answer_channel": "terminal",
  "decision": null
}
```

Headers: `Content-Type: application/json`, `X-AgentInbox-Contract: webhook/1.0`,
`X-AgentInbox-Signature: sha256=<hex HMAC-SHA256 over the exact body bytes>`.

## Receiver verification (any language)

```python
import hashlib, hmac
expected = "sha256=" + hmac.new(KEY, raw_body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-AgentInbox-Signature"])
```

Reject on mismatch, then render the message. Never parse `decision` as an answer; it is always `null`.

## ntfy.sh / self-hosted ntfy

```toml
url_ref = "env:NTFY_URL"   # e.g. https://ntfy.example/agentinbox
```

A tiny relay verifies the signature and maps `class`/`fingerprint`/`ttl_seconds` into the ntfy title/body. ntfy
actions must not call the inbox; the only action may be "open terminal docs".

## Pushover

```text
https://api.pushover.net/1/messages.json?token=…&user=…
```

Use a relay: Pushover's URL expects form fields, so verify the HMAC, then POST
`title=agentinbox <class>`, `message=<fingerprint> · ttl <mm:ss> · answer in the terminal`.

## Discord / Slack-compatible webhook

```toml
url_ref = "env:DISCORD_WEBHOOK_URL"
```

The Discord JSON shape is `{"content": "..."}`. A relay verifies the HMAC and forwards only the safe fields. Do
not configure Discord interactive components: this channel cannot answer.

## Microsoft Teams connector

```text
https://<tenant>.webhook.office.com/webhookb2/…
```

Relay to a MessageCard with `title`, `text` (class/fingerprint/TTL), and `potentialAction` omitted. No
`HttpPOST` action to the inbox.

## Email bridge

```toml
url_ref = "env:MAIL_BRIDGE_URL"
```

The bridge verifies the signature and sends a plain-text email: subject `agentinbox <class>`, body
`<fingerprint> · ttl <mm:ss>`, footer `answer in the terminal: agentinbox answer <id>`. Replies are not ingested;
the reply-to address must be a black hole.

## Anti-patterns

- an interactive button that posts an answer — buttons cannot mint a claim, and the raw API refuses;
- forwarding `arguments` to a third party — the payload never contains them; do not add them at the relay;
- storing the HMAC key in the receiver's URL or logs;
- treating a 2xx from the receiver as a human decision — it only means the notification was accepted.
