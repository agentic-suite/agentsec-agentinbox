# WBS v0.1.0 — Part 1: Foundation & AskStore (M0–M1)

**BLUF:** **M0 builds the foundation fresh** (no predecessor to port): packaging as `agentsec-agentinbox`, the
CLI framework with **reserved exit codes**, the fail-closed config model, CI quality gates, and `doctor`. **M1
delivers the pluggable AskStore contract (E11)** with SQLite (reference) + memory drivers — the durable truth
layer every later milestone writes through, proven by its own conformance suite before anything builds on it.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M0 — Foundation & identity

**Goal:** agentinbox exists as an installable, CI-gated Python project with its full CLI surface, its reserved
exit codes (a compatibility contract the rest of the suite consumes), a fail-closed config model, and a
`doctor` skeleton. Nothing asks, nothing answers — the skeleton is honest about that.

**CUJ:** — (foundation) · **Requirements:** [PRD 02](../../prd/02-architecture.md) (interfaces, exit codes),
[PRD 13](../../prd/13-non-functional-requirements.md) (N-13, N-16, N-20, N-36..N-39), [PRD 14](../../prd/14-non-goals.md)
(scope guard).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 0.D0 | **Design docs first** | Foundation design: CLI surface, exit-code contract, config model (incl. `AGENTINBOX_HOME`), store layout sketch | docs | reviewed before code | #4 | — | — |
| 0.1 | Packaging + build | `pyproject.toml` for `agentsec-agentinbox` (dist name) / `agentinbox` (package + console script); `make setup/lint/typecheck/test/cov` | build config | `pip install -e .`; `make setup` green | #5 | — | E10 |
| 0.2 | CLI framework + command surface | Full command skeleton: `serve`, `ask`, `inbox`, `answer`, `gate`, `export`, `verify-log`, `channels`, `report`, `doctor`, `init`, `version` — stubs that refuse honestly ("not implemented in this milestone") | CLI | `agentinbox --help` lists commands; stubs exit non-zero with a clear message | #6 | — | — |
| 0.3 | **Reserved exit codes** | Freeze the contract: `0` approved/allow · `2` denied · `3` expired/timeout (deny class) · `4` unavailable/fail-closed · `5` still pending · `1` usage/internal — documented + tested as a compatibility fixture | exit-code module + fixtures | any command that maps a decision uses exactly these; fixture test green | #7 | — | R6 |
| 0.4 | Configuration model | TOML config load/validate ([PRD 15 §config](../../prd/15-data-model.md) sketch): classes (TTL/roster/ladder), channels, bus, store, throttle, limits, secrets-as-refs only (literal secret = **lint error**); `AGENTINBOX_HOME` override | config loader | invalid/missing config fails closed with an actionable error; `doctor` explains the effective config | #8 | — | E9 |
| 0.5 | CI & quality gate | `ruff` + `mypy --strict` + `pytest` + coverage ≥95% + DCO check; actions on PR and push | GitHub Actions | CI green on a trivial PR | #9 | — | — |
| 0.6 | `doctor` skeleton | Checks store path/permissions, config validity, schema versions, clock presence — each check exit-coded; grows in M1/M20/M21 | CLI | `doctor` returns 0 on a healthy fresh install, names failures otherwise | #10 | — | E9 |
| 0.7 | Identity & governance docs | README (the real one), LICENSE/CODEOWNERS/SECURITY finalized, PRD-linked CONTRIBUTING pointer | docs | docs match the repo identity | #11 | — | — |
| 0.T | Tests | Config fail-closed, CLI smoke, exit-code fixtures, doctor | tests | all new paths covered; coverage ≥ 95% | #12 | — | — |
| 0.C | Coverage gate | Enforce ≥95% on this milestone's modules | coverage report | ≥95%; no untested new path | #13 | — | — |
| 0.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #14 | — | — |
| 0.CR | Code review | Findings in [codereview-log.md](codereview-log.md), resolved | review log | no open findings | #15 | — | — |
| 0.D | Docs | Foundation design + CLI reference start; [PRD 12](../../prd/12-traceability.md) rows wired | docs | docs updated + linked here | #16 | — | — |
| 0.CI | Commit & push | On the feature branch | git | pushed | — | — | — |
| 0.W | Update WBS | Checkpoint appended to the [index](wbs-v0.1.0-index.md) Progress | WBS | checkpoint recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · all tests pass · coverage ≥ 95% · lint strict clean · docs updated · committed+pushed
- [x] `pip install -e .` + `make` targets work; `agentinbox --help` lists the full surface
- [x] Reserved exit codes frozen + fixture-tested; bad config fails closed; CI green

**Closed 2026-11-06.** Design: [foundation](../design/v0.1.0/foundation.md) · Reference:
[CLI](../reference/cli.md), [config](../reference/config.md) · Gate: 129 tests, coverage 100%,
`ruff` clean, `mypy --strict` clean · Checkpoint in the [index](wbs-v0.1.0-index.md).

---

## Milestone M1 — AskStore contract + drivers (E11)

**Goal:** define the **only** way the core touches state — the typed AskStore interface with its hard semantics
(idempotent create, CAS on status, atomic single-use claim consumption, monotonic gapless audit seq,
exactly-once timer recovery, durable-commit-before-ack, capability flags) — and implement **SQLite (WAL,
reference)** and **memory** drivers, both passing the conformance suite (crash/race/redelivery/chain fixtures).
Future drivers (Postgres, embedded) inherit this contract instead of re-deriving semantics
([PRD 16 §D](../../prd/16-channel-and-harness-adapters.md)).

**CUJ:** — (infrastructure) · **Requirements:** [E11](../../prd/05-features.md),
[PRD 15 §integrity](../../prd/15-data-model.md), [PRD 13](../../prd/13-non-functional-requirements.md) (N-8..N-12, N-22).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 1.D0 | **Design docs first** | Store design: the typed interface, the seven semantics, schema DDL (asks/transitions/claims/deliveries/floods/audit), migration/version table, capability-flag selection | docs | reviewed before code | #17 | — | — |
| 1.1 | AskStore interface | `create_or_get_by_identity`, `get`, `cas_status`, `issue_claim`, `consume_claim`, `list_pending`, `append_event`, `export_session` + capability flags (`single_writer`, `multi_writer`, `cluster_safe`) | interface module | mypy-clean protocol; fail-closed capability check helper | #18 | — | E11 |
| 1.2 | SQLite driver (reference) | WAL, fsync'd commits, 0600 store / 0700 dir defaults, indexes (pending-by-expiry, by-session, by-agent, transitions-by-seq, chain-by-seq) | driver | all semantics fixtures pass | #19 | — | E11, E2 |
| 1.3 | Memory driver | Same semantics, no disk — for tests/embedded ephemeral use | driver | same fixtures pass (both drivers share the suite) | #20 | — | E11 |
| 1.4 | **Store conformance suite** | The seven semantics as fixtures: idempotent create (dedupe window), CAS race (exactly one winner), claim single-use, gapless seq under concurrent appends, exactly-once recovery from persisted instants, durable-commit-before-ack (crash mid-write), capability-refusal | fixtures | both drivers green; a deliberately broken fake driver **fails** the suite | #21 | — | E11, E2 |
| 1.5 | Schema versioning + migrations | Version table; forward migrations on open; **downgrade refuses loudly**; migration tested old→new per release | migration module | old-store fixture opens and migrates; downgrade exits non-zero | #22 | — | E10 |
| 1.6 | Driver selection + entry points | `agentinbox.store` entry points for third-party drivers; unlisted/unconformance-passed drivers refuse to load with a clear error | loader | a fake third-party driver loads only when it passes conformance | #23 | — | E11 |
| 1.T | Tests | Driver units + the conformance suite run against both drivers | tests | coverage ≥ 95% | #24 | — | — |
| 1.C | Coverage gate | Enforce ≥95% on store modules | coverage report | ≥95% | #25 | — | — |
| 1.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #26 | — | — |
| 1.CR | Code review | Findings resolved | review log | no open findings | #27 | — | — |
| 1.D | Docs | Store reference (semantics + DDL + capability flags); conformance suite doc for third-party driver authors | docs | docs updated + linked | #28 | — | — |
| 1.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 1.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [x] The AskStore interface is the only state path; both drivers pass the full conformance suite
- [x] Capability-mismatched configs refuse to start; downgrade refuses loudly; store perms correct by default

**Closed 2026-11-06.** Design: [store](../design/v0.1.0/store.md) · Reference: [store](../reference/store.md) ·
Gate: 203 tests, coverage 97.71%, `ruff` clean, `mypy --strict` clean · Checkpoint in the
[index](wbs-v0.1.0-index.md).

---

Part 1 green ⇒ the truth layer exists and is proven; proceed to
[Part 2 (M2–M3)](wbs-v0.1.0-part2-contract-lifecycle.md).
