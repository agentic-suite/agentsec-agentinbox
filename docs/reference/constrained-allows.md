# Constrained allows & denial repair reference (v0.1.0 · M27)

**BLUF:** producers can advertise narrower variants, approvers can pick or edit them, and denials return
a machine-readable repair packet. Only variants with an enforcer binding are selectable.

- Design: [`docs/design/v0.1.0/constrained-allows.md`](../design/v0.1.0/constrained-allows.md)
- Modules: `agentinbox/alternatives.py`, `agentinbox/repair.py` · **Tests:** `tests/constraints/`

## Producer: alternatives

```json
"alternatives": [
  {"id": "staging", "label": "Run on staging", "enforcer": "agentpolicy",
   "arguments": {"command": "psql staging -c 'select 1'"},
   "constraints": [{"id": "environment", "enforcer_ref": "agentpolicy:env",
                    "params": {"environment": "staging"}}],
   "fingerprint": "sha256:<64 hex>"}
]
```

- At most five, unique ids, non-empty label.
- `fingerprint` must equal the canonical hash of `{id,label,enforcer,arguments,constraints}`.
- No `enforcer` or a bad fingerprint → **advice only**, not selectable (SC-74).
- Arguments/params are redacted before storage like any other ask text.

## Approver: choosing and editing

```sh
agentinbox answer <ask_id> --approve --alternative staging
agentinbox answer <ask_id> --approve --edit command="psql prod -c 'select 1 limit 10'"
```

- An alternative and an edit set are mutually exclusive; an alternative can only allow.
- Edits are allowed only for fields in `[classes.<name>] edit_schema`; the edited form is
  re-fingerprinted (`edited_action_identity`) and recorded with `original_action_identity`, principal,
  and channel.
- If no alternatives exist, the card shows labelled **suggestions**; they are not selectable and leave
  no constraint.

## Resolve

`status` remains `allow`/`deny`/`pending` (compatible). Additive fields:

| Field | Meaning |
|---|---|
| `decision` | `allow`, `allow_with_constraints`, `allow_with_edits`, `deny`, `pending` |
| `constraints[]` | `{id, params, enforcer_ref}` from the chosen alternative |
| `edits` | the applied argument edits |
| `alternative_fingerprint` | the chosen alternative's fingerprint |
| `repair` | denial/expiry packet |

Repair packet:

```json
{"violated_invariant":"…","missing_evidence":["evidence_presence"],"suggested_scope":"…",
 "safe_alternative":"staging","retry_worthiness":"conditional","required_tier":null}
```

`retry_worthiness=pointless` means a blind retry will not help.

## Recall

A resubmission's card shows up to two prior same-class/tool denials as
`prior objection: <ask_id> denied once (<reason>)` — evidence from the chain, not a recommendation.
