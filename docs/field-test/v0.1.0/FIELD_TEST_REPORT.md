<!-- HAND-MAINTAINED DOCUMENT — edit by hand only.
     Do NOT regenerate or overwrite this file with any script or generator.
     A generated report builder must refuse a file carrying this marker (see PRD 21 §C:
     automation never overwrites the hand-maintained field-test report).
     A lossy automated rewrite has destroyed notes before; never again. -->

# agentinbox v0.1.0 — Field Test Report

> **Status: ⛔ STOPPED AFTER BATCH 16 — T1 SCRIPT ERROR + LEAK GATE (2026-11-07).** This is a **hand-maintained**
> journal, updated as the M32 sweep runs — not a generated scoreboard. Verdicts are entered **by hand, from
> committed result files under `field-test/v0.1.0/results/`**. Batch 1 first failed on a **field-step
> script defect** (duplicate `[classes.irreversible]` TOML), which was fixed and the case re-run green.
> Remaining suites are running in ≤5-case batches with deep validation after each.
> **Current:** **43 ✅ PASS · 8 ❌ FAIL · 2 ⛔ BLOCKED · 2 ▫ not run** — batches 0–16 run; deep validation
> 43 grounded PASS, 0 over-claimed; the Codex plugin-clone leak was caught and removed; final scan clean.
> The study cohort and the two remaining live cases are the only unverdicted work (recorded, not hidden).
> **Structure:** follows the `agentpolicy` v0.1.0 `FIELD_TEST_REPORT.md` format (a journal, not a
> scoreboard), pointed at [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) §6 (the 55-case matrix), §8 (CUJ map),
> §9.1 (the pre-registered study bars), §10 (run order), §11 (release gates).
> **Honesty rules:** a red blocks M33; attack packs are release-gating; `BLOCKED` is never reported as
> done; the study's bars are pre-registered and a miss is published as a miss.

---

## BLUF + Release Gate Verdict

> **⛔ STOPPED — 53/55 verdicted (43 ✅ PASS · 8 ❌ FAIL · 2 ⛔ BLOCKED · 2 ▫ not run).** Batch 0
> (5 core cases) and batch 1 (`FT-SC-10`, `FT-SC-10-LIVE`, `FT-SC-17`, `FT-SC-19`) are recorded and
> deep-validated (9 grounded PASS, 0 over-claimed, leak-clean). The live case's harness defect was fixed and
> re-run green; the sweep then paused per instruction. **No release (`v0.1.0` tag) may be cut from this
> report while any required case is `not run` or `BLOCKED`.**

### Run status (fills as the sweep runs)

| | Count |
|---|---|
| ✅ PASS (raw verdict) | 43 |
| — of which evidenced (asserted from committed result files, not exit-0) | 43 |
| ❌ FAIL | 8 |
| ⛔ BLOCKED (P/F\|B, environment cannot provide — named + evidenced) | 2 |
| ▫ not run | **2** (FT-SC-16-LIVE, FT-SC-24-LIVE) |
| Removed from scope (not claimed as supported) | 0 |

### Release gate verdict (M33 gate items; filled only as real runs land)

| # | Gate | Status | Evidence / honesty |
|---|---|---|---|
| 1 | Core SC-01–SC-26 re-run green on the expanded build (vs `ab94330` + PRD 17) | ▫ partial (8/26) | 8 ✅ core cases; the live extra case (FT-SC-10-LIVE) also ✅ after its step fix |
| 2 | Expansion SC-68–SC-90 verdicted with evidence | ▫ pending | plan §6 S9–S14 · #380–#383 |
| 3 | Attack packs green (SC-22/23/24) — **release-gating** | ❌ RED | SC-22/23 ✅; SC-24 ❌ on pytest unraisable warnings → **M33 blocked** |
| 4 | The 15-second study bars met (pre-registered, plan §9.1) | ▫ pending | met **or the miss published** with the M33 decision |
| 5 | Injection arm: 0 approvals from poisoned cards | ▫ pending | study + SC-23 |
| 6 | Harness recipes live (Claude Code + Codex CLI) with journal entries | ❌ FAIL | both T1 cases failed (answerer `mapfile` script error); LLM pairs captured 11/11 |
| 7 | Evidence clean: 0 scanner findings over store, captures, exports, packets | ▫ pending | SC-21 + the per-case leak gate |
| 8 | Report honest: verdicts from result files, red register populated, hand-maintained | ▫ pending | this document |

---

## Small-Group Run Journal

Work is done in **small groups** (by suite, in plan §10 order). Each group: **run → verify → fix → journal**,
then pause. A group is listed here only once **every** case in it has run; a failing case is fixed (with a
regression note) before the group closes. One run per case; a re-run is a **second** entry with its own log.

### Group 1 — Layer-0 core regression (SC-01–SC-26 vs `ab94330`) — ▫ partial (8/26 + live)

- **Run:** batch 0 (committed 5 cases) + batch 1 `run-suite.sh s0-core FT-SC-10 FT-SC-10-LIVE FT-SC-17 FT-SC-19`; logs in `field-test/v0.1.0/results/s0-core/`.
- **Verdicts:** ✅ `FT-SC-01, 02, 05, 06, 09, 10, 17, 19` and ✅ `FT-SC-10-LIVE` after the step fix.
- **Regressions vs baseline:** none observed in the product cases that ran.
- **Paused:** after the live re-run went green, per instruction; remaining batches not started.

### Group 2 — Readiness & constrained allows (SC-68–SC-74) — ▫ not run (#380)
### Group 3 — Operations (SC-75–SC-78) — ▫ not run (#381)
### Group 4 — Outcome closure & proof (SC-79–SC-82) — ▫ not run (#382)
### Group 5 — Grants & compression (SC-83–SC-86) — ▫ not run (#383)
### Group 6 — Insights & governance (SC-87–SC-90) — ▫ not run (#383)
### Group 7 — Attack packs re-confirmed on the final build (SC-22/23/24) — ❌ partial (SC-24 red)
### Group 8 — The 46-card study cohort — ⛔ blocked (#384)
### Group 9 — Harness recipes live (Claude Code, then Codex CLI) — ❌ failed (answerer script error)

### Sweep execution log (batches of ≤5, deep validation after each)

| Batch | Suite | Cases | Run | Deep validation | Verdicts |
|---|---|---|---|---|---|
| 0 (pre-sweep) | s0-core | FT-SC-01, 02, 05, 06, 09 | committed, 5 cases / 1 boot | 5 grounded PASS, leak clean | ✅ 5 pass |
| 1 | s0-core | FT-SC-10, 10-LIVE, 17, 19 | 4 cases / 1 clean boot; live case re-run after step fix | 9 verdicts total: 9 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass (live after fix) |
| 2 | s1-cross-channel | FT-SC-07, 08, 18 | 3 cases / 1 clean boot | 12 verdicts: 12 grounded PASS, 0 over-claimed, leak clean | ✅ 3 pass |
| 3 | s2-escalation | FT-SC-11, 12 | 2 cases / 1 clean boot | 14 verdicts: 14 grounded PASS, 0 over-claimed, leak clean | ✅ 2 pass |
| 4 | s3-flood | FT-SC-13, 14, PAIR | 3 cases / 1 clean boot | 17 verdicts: 17 grounded PASS, 0 over-claimed, leak clean | ✅ 3 pass (pair enforced) |
| 5 | s4-ci | FT-SC-15, 16 | 2 cases / 1 clean boot | 19 verdicts: 17 grounded PASS, 0 over-claimed, leak clean | ❌ 2 fail (pytest unraisable ResourceWarning, not product assertions) |
| 6 | s5-evidence | FT-SC-20, 21 | 2 cases / 1 clean boot | 21 verdicts: 17 grounded PASS, 0 over-claimed, leak clean | ❌ 2 fail (same pytest unraisable ResourceWarning) |
| 7 | s6-attacks | FT-SC-22, 23, 24 | 3 cases / 1 clean boot | 24 verdicts: 19 grounded PASS, 0 over-claimed, leak clean | ✅ 2 pass (release-gating) · ❌ 1 fail (unraisable warning) |
| 8 | s7-governance | FT-SC-25, 26 | 2 cases / 1 clean boot | 26 verdicts: 20 grounded PASS, 0 over-claimed, leak clean | ✅ 1 pass · ❌ 1 fail (unraisable warning) |
| 9 | s8-readiness | FT-SC-68, 69, 70 | 3 cases / 1 clean boot | 29 verdicts: 23 grounded PASS, 0 over-claimed, leak clean | ✅ 3 pass |
| 10 | s9-constrained | FT-SC-71, 72, 73, 74 | 4 cases / 1 clean boot | 33 verdicts: 27 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass |
| 11 | s10-operations | FT-SC-75, 76, 77, 78 | 4 cases / 1 clean boot | 37 verdicts: 31 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass |
| 12 | s11-outcomes | FT-SC-79, 80, 81, 82 | 4 cases / 1 clean boot | 41 verdicts: 35 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass |
| 13 | s12-grants | FT-SC-83, 84, 85, 86 | 4 cases / 1 clean boot | 45 verdicts: 39 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass |
| 14 | s13-insights | FT-SC-87, 88, 89, 90 | 4 cases / 1 clean boot | 49 verdicts: 43 grounded PASS, 0 over-claimed, leak clean | ✅ 4 pass |
| 15 | s14-study | FT-SC-03, 04 | 2 cases, no human cohort | 51 verdicts: 43 grounded PASS, 0 over-claimed, leak clean | ⛔ 2 blocked (participants absent) |
| 16 | s15-harness | FT-T1-CLAUDE, FT-T1-CODEX | 2 live cases; OMLX reachable | 53 verdicts: 43 grounded PASS, 0 over-claimed; **leak gate found a token in Codex plugin tmp** | ❌ 2 fail (answerer `mapfile`; Codex allow/audit; leaked plugin artifact removed) |

---

## Environment

*(recorded per run to `results/<suite>/env.json`; the row below is the fingerprint template)*

| Item | Value |
|---|---|
| Host / OS / arch | *(e.g. macOS Darwin arm64 · version)* |
| Python / venv | *(repo `.venv`, exact version)* |
| agentinbox build | *(commit + branch of the release candidate)* |
| Core regression baseline | `ab94330` (M23 core) + PRD 17 expected events |
| Channels configured | terminal · desktop · webhook (loopback) — as used per case |
| Claude Code | *(version, or "absent → FT-T1-CLAUDE BLOCKED")* |
| Codex CLI | *(version, or "absent → FT-T1-CODEX BLOCKED")* |
| Study corpus | *(checksum + participant count, once frozen — plan §9.1)* |
| Clock / sync | *(UTC, `doctor` clock check result)* |
| Results / journal | `field-test/v0.1.0/results/<suite>/` · `journal/<case>/` |

---

## OMLX LLM — the model choice, and why

The only LLM in this field test is the **box-local OMLX** server (`http://127.0.0.1:8000`) driving the
Tier-1 harness agents (Claude Code / Codex CLI). **No hosted model and no vendor key is used anywhere.**
agentinbox's own decision path is deterministic — the LLM is a test subject (it emits the tool call the
hook gates), never a decider.

**Pinned model: `Qwen3-4B-Instruct-2507-4bit`.** Chosen on the same two criteria as agentpolicy's
field test, in this order:

| OMLX model (served on this box) | tool calls (3 trials) | p50 latency | verdict |
|---|---|---|---|
| **`Qwen3-4B-Instruct-2507-4bit`** | **3/3** | **~1.0 s** | ✅ **PINNED** |
| `Qwen3.5-4B-4bit` / `mlx-community--Qwen3.5-4B-4bit` | 3/3 | ~6.6–6.8 s | fallback (~7× slower) |
| `Qwen3.5-9B-MLX-4bit` | 3/3 | ~12.9 s | too slow |
| `Qwen3-8B-4bit` | 3/3 | ~27.5 s | too slow (~27× slower) |
| `Llama-3.2-3B-Instruct-4bit` | **0/3** | ~0.8 s | ❌ disqualified — never emits a tool call |
| `MarkItDown` | — | — | document converter, not an LLM; excluded |

**Justification:** tool-call reliability gates (a model that never calls the guarded tool proves
nothing, however fast — hence Llama-3.2-3B is out despite the lowest latency); then latency decides
(the pin is ~7× faster at p50 than the Qwen3.5-4B pair, ~27× faster than Qwen3-8B, which is the
difference between minutes and an hour across a multi-call Tier-1 sweep). Provenance: it is exactly
agentpolicy's field-test pin, so the choice is evidence-backed, not novel. Both harnesses route
through `t1_proxy.py`, which logs every request/response pair (sanitized); the deep-validation gate
fails any Tier-1 PASS without a balanced, 2xx, secret-free capture. Re-derive with a field-test-shaped
request on a new box before re-pinning; a changed model is a new run, not a continuation. Full
protocol: plan [§4.1](FIELD_TEST_PLAN.md).

*(Benchmark figures to be re-measured and recorded here when the Tier-1 runs execute.)*

---

## What Was Tested

*(fills as groups close — state per group: which cases ran, on what build, with which drivers (plan §3), and
what the assertions were grounded in: store diffs, resolve JSON, audit chain, scanner runs — never "exit 0")*

- **Run (honest): 53/55 verdicted** — ✅ 43, ❌ 8 (six pytest-unraisable cases + two Tier-1), ⛔ 2 blocked (study), ▫ 2 not run (the two remaining live cases). The sweep stopped on a Tier-1 answerer script error and a leak-gate hit; the leaked plugin artifact was removed and the results rescanned clean.
  The deterministic L0 suites were green at authoring (924 tests, 95.11%, `ruff` + `mypy --strict` clean at
  `2dedc7d`); the field verdicts above are the first real runs.
- **Blocked (declared up front): the Tier-1 harness recipes and the study cohort** await the field box /
  real Claude Code / Codex CLI / ≥10 non-author participants. They are `P/F|B` cases (plan §0.2): blocked
  verdicts will carry evidence of the blocked attempt and feed **no** matrix label to M33 until unblocked.

**Status vocabulary:** `PASS | FAIL | BLOCKED | not run` — a PASS counts only with its assertion evidence
re-derived from the committed result files. **Class:** **P/F** = hard gate · **P/F|B** = pass/fail-or-blocked
(a named, evidenced block is acceptable; a silent skip never is).

---

## Scenario Results (Master Table)

55 cases (49 SC core/expansion + the flood-pair + 3 live daemon/fault cases + 2 Tier-1; IDs and pass conditions frozen in plan §6). **5 are PASS (the committed core group); 50 are `not run`; verdicts are entered by hand, one per case, from `results/<suite>/<case>/`.**

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-SC-01 | core-lifecycle | P/F | ✅ PASS | first ask, terminal, zero config — grounded in Docker |
| FT-SC-02 | core-lifecycle | P/F | ✅ PASS | malformed rejected loudly, nothing partial persists — grounded in Docker |
| FT-SC-03 | study | P/F\|B | ⛔ BLOCKED | ≥10 non-author participants not provisioned; no study result claimed |
| FT-SC-04 | study/quality | P/F\|B | ⛔ BLOCKED | same study cohort missing; no degraded-card result claimed |
| FT-SC-05 | core-lifecycle | P/F | ✅ PASS | rescope hint → new identity, no state reuse — grounded in Docker |
| FT-SC-06 | core-lifecycle | P/F | ✅ PASS | duplicate ingest coalesces — grounded in Docker |
| FT-SC-07 | cross-channel | P/F | ✅ PASS | second-surface approve + terminal parity — grounded in Docker |
| FT-SC-08 | cross-channel | P/F | ✅ PASS | race: one decision, second rejected `late` — grounded in Docker |
| FT-SC-09 | core-lifecycle | P/F | ✅ PASS | timeout = deny + warning, jitter ≤1 s — grounded in Docker |
| FT-SC-10 | core-lifecycle | P/F | ✅ PASS | expiry survives crash + clock step-back — grounded in Docker |
| FT-SC-10-LIVE | live | P/F | ✅ PASS | real kill -9 + restart; expired exactly once; resolve deny/`human_gate_timeout` — after fixing the step |
| FT-SC-11 | escalation | P/F | ✅ PASS | 3 a.m. drill, tier claims revoked — grounded in Docker |
| FT-SC-12 | escalation | P/F | ✅ PASS | ladder exhaustion denies, TTL never extended — grounded in Docker |
| FT-SC-13 | flood | P/F | ✅ PASS | attack pack: burst allowed / overflow denied (counts recorded) — grounded in Docker |
| FT-SC-14 | flood | P/F | ✅ PASS | legitimate burst — **passes together with SC-13** — grounded in Docker |
| FT-SC-PAIR | flood | P/F | ✅ PASS | paired verdict: SC-13 and SC-14 both pass — grounded in Docker |
| FT-SC-15 | ci | P/F | ❌ FAIL | pytest 9.2.0/Py3.13 turns an unclosed-SQLite ResourceWarning into `PytestUnraisableExceptionWarning` (6 passed / 2 failed); product assertions passed |
| FT-SC-16 | ci | P/F | ❌ FAIL | same pytest unraisable-warning failure (11 passed / 2 failed) in the CLI gate tests |
| FT-SC-16-LIVE | live | P/F | ▫ not run | real gate exit matrix 0/2/3/5 |
| FT-SC-17 | governance | P/F | ✅ PASS | self-review denied (+ allowed/audited variant) — grounded in Docker |
| FT-SC-18 | cross-channel | P/F | ✅ PASS | channel failover, no duplicate notify — grounded in Docker |
| FT-SC-19 | cross-channel | P/F | ✅ PASS | late answer = visible no-op — grounded in Docker |
| FT-SC-20 | evidence | P/F | ❌ FAIL | pytest 9.2.0/Py3.13 unraisable ResourceWarning (4 failed / 21 passed); product assertions passed |
| FT-SC-21 | evidence | P/F | ❌ FAIL | same unraisable ResourceWarning (1 failed / 11 passed); scanner assertions passed |
| FT-SC-22 | attacks | P/F | ✅ PASS | **release-gating** — spoof/replay/forge suite passed, grounded in Docker |
| FT-SC-23 | attacks | P/F | ✅ PASS | **release-gating** — injection suite passed, 0 approvals |
| FT-SC-24 | faults | P/F | ❌ FAIL | same pytest unraisable ResourceWarning; product assertions passed (release still blocked) |
| FT-SC-24-LIVE | live | P/F | ▫ not run | corrupt + locked store each fail closed (4) |
| FT-SC-25 | adapters | P/F | ✅ PASS | LangGraph round-trip + crash-resume, one execution — grounded in Docker |
| FT-SC-26 | offline | P/F | ❌ FAIL | pytest unraisable ResourceWarning; product assertions passed |
| FT-SC-68 | readiness | P/F | ✅ PASS | pre-write bounce, nothing stored, repair contract — grounded in Docker |
| FT-SC-69 | readiness | P/F | ✅ PASS | contradiction visible / reject-on-ingest — grounded in Docker |
| FT-SC-70 | readiness | P/F | ✅ PASS | same weak ask, different class bands — grounded in Docker |
| FT-SC-71 | constrained | P/F | ✅ PASS | one-click constrained allow + constraint set — grounded in Docker |
| FT-SC-72 | constrained | P/F | ✅ PASS | repair packet round trip, no human re-teach — grounded in Docker |
| FT-SC-73 | constrained | P/F | ✅ PASS | edit re-fingerprints, enforcer runs edited form — grounded in Docker |
| FT-SC-74 | constrained | P/F | ✅ PASS | unbindable = advice only, cannot be picked — grounded in Docker |
| FT-SC-75 | operations | P/F | ✅ PASS | 20-ask bundle: one screen, 20 answers, no approve-all — grounded in Docker |
| FT-SC-76 | operations | P/F | ✅ PASS | shift handoff preserves TTL + notes — grounded in Docker |
| FT-SC-77 | operations | P/F | ✅ PASS | incident mode, denies still deny — grounded in Docker |
| FT-SC-78 | operations | P/F | ✅ PASS | narrative reproduces a 3 a.m. denial — grounded in Docker |
| FT-SC-79 | outcomes | P/F | ✅ PASS | executed closure + offline-verifiable packet — grounded in Docker |
| FT-SC-80 | outcomes | P/F | ✅ PASS | exceeded manifest loud, never absorbed — grounded in Docker |
| FT-SC-81 | outcomes | P/F | ✅ PASS | rollback leaves the decision untouched — grounded in Docker |
| FT-SC-82 | outcomes | P/F | ✅ PASS | packet-only reviewer reconstructs end-to-end — grounded in Docker |
| FT-SC-83 | grants | P/F | ✅ PASS | 12-ask compressed view, 12 answers, export complete — grounded in Docker |
| FT-SC-84 | grants | P/F | ✅ PASS | window expires mid-burst → per-ask, 0 silent allows — grounded in Docker |
| FT-SC-85 | grants | P/F | ✅ PASS | owner revocation is immediate + loud — grounded in Docker |
| FT-SC-86 | grants | P/F | ✅ PASS | repeated denials → insight, no auto-hardening — grounded in Docker |
| FT-SC-87 | insights | P/F | ✅ PASS | 20 approvals → one redacted insight — grounded in Docker |
| FT-SC-88 | insights | P/F | ✅ PASS | noisy policy → named tuning diff (PR to apply) — grounded in Docker |
| FT-SC-89 | insights | P/F | ✅ PASS | calibration aggregate; per-principal gated + logged — grounded in Docker |
| FT-SC-90 | insights | P/F | ✅ PASS | divergence → proposal only, nothing applies itself — grounded in Docker |

**Harness cases (P/F|B — plan §S14):**

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-T1-CLAUDE | harness | P/F\|B | ❌ FAIL | triple + 6/6 LLM pairs pass; audit empty — answerer script used `mapfile`, unavailable on this macOS bash |
| FT-T1-CODEX | harness | P/F\|B | ❌ FAIL | 5/5 LLM pairs, deny held; allow not executed + audit empty (same `mapfile`); plugin-clone bearer token leaked into results and was removed |

---

## Per-Suite Results

*(fills by group: suite → cases run, pass rate, where the evidence lives, and what was deep-verified vs
spot-checked. A suite is complete only when every case in it has a verdict.)*

---

## Root Cause Analysis

*(one entry per FAIL or regression, entered when found: symptom → root cause → fix commit → regression
test that now guards it. No entry may be closed without all four. At authoring: none — nothing has run.)*

- **Six cases — ❌ pytest/toolchain, not product assertions.** `FT-SC-15, 16, 20, 21, 24, 26` fail under
  pytest 9.2.0 on Python 3.13 because unclosed-SQLite `ResourceWarning`s are promoted to
  `PytestUnraisableExceptionWarning`; the product assertions inside those selections passed (e.g. 6/2,
  11/2, 21/4, 11/1). Fix: none (do-not-fix rule); this is a harness/toolchain gate, not a policy defect.
- **FT-T1-CLAUDE / FT-T1-CODEX — ❌ Tier-1 answerer script error.** The three-call/allow-deny behaviour and
  LLM capture worked (Claude 6/6 pairs, Codex 5/5; secret-free), but `t1_answerer.sh` calls `mapfile`, which
  macOS's bash 3.2 does not provide, so the answerer died and `export --session` produced an empty audit;
  Codex's allow command also did not execute (the sandbox/runner path, not agentinbox). Fix: none applied
  (stop rule); both cases remain ❌ and feed **no** matrix label to M33.
- **Leak-gate hit — Codex plugin clone.** `ft_capture` copied Codex's `.tmp/plugins` into the case artifacts;
  `scan_results.py` found a bearer token there. The unsafe `.tmp` directory was removed from the results
  (evidence, not test code) and the final scan is clean; no secret was committed. The harness still needs a
  sanitisation/capture-exclusion fix before a rerun can publish the Codex evidence.
- **FT-SC-10-LIVE — ✅ after two harness-step fixes (never a product failure).** Symptom 1: the live
  daemon never started; the step appended a second `[classes.irreversible]` table to the `init` scaffold
  (`Cannot declare ('classes','irreversible') twice`), invalidating the TOML. Fix 1: the step now writes a
  complete dedicated config instead of appending duplicate tables. Symptom 2 (after fix 1): expiry fired
  exactly once, but the assertion grepped the export for `human_gate_timeout`, which lives on `resolve()`,
  not on the audit row (`reason="ttl"`). Fix 2: the assertion now calls the shipped `resolve()` and asserts
  `status=deny` + `reason_code=human_gate_timeout`. Re-run: ✅ PASS. Regression guard: the deterministic
  `FT-SC-10` suite and the live step now both cover the expiry contract.

---

## Defect Catalogue

| # | Case | Defect | Cause | Fix | Regression | Owner | Status |
|---|---|---|---|---|---|---|---|
| 1 | FT-SC-10-LIVE | live daemon did not start; then resolve assertion looked in the wrong artifact | duplicate `[classes.irreversible]` TOML table; `human_gate_timeout` lives on `resolve()`, not the audit row | step writes a dedicated config; assertion calls `resolve()` | live step re-run ✅ PASS | field-test harness | ✅ resolved |
| 2 | FT-SC-15, 16, 20, 21, 24, 26 | pytest reports failures though product assertions passed | pytest 9.2.0 / Python 3.13 promotes unclosed-SQLite `ResourceWarning` to `PytestUnraisableExceptionWarning` | none (do-not-fix rule) | none | field-test toolchain | ⛔ open |
| 3 | FT-T1-CLAUDE, FT-T1-CODEX | answerer dies, audit empty; Codex allow not executed | `mapfile` unavailable in macOS bash 3.2 | none (stop rule) | none | field-test harness | ⛔ open |
| 4 | FT-T1-CODEX | bearer token in results | `ft_capture` copied Codex `.tmp/plugins` | unsafe artifact removed; capture exclusion still needed | final leak scan clean | field-test harness | ⚠️ mitigated, fix needed |

---

## Field Notes — Findings, Learnings, and Observations

*(hand-written as the sweep runs: what surprised us, what the fixtures could not reproduce, where the
harness — not the product — broke. Numbered, dated, never summarized away.)*

1. **2026-11-07 — the first live case failed on the harness, not the product.** Batch 1's eight product
   cases were grounded (SC-10/17/19 and the five earlier), but `FT-SC-10-LIVE` never reached the daemon:
   its step appended a second `[classes.irreversible]` table to the `init` scaffold, so the config was
   invalid TOML. Lesson: **live steps must derive their config, not append duplicate tables** — and a
   live case must fail loudly before the first assertion, not with an empty export. The sweep stopped here
   per instruction; no test or script was changed.
2. **The suite-backed cases are real but shallow.** All eight ✅ rest on shipped pytest selections run
   inside the Docker SUT (the five batch-0 cases alone exercised 97 tests, all passing); they are grounded
   from verdict files, not CLI-level scenario walks. The flagship CLI steps remain the next harness gap —
   the ✅ verdicts do not yet claim the full PRD walkthrough.
3. **Deep validation is doing its job.** Batch 1: 9 verdicts, 9 grounded PASS, 0 over-claimed, leak scan
   clean. The gate independently re-read every verdict/assertion pair and would have failed an ungrounded
   PASS or a count mismatch (it already caught an assertion-accounting bug before this sweep).
4. **Two distinct harness lessons from one case.** (a) Never append a TOML table the `init` scaffold already
   defines — write a complete dedicated config for a live scenario. (b) Assert the product's actual
   contract: `human_gate_timeout` is a `resolve()` reason code, not an audit-row field (the row carries
   `reason="ttl"`). After both fixes the case passes; the product code was never changed.
5. **The live case now proves the recovery path for real.** `kill -9` mid-TTL → restart after expiry →
   exactly one `expired` transition, and `resolve()` returns `deny / human_gate_timeout`. This is stronger
   evidence than the in-process `FT-SC-10` suite alone.
6. **One toolchain theme explains six ❌.** `FT-SC-15/16/20/21/24/26` fail on pytest 9.2.0 + Python 3.13's
   unraisable `ResourceWarning` handling, not on their product assertions. The field verdict is still ❌
   (the harness must be reproducible), but the defect is in the runner's warning policy, not the inbox.
   This is the dominant failure theme of the sweep.
7. **Tier-1 got further than expected, then died on a shell portability bug.** OMLX answered, the hooks
   gated real calls, and LLM capture was complete (Claude 6/6, Codex 5/5, secret-free). The answerer then
   failed because `mapfile` is bash 4+, while macOS ships bash 3.2 — an empty audit and a failed Codex allow.
   Lesson: the harness must be bash-3.2-safe or run its answerer under a modern shell.
8. **The leak gate did its job on live evidence.** Codex's plugin clone carried a bearer token into the
   captured tree; the scanner caught it before commit, the unsafe `.tmp` tree was removed, and the rescan
   is clean. Lesson: live harness capture must exclude vendor/tool caches, not just sanitize output text.

---

## Coverage, Gaps, and Declared Limitations

Status vocabulary: **not run | ✅ PASS | ❌ FAIL | ⛔ BLOCKED** — this run so far: **43 ✅ PASS · 8 ❌ FAIL ·
2 ⛔ BLOCKED · 2 ▫ not run** (stopped after batch 16: T1 script error + leak gate).

- **Coverage so far:** 53/55 cases verdicted — 43 ✅ PASS, 8 ❌ FAIL, 2 ⛔ BLOCKED, 2 ▫ not run.
  Deep validation: 53 verdicts, 43 grounded PASS, 0 over-claimed; two leak-gate hits (T1 Codex plugin
  clone) were removed and the final scan is clean. The study bars are unproven (blocked); the two
  remaining live cases were not started after the stop rule.
- **Declared & Blocked register (fills as runs land):** every `BLOCKED` case names (1) what is missing,
  (2) the evidence of the blocked attempt, (3) the downstream gate consequence (M33 label withheld).
  **At authoring:** the Tier-1 harness recipes + the study cohort await the field box + participants.
- **Not tested (honest):** everything not later listed as PASS/FAIL/BLOCKED above — stated as `not run`,
  never omitted.

---

## Success Metrics (pre-registered bars; Achieved fills as the sweep runs)

| Measure | Target (plan §9.1 — frozen) | Achieved | Evidence |
|---|---|---|---|
| Core regression | SC-01–SC-26 green vs `ab94330` | ▫ pending | #401 run journal |
| Expansion verdicts | SC-68–SC-90 all evidenced | ▫ pending | #380–#383 result files |
| Study: core correctness | ≥9/10 participants ≥10/12 | ▫ pending | raw decisions sheet |
| Study: time | median < 15 s · p90 < 25 s | ▫ pending | per-card delivered→answered timings |
| Study: degraded | 100% deny-or-insufficient | ▫ pending | degraded-arm decisions |
| Study: poisoned | **0** approvals from injection | ▫ pending | poisoned-arm decisions |
| Study: expansion cards | ≥9/12 correct per participant median ≥ 9/12 | ▫ pending | expansion-arm decisions |
| Attack packs | 0 crafted allows (SC-22/23/24) | ❌ red | SC-22/23 ✅; SC-24 ❌ on pytest unraisable warnings → M33 blocked |
| Evidence hygiene | 0 scanner findings over any result | ⚠️ caught + cleaned | Codex plugin bearer token caught by leak gate; unsafe tree removed; final scan clean |
| Harness journal | both recipes: version + transcript + outcome | ❌ fail | both T1 cases failed; no matrix label |
| LLM capture (Tier-1) | every real call logged: balanced, 2xx, secret-free | ✅ 11/11 pairs | Claude 6/6, Codex 5/5; cases still ❌ on the answerer/allow/audit |

---

## Action Items

*(fills as the sweep runs; a checked item cites its evidence)*

1. [ ] Provision the field box (Claude Code + Codex CLI installed) — unblocks FT-T1-CLAUDE/FT-T1-CODEX.
2. [ ] Freeze the 46-card study corpus + pre-registered answers + checksum (#384).
3. [ ] Run Layer-0 core regression SC-01–SC-26 vs `ab94330` (#401) — **before any expansion case**.
4. [ ] Run expansion groups SC-68–SC-90 (#380–#383), then the attack-pack re-confirmation.
5. [ ] Run the study cohort; record raw timings + decisions (#384).
6. [ ] Run both harness recipes; write the journal entries (#402/#104 → M33 matrix labels).
7. [ ] Enter every verdict **by hand** into this report; populate the red register; publish (#385).
8. [ ] Close 32.T/C/L/CR/D gates (#386–#390); record the M32 checkpoint in the WBS index; then M33 may
       begin — **only** if this report carries no open red.

---

## Reproducibility / Evidence Paths

```sh
# Environment + harness (recorded per run)
#   fingerprint -> field-test/v0.1.0/results/<suite>/env.json
#   raw logs    -> field-test/v0.1.0/journal/<case>/  (never in this report)

# Layer-0 backstop (the deterministic suites under every case)
make test                      # 924 tests, >=95% coverage
make lint && make typecheck    # ruff zero, mypy --strict clean

# Per-case shape (as each case runs)
#   steps:   journal/<case>/steps.sh      # the exact CLI/in-process sequence
#   log:     results/<suite>/<case>/{commands.log,stdout,stderr,resolve.json,store.diff}
#   leak:    python -m agentinbox.scanner ...   # 0 findings required over every artifact

# Study (once frozen)
#   corpus checksum + answer sheet -> committed BEFORE any participant runs (plan §9.1)

# This report
#   hand-maintained: no generator may write this file (marker at top).
```

## Appendices

- Plan: [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) — §6 the 49-case matrix · §8 CUJ map · §9.1 study bars ·
  §10 run order · §11 release gates.
- WBS: [Part 17](../../wbs/v0.1.0/wbs-v0.1.0-part17-expansion-fieldtest-release.md) (M32 items
  #379–#390, #401; absorbed M24 #98–#110).
- PRDs: [17 scenarios](../../prd/17-scenarios.md) · [21 evidence register](../../prd/21-evidence-register-and-method.md) ·
  [31 CUJs](../../prd/31-0.1.0-cuj-and-feature-gaps.md) · 32–37 (expansion) ·
  [12 traceability](../../prd/12-traceability.md).
- Harness recipes: [harness-recipes.md](../adapters/harness-recipes.md) (Claude Code `PreToolUse` · Codex CLI wrapper).