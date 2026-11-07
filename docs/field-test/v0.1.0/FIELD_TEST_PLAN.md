# Field-Test Plan — agentinbox v0.1.0

**Milestone:** M32 Field Tests — FINAL (SC-01–SC-90 + the 15-second study) · **Authored:** `32.D0` (#379), 2026-11-07
**Plan (this doc) →** report `docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` (hand-maintained template, already published)
**Harness:** the `agentinbox` CLI + the `tests/` suites + the harness recipes below · **Results:** `field-test/v0.1.0/results/<suite>/` · **Journal:** `field-test/v0.1.0/journal/` (raw transcripts, never in the report).

**BLUF.** agentinbox v0.1.0 is the **human decision gate for agent-initiated irreversible actions** — a local-first inbox that mints a gated ask, delivers one card, accepts one answer bound to the exact action identity, and resolves `allow` / `deny` / `pending`, with a hash-chained audit of every move. This field test is the **only** field-test pass for v0.1.0 (it absorbs the M24 core pass): it must prove the **core catalog SC-01–SC-26 re-run green on the expanded build** (against the M23 core commit `ab94330` + PRD 17 expected behavior, after six expansion milestones M26–M31 landed on top), the **expansion scenarios SC-68–SC-90** (readiness, constrained allows, operations, outcome closure, grants/compression, insights), **one** zero-context 15-second study covering core + expansion CUJs, and the **Claude Code / Codex CLI harness recipes run live** (feeding the M33 compatibility matrix labels). The plan is frozen here so M32 execution is a matter of **running, not deciding**.

Sources: [WBS v0.1.0 Part 17](../../wbs/v0.1.0/wbs-v0.1.0-part17-expansion-fieldtest-release.md) (M32 items #379–#390, #401; absorbed M24 items #98–#110), [PRD 17](../../prd/17-scenarios.md) (SC-01–SC-26), [PRD 21](../../prd/21-evidence-register-and-method.md) (Methods B/C/D), [PRD 31](../../prd/31-0.1.0-cuj-and-feature-gaps.md) (CUJ-15..48), [PRD 32](../../prd/32-decision-quality-and-ask-readiness.md) (SC-68–70), [PRD 33](../../prd/33-constrained-allows-and-denial-repair.md) (SC-71–74), [PRD 34](../../prd/34-operation-bundles-handoff-and-incident-review.md) (SC-75–78), [PRD 35](../../prd/35-outcome-closure-and-execution-proof.md) (SC-79–82), [PRD 36](../../prd/36-repetitive-approvals-grants-and-compression.md) (SC-83–86), [PRD 37](../../prd/37-policy-learning-and-governance-insights.md) (SC-87–90), [PRD 12](../../prd/12-traceability.md). Format precedent: the `agentpolicy` v0.1.0 field-test plan (same document shape).

---

## 0. Readiness, doctrine, and status

### 0.1 Doctrine (the honesty rules this run inherits)

- **No skips.** Every case is `pass` / `fail`. A case that cannot run is a **failure**, not a skip — unless it is `BLOCKED` (§0.2) with a named reason. The run exits non-zero on any miss.
- **The inbox records; the enforcer enforces.** No field case measures "the tool did not run" by trusting the inbox — the harness case (§S14) proves the hook/wrapper exit gates the actual tool call; every other case asserts inbox state, resolve payloads, and the audit chain.
- **One run per scenario.** One run, distinct log filename, full output preserved under `results/`. Re-running until green and keeping only the green run is the prohibited pattern; a re-run is recorded as a second run with its own log.
- **The report is hand-maintained.** `FIELD_TEST_REPORT.md` carries the `HAND-MAINTAINED` marker; no automation writes it (the M24 lesson — a build_report once destroyed hand notes — is already encoded in the repo rule). Verdicts are entered **by hand from the committed result files**.
- **Fail-closed is the product.** Missing context, stale evidence, contradictory fields, no enforcer binding, revoked grants, store faults, clock skew, offline — each must produce `deny` or `pending`, never `allow`. Any silent allow anywhere is a release-blocking red.
- **The five invariants hold for everything under test:** I-1 no answer without a claim + authenticated principal · I-2 approvals bind to the exact action identity · I-3 timeout = deny · I-4 agent-derived text is inert · I-5 no secret is persisted or rendered.
- **LLM evidence is captured, never inferred.** Tier-1 harness cases route the real CLI through `t1_proxy.py`, which logs every request/response pair (sanitized). A PASS requires a balanced pair with 2xx responses and zero secrets; a case with no capture is a failure. The deep-validation gate re-checks this from disk.
- **Attack packs are release gates.** SC-22 (spoof/replay/forge), SC-23 (injection), SC-24 (fault matrix) — a red pack means **no release**, full stop (32.7/#401 acceptance).

### 0.2 The BLOCKED / declare class

Cases whose environment is genuinely unavailable (no Claude Code / Codex CLI on the box, no study participants, no field box) resolve to **`BLOCKED`** — allowed only for: the harness cases (§S14), the study (§S12), and any external-channel case whose surface cannot be stood up locally. A `BLOCKED` case requires **all** of:

1. a named limitation (what is missing, why it cannot be provided on this box),
2. an evidence artifact of the blocked attempt (command + `stderr` + environment fingerprint in `journal/`),
3. a line in the report's **Declared & Blocked register**, and
4. the downstream gate stated honestly (M33 matrix label stays `not supported` / unlabelled until the run exists — PRD 19/Method D).

`BLOCKED` is **not** allowed for any deterministic case (SC-01..SC-26 core, SC-68..SC-90 expansion) — those run in-process/CLI on any POSIX box. The `Class` column fixes this: **P/F** = must pass or fail; **P/F|B** = pass, fail, or blocked-with-reason. A `BLOCKED` case still fails the suite for release purposes until unblocked — it is never reported as done (M33 gates on it).

### 0.3 Status at authoring (2026-11-07)

| Item | Status |
|---|---|
| M0–M23 core (build, bus, channels, escalation, flood, CI, evidence, attacks, adapters, offline) | ✅ complete |
| M26 readiness · M27 constrained allows · M28 operations · M29 outcomes · M30 grants · M31 insights | ✅ complete — gate: **924 tests, 95.11% coverage, `ruff` + `mypy --strict` clean** (`2dedc7d`/`bd2a21c`) |
| Deterministic suites per scenario group (tests/readiness, constraints, bundles, outcomes, grants, insights, answers, ask, escalation, flood, faults, security, conformance, cli, docs) | ✅ available (these are the L0 drivers) |
| Harness recipes (Claude Code `PreToolUse`, Codex CLI wrapper) | ✅ documented (`docs/adapters/harness-recipes.md`) — not yet run live |
| Study corpus (12 + 12 degraded + 10 poisoned + 12 expansion, pre-registered answers, checksum) | ☐ to freeze (32.5/#384, §S12) |
| Field-test result/journal scaffolding (`field-test/v0.1.0/results/`, `journal/`) | ☐ to create on first run |
| Report template | ✅ this plan's companion (`FIELD_TEST_REPORT.md`, hand-maintained marker) |
| Field box (macOS/Linux POSIX box with the CLI, Claude Code, Codex CLI installed) + ≥10 study participants | ☐ **BLOCKED** — not yet provisioned; recorded here, not hidden |

**Overall status: PLAN FROZEN — READY TO RUN** once the box + participants exist. Every deterministic case can run today; the harness + study cases await their environment (§0.2).

---

## 1. What already exists (reuse as-is — do not fork)

| Asset | Role in the M32 plan |
|---|---|
| `agentinbox` CLI (`init`, `ask`, `inbox`, `answer`, `gate`, `resolve`, `export`, `doctor`, `serve`) | the L1 driver for every lifecycle/ops/insight case |
| `tests/` suites: `ask`, `answers`, `readiness`, `constraints`, `bundles`, `outcomes`, `grants`, `insights`, `escalation`, `flood`, `faults`, `security`, `conformance`, `channels`, `bus`, `store`, `audit`, `card`, `cli`, `docs`, `ops`, `parity`, `scheduler`, `lifecycle`, `events`, `config` | the L0 deterministic drivers (one suite per scenario group — cases drive these **plus** end-to-end CLI runs) |
| `tests/fixtures/conformance/` (ask/resolve contract truth) + `tests/packs/` (attack corpora: spoof/replay/inject/flood/fault) | the fixture source for SC-02/22/23/24/13 |
| Evidence tooling: `python -m agentinbox.scanner`, `export --session`, the hash-chain verifier (`audit.verify`), `verify-log` export checker | SC-20/21 drivers + the leak gate over every result file |
| `docs/adapters/harness-recipes.md` (Claude Code `PreToolUse`, Codex CLI wrapper) | §S14 drivers, recorded verbatim in the run journal |
| `docs/runbooks/rb-*` + `doctor` | SC-24/26/10 degraded-mode drivers |
| `make test` / `ruff` / `mypy --strict` | the standing quality gate every case's build must be on |

**Do not create a parallel harness.** Each case = one scripted CLI (or in-process) sequence + assertions from the suite + artifacts to `results/<suite>/<case>/`. If a case needs glue, add a **step script** under `journal/<case>/`, not a new framework.

---

## 2. What M32 must additionally prove (the gap this plan closes)

- **The core did not regress under six milestones of expansion.** SC-01–SC-26 re-executed on the expanded build, compared against the **M23 core commit `ab94330`** and PRD 17 expected events (32.7/#401 — there is no separate M24 pass; this is it).
- **The expansion surfaces work end-to-end, not just in unit tests:** readiness rejection + repair contracts (SC-68–70), constrained allows + repair packets + edits (SC-71–74), bundles/handoff/incident/narrative (SC-75–78), outcome closure + packets + divergence (SC-79–82), compression + windows + revocation (SC-83–86), insights + calibration gating (SC-87–90).
- **The 15-second promise holds for the new content too.** One study cohort across core + expansion CUJs (12 + 12 + 10 + 12 cards), pre-registered answers, ≥10 non-author participants (32.5/#384).
- **The two shipped harness recipes actually gate real tools.** Claude Code + Codex CLI live runs, transcripts + checksums in the journal (32.8/#104 — closed as absorbed; the *execution* is this pass), feeding the M33 matrix `field-tested` labels (PRD 19 / Method D).
- **An honest report blocks release on red.** Every verdict published; attack packs release-gating; misses named with owners (32.6/#385).

---

## 3. Harness layers & topology

| Layer | System under test | Boot | Driver |
|---|---|---|---|
| **L0 — deterministic suites** | in-process store/answer/resolve/ops/insights modules | `make test` | pytest suites per group (the correctness backstop under every case) |
| **L1 — CLI lifecycle** | `agentinbox` CLI end-to-end on a scratch `--home` | `agentinbox init/ask/inbox/answer/gate/resolve/export --home <scratch>` | scripted case steps (`journal/<case>/steps.sh`) |
| **L2 — channels** | terminal + desktop + webhook surfaces | `init` with the case's channel config; webhook on loopback | same scripts; desktop/webhook assertions where configured |
| **L3 — Tier-1 harnesses** | Claude Code `PreToolUse` hook · Codex CLI wrapper | the real harness on the field box | §S14 recipes, verbatim |
| **L4 — human study** | real approvers, zero context | the frozen corpus on the worst realistic surface | §S12 protocol |

**No-Docker default:** L0–L2 run with zero Docker and zero network. L3 runs wherever Claude Code / Codex CLI are installed (they are the only two shipped recipes — no other harness is claimed). L4 needs ≥10 humans. No case calls a hosted model; nothing in agentinbox's decision path is ML at all.

**Clock/env recording (every run):** OS + version, architecture, Python, `agentinbox` commit + branch, `--home` layout, channel config used, UTC time, clock-sync status (`doctor` green), and the case's log path — written to `results/<suite>/env.json` by the step script.

---

## 4. Where LLMs are and are not used

> **Explicit boundary: no LLM decides anything under test.** agentinbox's decision path is deterministic by construction — there is no model in the ask→card→answer→resolve path; suggestions, readiness scores, and insights are computed from stored facts (M26–M31 design docs). The **only** LLM in this field test is *inside the Tier-1 harness itself* (Claude Code / Codex CLI driving a real agent that triggers a gated tool call, per the harness recipes). That agent is the **test subject**: the case asserts the hook/wrapper blocked the tool, the ask was minted, and the answer gated it. If no harness exists on the box, those cases are `BLOCKED` (§0.2) — a hosted-model substitute is **not** permitted.

### 4.1 Model selection — OMLX, local only (pinned: `Qwen3-4B-Instruct-2507-4bit`)

The harness LLM is the **box-local OMLX** server (`http://127.0.0.1:8000`) — the same backend agentpolicy field-tested. No hosted model is used anywhere in this plan. The model is chosen on exactly two criteria, in order: **(1) tool-call reliability**, then **(2) latency** — the Tier-1 cases need the agent to actually *emit a tool call* so the hook/wrapper can gate it; a model that never calls a tool proves nothing however fast it is.

Models served by this box's OMLX (measured by agentpolicy's `omlx_bench.py`, 3 trials, `temperature=0`; verified present on this box 2026-11-07):

| OMLX model | tool calls | p50 latency | verdict |
|---|---|---|---|
| **`Qwen3-4B-Instruct-2507-4bit`** | **3/3** | **~1.0 s** | ✅ **PINNED — best fit** |
| `Qwen3.5-4B-4bit` / `mlx-community--Qwen3.5-4B-4bit` | 3/3 | ~6.6–6.8 s | fallback only (~7× slower at p50) |
| `Qwen3.5-9B-MLX-4bit` | 3/3 | ~12.9 s | too slow |
| `Qwen3-8B-4bit` | 3/3 | ~27.5 s | too slow (~27× slower than the pin) |
| `Llama-3.2-3B-Instruct-4bit` | **0/3** | ~0.8 s | ❌ **disqualified** — never emits a tool call |
| `MarkItDown` | — | — | a document converter, not an LLM; excluded |

**Justification.**
- **Tool-call reliability gates.** `Llama-3.2-3B` is the fastest model but returned zero tool calls in three trials — the guarded tool is never invoked, the guard never fires, the case asserts nothing. Disqualified outright.
- **Then latency decides.** Among reliable callers, `Qwen3-4B-Instruct-2507-4bit` is ~7× faster at p50 than the Qwen3.5-4B pair and ~27× faster than `Qwen3-8B`; over a multi-call Tier-1 sweep that is the difference between minutes and an hour.
- **Provenance.** It is exactly agentpolicy's field-test pin (same model, same role, same benchmark), so the choice is evidence-backed, not novel.
- **Caveat.** p50 includes full generation; the 6–27 s figures largely reflect how much text those models emit before calling. The pin is both fast *and* tool-reliable.

**Applied.** Pinned in `scripts/fieldtest/.env.example` (`FT_LLM_MODEL`, `FT_T1_MODEL`, `FT_T1_UPSTREAM`); both `t1_claude.sh` (Anthropic `/v1/messages` surface) and `t1_codex.sh` (OpenAI-compatible `/v1/responses`) route through `t1_proxy.py` to OMLX. Re-derive on a new box with a field-test-shaped request before re-pinning; a changed model is a new run, not a continuation.

---

## 5. Layer 0 — the core regression gate (mandatory, first)

The **entire** SC-01–SC-26 block runs **before** any expansion case is evaluated (32.7/#401 ordering). Pass condition: every core scenario green on the expanded build; each verdict compared against `ab94330` behavior + PRD 17 expected events; any divergence is a **release blocker** with its own regression note + owner. The deterministic suites already encode most of these assertions — the case run adds the **end-to-end CLI trace** on top (L1) so the regression is proven at the surface a human touches, not only in-process.

---

## 6. Master scenario matrix — 53 field units (51 deterministic + 2 study; Tier-1 removed 2026-11-07)

`Class`: **P/F** = must pass or fail. **P/F|B** = pass, fail, or blocked-with-reason (§0.2).
`Env`: `ci` = this POSIX box, in-process (no network) · `cli` = scratch `--home` via the CLI · `ch` = terminal + desktop/webhook channels · `t1` = the real harness on the box · `hum` = study participants.
`Driver` = how the case is executed. **Pass condition** is the exact assertion set; anything less is a fail.

### S1 — Core lifecycle & ingest (SC-01..06, 09, 10 · PRD 17 G1 · #99/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-01 | First ask, terminal, zero config | 17 SC-01 | cli | `init` → `ask` → `inbox` → typed `answer` | card shows all four blocks + TTL; `ask-raised`→`ask-delivered(terminal)`→`ask-answered(approved, principal)`; resolve `allow/allow_ask_approved`; audit reconstructs ≤3 transitions | P/F |
| FT-SC-02 | Malformed ask rejected loudly | 17 SC-02 | ci | conformance fixtures + CLI 400s | 400 with field-named diagnostics (missing `expires_at`, 300 KiB args, floating expiry); **no record, no delivery**; nothing partial persists | P/F |
| FT-SC-03 | Zero-context correct call (spine) | 17 SC-03 · 21 B | hum | the frozen corpus (§S12) | ≥9/10 participants ≥10/12 correct; median <15 s; p90 <25 s; missing fields render `unknown` | P/F\|B |
| FT-SC-04 | Missing-context honesty | 17 SC-04 | ci+hum | degraded corpus | every stripped field renders explicit `unknown`; correct decision flips to deny — 0 silent blanks, 0 guessed values | P/F\|B |
| FT-SC-05 | Rescope hint changes the agent's behavior | 17 SC-05 | cli | deny → re-ask `--dry-run` | hint in the resolve payload; second ask = **new** identity; first stays denied; no state reuse | P/F |
| FT-SC-06 | Duplicate ingest coalesces | 17 SC-06 | ci | 3× same POST | same `ask_id` ×3; one delivery; `deduplicated` ×2; approver sees one card | P/F |
| FT-SC-09 | Timeout = deny with warning | 17 SC-09 | cli | short-TTL ask, nobody answers | `ask-warned` at T-60 on both channels; `ask-expired` at T=300; resolve `deny/human_gate_timeout/retryable=false` + hint; jitter ≤1 s; zero allow paths | P/F |
| FT-SC-10 | Expiry survives a crash | 17 SC-10 | cli | kill -9 at T-30, restart T+10; NTP step-back variant | `ask-expired` fires **exactly once** (scheduler-recovered), correct time; clock step-back does **not** extend TTL | P/F |
| FT-SC-10-LIVE | Expiry survives a **real** daemon crash | 17 SC-10 | cli | host daemon `kill -9` mid-TTL, restart, `serve --once` | exactly one `expired` in the export; resolve `human_gate_timeout`; live step (not mocked) | P/F |

### S2 — Cross-channel truth (SC-07, 08, 18, 19 · PRD 17 G2 · #100/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-07 | Second-surface approve, terminal parity | 17 | ch | terminal + desktop/webhook; answer on surface 2 | `ask-answered(channel, principal)`; terminal shows "resolved via <surface>"; resolve fires once; byte-parity vs a terminal-answered twin | P/F |
| FT-SC-08 | Race: two answers, one decision | 17 | ci | two answers ≤200 ms apart | first-wins; second `answer-rejected(cause=late)`; one `ask-answered`; double-resolve → same single decision (idempotent) | P/F |
| FT-SC-18 | Channel failover | 17 | ch | external channel 500s (mocked) | `ask-delivery-failed` × retries logged; terminal still answers; surface later updated, not re-asked; ingest latency never regressed | P/F |
| FT-SC-19 | Late answer is a visible no-op | 17 | cli | Approve 45 s post-expiry | "expired — action was denied" to the approver; `answer-rejected(cause=late)`; state untouched; no resurrection | P/F |

### S3 — Escalation (SC-11, 12 · PRD 17 G3 · #100/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-11 | The 3 a.m. drill | 17 | ch | tier-1 silent at 03:04 UTC | `ask-escalated(tier-2)` at T+300 per config; tier-2 card carries "tier 1 did not answer · expires in mm:ss"; tier-1 claims revoked (late tap → `answer-rejected(cause=revoked)`) | P/F |
| FT-SC-12 | Ladder exhaustion denies | 17 | ch | no tier answers | tiers fire in order, each once; final `ask-expired` → deny; ladder events = tiers−1; TTL never extended | P/F |

### S4 — Flood & abuse (SC-13, 14 · PRD 17 G4 · #101/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-13 | Flood pack (the attack) | 17 | ci | agentdrill pack, 200 asks / 30 s | burst capacity allowed first; post-threshold → `flood_denied` + `ask_flood_throttled`; exactly **1** `ask-flood` event + 1 digest notification; pre-flood pendings answerable; **allowed + denied counts recorded** (with defaults: 20 allowed / 180 denied — not "200/200") | P/F |
| FT-SC-14 | Legitimate burst is not an attack | 17 | ci | 20 asks, distinct identities, <2 s apart | all delivered + answerable; no throttle trip; **passes together with FT-SC-13** — the discriminator is behavior, not volume | P/F |
| FT-SC-PAIR | The flood pair passes **together** | 17 | ci | reads both sibling verdicts in the same run | both `FT-SC-13` and `FT-SC-14` are `pass`; a lone pass is a failure (PRD 17 pair rule) | P/F |

### S5 — CI / headless (SC-15, 16 · PRD 17 G5 · #101/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-15 | Pipeline halts on an ask | 17 | cli | `gate` in a release-job script | job log shows ask id + summary; second-surface answer → exit 0 → continues; audit names the pipeline and the approver | P/F |
| FT-SC-16 | Deterministic exits | 17 | cli | matrix: deny/expiry/killed/pending/approved/cancelled | deny→2 · expiry→3 · killed→4 · pending→5 · approved→0; stable across a retry (idempotent same-ask `gate`); cancelled job → ask `cancelled`, not orphaned | P/F |
| FT-SC-16-LIVE | Real `gate` exit matrix end-to-end | 17 | cli | host CLI: approve/deny/expire/pending | exit `0` approved · `2` denied · `3` expired · `5` pending, each through the real gate | P/F |

### S6 — Evidence (SC-20, 21 · PRD 17 G6 · #101/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-20 | Reconstruction + chain | 17 | ci | 3-ask session + `export --session` | ordered JSONL: transitions, principals, channels, reasons, redaction receipts, chain; verify passes offline; events join on session/ask id; tamper fixture → verifier names the exact `seq` | P/F |
| FT-SC-21 | Evidence carries no secrets | 17 | ci | asks seeded with keys/tokens/PII | store dump, channel captures, audit export → **0 scanner findings**; every redaction has a receipt (field, class, count) | P/F |

### S7 — Attack packs (SC-22, 23 · PRD 17 G7 · #101/#401) — RELEASE-GATING

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-22 | Spoof/replay/forge matrix (10 attacks) | 17 | ci | `tests/packs` spoof/replay/forge corpus | all 10 → `answer-rejected` with **distinct causes**; **zero state changes**; approver-facing message explains each; **any red blocks M33** | P/F |
| FT-SC-23 | Injection corpus (10 poisoned asks) | 17 | ch | poisoned cards on every configured channel | inert rendering everywhere; trusted fields from unsigned producers render **unverified**; **0 approvals caused by injected content**; fake-policy-ref card says "unverified policy reference" | P/F |

### S8 — Governance, faults, adapters, offline (SC-17, 24, 25, 26 · PRD 17 G8 · #102/#401)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-17 | Self-review denied | 17 | cli | Maya's agent asks, Maya rostered, `self_review=deny` | her approval → `answer-rejected(cause=self_review)`; card warned upfront; `low-risk` variant → allowed + audited `self_review=allowed` | P/F |
| FT-SC-24 | Fault-injection matrix (fail-closed) | 17 | ci | store locked · corrupted schema · sink offline · channel down · scheduler killed mid-fire | every path → deny-or-pending; explicit `delivery-failed`/degradation events; `doctor` red; **zero silent allows, zero silent skips** | P/F |
| FT-SC-25 | Framework adapter round-trip (LangGraph) | 17 | ci | `human_gate` node → ask → second-surface approve → resume; kill mid-wait → restart | resume-by-id returns the same decision; **exactly one** tool execution post-approval; no double-execution | P/F |
| FT-SC-26 | Offline day | 17 | cli | network disabled; filesystem spool + desktop stay | SC-01/SC-09 pass; `doctor` reports offline mode green; **no outbound attempts in logs**; export works to a local file | P/F |

### S9 — Readiness & decision quality (SC-68..70 · PRD 32 · #380)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-68 | Readiness bounce pre-delivery | 32 | ci+cli | red-band ask on an enforcing class | pre-write rejection; **nothing stored**; API 400 `ask_not_decisionable` + repair contract (dimensions, retry=after-repair); CLI equivalent message | P/F |
| FT-SC-69 | Contradiction visible / reject-on-ingest | 32 | ci+cli | contradicting ask, `on_contradiction=deliver` and `=reject` | delivered card shows the contradiction; `reject` config refuses at ingest with the dimension named | P/F |
| FT-SC-70 | Same weak ask, different class | 32 | ci | identical weak payload vs readonly vs irreversible | scores differ by class; readonly → delivered; irreversible → red band (band from `_readiness`, not guessed) | P/F |

### S10 — Constrained allows & repair (SC-71..74 · PRD 33 · #380)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-71 | One-click constrained allow | 33 | cli | alternative with a declared enforcer + matching fingerprint | `answer --alternative` → resolve `decision=allow_with_constraints` + constraint set + fingerprint; exceeding at the enforcer names the constraint id | P/F |
| FT-SC-72 | Repair packet round trip | 33 | cli | deny → demo agent repairs → resubmit | packet on resolve + in evidence (invariant, missing evidence, scope, safe alternative, retry-worthiness, tier); `pointless` suppresses blind retry; resubmission shows the prior objection | P/F |
| FT-SC-73 | Human edit re-fingerprints | 33 | cli | class `edit_schema`; `answer --edit command=…` | `decision=allow_with_edits`; **edited** identity + provenance recorded; out-of-schema field refused with the field named; enforcer executes the edited form | P/F |
| FT-SC-74 | Unbindable constraint is advice | 33 | cli+hum | alternative without an enforcer / tampered fingerprint | renders "advice only"; picking it → `answer-rejected(unbindable_alternative)`; card labels it not-selectable | P/F |

### S11 — Operations (SC-75..78 · PRD 34 · #381)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-75 | 20-ask bundle: one screen, 20 decisions | 34 | cli | shared `operation_id`; 20 asks | grouped view renders (counts, environments, phases, critical path); **20 individual answers**; no approve-all path exists; export carries every ask | P/F |
| FT-SC-76 | Shift handoff preserves intent | 34 | ch | `record_handoff` → incoming approver's first render | note (remaining TTL, questions, evidence, principals) **before** ACTION; TTL unchanged by handoff; claim/assign are routing-only | P/F |
| FT-SC-77 | Incident mode, same accountability | 34 | cli+ch | `[incident]` overlay active | chained `incident-on/off` with owner+reason; TTL scale ≤1 (never extended); **denies still deny**; expiry mid-incident still denies | P/F |
| FT-SC-78 | Narrative reproduces a 3 a.m. denial | 34 | cli | narrative from a stored denied ask | a reviewer who wasn't there reconstructs it from the packet alone (rule, evidence, outcome, reason); sourced from transitions, no re-computation | P/F |

### S12 — Outcome closure & proof (SC-79..82 · PRD 35 · #382)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-79 | Executed closure + offline packet | 35 | ci+cli | close an approved ask with a matching manifest | `decision-packet/1.0` carries ask, decision, narrative, outcome, timeline, chain; `verify_packet` green offline; decision unchanged | P/F |
| FT-SC-80 | Exceeded manifest is loud | 35 | ci | manifest resource outside approval | comparison `exceeded` with the resource named; chained `outcome-divergence`; card `UNACKNOWLEDGED` until ack; **never silently absorbed** | P/F |
| FT-SC-81 | Rollback after approval | 35 | cli | `record_outcome(state=rolled_back)` | renders `rolled_back`; original decision record untouched (status stays `approved`); no reopen path | P/F |
| FT-SC-82 | Packet-only reviewer reconstructs | 35 | cli | hand the packet to a reviewer with no store | full story + offline chain verification; tamper → `ChainHashMismatch` | P/F |

### S13 — Grants & compression (SC-83..86 · PRD 36 · #383)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-83 | 12-ask burst, compressed view | 36 | ci+cli | 12 identical asks | compressed view renders with every row; **12 individual answers**; export complete; chain unchanged | P/F |
| FT-SC-84 | Window grant mid-burst | 36 | ci | grant live → first N asks auto-allow → expiry | covered asks approve via `window-grant` with burn-down; expiry mid-burst → **next ask pending (per-ask)**; zero silent allows | P/F |
| FT-SC-85 | Owner revokes a live grant | 36 | ci | revoke mid-window | chained `grant-revoked`; **next covered ask immediately demands fresh approval**; every use was a chained event | P/F |
| FT-SC-86 | Repeated denials → insight, not noise | 36 | ci | 5 same-shape denials | `repeated_denials` surfaces the cluster at threshold; **nothing auto-approves, nothing auto-hardens**; states unchanged | P/F |

### S14 — Insights & governance learning (SC-87..90 · PRD 37 · #383)

| ID | Capability | PRD | Env | Driver | Pass condition | Class |
|---|---|---|---|---|---|---|
| FT-SC-87 | 20 approvals → one redacted insight | 37 | ci | 20 similar approvals | exactly one repetitive-approval insight; counts + time range + one representative ask; **no raw arguments in the payload**; export scanner-clean | P/F |
| FT-SC-88 | Noisy policy → named tuning diff | 37 | ci | 10 same-reason denials | cluster insight names the reason; `to_action(config_diff)` exports a reviewable body; **applying is a PR, not an inbox button** | P/F |
| FT-SC-89 | Calibration gated + logged | 37 | ci | aggregate then per-principal view | aggregate renders by default; per-principal **requires** `governance_principals`; every access is a chained `insight-calibration-access` event | P/F |
| FT-SC-90 | Divergence → hardening proposal only | 37 | ci | divergence-heavy class | proposal present; **no path applies it**; decisions unchanged (asserted); action records reviewer + origin | P/F |

---

## 7. Detailed case specifications (flagship + novel mechanics)

Each case: **Goal · Preconditions · Steps · Assertions · Artifacts · Fallback**. `pass` = every assertion true, evidenced from the stored result. The non-flagship cases follow the same shape and are frozen in §6 + PRD 17/31–37; their per-case step scripts land in `journal/<case>/` as they run.

- **FT-SC-01 — the first-ask spine (flagship).** Goal: a brand-new user goes zero→allow on one terminal. Pre: scratch `--home`, `init`. Steps: producer ask (restore prod DB) → `inbox` → approve with typed confirmation. Assert: 4 blocks, TTL 300 s, exact event triple, resolve `allow/allow_ask_approved`, audit ≤3 transitions. Artifacts: terminal capture + resolve JSON. Fallback: none (P/F).
- **FT-SC-08 — the race (flagship).** Two answer submissions ≤200 ms apart (mocked clocks). Assert: one transition, one `answer-rejected(cause=late)`, idempotent double-resolve. Artifacts: both submissions + store diff.
- **FT-SC-13 + FT-SC-14 — the flood discriminator (flagship pair).** Run back-to-back on the same config. Assert both verdicts **and their contrast** (20 allowed / 180 denied vs 20/20 delivered). A tool that fails the pair is not field-ready even if each half "passes".
- **FT-SC-22 + FT-SC-23 — the attack packs (flagship, release-gating).** All 10 spoof/replay/forge attacks rejected with distinct causes + zero state change; all 10 poisoned cards inert on every configured channel + 0 injection approvals. Any red → **M33 blocked**, recorded in the report's red register with an owner.
- **FT-SC-24 — the fault matrix (flagship).** Each fault (locked store, corrupted schema, offline sink, channel down, scheduler killed) driven separately; every path must land deny-or-pending with an explicit degradation event. Silent allow or silent skip = red.
- **FT-SC-68 — the readiness bounce (flagship).** Red-band ask on an enforcing class. Assert: **nothing stored** (store diff empty), API 400 + `ask_not_decisionable` + repair contract with dimensions + `retry: after-repair`, CLI message parity. This is the newest load-bearing reject — it must fail closed before persistence.
- **FT-SC-72 — the repair round trip (flagship).** Deny → read the packet → agent repairs (adds the missing evidence / narrows scope) → resubmit → allow. Assert the packet fields, `retry_worthiness` honesty, prior-objection recall on the resubmission card, and that the **original denial is untouched**.
- **FT-SC-75 — no approve-all (flagship).** 20 asks, one operation. Assert the grouped view renders AND that answering remains per-ask — prove by answering 3 of 20 and showing 17 pending. Any group-decision path is a design red, not a test miss.
- **FT-SC-84 — the window that expires mid-burst (flagship).** Grant with a short TTL; ask #n covered, ask #n+1 after expiry → pending. Assert the **transition has no silent allow** and every consumed use is a chained event.
- **FT-SC-87/89 — redaction and the gate (flagship pair).** The insight payload carries shapes/counts/ids only (grep the export for the seeded raw command — must be absent); calibration per-principal access is refused without governance config and logged when granted.

---

## 8. CUJ coverage matrix (CUJ-15..48 + the core)

Every expansion CUJ is proven by ≥1 case; core CUJs ride the SC-01–SC-26 block (PRD 17 G1–G8). A `BLOCKED` case still names its CUJ in the report with the limitation.

| CUJ | Journey | Proving cases |
|---|---|---|
| CUJ-15 | Approve safely in 5 s (already narrowed) | FT-SC-71, study expansion cards |
| CUJ-16 | Denied once → agent resubmits correctly | FT-SC-72, FT-SC-05 |
| CUJ-17 | Review the whole operation | FT-SC-75 |
| CUJ-18 | Explain a decision without logs | FT-SC-78, FT-SC-82 |
| CUJ-19 | The product flags asks that never needed a human | FT-SC-87 |
| CUJ-20 | Incident mode without losing accountability | FT-SC-77 |
| CUJ-21 | Hand off across time zones | FT-SC-76 |
| CUJ-22 | Approve one, not the next ten lookalikes | FT-SC-83 |
| CUJ-23 | Catch ambiguous asks pre-delivery | FT-SC-68, FT-SC-70 |
| CUJ-24 | Prove human approved what executed | FT-SC-79, FT-SC-80, FT-SC-82 |
| CUJ-25..28 | Readiness banners / safe-vs-poor / contradictions | FT-SC-68..70 |
| CUJ-29..32 | One-move constrained approval · teach-permanently · machine fixes | FT-SC-71..74 |
| CUJ-33..36 | Deploy-as-one-operation · handoff · incident · blocked view | FT-SC-75..77 |
| CUJ-37..40 | Approved==executed · closure · one packet · drift | FT-SC-79..82 |
| CUJ-41..44 | Compression · tiny windows · burn-down · no drift | FT-SC-83..86 |
| CUJ-45..48 | Never-needed-a-human · noisy policy · calibration · hotspots | FT-SC-86..90 |
| core CUJs (1..14) | ask→card→answer→resolve, parity, escalation, flood, CI, evidence, adapters | FT-SC-01..26 |

---

## 9. Harness work (M32 items)

Do **not** fork the shipped harness. The additions this pass needs:

1. **Per-case step scripts + result files (`32.T`, #386).** One `journal/<case>/steps.sh` + `results/<suite>/<case>/` per case: env fingerprint, command log, stdout/stderr, resolve JSON, store/audit diffs, scanner run. Distinct log filenames per case (no shared temp names — the parallel-work rule).
2. **Study corpus freeze (`32.5`, #384).** The 46-card corpus (§S12 below), pre-registered answer sheet, `sha256` checksum recorded in the report **before** any participant runs. Corpus lives under `docs/field-test/v0.1.0/corpus/`, gitignored raw ordering until the run, checksum committed.
3. **Harness recipe journal (`32.8`, absorbed #104/#402).** Claude Code + Codex runs recorded per PRD 21 §D: harness version, date, transcript (redacted, scanner-checked), the gated tool call, the answer, the post-answer tool execution, deny + expiry behavior.
4. **Regression baseline pack (`32.7`, #401).** The SC-01–SC-26 expected-event sheet (this plan §S1–S8 + PRD 17) pinned against `ab94330` — the comparison source for the re-run.
5. **The report (`32.6`, #385).** Hand-maintained from the template; every verdict entered by hand from committed result files.

### 9.1 The 15-second study protocol (one cohort; PRD 21 Method B, extended)

- **Corpus (46 cards, pre-registered, checksummed):** 12 core + 12 degraded (SC-04 style: stripped policy_ref, null blast_radius, unknown reversibility) + 10 poisoned (SC-23 style: injected "approvals", fake urgency, unverified policy refs) + **12 expansion** (2 each: readiness red-band, constrained-alternative, unbindable-advice, bundle/handoff, closure-divergence, grant-burndown).
- **Participants:** ≥ 10 approvers who **did not author any card**; zero context provided (no session history, no coaching); randomized per-participant order.
- **Surface:** the worst realistic screen (the terminal card) — desktop/webhook variants recorded if a participant's flow uses one.
- **Instrumentation:** per-card delivered→answered timestamps from the store itself (not self-report).
- **Pass bars (pre-registered, frozen here):** ≥9/10 participants ≥10/12 core-correct; **median < 15 s; p90 < 25 s**; 100% of degraded cards answered deny-or-insufficient (never a confident wrong allow); **0 approvals caused by poisoned cards**; ≥9/12 expansion-correct per participant median ≥ 9/12. A missed bar is **published as missed** and M33 gates on the documented decision (#384/#385 acceptance).
- **Publication:** raw per-card timings + decisions + corpus checksum; small-n stated as small-n.

---

## 10. Execution order

1. **L0 suites green** on the release-candidate commit (`make test` + `ruff` + `mypy --strict`) — the standing gate.
2. **Layer 0 regression first (#401):** SC-01–SC-26 end-to-end CLI traces, compared against the `ab94330` baseline pack. No expansion case is evaluated before this block is green.
3. **SC-68–SC-74 (#380)** readiness + constrained allows → repair round trip.
4. **SC-75–SC-78 (#381)** operations → **SC-79–SC-86 (#382)** closure, grants → **SC-87–SC-90 (#383)** insights.
5. **Attack packs re-confirmed (#401 acceptance):** SC-22/23/24 re-run on the final build — red = M33 blocked.
6. **Study (#384):** corpus frozen + checksummed → participants → timings recorded. One cohort, one run.
7. **Harness recipes (#402/#104):** Claude Code then Codex CLI live runs; journal entries with versions + transcripts; `BLOCKED` honestly if the box cannot run one.
8. **Report (#385):** hand-entered verdicts; red register; published. Then 32.T/C/L/CR/D gates (#386–#390) and the M32 WBS checkpoint.

---

## 11. Gates, release-gate mapping & honesty

- A case passes **only** on its full assertion set from committed result files; anything less is a fail. `BLOCKED` is reserved for P/F|B cases with evidence + a named limitation.
- **Red blocks M33 (32.6/#385):** any FAIL — and specifically any attack-pack red (SC-22/23/24) — blocks the release milestone until fixed and re-run. Regressions vs the `ab94330` baseline are release-blocking with a named owner.
- **The M33 matrix consumes this run (Method D):** a `field-tested` Claude Code / Codex label requires its journal entry (#402); a `BLOCKED` harness yields **no label**, never a softened one.
- **The study gates M33 on its bars:** met, or the miss published with the decision (#384 acceptance).
- **No automation writes the report.** The hand-maintained marker + the builder-refusal guard are part of the product's credibility (PRD 21 §C).
- **Do not claim a gate passed unless it ran on the merged HEAD** of the release-candidate branch.

---

## 12. Report template

`docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` — published alongside this plan (hand-maintained marker at top): BLUF + release-gate verdict, run-status counts, small-group run journal, environment, what-was-tested, the **55-row master table** (all rows start `not run`), root-cause + defect sections, field notes, declared & blocked register, success metrics vs the pre-registered bars, action items, and reproducibility paths. Verdicts are entered **only** from committed result files.

---

## 13. Out of scope & limitations (stated up front)

- Enforcement of outcomes is the enforcer's job (the decision rule); field cases assert **inbox** state + the two harness exit-gate behaviors.
- Single-box, small-team run; the study is small-n and published as small-n — no population statistics, no enterprise-scale claims (PRD 21 non-claims).
- No third-party audit at v0.1.0; no hosted models anywhere in this plan; no harness beyond Claude Code / Codex CLI is claimed.
- M24/M25's original single passes are **absorbed here and into M33** — there is no separate core field pass or release rehearsal.

---

**Frozen:** 2026-11-07 · reviewed before execution · execution is `32.1`–`32.8` (#379–#385, #401; absorbed #98–#110).