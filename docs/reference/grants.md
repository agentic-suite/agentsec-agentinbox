# Grants & compression reference (v0.1.0 · M30)

**BLUF:** bounded windows for repeated intents; compression is a view, never a group decision.

- Design: [`docs/design/v0.1.0/grants.md`](../design/v0.1.0/grants.md)
- Module: `agentinbox/grants.py` · **Tests:** `tests/grants/`

## Issue a window

```python
grant = issue_grant(store, config, scope="class", class_name="irreversible",
                    owner="alice", reason="deploy window", issued_by="alice",
                    ttl_seconds=900, max_uses=10, max_per_minute=3)
```

A session grant is the same with `scope="session", session_id="…"`; only one may be active per session.
Owner, reason, issuer, and positive ceilings are required. Issuance is a chained `grant-issued` event.

## Coverage and burn-down

New asks for the covered class/session are approved automatically only while the grant is active, under
`max_uses` and `max_per_minute`; each use writes `grant-used` and the answer carries
`authorization.source=window-grant`. The card shows `GRANT` with `uses/max_uses`, remaining seconds,
owner, issuer, and status (`active`/`spent`/`expired`/`revoked`). `doctor` lists active grants.

## Expire and revoke

```python
revoke_grant(store, grant_id, by="alice", reason="change freeze")
end_session(store, session_id)
expire_due_grants(store)
```

Revocation and expiry are immediate: the next ask reverts to per-ask approval. Every change is chained.

## Compression and repeated denies

```python
group = compress(store, ask)              # COMPRESSED xN + every row; view only
items = repeated_denials(store, threshold=5)
```

Compression never removes asks from exports and never answers the group. Repeated denials are an
insight for tuning, not an auto-approval or auto-hardening.
