# Outcome closure & execution proof design — v0.1.0 (M29)

**BLUF:** approval alone cannot prove the approved thing is what ran. Closures are **observations**
(the decision never changes), receipts are **evidence not credentials**, and approved-vs-executed
comparison is **derived from stored facts** — the producer's manifest is untrusted input.

- **Milestone:** M29 (WBS Part 15, issues #341–#352) · **Requirements:** PRD 35 R101–R107
- **Module:** `agentinbox/outcomes.py` · **Tests:** `tests/outcomes/`

## 1. Closure states (R101)

`executed / failed / cancelled / rolled_back / superseded` are appended as `outcome` observations on an
**approved** ask. Status stays `approved`; no closure can reopen or alter the decision. No outcome means
`outcome: unknown`.

## 2. Receipts (R102)

Whitelisted, capped fields: `run_url`/`url` (≤2048), `digest`/`job_id` (≤2048), `resources` (≤50 × 256).
The canonical receipt is passed through the shared secret scanner; any credential shape refuses the
closure. Receipts render on the card and in the narrative.

## 3. Comparison (R103)

The approved identity is the edited identity from the answer transition when present, else the ask
fingerprint. Executed manifest = `{fingerprint?, environment?, resources[], constraints[]}`:

| Condition | Status |
|---|---|
| no manifest / empty | `unknown` |
| fingerprint present and equal, resources subset | `match` |
| no fingerprint, resources subset | `partial` |
| executed resources not approved | `exceeded` (exceeding resources named) |
| fingerprint present and different | `divergent` |

## 4. Divergence (R104)

`exceeded`/`divergent` appends a chained `outcome-divergence` audit event. The card shows
`divergence: UNACKNOWLEDGED`; `acknowledge_divergence` appends `divergence-acked` (principal) and the
card shows `acknowledged`. No approval path is opened.

## 5. Portable packet (R105)

`decision_packet` emits `decision-packet/1.0`: ask, payload, decision, narrative, outcome, timeline,
trace, the full audit chain segment, and offline verification instructions. `verify_packet` rebuilds
`AuditEntry` rows and re-verifies the chain; tampering raises `ChainHashMismatch`.
CLI: `agentinbox export --ask <id> --packet [--out ABS]`.

## 6. Trace and SLA (R106/R107)

`trace` joins ask → policy → decision → outcome → divergence (writeback reserved `None`). Classes may set
`closure_sla_seconds`; `outcome_sla_pending` reports approved asks with no outcome past it, and `doctor`
surfaces `outcome-pending-past-sla`. Nothing auto-closes.

## 7. Tests

`tests/outcomes/test_outcomes.py`: closure immutability, unknown outcomes, credential refusal, receipt
caps, all comparison statuses, chained divergence + acknowledgement, offline packet verification and
tamper detection, end-to-end trace, and SLA surfacing.
