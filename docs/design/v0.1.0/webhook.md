# Webhook channel design — v0.1.0 (M13)

**BLUF:** the webhook reaches whatever the team already runs (ntfy, Pushover, Discord, Teams, email bridges) over
one honest primitive: an **HMAC-signed outbound POST** carrying a display-only summary. It says "answer in your
terminal"; it has **no answer path**. Every attempt is a Delivery record + event, retries are bounded with
failover, and a class with no enabled channel refuses at load.

- **Milestone:** M13 ([WBS Part 7](../../wbs/v0.1.0/wbs-v0.1.0-part7-flood-webhook.md), issues #249–#259)
- **Requirements:** E7, E4, D-5, E9 · PRD 16 §B.4, PRD 18 §assurance, PRD 13 N-3b · CUJ-3, CUJ-9

---

## 1. Payload

Canonical JSON (sorted keys, no whitespace) over a **display-only** view:

```json
{
  "contract": "webhook/1.0",
  "ask_id": "ask_…",
  "class": "irreversible",
  "fingerprint": "sha256:…",
  "status": "pending",
  "ttl_seconds": 240,
  "expires_at": "2026-11-08T12:05:00.000000Z",
  "action": "run_command",
  "answer_command": "agentinbox answer ask_…",
  "answer_channel": "terminal",
  "decision": null
}
```

It never includes `arguments`, tool output, blast-radius text, policy clauses, or credentials. `decision` is
always `null`: the payload is structurally a notification, not an answer form.

## 2. Signature

`X-AgentInbox-Signature: sha256=<hex>` is HMAC-SHA256 over the exact canonical bytes that are POSTed.
`X-AgentInbox-Contract: webhook/1.0` identifies the shape. The secret is resolved from a **reference** at
delivery time (`env:NAME` or `file:/absolute/path`); literal secrets in config are already refused. A missing
reference or a non-2xx response is a `ChannelError` (delivery failure), recorded as a failed attempt.

## 3. Display-only enforcement

`WebhookChannel` implements `deliver()` and `authenticate()` returns `None`; there is no `answer`, `submit`,
`decide`, or response parser. A crafted POST *to* the inbox is not a webhook concern: the inbound API has no
answer endpoint for an unauthenticated raw caller (M6 raw-API guard). The payload says "answer in the terminal";
buttons/actions are the receiver's problem and cannot mint a claim.

## 4. Delivery accounting (E7)

`DeliveryWiring` (M9) records every attempt:

- `DeliveryRecord(attempt=n, status=delivered|failed, target=channel, error=…)`;
- `ask-delivered` on success, `delivery-failed` on failure;
- bounded retries (3) with injectable backoff, then failover to the next configured channel;
- `ingest` publishes to the bus and returns; it never waits on delivery.

A channel that is down for ten minutes produces a logged streak of failures (one record/event per attempt), while
the terminal remains answerable and the ask's TTL is untouched. A successfully delivered channel is not
re-notified by a later failover attempt.

## 5. Unroutable classes

At load, if any channel is configured, every class must resolve to at least one **enabled** channel through its
ladder tiers' rosters (or the whole roster when there is no ladder). A class with zero enabled channels refuses
with a class-named error. A configured-but-down channel is different: it is a **delivery failure** (pending +
`delivery-failed`), not a config error.

## 6. Recipes

`docs/adapters/webhook-recipes.md` documents ntfy.sh, Pushover, Discord, Teams, and email bridges: URL setup,
receiver-side signature verification, and the display-only caveat. Fixtures render each recipe's receiver view
from the same payload contract; none implies an answer path.

## 7. `agentinbox channels`

Lists configured channels and their health. `terminal` is always available; `desktop` uses the M8 reachability
check; `webhook` verifies its references resolve. Any enabled-but-unhealthy channel exits `4`.

## 8. Tests

`tests/channels/test_webhook.py` covers payload content, signature, display-only, missing refs, and network
failures. `tests/cli/test_channels.py` covers health/exit codes. Delivery accounting reuses the M9 suite with a
webhook that fails for the whole streak.
