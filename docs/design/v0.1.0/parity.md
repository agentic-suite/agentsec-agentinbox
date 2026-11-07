# Multi-surface parity design — v0.1.0 (M14)

**BLUF:** "approved in the terminal" and "approved from the second surface" are the **same fact with one
provenance**. Every surface reads the same store and renders the same M5 card; the decision record is built in
one module, so only `channel` and `principal` may differ. Races resolve first-wins, late answers are visible
no-ops, and a downed surface loses nothing — it updates to the outcome when it next reads.

- **Milestone:** M14 ([WBS Part 8](../../wbs/v0.1.0/wbs-v0.1.0-part8-parity-audit.md), issues #260–#270)
- **Requirements:** R2, E3/E4, D-5 · PRD 16 §F · CUJ-3, CUJ-9 · SC-07/08/18/19

---

## 1. The single choke point

All answering goes through `AnswerVerifier.submit` (M6). Channels deliver and authenticate; none decides. The
store's `cas_status` is the only writer of a decision, so there is no second execution path.

## 2. Decision record parity

`agentinbox.parity.decision_record(store, ask_id)` builds:

```json
{
  "ask_id": "ask_…",
  "action_identity": "sha256:…",
  "status": "approved",
  "decided_at": "2026-11-08T12:00:00.000000Z",
  "decision": "approve",
  "reason": null,
  "channel": "terminal",
  "principal": "alice"
}
```

`comparable_decision()` canonicalises the record after removing `channel` and `principal`. Two surfaces answering
the same logical ask therefore produce byte-identical comparable records; the varying fields are exactly the
provenance the record names.

## 3. Surface rendering

`surface_outcome(store, ask_id, surface=…)` renders the M5 card for `text`, `terminal`, `desktop`, or `ci`. All
four share the same core body (ask id, status, fingerprint, blocks); only the surface footer differs. A surface
that was showing `pending` reads the new `approved`/`denied` status on its next read — no re-ask, no second
delivery, no local state to reconcile.

## 4. Races

Two surfaces answering within milliseconds: the store CAS picks exactly one winner. The winner writes one
`answer` transition; the loser's claim is not consumed and its attempt is recorded as
`answer-rejected(cause=late)` with the winner principal/time. `resolve` stays idempotent, so no surface can
produce a second decision.

## 5. Late answers

An answer after resolution is a **visible no-op**:

- the responder is told `already resolved by <principal> at <iso>` (the winner is public, by design);
- the state is untouched;
- one `late-answer` observation records the attempted decision, winner, and winner time.

## 6. Failover

A downed channel produces bounded, enumerated delivery failures (`DeliveryRecord` + `delivery-failed`); other
channels are unaffected and failover proceeds. The downed surface later reads the outcome instead of being
re-asked. The ask's TTL and status are never changed by delivery.

## 7. Conformance

The M7 channel suite runs against terminal, desktop, webhook, and the CI-wait surface. Each must have
`deliver`/`authenticate`, must not have `decide`/`submit`, and a display-only surface's `authenticate()` must
return `None`. A deliberately deciding channel fails the suite.

## 8. Tests

`tests/parity/` covers record parity, surface rendering, the 8-thread race, late-answer messages/evidence, and
the failover matrix. `tests/channels/test_conformance.py` covers all four surfaces plus the broken-channel case.
