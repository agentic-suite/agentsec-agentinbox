# Lifecycle design — v0.1.0 (M3)

**BLUF:** One versioned state machine, enforced in one place. `Ask` is the durable approval object;
`Transition` is the append-only history; `Claim` and `Delivery` complete the audit join; and the
`resolve/1.0` read path turns status + `expires_at` into `allow | deny | pending` with stable reason codes.
**Terminal is terminal**: after a decision the only legal append is a `late-answer` observation. Expiry is
derived on read from `expires_at`, so a crash between "decided" and "recorded" resolves safely to deny.

- **Milestone:** M3 ([WBS Part 2](../../wbs/v0.1.0/wbs-v0.1.0-part2-contract-lifecycle.md), issues #136–#146)
- **Requirements:** PRD 15 §entities/§lifecycle · PRD 02 §lifecycle · D-4

---

## 1. States and legal edges

```
pending ──► approved        (terminal: answer + principal + claim)
        ├──► denied          (terminal: answer)
        ├──► expired         (terminal: TTL elapsed; deny to producer, human_gate_timeout)
        ├──► cancelled       (terminal: producer withdrew)
        └──► flood_denied    (terminal: throttle trip; ask_flood_throttled)
```

The edge table is data, not control flow:

```python
LEGAL_EDGES = {AskStatus.PENDING: frozenset(AskStatus.terminal())}
```

- `assert_can_transition(current, new)` raises `IllegalTransition` for anything not in the table.
- An illegal attempt appends a non-state-changing `illegal-transition-rejected` observation
  (from = current, to = current, detail = attempted target) and then raises, so attempts are evidence.
- Terminal states have no outgoing edges. `late-answer` is the **one** allowed post-terminal observation:
  it records the responder and the winning answer, changes nothing, and returns "already resolved".
- The machine is versioned with the contract; the forward slate extends it additively (PRD 30 R69).

`AskStatus` and this table are the only place statuses are compared for legality. A channel, scheduler, or
adapter never writes `status` directly — it calls `transition()`.

## 2. Entities

| Entity | Storage | Notes |
|---|---|---|
| `Ask` | `asks` + redacted `payload` | descriptive fields (`tool`, `action`, `policy_ref`, …) live in the already-redacted payload; scheduling fields are columns |
| `Transition` | `transitions` (per-ask `seq`) + audit chain | append-only; no update/delete API exists |
| `Claim` | `claims` | hash only; `state(at)` derives issued/used/revoked/expired |
| `Delivery` | `deliveries` | one row per channel attempt; `record_delivery` / `list_deliveries` |
| `AuditEntry` | `audit` | hash-chained; verified by `verify_audit_chain` |

`Ask` gains `warn_at`, `escalate_at`, and `tier` columns in schema v3 (they are derived at ingest from the
class config in M4). `status` is stored; **expiry is derived on read** and never written by a reader.

## 3. Resolve read path (`resolve/1.0`)

| Stored state | Derived at `now` | `status` | `reason_code` | retryable |
|---|---|---|---|---|
| pending, `expires_at > now` | pending | `pending` | `deny_ask_pending` | `true` |
| pending, `expires_at <= now` | **expired** (derived) | `deny` | `human_gate_timeout` | `false` |
| approved | approved | `allow` | `allow_ask_approved` | `false` |
| denied | denied | `deny` | `deny_ask_denied` | `false` |
| expired | expired | `deny` | `human_gate_timeout` | `false` |
| cancelled | cancelled | `deny` | `deny_ask_denied` (explanation says cancelled) | `false` |
| flood_denied | flood_denied | `deny` | `ask_flood_throttled` | `false` |
| unknown ask | — | `deny` | `deny_ask_unknown` | `false` |

Expiry carries a **rescope hint** (e.g. "narrow the target, or request a standing approval for class X") so
the producer can act instead of retrying blindly. `answered_by` comes from the winning transition, not from
a request field.

## 4. Crash windows

- Decision recorded but producer not yet told → on restart the ask reads approved/denied; the producer's
  next poll sees it. Idempotency by `action_identity` prevents double execution.
- Expiry decision lost between "derived" and "recorded" → the next read derives expired again; M4 records it
  with a CAS so exactly one transition is written.
- A late answer never overwrites a decision; it is an observation and the responder is told who won.

## 5. Interface additions

The AskStore contract grows additively (conformance version **2**):

```python
def transitions_for(self, ask_id: str) -> list[TransitionRecord]: ...
def record_delivery(self, delivery: DeliveryRecord) -> None: ...
def list_deliveries(self, ask_id: str) -> list[DeliveryRecord]: ...
```

## 6. Tests

| File | Covers |
|---|---|
| `tests/lifecycle/test_state_machine.py` | every legal edge, illegal edges + evidence, terminal-is-terminal, late-answer |
| `tests/lifecycle/test_entities.py` | Ask round-trip incl. warn/escalate/tier, delivery accounting, claim state |
| `tests/lifecycle/test_resolve.py` | pending/expired/approved/denied/cancelled/flood/unknown reads + derived expiry |
