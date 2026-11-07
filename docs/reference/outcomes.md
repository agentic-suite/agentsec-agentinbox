# Outcome closure & execution proof reference (v0.1.0 · M29)

**BLUF:** close approved asks with an outcome and proof; outcomes describe, never authorize.

- Design: [`docs/design/v0.1.0/outcomes.md`](../design/v0.1.0/outcomes.md)
- Module: `agentinbox/outcomes.py` · **Tests:** `tests/outcomes/`

## Record a closure

```python
record_outcome(store, ask_id, state="executed", principal="ci-bot",
               receipt={"run_url": "https://ci/runs/7", "digest": "sha256:…",
                        "job_id": "deploy-7", "resources": ["db:prod/customers"]},
               manifest={"fingerprint": ask.action_identity,
                         "resources": ["db:prod/customers"]})
```

States: `executed`, `failed`, `cancelled`, `rolled_back`, `superseded`. Only an approved ask can close;
the decision and status are unchanged. No closure renders `outcome: unknown`.

Receipts are whitelisted and capped; any secret shape refuses the closure. Receipts render on the card
and in the narrative.

## Comparison and divergence

`compare_execution` derives `match`, `partial`, `exceeded`, `divergent`, or `unknown` from the approved
identity/resources and the executed manifest. `exceeded`/`divergent` writes a chained
`outcome-divergence` event and the card shows `UNACKNOWLEDGED` until:

```python
acknowledge_divergence(store, ask_id, principal="alice")
```

## Packet

```sh
agentinbox export --ask <ask_id> --packet --out /abs/packet.json
```

`decision-packet/1.0` carries ask, decision, narrative, outcome, timeline, trace, the audit chain
segment, and verification instructions. `verify_packet(packet)` verifies offline; tampering raises.

## Trace and SLA

`trace(store, ask_id)` walks ask → policy → decision → execution → divergence. Set
`[classes.<name>] closure_sla_seconds = 86400`; unclosed approved asks past it are returned by
`outcome_sla_pending` and surfaced by `doctor` as `outcome-pending-past-sla` (never auto-closed).
