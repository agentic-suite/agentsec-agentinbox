# WBS — agentinbox v0.1.0 (Index)

**BLUF:** v0.1.0 delivers the **entire ask lifecycle with zero external dependencies**: the `ask/1.0` contract
and idempotent ingest, the durable store + crash-safe scheduler (**timeout = deny**), the decision card
(zero-context correct in <15 s), **unforgeable single-use claims + authenticated answers**, terminal/TUI +
desktop-notification + CI-checkpoint + signed-webhook channels (**no chat platform required**), the
filesystem-spool bus (movement ≠ truth), escalation ladders, flood protection, the hash-chained audit log +
agentwatch event set, the agentpolicy resolve bridge, and the producer adapters (agentpolicy reference,
generic CLI/HTTP, LangGraph `interrupt()`, `--exec`). **Twenty-six milestones (M0–M25)** across **thirteen
detail files**; **field tests (M24) and release readiness (M25) are last.**

> **Milestone ranges by intent:** **M0–M9** = the core engine (store → contract → lifecycle → scheduler →
> card → claims → terminal → desktop → bus) · **M10–M14** = reach (CI, escalation, flood, webhook, multi-channel
> truth) · **M15–M19** = evidence + producers (audit chain, agentwatch, resolve bridge, adapters,
> conformance) · **M20–M23** = hardening + ops + docs · **M24–M25** = field tests + release. The WBS builds the
> whole set to one release; nothing in the forward slate (PRDs 24–30) is in scope — v0.1.0 is the
> [PRD 05](../../prd/05-features.md) §A/§B P0 set only (R1–R7 + E1–E12).

## Standard milestone exit criteria (applies to EVERY milestone)

Every milestone is worked in this order:

1. **Design docs written first** — the milestone's `.D0` work item opens it (design + reference docs for the
   subsystem, written before code).
2. **Implement** the milestone's work items (one ticket at a time: test first (RED) → implement (GREEN)).
3. **Close with the standing gates:**
   - [ ] **All tests pass** (`make test`) — the `.T` work item
   - [ ] **Coverage ≥ 95%** (enforced in CI) — the `.C` work item
   - [ ] **Lint strict clean** — `ruff` zero violations; `mypy --strict` clean — the `.L` work item
   - [ ] **Code review complete** — findings in [codereview-log.md](codereview-log.md), all resolved — `.CR`
   - [ ] **Docs updated** — design/reference docs + the [PRD 12](../../prd/12-traceability.md) requirement →
     test row moves with the work — `.D`
   - [ ] **Committed & pushed** — the work is on the feature branch — `.CI`
   - [ ] **WBS updated** — a dated checkpoint (commit refs + gate result) appended to the Progress section — `.W`

> Every milestone therefore carries **eight standing gate work items** — `.D0` design · `.T` tests · `.C`
> coverage · `.L` lint/types · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS — in addition to its
> implementation items.

## Standard milestone closure (applies to EVERY milestone)

A milestone is **closed** only when all of these hold:

1. **Implemented** — every work item done; no "core slice", no partials.
2. **Tests green** — the milestone's tests pass, and the standard gates run **once at milestone end** (full
   suite, coverage ≥95%, `ruff`, `mypy --strict`) — not per ticket.
3. **Committed & pushed** — the work is on the feature branch, pushed.
4. **Tracking issue closed** — or explicitly commented with status.
5. **Docs updated** — the milestone's design/reference docs updated and linked from this WBS.
6. **Checkpoint recorded** — a dated line appended to the Progress section (commit refs + gate result).
7. **Field tests (M24) and release readiness (M25) are the final milestones** — **M25 tags `v0.1.0`**.

> **One ticket at a time:** per work item, write the test first (RED) → implement (GREEN) → next. Do **not** run
> the full suite between tickets; run it at milestone end only.

## Milestones

| M | Name | Detail file |
|---|---|---|
| **M0** | **Foundation & identity** (fresh build: packaging, CLI, exit codes, config, CI) | [Part 1](wbs-v0.1.0-part1-foundation-store.md) |
| M1 | AskStore contract + SQLite/memory drivers (E11) | [Part 1](wbs-v0.1.0-part1-foundation-store.md) |
| M2 | Ask contract + idempotent ingest + redaction (E1, E6) | [Part 2](wbs-v0.1.0-part2-contract-lifecycle.md) |
| M3 | Ask record + lifecycle state machine (PRD 15) | [Part 2](wbs-v0.1.0-part2-contract-lifecycle.md) |
| M4 | Scheduler, TTL/expiry + crash-safe recovery (E2, E8) | [Part 3](wbs-v0.1.0-part3-scheduler-card.md) |
| M5 | Decision card renderer + untrusted rendering (R1, E5) | [Part 3](wbs-v0.1.0-part3-scheduler-card.md) |
| M6 | Claims + answer-verification pipeline (E3, E4) | [Part 4](wbs-v0.1.0-part4-claims-terminal.md) |
| M7 | Terminal/TUI channel (R2) | [Part 4](wbs-v0.1.0-part4-claims-terminal.md) |
| M8 | Desktop notification channel (R2) | [Part 5](wbs-v0.1.0-part5-desktop-bus.md) |
| M9 | AskBus: contract + in-proc + filesystem spool (E12) | [Part 5](wbs-v0.1.0-part5-desktop-bus.md) |
| M10 | CI checkpoint: `gate` + reserved exit codes (R6) | [Part 6](wbs-v0.1.0-part6-ci-escalation.md) |
| M11 | Escalation ladder (R4) | [Part 6](wbs-v0.1.0-part6-ci-escalation.md) |
| M12 | Flood guard: throttling + auto-deny + digest (R7) | [Part 7](wbs-v0.1.0-part7-flood-webhook.md) |
| M13 | Webhook channel (display-only) + delivery accounting (E7) | [Part 7](wbs-v0.1.0-part7-flood-webhook.md) |
| M14 | Multi-channel single truth: parity, races, failover (R2) | [Part 8](wbs-v0.1.0-part8-parity-audit.md) |
| M15 | Audit chain, verify-log + export (R5) | [Part 8](wbs-v0.1.0-part8-parity-audit.md) |
| M16 | agentwatch event set + sink (R5, PRD 20 §B) | [Part 9](wbs-v0.1.0-part9-events-bridge.md) |
| M17 | agentpolicy resolve bridge + rescope hints (PRD 02 lifecycle) | [Part 9](wbs-v0.1.0-part9-events-bridge.md) |
| M18 | Producer adapters: agentpolicy reference + CLI/HTTP/`--exec` (E1) | [Part 10](wbs-v0.1.0-part10-adapters-conformance.md) |
| M19 | LangGraph reference adapter + conformance kit (E1, CUJ-13) | [Part 10](wbs-v0.1.0-part10-adapters-conformance.md) |
| M20 | Fail-closed fault matrix + doctor hardening (E9) | [Part 11](wbs-v0.1.0-part11-failclosed-ops.md) |
| M21 | Ops: service units, backup/restore, migrations, `report` (E10, PRD 22/13) | [Part 11](wbs-v0.1.0-part11-failclosed-ops.md) |
| M22 | Security hardening sweep + evidence scanner (PRD 06/18) | [Part 12](wbs-v0.1.0-part12-security-docs.md) |
| M23 | Docs completion: reference, quickstart, runbooks, recipes | [Part 12](wbs-v0.1.0-part12-security-docs.md) |
| **M24** | **Field tests** (SC-01–SC-26 + the 15-second study) | [Part 13](wbs-v0.1.0-part13-fieldtest-release.md) |
| **M25** | **Release readiness** (last; tags `v0.1.0`) | [Part 13](wbs-v0.1.0-part13-fieldtest-release.md) |

## Issues & milestones (GitHub)

**Created 2026-11-04.** Every work item ships as a **GitHub issue** under milestone `0.1.0 — M<n> <name>` (labels `0.1.0`, `wbs`; gate items also `gate`). Body standard: Why · What · How · Data & schema impact · Security & privacy · Edge cases · Testing · Risks & mitigations · Acceptance criteria · Dependencies · References · Definition of done; marker `<!-- wbs:<file>:<item> -->`. **The `Issue` column in each part file holds the live number.** The two process items per milestone (`.CI` commit, `.W` WBS checkpoint) are tracked here, not as issues.

**26 milestones · 300 issues** (`agentic-suite/agentsec-agentinbox`). Issue numbers reflect creation order (part files are processed in filename order), so ranges are not consecutive across the table.

| M | Milestone | Issues | M | Milestone | Issues |
|---|---|---|---|---|---|
| M0 | Foundation & identity | #4–#16 (13) | M13 | Webhook channel (display-only) + delivery accounting (E7) | #249–#259 (11) |
| M1 | AskStore contract + drivers (E11) | #17–#28 (12) | M14 | Multi-channel single truth (R2) | #260–#270 (11) |
| M2 | Ask contract + idempotent ingest + redaction (E1, E6) | #124–#135 (12) | M15 | Audit chain, verify-log + export (R5) | #271–#281 (11) |
| M3 | Ask record + lifecycle state machine (PRD 15) | #136–#146 (11) | M16 | agentwatch event set + sink (R5) | #282–#292 (11) |
| M4 | Scheduler, TTL/expiry + crash-safe recovery (E2, E8) | #147–#157 (11) | M17 | agentpolicy resolve bridge + rescope hints (PRD 02 lifecycle) | #293–#303 (11) |
| M5 | Decision-card renderer + untrusted rendering (R1, E5) | #158–#168 (11) | M18 | Producer adapters: agentpolicy reference + CLI/HTTP/`--exec` (E1) | #29–#39 (11) |
| M6 | Claims + answer-verification pipeline (E3, E4) | #169–#180 (12) | M19 | LangGraph reference adapter + conformance kit (E1, CUJ-13) | #40–#50 (11) |
| M7 | Terminal/TUI channel (R2) | #181–#191 (11) | M20 | Fail-closed fault matrix + doctor hardening (E9) | #51–#61 (11) |
| M8 | Desktop notification channel (R2) | #192–#202 (11) | M21 | Ops: service units, backup/restore, migrations, `report` (E10, PRD 22) | #62–#73 (12) |
| M9 | AskBus: contract + in-proc + filesystem spool (E12) | #203–#214 (12) | M22 | Security hardening sweep + evidence scanner (PRD 06/18) | #74–#85 (12) |
| M10 | CI checkpoint (R6) | #215–#226 (12) | M23 | Docs completion (reference, quickstart, runbooks, recipes) | #86–#97 (12) |
| M11 | Escalation ladder (R4) | #227–#237 (11) | M24 | Field tests (SC-01–SC-26 + the 15-second study) | #98–#110 (13) |
| M12 | Flood guard (R7) | #238–#248 (11) | M25 | Release readiness (tags `v0.1.0`) | #111–#123 (13) |

## Progress

- **2026-11-06 — M0 Foundation & identity closed.** Issues #4–#16. Commits on `feat-0.1.0`:
  `3f5626a` design · `f1d425f` packaging · `0275552` CLI surface · `7acfc44` exit codes ·
  `6df485f` config/`init` · `5707635` CI · `0f30b01` doctor · `d7e423e` identity docs ·
  `199fe66` reference docs + review log.
  **Gate (run once at milestone end):** 129 tests pass · coverage **100%** (≥95 required) ·
  `ruff` clean · `mypy --strict` clean · DCO signed. Workflow YAML validated; 8 review findings
  resolved ([log](codereview-log.md)). Next: **M1** (`1.D0` store design).
- **2026-11-06 — M1 AskStore contract + drivers (E11) closed.** Issues #17–#28. Commits on `feat-0.1.0`:
  `07fd35a` design+interface · `539d6da` SQLite · `2634b4a` memory · `bb1ce53` conformance · `87e0742`
  migrations · `727af69` loader. **Gate:** 203 tests pass · coverage **97.71%** · `ruff` clean ·
  `mypy --strict` clean · DCO signed. Both drivers pass the same suite; a broken driver fails it; a store
  newer than the build refuses loudly. Next: **M2** (`2.D0` ask contract).
- **2026-11-06 — M2 Ask contract + ingest + redaction (E1, E6) closed.** Issues #124–#135. Commits on
  `feat-0.1.0`: `d4fad27` schema+model · `5604e42` validation/identity/redaction/trust · `38acdda` API.
  **Gate:** 268 tests pass · coverage **96.45%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  SC-02/SC-06 proven at the unit level; secrets never reach the store; trust cannot be self-asserted.
  Next: **M3** (`3.D0` lifecycle).

## PRD coverage matrix (every doc 00–30)

| PRD | Topic | Milestone(s) |
|---|---|---|
| **PRD 00** | Press release / FAQ | narrative; validated at M25 |
| **PRD 01** | Why | context (all milestones) |
| **PRD 02** | Architecture (components, trust boundaries, failure semantics) | M0–M20 |
| **PRD 03** | Landscape (control patterns ported) | M7–M15 (the pattern sources) |
| **PRD 04** | Users, stories & CUJs (CUJ-1..14) | M2–M25 |
| **PRD 05** | Features R1–R7 + E1–E12 (v0.1.0 P0) | M0–M22 |
| **PRD 06** | Security baseline (invariants, threats) | M6, M20, M22 |
| **PRD 07** | Success metrics | M21 (`report`), M24 (study), M25 |
| **PRD 08** | Risks | cross-cutting; reviewed at M24 |
| **PRD 09** | Roadmap | M25 (release notes scope) |
| **PRD 10** | Feature parity | M18–M19 (producer parity), M25 |
| **PRD 11** | Decisions D-1..D-27 | cross-cutting (honored every milestone) |
| **PRD 12** | Traceability (maintained) | every milestone |
| **PRD 13** | NFRs (performance, portability, offline) | M1, M4, M21 |
| **PRD 14** | Non-goals (scope guard — **the forward slate is out of scope**) | every milestone |
| **PRD 15** | Data model + lifecycle + contracts | M2–M4, M16–M17 |
| **PRD 16** | Channel/bus/store/producer adapters | M7–M13, M18–M19 |
| **PRD 17** | Scenario catalog SC-01–SC-26 (v0.1.0 gates) | fixtures M1–M22; executed M24 |
| **PRD 18** | Approval integrity (pipeline, claims, assurance) | M6, M22 |
| **PRD 19** | Harness compatibility (honest labels) | M18–M19, M25 |
| **PRD 20** | Standards, events & claims (§B event set) | M16, M22 (claims lint), M25 |
| **PRD 21** | Evidence register & method | M22 (scanner), M24 (study), M25 |
| **PRD 22** | Operations & governance | M21 |
| **PRD 23** | Enterprise adoption (honest gaps) | M25 (claims, no over-claim) |
| **PRD 24** | Constrained approvals, effects & ask semantics | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 25** | Evidence, previews & decision quality | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 26** | Approver experience, teams & operations | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 27** | Governance, identity & extensibility | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 28** | Review loops & operational orchestration | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 29** | Trust maturity, writeback & human performance | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |
| **PRD 30** | Correctness, conflict & abuse hardening | deferred — v0.1.0 out of scope ([PRD 14](../prd/14-non-goals.md)); forward-slate WBS written at v0.1.x |

## Requirements → milestone (v0.1.0: R1–R7, E1–E12)

| Req | Milestone | Req | Milestone |
|---|---|---|---|
| R1 decision card | M5 | E1 ask contract + idempotent ingest | M2, M18 |
| R2 any-channel answer, one truth | M7–M9, M13, **M14** | E2 durable store + recovery | M1, M4 |
| R3 timeout = deny + warning | **M4** (+M17 rescope) | E3 unforgeable claims | M6 |
| R4 escalation ladder | M11 | E4 answer authN/authZ | M6 |
| R5 audit trail (chain + events) | M15, M16 | E5 injection-resistant rendering | M5 |
| R6 CI checkpoints | M10 | E6 redaction-before-persistence | M2, M22 |
| R7 flood protection | M12 | E7 delivery accounting + hygiene | M13 |
| | | E8 time correctness | M4 |
| | | E9 fail-closed degradation | M20 |
| | | E10 versioning + compatibility | M21 |
| | | E11 pluggable store contract | M1 |
| | | E12 pluggable bus (movement ≠ truth) | M9 |

## CUJ → milestone (CUJ-1..14)

| CUJ | Journey (short) | Milestone |
|---|---|---|
| **CUJ-1** | First gate in five minutes | **M18** (end-to-end producer→terminal→record) |
| **CUJ-2** | Zero-context correct call in <15 s | **M5** |
| **CUJ-3** | Approve a prod drop from a second surface | **M14** |
| **CUJ-4** | Timeout with a rescope, not a hang | **M4** (+M17 hint) |
| **CUJ-5** | 3 a.m. escalation to on-call | **M11** |
| **CUJ-6** | Flood neutralized | **M12** |
| **CUJ-7** | CI pipeline halts on an ask | **M10** |
| **CUJ-8** | Deny with a reason that teaches | **M6** |
| **CUJ-9** | Same ask, two channels, one truth | **M14** |
| **CUJ-10** | Audit reconstruction | **M15** |
| **CUJ-11** | Poisoned context in the ask | **M5** (+M22 corpus gate) |
| **CUJ-12** | Air-gapped / offline day | **M21** |
| **CUJ-13** | Plugin: framework interrupt → inbox → resume | **M19** |
| **CUJ-14** | Enterprise reviewer honesty | **M25** (claims lint + gap docs) |

> Every CUJ appears in exactly one milestone's **CUJ** column in its part file. No CUJ is orphaned; no
> milestone claims a CUJ it does not deliver.


## Scenario → milestone (SC-01..SC-26, [PRD 17](../prd/17-scenarios.md))

| Scenario | What it proves | Authored / gated at | Executed |
|---|---|---|---|
| **SC-01** | First terminal ask, zero config | M7 (terminal channel) | **M24** |
| **SC-02** | Malformed/oversized ask rejected, nothing partial | M2 (ingest) | **M24** |
| **SC-03** | Zero-context correct call (the 15-second spine) | M5 (card + corpus) | **M24** (study) |
| **SC-04** | Missing-context honesty (`unknown`, never guessed) | M5 | **M24** (study) |
| **SC-05** | Rescope hint changes agent behavior | M17 (resolve bridge) | **M24** |
| **SC-06** | Duplicate ingest coalesces | M2 | **M24** |
| **SC-07** | Second-surface approve, terminal parity | M14 | **M24** |
| **SC-08** | Race: two answers, one decision | M6 + M14 | **M24** |
| **SC-09** | Timeout = deny with warning | M4 | **M24** |
| **SC-10** | Expiry survives crash + clock jumps | M4 | **M24** |
| **SC-11** | 3 a.m. escalation drill | M11 | **M24** |
| **SC-12** | Ladder exhaustion denies, TTL unchanged | M11 | **M24** |
| **SC-13** | Flood pack: N denies, 1 event, 1 digest | M12 | **M24** |
| **SC-14** | Legitimate burst survives (with SC-13) | M12 | **M24** |
| **SC-15** | CI pipeline halts and resumes on answer | M10 | **M24** |
| **SC-16** | Deterministic CI exit codes | M10 | **M24** |
| **SC-17** | Self-review denied | M6 | **M24** |
| **SC-18** | Channel failover loses nothing | M13 + M14 | **M24** |
| **SC-19** | Late answer is a visible no-op | M14 | **M24** |
| **SC-20** | Reconstruction + chain verification | M15 | **M24** |
| **SC-21** | Evidence carries no secrets | M22 (scanner) | **M24** |
| **SC-22** | Spoof/replay/forge matrix (release gate) | M6 + M22 | **M24** |
| **SC-23** | Injection corpus (release gate) | M5 + M22 | **M24** |
| **SC-24** | Fault-injection matrix (fail-closed) | M20 | **M24** |
| **SC-25** | Framework adapter round-trip + crash resume | M19 | **M24** |
| **SC-26** | Offline day | M21 | **M24** |

**Release gating at M24:** SC-13, SC-22, SC-23 (and SC-24's fail-closed matrix) are release-blocking — a red
verdict blocks M25. The scenario catalog's SC-27..SC-67 belong to the forward slate (PRDs 24–30) and are
explicitly out of v0.1.0 scope.

## Decisions (PRD 11)

D-1 (timeout = deny, always) → M4 · D-2 (identity-bound approvals) → M6 · D-3 (claim + principal, both) → M6 ·
D-5 (channels are renderers, not deciders) → M5/M7 · D-6 (open, SDK-agnostic contract) → M2/M18 · D-7
(terminal-first, no chat platform) → M7–M9 · D-8 (local-first single store) → M1 · D-10 (agentwatch is the only
vocabulary) → M16 · D-11 (escalation never extends TTL) → M11 · D-12 (flood denial is a decision) → M12 ·
D-13/D-14 (queue moves, store decides; filesystem bus, one box) → M9.

## v0.1.0 release gate (all milestones)

- [ ] M0–M25 exit criteria satisfied (design docs first, tests, coverage ≥95%, ruff/mypy, review, docs)
- [ ] Every R1–R7 + E1–E12 demonstrated by its acceptance test ([PRD 12](../../prd/12-traceability.md) rows green)
- [ ] Timeout never allows (runtime zero-allow counter + fixtures); every failure path is deny-or-pending (M20)
- [ ] SC-01–SC-26 executed with the honest report published (M24); attack packs green
- [ ] Install → first recorded approval < 5 minutes on the field-test box (CUJ-1)
- [ ] Full lifecycle works with **no chat platform and no network** (CUJ-12)
- [ ] agentwatch events join to agentpolicy decisions on common ids; chain verifies offline (M15–M17)
- [ ] Compatibility matrix published with honest labels only (field-tested / conformance-tested / documented /
  not-supported) (M25)
- [ ] SBOM + signed artifacts (SLSA/Sigstore); OpenSSF Scorecard recorded; claims lint green vs the
  [PRD 20 §G](../../prd/20-standards-and-claims.md) vocabulary

Review log: [codereview-log.md](codereview-log.md).
