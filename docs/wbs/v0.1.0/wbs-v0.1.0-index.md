# WBS — agentinbox v0.1.0 (Index)

**BLUF:** v0.1.0 delivers the **entire ask lifecycle with zero external dependencies**: the `ask/1.0` contract
and idempotent ingest, the durable store + crash-safe scheduler (**timeout = deny**), the decision card
(zero-context correct in <15 s), **unforgeable single-use claims + authenticated answers**, terminal/TUI +
desktop-notification + CI-checkpoint + signed-webhook channels (**no chat platform required**), the
filesystem-spool bus (movement ≠ truth), escalation ladders, flood protection, the hash-chained audit log +
agentwatch event set, the agentpolicy resolve bridge, and the producer adapters (agentpolicy reference,
generic CLI/HTTP, LangGraph `interrupt()`, `--exec`). **Thirty-four milestones (M0–M33)** across **seventeen
detail files**; **the final two milestones are field tests (M32) and release readiness (M33)** — M24/M25 are
the core field-test pass and release rehearsal, both re-executed at M32/M33 after the 0.1.0 expansion.

> **Milestone ranges by intent:** **M0–M9** = the core engine (store → contract → lifecycle → scheduler →
> card → claims → terminal → desktop → bus) · **M10–M14** = reach (CI, escalation, flood, webhook, multi-channel
> truth) · **M15–M19** = evidence + producers (audit chain, agentwatch, resolve bridge, adapters,
> conformance) · **M20–M23** = hardening + ops + docs · **M24–M25** = core field tests + release rehearsal ·
> **M26–M31** = 0.1.0 expansion features (PRDs 31–37) · **M32–M33** = **final** field tests + release. The WBS builds the
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
7. **The final two milestones are field tests (M32) and release readiness (M33)** — **M33 tags `v0.1.0`**.
   M24 (core field tests, SC-01–SC-26) and M25 (release rehearsal) are re-executed there for the expanded scope;
   nothing follows M33.

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
| **M24** | **Core field tests** (SC-01–SC-26 + the 15-second study; re-run at M32) | [Part 13](wbs-v0.1.0-part13-fieldtest-release.md) |
| **M25** | **Core release rehearsal** (tag deferred to M33) | [Part 13](wbs-v0.1.0-part13-fieldtest-release.md) |
| **M26–M31** | **0.1.0 expansion features** (PRDs 31–37) | [Parts 14–16](wbs-v0.1.0-part14-quality-constraints.md) |
| **M32** | **Field tests — FINAL** (SC-01–SC-90; 15-second study) | [Part 17](wbs-v0.1.0-part17-expansion-fieldtest-release.md) |
| **M33** | **Release readiness — FINAL** (tags `v0.1.0`) | [Part 17](wbs-v0.1.0-part17-expansion-fieldtest-release.md) |

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
| M11 | Escalation ladder (R4) | #227–#237 (11) | M24 | Core field tests (re-run at M32) | #98–#110 (13) |
| M12 | Flood guard (R7) | #238–#248 (11) | M25 | Core release rehearsal (tag at M33) | #111–#123 (13) |

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
- **2026-11-06 — M3 Ask record + lifecycle closed.** Issues #136–#146. **Gate:** 300 tests pass · coverage
  **96.65%** · `ruff` clean · `mypy --strict` clean · DCO signed. One edge table enforces every legal
  transition; illegal attempts are evidence; terminal is terminal; expiry is derived on read, never written
  by a reader. Store schema v3 adds `warn_at`/`escalate_at`/`tier`; conformance version 2 adds
  transitions/delivery reads. Next: **M4** (`4.D0` scheduler).
- **2026-11-06 — M4 Scheduler / timeout=deny closed.** Issues #147–#157. **Gate:** 317 tests pass · coverage
  **95.94%** · `ruff` clean · `mypy --strict` clean · DCO signed. Warn at `T-60`, expiry at `T`, recovery fires
  once with a marker, concurrent schedulers cannot double-expire, backwards jumps cannot postpone, and the
  zero-allow-on-expiry counter stays 0. `doctor` warns when persisted evidence is ahead of the clock.
  Next: **M5** (`5.D0` decision card).
- **2026-11-08 — M8 Desktop notification channel closed.** Issues #192–#202. **Gate:** 397 tests pass ·
  coverage **95.69%** · `ruff` clean · `mypy --strict` clean · DCO signed. Notifications carry class +
  fingerprint + TTL + tier only; `authenticate()` never returns a principal (no answer path); once-per-tier
  and single-digest fixtures green; `doctor` reports `desktop` and fails closed when enabled-but-headless.
  Next: **M9** (`9.D0` bus design).
- **2026-11-08 — M9 AskBus contract + drivers closed.** Issues #203–#214. **Gate:** 434 tests pass ·
  coverage **95.82%** · `ruff` clean · `mypy --strict` clean · DCO signed. In-proc default; filesystem spool
  with rename-CAS publish, fsync,
  `flock` single-owner refusal, crash resume, bounded poll, and aggressive `done/` pruning. A 200-ask flood
  publishes one rolling digest job; delivery wiring records every attempt (`ask-delivered`/`delivery-failed`),
  retries with bounded backoff, and fails over. `serve --once` drains the spool. Next: **M10** (`10.D0` gate design).
- **2026-11-08 — M10 CI checkpoint (`gate`) closed.** Issues #215–#226. **Gate:** 453 tests pass ·
  coverage **95.62%** · `ruff` clean · `mypy --strict` clean · DCO signed. `gate --ask --wait --timeout`
  maps approved→0, denied/cancelled→2, expired/budget→3, unavailable→4, pending→5; a lapsed budget never
  mutates the ask; SIGTERM/SIGINT records a `cancelled` transition; retries are read-only idempotent.
  Four CI recipes documented. Next: **M11** (`11.D0` escalation design).
- **2026-11-08 — M11 Escalation ladder closed.** Issues #227–#237. **Gate:** 488 tests pass ·
  coverage **95.51%** · `ruff` clean · `mypy --strict` clean · DCO signed. Config-driven tiers with
  validated delays (no implicit zero delay,
  every tier has a roster), `escalate_at` fired by the M4 scheduler, atomic tier change + prior-tier claim
  revocation, tier-aware authorization, one `renotify` job/notification per tier, `expires_at` immutable
  through exhaustion (SC-12), and digested `inbox-config-changed` evidence. Next: **M12** (`12.D0` flood design).
- **2026-11-08 — M12 Flood guard closed.** Issues #238–#248. **Gate:** 509 tests pass · coverage
  **95.79%** · `ruff` clean · `mypy --strict` clean · DCO signed. Coalescing first (retries never consume tokens), then per-key token buckets
  (`agent|session|environment|producer-uid`) with per-class overrides; over-threshold asks auto-deny with
  `ask_flood_throttled` + `retry_after_s`; one `ask-flood` event and one rolling digest per window; the
  200-ask pack yields 180 denies, 1 event, 1 digest; a 20-action migration survives; flood denials can never
  be resurrected. Next: **M13** (`13.D0` webhook design).
- **2026-11-08 — M13 Webhook channel + delivery accounting closed.** Issues #249–#259. **Gate:** 524 tests
  pass · coverage **95.47%** · `ruff` clean · `mypy --strict` clean · DCO signed. HMAC-signed `webhook/1.0` POST with an allow-listed
  display-only payload, refs-only secrets, http(s)-only URLs, `deliver()`-only adapter (no answer path),
  bounded retries + per-attempt Delivery records/events + failover, unroutable classes refused at load,
  `channels` health command, and five receiver recipes. Next: **M14** (`14.D0` parity design).
- **2026-11-08 — M14 Multi-channel single truth closed.** Issues #260–#270. **Gate:** 532 tests pass ·
  coverage **95.30%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  One `parity.decision_record`/`comparable_decision` source; surface
  rendering for text/terminal/desktop/ci; an 8-thread race yields one `answer` and seven `late` no-ops;
  late answers name the winner/time and record evidence; failover shows the outcome without re-asking; the
  conformance suite runs all four surfaces and rejects a deciding channel. Next: **M15** (`15.D0` audit design).
- **2026-11-08 — M15 Audit chain, verify-log + export closed.** Issues #271–#281. **Gate:** 561 tests pass
  · coverage **95.55%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  Transitions, deliveries, floods, exports, and retention
  markers append chained entries; `verify-log` names the first bad seq; `export --session/--ask --format
  jsonl|csv [--out]` emits ordered asks/transitions/deliveries/chain (0600, audited); retention prunes
  detail with a chain marker; no import authority exists (negative test). Next: **M8–M15 complete**.
- **2026-11-08 — M16 agentwatch event set + sink closed.** Issues #282–#292. **Gate:** 572 tests pass ·
  coverage **95.39%** · `ruff` clean · `mypy --strict` clean · DCO signed. Ten event types projected from the audit chain (audit schema v4
  carries the payload), schema fixtures with payload allow-lists, join keys + producer `traceparent`,
  frozen rejection-cause map, buffered sink with flush + `event-gap` markers, and a no-untrusted-text
  fixture. Next: **M17** (`17.D0` resolve bridge).
- **2026-11-08 — M17 agentpolicy resolve bridge closed.** Issues #293–#303. **Gate:** 587 tests pass ·
  coverage **95.48%** · `ruff` clean · `mypy --strict` clean · DCO signed. Frozen reason-code registry; every state maps to its exact code;
  `resolve/1.0` carries `retryable`/`retry_after`/`rescope_hint`/`answered_by`/`action_identity`; class
  hints + deny-reason echo (capped, labelled, not policy); identity mismatch denied; the API long-poll
  returns resolve and handles unknown/mismatch; re-reads are idempotent. Next: **M18** (`18.D0` adapters).
- **2026-11-08 — M18 Producer adapters (agentpolicy + CLI/HTTP) closed.** Issues #29–#39. **Gate:** 608
  tests pass · coverage **95.30%** · `ruff` clean · `mypy --strict` clean · DCO signed. Signed agentpolicy
  adapter (trusted fields, `401` on bad
  signature) with a create→answer→allow round-trip; `ask --file`/`--exec` (executes only on allow); API
  token/adapter/uid/caps/flood hardening; concurrent store open/migration race fixed; CUJ-1 measured;
  producer guide. Next: **M19** (`19.D0` LangGraph + conformance kit).
- **2026-11-08 — M19 LangGraph reference adapter + conformance kit closed.** Issues #40–#50. **Gate:** 625
  tests pass · coverage **95.09%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  Framework-neutral interrupt/resume gate; durable
  resume-by-id; `ExecutionJournal` makes tool execution at-most-once across crashes; the `conformance` kit
  (9 checks against a fresh store) gates channels/producers/contract/redaction/idempotency/exit codes/events;
  broken store fails red; example graph, adapter template, Claude Code/Codex recipes. Next: **M20**.
- **2026-11-08 — M20 Fail-closed fault matrix + doctor hardening closed.** Issues #51–#61. **Gate:** 641
  tests pass · coverage **95.10%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  `FAILURE_MATRIX` covers eight faults (store locked/corrupt,
  schema, sink, channel 500, scheduler kill, invalid reload, clock skew); store open errors now fail closed
  (`StoreError` → `503`/exit 4); doctor adds `chain`, `spool`, `keys`, downgrade refusal and stays <2 s;
  `ConfigHolder` keeps the last-good config and records `inbox-config-changed(failed)`; zero-allow counter
  stays 0. Next: **M21**. 

- **2026-11-08 — PRD conformance review (M0–M20).** Audited the built milestones against PRDs
  02/05/06/11/13/15/16/18/19/20/22. Fixed and regression-tested: audit payload re-hashing + corrupt-payload
  fail-closed; complete-chain export; `[unverified]` trust labels; prior-asks/credential-class card fields;
  warning delivery; escalation wording; delivery-error redaction; lock-free producer publishing; claim
  `action_identity` binding (schema v5); `serve` starting the loopback API with a `0600` token; read-only
  `verify-log` (no migration); a persisted event-sink delivery cursor; `requested_by` in the signed trusted
  profile. Reconciled the PRD wording: claim entropy is 128-bit in PRD 05 and PRD 18; the 200/30 s flood verdict
  records the burst capacity + denied remainder (PRD 05 R7, PRD 17 SC-13, WBS 12.3). Added
  `require_signed_producer` (self-review enforceable), an in-place SIGHUP reload (channels/retention/API), and
  the not-verified claims table. Details in the
  [review log](codereview-log.md#prd-conformance-review-m0m20-2026-11-08).

- **2026-11-07 — M21 Ops: service units, backup/restore, migrations, `report` closed.** Issues #62–#73.
  Commit `3ac7cf5`. **Gate:** 750 tests pass · coverage **95.27%** · `ruff` clean · `mypy --strict` clean ·
  DCO signed. `serve --install` writes user-scoped launchd/systemd units (no root); SIGTERM stops accepting,
  flushes events, closes cleanly, and a dead `serve.lock` makes `gate` exit 4. `doctor --backup` uses the
  SQLite online-backup path (WAL-safe) and carries key **references** only; `doctor --restore` allow-lists
  extraction, verifies the chain, and expires overdue pending asks once (never resurrects a decision).
  `compat` freezes the contract/exit/event surface with the additive-only matrix; every released schema
  migrates forward and downgrade refuses loudly. `report --json` is read-only and local-only (p50/p99,
  expiries, escalations, floods, rejected causes, deny rate by class). Doctor adds `offline`; the SC-26
  offline day runs with non-loopback sockets blocked. Benches record N-1..N-7. Next: **M22** (`22.D0` security sweep).

- **2026-11-07 — M22 Security hardening sweep + evidence scanner closed.** Issues #74–#85. Commit
  `88bf037`. **Gate:** 793 tests pass · coverage **95.19%** · `ruff` clean · `mypy --strict` clean · DCO signed.
  The evidence scanner shares the redaction pattern set and scans store dumps (read-only), rendered
  terminal/desktop/CI/webhook payloads, audit exports, and backup archives; a seeded leak fails and CI runs
  the self-test. Spoof/replay/forge, injection, and flood packs are release-blocking (`python -m
  agentinbox.packs`), and a broken gate fixture turns the spoof pack red. Invariants I-1..I-5 each have a
  negative fixture; credential failures collapse to the public cause `bad_claim`; claim/token/HMAC compares
  are constant-time; logs strip control/ANSI; creation paths force 0700/0600 under `umask 000`; there is no
  `--yes`. Own-posture checks prove zero runtime dependencies/no ML, emit a CycloneDX SBOM dry run, and
  validate the committed `security.txt` (SLA in `SECURITY.md`). Next: **M23** (`23.D0` docs plan).

- **2026-11-07 — M23 Docs completion closed.** Issues #86–#97. Commit `TBD`. **Gate:** 799 tests pass ·
  coverage **95.19%** · `ruff` clean · `mypy --strict` clean · DCO signed. The quickstart is step-tested
  through a pty (first approval recorded in ~1.5 s, hard limit 300 s); a doc-coverage test walks the CLI
  parser and config dataclasses so no flag/key can ship undocumented; eight runbooks (RB-1..RB-8) carry
  symptoms → steps → verify; MCP and Temporal recipes join the harness/CI recipes; the approver guide and
  the honest enterprise page state the v0.1.0 gaps before features; terminal captures are text from the
  real renderer; README install/usage/quickstart are live (PyPI/tag still M25). Next: **M24** (`24.D0` field-test plan).

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
| **PRD 31** | CUJ & feature gaps (0.1.0 expansion) | M49 |
| **PRD 32** | decision quality & ask readiness | M50 |
| **PRD 33** | constrained allows & denial repair | M51 |
| **PRD 34** | operation bundles, handoff & incident review | M52 |
| **PRD 35** | outcome closure & execution proof | M53 |
| **PRD 36** | repetitive approvals, grants & compression | M54 |
| **PRD 37** | policy learning & governance insights | M55 |

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

## 0.1.0 expansion (M26–M33 · PRDs 31–37)

> **All of this is v0.1.0 work.** PRDs 31–37 extend the 0.1.0 program; they are appended as M26–M33 so the
> already-built core (M0–M25) is untouched. **M32 (field tests) and M33 (release readiness) are the final two
> milestones** — M24/M25 are re-executed there, and **nothing follows M33**; M33 tags `v0.1.0`.

| M | Name | Detail file |
|---|---|---|
| **M26** | **Ask readiness & decision quality** (PRD 32) | [Part 14](wbs-v0.1.0-part14-quality-constraints.md) |
| **M27** | **Constrained allows & denial repair** (PRD 33) | [Part 14](wbs-v0.1.0-part14-quality-constraints.md) |
| **M28** | **Operation bundles, handoff & incident review** (PRD 34) | [Part 15](wbs-v0.1.0-part15-operations-outcomes.md) |
| **M29** | **Outcome closure & execution proof** (PRD 35) | [Part 15](wbs-v0.1.0-part15-operations-outcomes.md) |
| **M30** | **Repetitive approvals, grants & compression** (PRD 36) | [Part 16](wbs-v0.1.0-part16-grants-learning.md) |
| **M31** | **Policy learning & governance insights** (PRD 37) | [Part 16](wbs-v0.1.0-part16-grants-learning.md) |
| **M32** | **Field tests — FINAL (SC-01–SC-90)** (PRD 31) | [Part 17](wbs-v0.1.0-part17-expansion-fieldtest-release.md) |
| **M33** | **Release readiness — FINAL (tags `v0.1.0`)** (PRD 31) | [Part 17](wbs-v0.1.0-part17-expansion-fieldtest-release.md) |

### Issues

| M | Milestone | Issues |
|---|---|---|
| M26 | Ask readiness & decision quality | #306–#317 (12) |
| M27 | Constrained allows & denial repair | #318–#328 (11) |
| M28 | Operation bundles, handoff & incident review | #329–#340 (12) |
| M29 | Outcome closure & execution proof | #341–#352 (12) |
| M30 | Repetitive approvals, grants & compression | #353–#364 (12) |
| M31 | Policy learning & governance insights | #365–#378 (14) |
| M32 | Field tests — FINAL (SC-01–SC-90) | #379–#390, #401 (13) |
| M33 | Release readiness (expanded v0.1.0) | #391–#400 (10) |

### CUJ → milestone (expansion)

| CUJ | Journey | Milestone |
|---|---|---|
| **CUJ-15..18** | constrained allows / repair / operations review / decision narrative | **M26–M28** |
| **CUJ-19** | which asks should never reach a human | **M31** |
| **CUJ-20–21** | incident mode / shift handoff | **M28** |
| **CUJ-22** | approve one, not ten | **M30** |
| **CUJ-23–28** | ask readiness / quality / contradictions | **M26** |
| **CUJ-29–32** | safe subsets / deny-repair / machine-shaped fixes | **M27** |
| **CUJ-33–36** | operation bundles / handoff / blocked view | **M28** |
| **CUJ-37–40** | approved==executed / closure / packets / drift | **M29** |
| **CUJ-41–44** | compression / windows / burn-down | **M30** |
| **CUJ-45–48** | never-needed-a-human / noisy policy / calibration / hotspots | **M31** |

### Scenario → milestone (expansion)

| Scenario | What it proves | Authored | Executed |
|---|---|---|---|
| **SC-68–SC-70** | readiness rejection, contradictions, class-dependent scoring | M26 | **M32** |
| **SC-71–SC-74** | constrained allow, repair round-trip, edits, unbindable advice | M27 | **M32** |
| **SC-75–SC-78** | bundles, handoff, incident mode, narrative | M28 | **M32** |
| **SC-79–SC-82** | closure, divergence, packet-only reconstruction | M29 | **M32** |
| **SC-83–SC-86** | compression, window expiry, revocation, repeated denies | M30 | **M32** |
| **SC-87–SC-90** | insights, calibration access, tuning proposals | M31 | **M32** |
| **SC-01–SC-26** | core catalog re-run on the expanded build (M24 baseline) | M1–M23 | **M32** (final gate) |

### Expansion milestone exit criteria

Every expansion milestone applies the standard gates (`.D0` design first, `.T` tests, `.C` coverage ≥95%, `.L`
ruff + `mypy --strict`, `.CR` review log, `.D` docs, `.CI` commit, `.W` checkpoint) and preserves the five
invariants plus the enforcement honesty clause: **the inbox records/returns, the enforcer enforces; insights,
suggestions, and grants never act on their own.**
