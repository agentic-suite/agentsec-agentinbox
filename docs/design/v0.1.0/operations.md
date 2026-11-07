# Operation bundles, handoff & incident design — v0.1.0 (M28)

**BLUF:** humans review **operations**, not isolated asks. A bundle groups asks by producer-declared
`operation_id` (or a labelled session+window heuristic) and is **derived on read** — every child ask
keeps its own status, claim, and audit rows. There is no bundle-level decision path.

- **Milestone:** M28 (WBS Part 15, issues #329–#340) · **Requirements:** PRD 34 R94–R100, SC-75..78
- **Module:** `agentinbox/operations.py` · **Tests:** `tests/bundles/`

## 1. Bundle derivation (R94/R95)

- Explicit: `context.operation_id` (all matching asks).
- Derived: same `session_id` + class within 900 s; rendered with a `(derived)` label.
- View: counts by status, environments touched, phases (declared `context.phase`, else
  `review`/`decided` inferred from status), and the **critical path** = pending ask with the earliest
  expiry. `Bundle.render()` lists each ask; answering remains per-ask only.

## 2. Claim / assign / handoff (R96/R97)

- `claim_ask` / `assign_ask` append `claimed` / `assigned` observations (`routing_only: true`); status,
  TTL, and answer eligibility are unchanged.
- `record_handoff` appends a `handoff` observation with outgoing/incoming principal, note, open
  questions, evidence gathered, and `remaining_s` (never negative).
- The card renders a `HANDOFF` block **before** `ACTION` when the latest handoff exists.

## 3. Incident overlay (R98)

`[incident]` is config-declared, bounded, and audited: `enabled`, `owner`, `reason`, `ttl_scale` in
`(0, 1]`, `classes`. `record_incident` writes `incident-on` / `incident-off` with the full state to the
hash chain. The overlay never converts a deny to an allow and never extends TTLs.

## 4. Narrative and timeline (R99/R100)

- `narrative(ask, transitions)` renders ask, rule, evidence/freshness, missing evidence,
  contradictions, alternatives offered, outcome (who/channel/when/reason), constraints, and edits —
  all from stored transitions.
- `timeline(asks, transitions)` orders rows by `(at, ask_id, seq)` and carries `operation_id`;
  `bundle_export` emits `bundle/1.0` with asks + timeline in one packet.

## 5. Tests

`tests/bundles/test_operations.py`: 20-ask bundle with per-ask truth, derived labelling, claim/assign
routing-only, handoff rendering + TTL preservation, incident audit + deny preservation, narrative,
timeline order, and bundle export.
