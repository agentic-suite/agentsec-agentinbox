# WBS v0.1.0 — Part 9: agentwatch Events & the agentpolicy Bridge (M16–M17)

**BLUF:** **M16 emits the ecosystem's vocabulary**: the v0.1.0 ask-lifecycle event set
(`ask-raised/delivered/delivery-failed/warned/escalated/answered/expired/cancelled/flood` +
`answer-rejected`) in the agentwatch security-event schema — additive per its versioned process, with
sink buffering + gap markers so a downed sink never blocks a decision (R5, PRD 20 §B; D-10). **M17 closes the
loop with the producer of record**: the agentpolicy resolve bridge mapping every agentinbox terminal state to
agentpolicy's reason codes (`allow_ask_approved`/`deny_ask_denied`/`human_gate_timeout`/`deny_ask_pending`/
`deny_ask_unknown`/`deny_action_identity_mismatch`/`ask_flood_throttled`), with `retryable`/`retry_after`/
`rescope_hint` so the agent gets an outcome it can act on — not a hang, not a failure (PRD 02 §lifecycle;
CUJ-4's ending).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M16 — agentwatch event set + sink (R5)

**Goal:** every gate transition lands in the schema the rest of the suite already reads: the nine v0.1.0 event
types with their evidence payloads, emitted with `emitter: "agentinbox"` + join keys (`ask_id`, `session_id`,
`agent_id`, `action_identity`, `traceparent`), an additive-version process with in-repo fixtures (the
schema's own stewardship rules), and a buffered sink that degrades loudly without ever blocking decisions.

**CUJ:** CUJ-10 (evidence join) · **Requirements:** R5, [PRD 20 §A/§B](../../prd/20-standards-and-claims.md),
[PRD 15 §events](../../prd/15-data-model.md), E9 (sink down), D-10.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 16.D0 | **Design docs first** | Event-set design: the nine types + evidence payloads, `event_version` additive process (fixtures + changelog per the schema's rules), sink buffering/degradation, join keys | docs | reviewed before code; agentwatch schema stewardship consulted | #282 | — | — |
| 16.1 | Event emitter | Typed emitters for the v0.1.0 set ([PRD 20 §B](../../prd/20-standards-and-claims.md) table): raised, delivered/delivery-failed, warned, escalated, answered, expired, cancelled, flood, answer-rejected (with distinct causes) | emitters | every transition in an integration run emits exactly its event with correct payload (SC-20 event trace) | #283 | CUJ-10 | R5 |
| 16.2 | Schema fixtures + versioning | In-repo fixtures validating the events against `security-event.schema.json`; additive-version discipline (new optional fields only; `event_version` bump process documented); never write back legacy shapes | fixtures | fixtures validate against the published schema; a breaking-shape fixture fails CI | #284 | — | R5, E10 |
| 16.3 | Sink + buffering | Sink writes buffered with a bounded queue; sink down → local chain remains authoritative, buffer flushes on recovery, **overflow emits a gap marker** (never silent loss); the decision path never blocks on the sink | sink | fault fixture: sink offline → decisions unaffected, gap marker on overflow, flush on recovery | #285 | — | E9 |
| 16.4 | Join keys + traceparent | `session_id`/`agent_id`/`ask_id`/`action_identity` on every event; `traceparent` carried when the producer supplied one (W3C correlation) | payload rules | cross-tool join fixture: an agentwatch record joins the agentpolicy decision + the inbox ask on common ids | #286 | — | R5 |
| 16.5 | **No-ML/no-drift guard** | Events are facts (states, principals, times, codes) — no inference, no enrichment beyond payload rules; a lint/test asserts no event field is derived from untrusted text | guard | negative fixture: untrusted-derived field fails | #287 | — | E5, N-1 |
| 16.T | Tests | Emitter payloads, schema validation, sink degradation, joins | tests | coverage ≥ 95% | #288 | — | — |
| 16.C | Coverage gate | ≥95% | report | ≥95% | #289 | — | — |
| 16.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #290 | — | — |
| 16.CR | Code review | Findings resolved | log | no open findings | #291 | — | — |
| 16.D | Docs | Event reference (types, payloads, versioning process, sink rules) | docs | updated + linked | #292 | — | — |
| 16.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 16.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] The nine v0.1.0 events validate against the published schema; fixtures + versioning process in-repo
- [ ] A downed sink never blocks a decision; gaps are marked; joins work cross-tool

---

## Milestone M17 — agentpolicy resolve bridge + rescope hints (PRD 02 lifecycle)

**Goal:** the Wave-0 loop closes: agentpolicy says `ask` → agentinbox holds the human round-trip → the
producer gets a **structured outcome in agentpolicy's own reason-code vocabulary**: approved →
`allow_ask_approved`; denied → `deny_ask_denied` (+ the human's reason); expired → `human_gate_timeout` with
`retryable=false` + a **rescope hint** ("narrow to db:staging/customers, or request a standing approval");
flood → `ask_flood_throttled` with retry-after-window semantics; unknown/mismatch → the deny family. The
agent **acts** on the outcome instead of hanging — CUJ-4's "rescope-not-failure" made real.

**CUJ:** CUJ-4 (ending), CUJ-8 (reason delivered) · **Requirements:** [PRD 02 §lifecycle table](../../prd/02-architecture.md),
[PRD 15 §resolve/1.0](../../prd/15-data-model.md), R3 (rescope), agentpolicy's `ask.py` reason codes (reused,
never re-invented).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 17.D0 | **Design docs first** | Bridge design: the state → reason-code mapping table (frozen), `resolve/1.0` payload (`status`, `reason_code`, `explanation`, `retryable`, `retry_after`, `rescope_hint`, `answered_by`, `action_identity`), rescope-hint authoring rules | docs | reviewed before code; codes match agentpolicy's registry exactly | #293 | — | — |
| 17.1 | Reason-code bridge | The frozen mapping implemented once; codes imported from the shared registry (no string drift); `ask_flood_throttled` added to agentpolicy's registry via its process | bridge | outcome matrix fixture: every terminal state → the exact code; a drift test fails on mismatch | #294 | CUJ-4 | R3, R5 |
| 17.2 | Rescope hints | Class-aware hint authoring (config per class + deny-reason echo); hints are advisory text the **agent** reads — escaped, capped, never executed, labeled "human/derived input, not policy" | hints | SC-05: hint present in the deny; agent re-asks narrower (new identity, no state reuse) | #295 | CUJ-4 | R3 |
| 17.3 | `retryable` / `retry_after` | Denied-on-flood and rate-shaped outcomes carry retry semantics the agent honors (matching agentpolicy's `rate-limit` posture); expiry carries `retryable=false` | semantics | producer fixture: flood → waits `retry_after`, re-asks; expiry → no auto-retry | #296 | — | R7 |
| 17.4 | Resolve API + long-poll integration | `GET /v1/asks/{id}?wait=` returns `resolve/1.0`; the CLI `gate`/`ask` and adapters consume it; idempotent re-reads return the same decision | API | double-resolve fixture: identical payloads, one decision | #297 | — | E1 |
| 17.5 | Unknown/mismatch family | `deny_ask_unknown` for vanished ids; `deny_action_identity_mismatch` when the resolve call presents different identity — **an approval for X never releases Y** (D-2) | guards | mismatch fixture: ask-B args under ask-A's id → deny with the mismatch code | #298 | — | D-2, E4 |
| 17.T | Tests | Mapping matrix, hints, retry semantics, idempotent resolve, mismatch | tests | coverage ≥ 95% | #299 | — | — |
| 17.C | Coverage gate | ≥95% | report | ≥95% | #300 | — | — |
| 17.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #301 | — | — |
| 17.CR | Code review | Findings resolved | log | no open findings | #302 | — | — |
| 17.D | Docs | Resolve-contract reference (`resolve/1.0`, the mapping table, rescope-hint rules) | docs | updated + linked | #303 | — | — |
| 17.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 17.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Every terminal state resolves to the exact agentpolicy reason code (drift test enforces it)
- [ ] Expired asks return rescope-not-failure; approvals never release a different identity

---

Part 9 green ⇒ the ecosystem sees every gate (M16) and producers get real outcomes (M17); proceed to
[Part 10 (M18–M19)](wbs-v0.1.0-part10-adapters-conformance.md).
