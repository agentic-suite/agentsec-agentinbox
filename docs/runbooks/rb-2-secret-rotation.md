# RB-2 — Signing-secret rotation

**Symptoms:** you need to rotate an adapter HMAC key or the webhook HMAC key without losing pending asks.

**Steps**
1. Add the new value to the secret store (`env:` variable or `file:`), keeping the old value available.
2. Point the producer/receiver at the new value during an overlap window; update `config.toml` only if
   the reference name changes.
3. Reload: `kill -HUP <serve pid>`; a valid file applies in place, an invalid one is refused loudly and
   the last-good config stays.
4. Remove the old value after the overlap.
5. Rotate the **API token** by restarting `serve` (it writes a new `<home>/api-token`); update producers.

**Verify:** `agentinbox doctor` (`keys` green), a signed producer request succeeds, unsigned/old-key
requests are `401`; `verify-log` passes. Claims are local and unaffected by key rotation.
