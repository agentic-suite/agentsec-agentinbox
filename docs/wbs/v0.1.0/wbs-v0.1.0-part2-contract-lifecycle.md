# WBS v0.1.0 — Part 2: Ask Contract & Lifecycle (M2–M3)

**BLUF:** **M2 opens the front door**: the versioned `ask/1.0` JSON contract with schema validation,
idempotent ingest keyed by `action_identity` + `session_id`, per-field/total size caps, and **redaction before
persistence** with receipts — plus the trusted/untrusted field classification (computed, never asserted).
**M3 gives the ask its durable shape**: the Ask/Transition/Claim/Delivery entities and the v0.1.0 state
machine (5 terminal states + delivery sub-states), append-only transitions, terminal-is-terminal.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M2 — Ask contract + idempotent ingest + redaction (E1, E6)

**Goal:** any producer can POST a valid ask and get back a stable ask id — twice if it retries, it gets the
same id and one record. Everything persisted is already redacted, everything classified. Malformed asks are
rejected with field-named diagnostics, never partially stored (SC-02).

**CUJ:** CUJ-13 groundwork (the contract integrators code against) · **Requirements:** [E1](../../prd/05-features.md),
[E6](../../prd/05-features.md), [PRD 15 §contract](../../prd/15-data-model.md),
[PRD 18 §trust](../../prd/18-approval-integrity.md) (trusted-field rules), [PRD 06](../../prd/06-security-baseline.md) (T13).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 2.D0 | **Design docs first** | Contract design: `ask/1.0` schema, canonicalization (args → `action_identity`), redaction pipeline placement, trusted-field rules | docs | reviewed before code | #124 | — | — |
| 2.1 | `ask/1.0` JSON Schema + models | Required fields (action_identity, tool, action, arguments, agent_id, session_id, environment, data_class, class, reason_code, policy_ref, criticality, requested_by, expires_at, context); JSON Schema shipped in-repo as the contract truth + fixtures | schema + models | valid payload round-trips; unknown fields tolerated-and-preserved (E18 posture) | #125 | — | E1 |
| 2.2 | Validation + size caps | Per-field and total (default 256 KiB) caps; `expires_at` mandatory and within the class ceiling; malformed → 400 with the **named failing field** | validator | SC-02 fixtures: missing/oversized/floating expiry each rejected, nothing partial persists | #126 | — | E1 |
| 2.3 | Canonical identity | Canonical-JSON args → `action_identity` hash (one canonical form, matching agentpolicy's construction); duplicate identity+session within the dedupe window → same ask id + `deduplicated` transition | identity module | 3× retry POST → one ask, one record, 2 dedupe transitions (SC-06) | #127 | — | E1, D-2 |
| 2.4 | Redaction before persistence | Pattern + shape redactor (keys, tokens, private keys, conn strings, PII classes) runs at ingest; receipts (field, class, count) stored; raw values never persisted anywhere | redactor | seeded secrets → 0 raw occurrences in store; receipts present (SC-21 groundwork) | #128 | — | E6 |
| 2.5 | Trusted/untrusted classification | `reason_code`/`policy_ref`/`criticality`/`class`/`environment`/`data_class` = trusted **only from authenticated producers** (agentpolicy adapter key); unauthenticated trusted fields marked **unverified**; agent-supplied strings always untrusted | classifier | unsigned producer → card-level fields render unverified (fixture); producers cannot self-assert trust | #129 | — | E19-posture, T13 |
| 2.6 | Ingest API + long-poll read | `POST /v1/asks` (loopback + socket token; producer uid recorded where the OS exposes it), `GET /v1/asks/{id}`, `GET /v1/asks/{id}?wait=25s` bounded long-poll | API | ingest p50 < 50 ms fixture; long-poll wakes on resolve; producers never busy-loop | #130 | — | E1, N-1 |
| 2.T | Tests | Contract fixtures (in-repo truth), idempotency, caps, redaction, classification, API | tests | coverage ≥ 95% | #131 | — | — |
| 2.C | Coverage gate | ≥95% on this milestone's modules | report | ≥95% | #132 | — | — |
| 2.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #133 | — | — |
| 2.CR | Code review | Findings resolved | log | no open findings | #134 | — | — |
| 2.D | Docs | Contract reference (`ask/1.0`), producer guide start, redaction policy | docs | updated + linked | #135 | — | — |
| 2.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 2.W | Update WBS | Checkpoint in index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [x] Duplicate ingest coalesces; malformed asks reject with field-named diagnostics and store nothing partial
- [x] No raw secret ever persists; trusted fields from unauthenticated producers render unverified

**Closed 2026-11-06.** Design: [ask contract](../design/v0.1.0/ask-contract.md) · Reference:
[ask contract](../reference/ask-contract.md) · Gate: recorded in the [index](wbs-v0.1.0-index.md).

---

## Milestone M3 — Ask record + lifecycle state machine (PRD 15)

**Goal:** the durable entities and the v0.1.0 state machine, written through the M1 store: `Ask` +
5 terminal states (`approved`/`denied`/`expired`/`cancelled`/`flood_denied`) + delivery/escalation sub-states
as recorded observations; `Transition` append-only with per-ask seq; `Claim` + `Delivery` entities persisted;
**terminal is terminal** (the only post-terminal write is a `late-answer` observation).

**CUJ:** — (core) · **Requirements:** [PRD 15 §entities/lifecycle](../../prd/15-data-model.md),
[PRD 02 §lifecycle](../../prd/02-architecture.md), D-4/D-24-posture.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 3.D0 | **Design docs first** | Lifecycle design: states, legal edges, transition payloads, derived-on-read expiry vs recorded-on-transition answers, crash-window resolution | docs | reviewed before code | #136 | — | — |
| 3.1 | Ask entity + persistence | Full `Ask` record through AskStore: all [PRD 15](../../prd/15-data-model.md) fields; `status` derived-on-read for expiry | store-backed entity | record round-trips; expiry reads correctly after restart | #137 | — | — |
| 3.2 | Transition log | Append-only per-ask transitions with `seq`, `from`, `to`, `at`, principal/channel/claim refs, structured redacted detail; append via `append_event` (gapless seq) | transitions | transition fixtures green; no mutation APIs exist (append only) | #138 | — | E2 |
| 3.3 | State machine + guard | The v0.1.0 legal-edge table enforced in one place; illegal transitions raise + are rejected (groundwork for the full fuzz in the forward slate) | state machine | approved→denied attempt → rejected + logged; all v0.1.0 edges exercised | #139 | — | — |
| 3.4 | Claim + Delivery entities | Claim (hashed secret, binding fields, state) and Delivery (attempt, status, error) persisted per [PRD 15](../../prd/15-data-model.md) | entities | records complete the audit join (SC-20 groundwork) | #140 | — | — |
| 3.5 | Resolve read-path (v0.1.0 statuses) | `resolve/1.0` read: `allow | deny | pending` with reason codes + `retryable`; the full vocabulary arrives with the bridge (M17) and the forward slate later | #141 | pending/expired/denied reads correct (E2 interplay) | — | — | — |
| 3.T | Tests | Entity round-trips, transition append rules, state-machine guard, derived expiry | tests | coverage ≥ 95% | #142 | — | — |
| 3.C | Coverage gate | ≥95% | report | ≥95% | #143 | — | — |
| 3.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #144 | — | — |
| 3.CR | Code review | Findings resolved | log | no open findings | #145 | — | — |
| 3.D | Docs | Lifecycle reference (states, edges, invariants) | docs | updated + linked | #146 | — | — |
| 3.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 3.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [x] All v0.1.0 states reachable via legal edges only; illegal transitions rejected + logged
- [x] Transitions are append-only; terminal is terminal; derived expiry reads correctly

**Closed 2026-11-06.** Design: [lifecycle](../design/v0.1.0/lifecycle.md) · Reference:
[lifecycle](../reference/lifecycle.md) · Gate: recorded in the [index](wbs-v0.1.0-index.md).

---

Part 2 green ⇒ asks can enter and live; proceed to [Part 3 (M4–M5)](wbs-v0.1.0-part3-scheduler-card.md).
