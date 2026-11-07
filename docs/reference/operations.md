# Operation bundles, handoff & incident reference (v0.1.0 · M28)

**BLUF:** one operation, many asks, per-ask truth. Bundles are derived; there is no approve-all.

- Design: [`docs/design/v0.1.0/operations.md`](../design/v0.1.0/operations.md)
- Module: `agentinbox/operations.py` · **Tests:** `tests/bundles/`

## Bundle

```python
from agentinbox.operations import derive_bundle, bundle_export

bundle = derive_bundle(store, ask)        # explicit operation_id or (derived) session window
bundle.render()                            # grouped counts, environments, phases, critical path
bundle_export(store, bundle)               # {"contract": "bundle/1.0", asks, timeline}
```

`critical_path` names the pending ask with the earliest expiry; `None` when nothing is pending.
Every ask is still approved/denied individually.

## Claim, assign, handoff

```python
claim_ask(store, ask_id, principal="alice")
assign_ask(store, ask_id, assignee="bob", by="alice")
record_handoff(store, ask_id, outgoing="alice", incoming="bob",
               note="rollback plan missing", open_questions=["backup verified?"],
               evidence=["diff"])
```

These are observations only: status, expiry, and answer eligibility do not change. A handoff carries
`remaining_s`, prior context, questions, and evidence; the card shows a `HANDOFF` block before `ACTION`.

## Incident mode

```toml
[incident]
enabled = true
owner = "alice"
reason = "SEV-1"
ttl_scale = 0.5          # (0, 1]; never extends TTLs
classes = ["irreversible"]
```

`record_incident(store, config)` appends a chained `incident-on`/`incident-off` event with owner,
reason, scale, and classes. Deny paths never become allows.

## Narrative & timeline

```python
narrative(ask, store.transitions_for(ask.ask_id))
timeline(bundle.asks, transitions)
```

The narrative reconstructs rule, evidence, alternatives, constraints/edits, and outcome from stored
transitions; the timeline is ordered by transition sequence and exported with the bundle.
