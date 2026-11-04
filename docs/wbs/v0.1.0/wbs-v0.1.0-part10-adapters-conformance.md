# WBS v0.1.0 — Part 10: Producer Adapters & Conformance (M18–M19)

**BLUF:** **M18 makes the first CUJ real end-to-end**: the agentpolicy reference adapter (signed trusted
fields), the universal `agentinbox ask` CLI + `--exec` (any process can gate itself), and the loopback HTTP
surface — install → first recorded approval in under five minutes, no chat platform, no cloud (E1, D-6/D-7;
CUJ-1). **M19 proves harness-agnosticism with a working framework adapter**: the LangGraph `interrupt()`
reference (pause → ask → answer → `Command(resume=…)`, durable across crashes; SC-25) plus the
**conformance kit** (`agentinbox conformance`) that any integration runs to self-verify against the contract
(E1, CUJ-13) — the kit that lets PRD 19's matrix grow by PR instead by fork.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M18 — Producer adapters: agentpolicy reference + CLI/HTTP/`--exec` (E1)

**Goal:** three producer paths, one contract: (1) the **agentpolicy adapter** — its `AskBroker` hands us the
ask with adapter-signed trusted fields; (2) the **universal CLI** — `agentinbox ask --file ask.json` and
`agentinbox ask --exec <command>` ("gate this exact command"), making any harness with a pre-exec hook
compatible before any bespoke adapter exists; (3) the **loopback HTTP API** — already built in M2, hardened
here (socket token, producer uid recording). CUJ-1 is measured at this milestone: install → first recorded
approval < 5 min.

**CUJ:** CUJ-1 (delivered) · **Requirements:** E1, [PRD 16 §E.1/E.2/E.5](../../prd/16-channel-and-harness-adapters.md),
[PRD 18](../../prd/18-approval-integrity.md) (T13/T14), D-6, D-7.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 18.D0 | **Design docs first** | Adapter design: producer contract profile (auth, signing of trusted fields, uid recording), the `--exec` gating semantics (exit codes on deny/expiry), the 5-minute onboarding path | docs | reviewed before code | #29 | — | — |
| 18.1 | agentpolicy reference adapter | `AskBroker.create` → `ask/1.0` POST with HMAC-signed trusted fields (shared key, configured via ref); resolve long-poll feeds agentpolicy's `approve/deny/resolve`; Wave-0 wiring documented ("Replit rule fires → laptop pings → deny with a reason") | adapter | end-to-end fixture: agentpolicy ask → terminal answer → `allow_ask_approved` back; trusted fields render verified | #30 | CUJ-1 | E1, E19-posture |
| 18.2 | Universal CLI producer | `agentinbox ask --file` (contract-validated) + `--exec <command>`: wraps the command, mints the ask, blocks on resolve, and **only executes on allow** (deny/expiry → the command never runs; exit codes per M0's contract) | CLI | `--exec` fixture: denied command never executes; approved executes exactly once | #31 | CUJ-1 | E1, R6 |
| 18.3 | Loopback API hardening | Socket-token auth enforced; producer uid recorded where the OS exposes it; rate limit on ingest; size caps re-verified at this level | API | T13/T14 fixtures: unauthenticated POST refused; uid in throttle keys | #32 | — | E4, T13 |
| 18.4 | **CUJ-1 timing target** | The 5-minute path: `pip install` → `init` (terminal-only config) → first recorded approval; measured + documented (the docs promise it, the fixture proves it) | onboarding | measured install→first-approval < 5 min on the field-test box (recorded for M24) | #33 | CUJ-1 | R1, N-31 |
| 18.5 | Producer guide | The integration doc: contract, auth, signing, `--exec`, exit codes, error taxonomy (field-named 400s), long-poll guidance | docs | a third party can integrate from the doc alone (reviewed against the fixture) | #34 | — | E1 |
| 18.T | Tests | Adapter round-trip, `--exec` gating, API hardening, onboarding fixture | tests | coverage ≥ 95% | #35 | — | — |
| 18.C | Coverage gate | ≥95% | report | ≥95% | #36 | — | — |
| 18.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #37 | — | — |
| 18.CR | Code review | Findings resolved | log | no open findings | #38 | — | — |
| 18.D | Docs | Producer reference (contract + auth + `--exec` + onboarding) | docs | updated + linked | #39 | — | — |
| 18.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 18.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] agentpolicy → inbox → answer → `allow_ask_approved` end-to-end; `--exec` never runs denied commands
- [ ] CUJ-1 measured < 5 minutes and documented; producers can integrate from the guide alone

---

## Milestone M19 — LangGraph reference adapter + conformance kit (E1, CUJ-13)

**Goal:** the proof that **any framework with a pause-for-human can emit an ask**: a LangGraph `human_gate`
node calling `interrupt(payload)` → adapter serializes to `ask/1.0` → any channel answers → the graph
resumes with `Command(resume=decision)`; both the ask and the checkpoint survive process death (resume-by-id
is idempotent — SC-25). Plus the **conformance kit** — the fixtures + `agentinbox conformance` harness
(round-trip ingest→answer→resolve, redaction, idempotency, exit codes, event shapes) — that third-party
adapters run to earn a PRD 19 matrix row.

**CUJ:** CUJ-13 · **Requirements:** E1, [PRD 16 §E.3](../../prd/16-channel-and-harness-adapters.md) (LangGraph
row), [PRD 19](../../prd/19-harness-compatibility.md) (conformance-tested label), [PRD 30 E18-posture](../../prd/30-correctness-conflict-abuse-hardening.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 19.D0 | **Design docs first** | Adapter pattern design: interrupt→ask / resume→resolve mapping, durability story (checkpoint + store both survive), the conformance kit's fixture set + self-verify command | docs | reviewed before code | #40 | — | — |
| 19.1 | LangGraph reference adapter | `human_gate` node + adapter: interrupt payload → ask; `?wait=` long-poll; `Command(resume=approve/deny)`; example graph shipped in `docs/adapters/langgraph/` | adapter | example graph pauses, is answered from a second surface, resumes once; replay does not double-execute the tool | #41 | CUJ-13 | E1 |
| 19.2 | Crash-resume durability | Process dies while waiting → durable ask persists; on resume the adapter queries by ask id and gets the recorded outcome; no lost decision, no double-execution | durability | SC-25: kill -9 mid-wait → restart → same single decision; tool executed once | #42 | CUJ-13 | E2, E1 |
| 19.3 | **Conformance kit** | `tests/fixtures/conformance/` + `agentinbox conformance`: contract round-trips (ask/resolve), redaction at ingest, idempotent ingest, exit-code mapping, event shapes, channel/producer invariants — runnable by any integration without our involvement | kit | the kit passes against the reference adapters in CI; a deliberately broken adapter **fails** it | #43 | — | E1, E10 |
| 19.4 | Adapter template + guide | The thin-adapter recipe (what an adapter must/must-never do per [PRD 16 §A](../../prd/16-channel-and-harness-adapters.md)); template repo structure for community adapters | guide | a reviewer can accept an adapter PR by requiring kit-green + contract review | #44 | — | E1, D-5 |
| 19.5 | Harness recipes (documented tier) | Claude Code `PreToolUse` hook recipe + Codex CLI wrapper recipe (documented, field-tested at M24; honest labels per PRD 19) | recipes | recipes reproduce against the kit; labels ready for the M25 matrix | #45 | — | R2, PRD 19 |
| 19.T | Tests | Adapter round-trip, crash-resume, conformance kit, recipes | tests | coverage ≥ 95% | #46 | — | — |
| 19.C | Coverage gate | ≥95% | report | ≥95% | #47 | — | — |
| 19.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #48 | — | — |
| 19.CR | Code review | Findings resolved | log | no open findings | #49 | — | — |
| 19.D | Docs | Framework-adapter guide + conformance-kit reference + recipe docs | docs | updated + linked | #50 | — | — |
| 19.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 19.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-25 green: pause → answer → resume, crash-safe, exactly-once tool execution
- [ ] The conformance kit gates adapters in CI; the adapter guide + recipes are complete for M24/M25

---

Part 10 green ⇒ anyone can produce asks and prove their integration; proceed to
[Part 11 (M20–M21)](wbs-v0.1.0-part11-failclosed-ops.md).
