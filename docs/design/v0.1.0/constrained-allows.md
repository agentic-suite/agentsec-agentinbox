# Constrained allows & denial repair design — v0.1.0 (M27)

**BLUF:** the gate grows from approve/deny to **shape the action**: producer-declared narrowed variants
are one-click choices only when an enforcer binding exists; denials carry a machine-readable repair
packet; human edits are re-fingerprinted and recorded. The inbox records and returns; the enforcer
enforces — a constraint no enforcer can honor is never offered as a choice.

- **Milestone:** M27 ([WBS Part 14](../../wbs/v0.1.0/wbs-v0.1.0-part14-quality-constraints.md), issues #318–#328)
- **Requirements:** PRD 33 R87–R93 · CUJ-15/16/29–32 · SC-71..74
- **Modules:** `alternatives.py`, `repair.py`, `answers.py`, `resolve.py`, `card.py`

---

## 1. Alternatives and enforcer binding (R87/R93)

An ask may carry up to five `alternatives[]`:

```json
{"id":"staging","label":"Run on staging","enforcer":"agentpolicy",
 "arguments":{"command":"psql staging -c 'select 1'"},
 "constraints":[{"id":"environment","enforcer_ref":"agentpolicy:env","params":{"environment":"staging"}}],
 "fingerprint":"sha256:<64 hex>"}
```

Selectable iff `enforcer` is non-empty **and** `fingerprint == alternative_fingerprint(alternative)`
(SHA-256 over canonical `{id,label,enforcer,arguments,constraints}`). Otherwise it renders as
`advice only (no enforcer binding)` and selecting it is rejected (`unbindable_alternative`). Unknown id
→ `unknown_alternative`. Choosing one approves with `decision=allow_with_constraints`; the resolve and
the answer transition carry the constraint list and the alternative fingerprint.

## 2. Suggestions (R88)

When no alternatives are advertised, the card suggests at most three class-generic narrowings
(staging demotion for production, dry-run for destructive verbs, an explicit limit). They are labelled
`suggestion`, are **not** selectable, and leave no constraint unless a human later edits the ask
through the declared edit schema.

## 3. Denial repair packet (R89, SC-72)

Every human deny records and returns:

```json
{"violated_invariant":"missing the migration diff","missing_evidence":["evidence_presence"],
 "suggested_scope":"…","safe_alternative":"staging","retry_worthiness":"conditional",
 "required_tier":null}
```

`retry_worthiness`: `pointless` when readiness is red or the reason names a hard objection
(wrong/unsafe/never), else `conditional`. The packet rides the answer transition detail and the resolve;
an agent can repair and resubmit without parsing prose.

## 4. Edits and provenance (R90/R91, SC-73)

`[classes.<name>] edit_schema = ["command", …]` declares editable argument fields. An approver submits
`--edit command=…`; the edited arguments are re-canonicalized and `edited_action_identity` is recomputed.
The answer transition records `edits`, `original_action_identity`, `edited_action_identity`, principal
and channel. Out-of-schema fields are rejected with the field named (`edit_schema`); edits apply only to
an allow. The edited form is what the enforcer must execute; the card/resolve return it.

## 5. Repair recall (R92)

Before answering a resubmission, the card surfaces up to two prior human denials of the same class+tool
that carried a repair packet: `prior objection: <ask_id> denied once (<reason>)`. The audit chain is the
source; no new store query and no inference.

## 6. Resolve vocabulary (R92/R20)

`status` stays `allow` / `deny` / `pending` for old clients; `decision` is additive:
`allow`, `allow_with_constraints`, `allow_with_edits`, `deny`, `pending`. New fields: `constraints[]`,
`edits`, `alternative_fingerprint`, `repair`. Expiry carries a repair packet with
`violated_invariant=human_gate_timeout`.

## 7. Tests

`tests/constraints/`: bindable vs unbindable/tampered alternatives, suggestion rendering and no-constraint
when unpicked, repair packets (conditional/pointless), edit re-fingerprinting and schema refusal, recall,
and additive resolve compatibility.
