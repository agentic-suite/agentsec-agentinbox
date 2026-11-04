# WBS v0.1.0 — Part 8: Multi-Channel Truth & Audit Chain (M14–M15)

**BLUF:** **M14 proves the one-truth claim**: the same ask answered on any surface resolves once, with the
record naming the winning channel/principal/time; races resolve first-wins; late answers are logged no-ops;
channel failover loses nothing (R2, CUJ-3/9; SC-07/08/18/19). **M15 builds the evidence**: the append-only,
hash-chained audit log with `verify-log`, tamper detection, `export` (JSONL/CSV, chain carried), retention
with chain-preserving pruning — the artifact auditors and postmortems reconstruct from (R5, CUJ-10; SC-20).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M14 — Multi-channel single truth (R2)

**Goal:** "approved in the terminal" and "approved from the second surface" are the **same fact with one
provenance**: byte-parity decision records across channels (modulo channel/principal fields), one resolve,
surfaces updating to the outcome within their poll interval, and a race + late-answer discipline that holds
across every pair of channels v0.1.0 ships (terminal × desktop × webhook-display × CI-wait).

**CUJ:** CUJ-3, CUJ-9 · **Requirements:** R2, E3/E4 (pipeline shared), [PRD 16 §F](../../prd/16-channel-and-harness-adapters.md),
D-5.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 14.D0 | **Design docs first** | Parity design: the shared pipeline as the single choke point, per-surface outcome refresh (poll intervals), the parity fixture matrix (channel pairs), race/late-answer semantics across surfaces | docs | reviewed before code | #260 | — | — |
| 14.1 | **Channel parity fixtures** | Same ask answered on each channel → **byte-identical** decision records modulo channel/principal; outcome text renders on the losing surface within its poll interval | fixtures | SC-07 green for every v0.1.0 channel pair | #261 | CUJ-3 | R2 |
| 14.2 | Cross-channel races | Terminal + second surface answered within 200 ms (mocked): exactly one `ask-answered`; loser logs `answer-rejected(late)` with winner identity + time; **no double-execution path exists** (resolve idempotent) | race fixtures | SC-08 green; no surface can produce a second decision | #262 | CUJ-9 | E4 |
| 14.3 | Late answers | An answer after resolution on any surface = visible no-op: responder told "already resolved by X at T", state untouched, event recorded | late answers | SC-19 green on every channel pair | #263 | — | E4 |
| 14.4 | Failover matrix | One channel down → others unaffected; the downed surface later updates to the outcome (not re-asked); delivery failures enumerated per ask | failover | SC-18 re-run at integration level (beyond M13's unit fixtures) | #264 | — | E7 |
| 14.5 | Channel conformance suite (all channels) | The M7-authored suite now runs terminal + desktop + webhook + CI-wait: deliver/authenticate/no-decide + parity + race fixtures per channel | conformance | every channel green; a fake deciding-channel fails the suite | #265 | — | R2, D-5 |
| 14.T | Tests | Parity matrix, races, late answers, failover, conformance | tests | coverage ≥ 95% | #266 | — | — |
| 14.C | Coverage gate | ≥95% | report | ≥95% | #267 | — | — |
| 14.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #268 | — | — |
| 14.CR | Code review | Findings resolved | log | no open findings | #269 | — | — |
| 14.D | Docs | Channel-parity reference (the one-truth rules + the fixture matrix) | docs | updated + linked | #270 | — | — |
| 14.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 14.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Byte-parity across all v0.1.0 channel pairs; races resolve once; late answers are visible no-ops
- [ ] The channel conformance suite gates every channel equally — no channel can decide

---

## Milestone M15 — Audit chain, verify-log + export (R5)

**Goal:** the record an auditor trusts: every transition/delivery/flood appends a chained `AuditEntry`
(`seq`/`prev_hash`/`entry_hash` over canonical bytes), `verify-log` recomputes and names the first bad seq,
`export --session/--ask --format jsonl|csv` emits ordered evidence with the chain included (verifiable
**offline**), retention prunes with chain markers so verification still passes, and a corrupted row is
**detected, not skipped**.

**CUJ:** CUJ-10 · **Requirements:** R5, [PRD 15 §integrity](../../prd/15-data-model.md), [PRD 22 §D](../../prd/22-operations-and-governance.md)
(retention), D-10.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 15.D0 | **Design docs first** | Chain design: canonical-JSON digest, hash construction, gapless seq via the M1 store, offline verification format, retention/pruning markers, export shapes | docs | reviewed before code | #271 | — | — |
| 15.1 | Append-only chain | Every Transition/Delivery/FloodEvent appends `AuditEntry` via `append_event` (gapless seq from the store contract); payload digests over canonical bytes | chain | concurrent appends keep seq gapless (M1 fixture reused at this level) | #272 | — | R5, E11 |
| 15.2 | `verify-log` | Recompute the chain; first mismatch names its seq; tamper fixture (flip one payload) **must** be detected | verifier | SC-20: clean chain verifies; tamper detected by exact seq | #273 | CUJ-10 | R5 |
| 15.3 | **Export** | `agentinbox export --session/--ask --format jsonl | csv`: ordered transitions with principals/channels/reason codes/redaction receipts + the chain; exports written on request only; export itself is audited | CLI | #274 | — | CUJ-10 | R5 |
| 15.4 | Retention + pruning | Policy `never/90d/1y/custom`; pruning emits a chain marker so `verify-log` still passes; spool jobs pruned aggressively (movement ≠ evidence) | retention | pruned-chain fixture verifies; marker recorded | #275 | — | R5, E12 |
| 15.5 | Read-only evidence posture | Exports are read-only artifacts; a re-import path does **not** exist (evidence leaves, it never re-enters as authority) | posture | no import-authority code path exists (negative test) | #276 | — | D-10 |
| 15.T | Tests | Chain appends, verify, tamper, export shapes, retention | tests | coverage ≥ 95% | #277 | — | — |
| 15.C | Coverage gate | ≥95% | report | ≥95% | #278 | — | — |
| 15.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #279 | — | — |
| 15.CR | Code review | Findings resolved | log | no open findings | #280 | — | — |
| 15.D | Docs | Audit reference (chain, verify, export, retention, offline verification recipe) | docs | updated + linked | #281 | — | — |
| 15.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 15.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-20 green: reconstruction + offline verification; tampering detected by exact seq
- [ ] Retention prunes without breaking verification; exports are read-only by construction

---

Part 8 green ⇒ one truth across surfaces (M14) and defensible evidence (M15); proceed to
[Part 9 (M16–M17)](wbs-v0.1.0-part9-events-bridge.md).
