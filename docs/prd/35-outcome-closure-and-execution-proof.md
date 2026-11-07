# PRD 35 — Outcome Closure & Execution Proof

**BLUF:** trust is incomplete if it ends at approval. This PRD closes the loop: **post-decision outcome
states** (executed / failed / cancelled / rolled back / superseded), **execution receipts** attached from CI,
deploys, and writeback targets, an **approved-vs-executed comparison** that surfaces drift, divergence
alerting, and a **portable decision packet** — one artifact for CAB, postmortems, compliance, and release
review.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

Today the chain proves *a human approved something*. It cannot prove *the thing that ran is what they
approved*. That gap is where auditors live and where trust quietly dies. This PRD extends [PRD 29](29-trust-maturity-writeback-performance.md)'s
writeback posture (R64) from *best-effort state sync* into **closure with proof**: every approved ask ends in a
comparable, exportable, divergence-checked record.

**Honesty clause (inherited):** outcomes **describe, never authorize** (PRD 29 E16). No receipt, no green
checkmark, no "it ran fine" ever relaxes a future gate.

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-24** | "Prove the human approved exactly what executed" — approved scope vs actual, with drift named | P0 |
| **CUJ-37** | "Approved==executed, verifiable" — fingerprint comparison, not a promise | P0 |
| **CUJ-38** | "Close the ask with an outcome, not silence" — no approved ask fades into the void | P0 |
| **CUJ-39** | "One packet for CAB, postmortem, and audit" — portable, self-contained, verifiable | P1 |
| **CUJ-40** | "Spot unsafe drift after approval" — executed-scope-exceeds-approved is loud | P0 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R101** | **Post-decision outcome states.** After a terminal decision, the ask may carry a closure state: `executed / failed / cancelled / rolled_back / superseded` — recorded as **observations** (the decision never changes; terminal stays terminal, PRD 15). Unresolved closures render as `outcome: unknown`. | v0.1.0 | A closed ask shows its outcome; an ignored one shows unknown; no closure observation can reopen or alter the decision |
| **R102** | **Execution receipt attachment.** Producers or writeback adapters attach receipts — run URLs, artifact digests, job ids, changed-resource manifests — redacted, capped, and recorded like all untrusted content. Receipts are evidence, never credentials. | v0.1.0 | Receipt fixture stores zero secrets; the receipt renders on the card and narrative |
| **R103** | **Approved-vs-executed comparison.** The core compares the approved fingerprint/constraint set with the executed manifest: `match / partial / exceeded / divergent`. Comparison is derived-on-read from stored data; the producer's claim is untrusted input. | v0.1.0 | A manifest exceeding the approved scope reads `exceeded` with the exceeding resources named |
| **R104** | **Divergence alerting.** `exceeded/divergent` outcomes emit a loud, chained event (`outcome-divergence`) surfacing on `inbox`, the narrative, and the export; class config may demand acknowledgement before the divergence is considered reviewed. | v0.1.0 | Divergence fixture alerts without any approval path being opened |
| **R105** | **Portable decision packet.** `agentinbox export --ask <id> --packet` emits a self-contained bundle: ask, redacted evidence, decision, principal, constraints/edits (PRD 33), narrative (PRD 34), outcome, chain segment + verification instructions. Verifiable offline (PRD 20 §G posture). | v0.1.0 | A reviewer with only the packet verifies the chain segment and reads the full story — no store access |
| **R106** | **Outcome-aware traceability.** Closures join to the original ask, the policy decision, and (where present) the writeback record; the M24 reconstruction query covers outcomes end-to-end. | v0.1.0 | Reconstruction fixture walks ask → decision → execution → divergence without manual stitching |
| **R107** | **Outcome SLA.** Classes may configure a closure expectation (e.g., irreversible asks closed within 24 h); unclosed asks past it surface in `doctor` and the PRD 37 insights — never auto-closed. | v0.1.0 | An ignored irreversible approval appears in doctor findings as `outcome-pending-past-sla` |

## Non-goals

- The inbox does not execute anything, sandbox anything, or gate future actions on outcomes (PRD 29 E16).
- Receipts do not replace the enforcer's own logs.
- No silent auto-closure: unknown outcomes stay unknown until a principal records them.

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-79** | An approved deploy closes as executed with a matching manifest; the packet verifies offline |
| **SC-80** | An executed manifest exceeding approved scope reads `exceeded`, alerts, and is never silently absorbed |
| **SC-81** | A rollback after approval renders as `rolled_back` without touching the original decision record |
| **SC-82** | A packet-only reviewer reconstructs a decision end-to-end (M24 extension) |

## Traceability

| Requirement | Test |
|---|---|
| R101–R102 | `tests/outcomes/test_closure.py`, `test_receipts.py` |
| R103–R104 | `tests/outcomes/test_comparison.py`, `test_divergence.py` |
| R105 | `tests/outcomes/test_packet_export.py` |
| R106–R107 | `tests/outcomes/test_traceability.py`, `test_sla.py` |
