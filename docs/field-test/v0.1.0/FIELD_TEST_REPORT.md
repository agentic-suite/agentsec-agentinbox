<!-- HAND-MAINTAINED DOCUMENT — edit by hand only.
     Do NOT regenerate or overwrite this file with any script or generator.
     A generated report builder must refuse a file carrying this marker (see PRD 21 §C:
     automation never overwrites the hand-maintained field-test report).
     A lossy automated rewrite has destroyed notes before; never again. -->

# agentinbox v0.1.0 — Field Test Report

> **Status: ▫ NOT RUN (plan frozen, sweep pending).** This is a **hand-maintained** journal, updated as the
> M32 sweep runs — not a generated scoreboard. Verdicts are entered **by hand, from committed result files
> under `field-test/v0.1.0/results/`**; counts below are placeholders until real runs exist and are
> never auto-filled. Nothing in this template claims a result it does not have.
> **Current:** **0 ✅ PASS · 0 ❌ FAIL · 0 ⛔ BLOCKED · 55 ▫ not run (plan frozen 2026-11-07)** — every row of
> the master table starts `not run`; the plan ([FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) §6) is frozen and
> reviewed; the field box + ≥10 study participants are **not yet provisioned** (recorded, not hidden).
> **Structure:** follows the `agentpolicy` v0.1.0 `FIELD_TEST_REPORT.md` format (a journal, not a
> scoreboard), pointed at [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) §6 (the 49-case matrix), §8 (CUJ map),
> §9.1 (the pre-registered study bars), §10 (run order), §11 (release gates).
> **Honesty rules:** a red blocks M33; attack packs are release-gating; `BLOCKED` is never reported as
> done; the study's bars are pre-registered and a miss is published as a miss.

---

## BLUF + Release Gate Verdict

> **▫ PENDING — the M32 sweep has not run.** Placeholders below state what the sweep must prove and where
> its verdicts will land. Nothing here is a claim. The first run fills: the Layer-0 core regression
> (SC-01–SC-26 vs the `ab94330` baseline, plan §5), the expansion cases (SC-68–SC-90), the 46-card
> 15-second study (plan §9.1), and the Claude Code / Codex CLI live recipes (plan §7 flagship, §S14).
> **No release (`v0.1.0` tag) may be cut from this report while this BLUF reads PENDING.**

### Run status (fills as the sweep runs)

| | Count |
|---|---|
| PASS (raw verdict) | 0 |
| — of which evidenced (asserted from committed result files, not exit-0) | 0 |
| FAIL | 0 |
| BLOCKED (P/F\|B, environment cannot provide — named + evidenced) | 0 |
| not run | **55** (all rows of the master table below) |
| Removed from scope (not claimed as supported) | 0 |

### Release gate verdict (M33 gate items; filled only as real runs land)

| # | Gate | Status | Evidence / honesty |
|---|---|---|---|
| 1 | Core SC-01–SC-26 re-run green on the expanded build (vs `ab94330` + PRD 17) | ▫ pending | plan §5 · #401 — no regression may be open at release |
| 2 | Expansion SC-68–SC-90 verdicted with evidence | ▫ pending | plan §6 S9–S14 · #380–#383 |
| 3 | Attack packs green (SC-22/23/24) — **release-gating** | ▫ pending | any red = **M33 blocked** |
| 4 | The 15-second study bars met (pre-registered, plan §9.1) | ▫ pending | met **or the miss published** with the M33 decision |
| 5 | Injection arm: 0 approvals from poisoned cards | ▫ pending | study + SC-23 |
| 6 | Harness recipes live (Claude Code + Codex CLI) with journal entries | ▫ pending | `BLOCKED` yields **no matrix label**, never a softened one |
| 7 | Evidence clean: 0 scanner findings over store, captures, exports, packets | ▫ pending | SC-21 + the per-case leak gate |
| 8 | Report honest: verdicts from result files, red register populated, hand-maintained | ▫ pending | this document |

---

## Small-Group Run Journal

Work is done in **small groups** (by suite, in plan §10 order). Each group: **run → verify → fix → journal**,
then pause. A group is listed here only once **every** case in it has run; a failing case is fixed (with a
regression note) before the group closes. One run per case; a re-run is a **second** entry with its own log.

### Group 1 — Layer-0 core regression (SC-01–SC-26 vs `ab94330`) — ▫ not run (#401)

- **Run:** *(recorded when run — exact commands + log paths)*
- **Verdicts:** *(26 rows from the master table, entered by hand)*
- **Regressions vs baseline:** *(none documented, or each with cause + owner + fix commit)*

### Group 2 — Readiness & constrained allows (SC-68–SC-74) — ▫ not run (#380)
### Group 3 — Operations (SC-75–SC-78) — ▫ not run (#381)
### Group 4 — Outcome closure & proof (SC-79–SC-82) — ▫ not run (#382)
### Group 5 — Grants & compression (SC-83–SC-86) — ▫ not run (#383)
### Group 6 — Insights & governance (SC-87–SC-90) — ▫ not run (#383)
### Group 7 — Attack packs re-confirmed on the final build (SC-22/23/24) — ▫ not run (#401 acceptance)
### Group 8 — The 46-card study cohort — ▫ not run (#384)
### Group 9 — Harness recipes live (Claude Code, then Codex CLI) — ▫ not run (#402/#104)

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

- **Not yet run (honest): all 55 cases** — the plan is frozen ([FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md)) and
  the deterministic L0 suites were green at authoring (924 tests, 95.11%, `ruff` + `mypy --strict` clean at
  `2dedc7d`), but **no field case has run and no verdict exists**.
- **Blocked (declared up front): the Tier-1 harness recipes and the study cohort** await the field box /
  real Claude Code / Codex CLI / ≥10 non-author participants. They are `P/F|B` cases (plan §0.2): blocked
  verdicts will carry evidence of the blocked attempt and feed **no** matrix label to M33 until unblocked.

**Status vocabulary:** `PASS | FAIL | BLOCKED | not run` — a PASS counts only with its assertion evidence
re-derived from the committed result files. **Class:** **P/F** = hard gate · **P/F|B** = pass/fail-or-blocked
(a named, evidenced block is acceptable; a silent skip never is).

---

## Scenario Results (Master Table)

55 cases (49 SC core/expansion + the flood-pair + 3 live daemon/fault cases + 2 Tier-1; IDs and pass conditions frozen in plan §6). **All rows
start `not run`; verdicts are entered by hand, one per case, from `results/<suite>/<case>/`.**

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-SC-01 | core-lifecycle | P/F | ▫ not run | first ask, terminal, zero config — plan §S1 |
| FT-SC-02 | core-lifecycle | P/F | ▫ not run | malformed rejected loudly, nothing partial persists |
| FT-SC-03 | study | P/F\|B | ▫ not run | the 15-second spine — bars in plan §9.1 |
| FT-SC-04 | study/quality | P/F\|B | ▫ not run | degraded cards → explicit `unknown` + deny |
| FT-SC-05 | core-lifecycle | P/F | ▫ not run | rescope hint → new identity, no state reuse |
| FT-SC-06 | core-lifecycle | P/F | ▫ not run | duplicate ingest coalesces |
| FT-SC-07 | cross-channel | P/F | ▫ not run | second-surface approve + terminal parity |
| FT-SC-08 | cross-channel | P/F | ▫ not run | race: one decision, second rejected `late` |
| FT-SC-09 | core-lifecycle | P/F | ▫ not run | timeout = deny + warning, jitter ≤1 s |
| FT-SC-10 | core-lifecycle | P/F | ▫ not run | expiry survives crash + clock step-back |
| FT-SC-10-LIVE | live | P/F | ▫ not run | real daemon kill -9 + restart, expired exactly once |
| FT-SC-11 | escalation | P/F | ▫ not run | 3 a.m. drill, tier claims revoked |
| FT-SC-12 | escalation | P/F | ▫ not run | ladder exhaustion denies, TTL never extended |
| FT-SC-13 | flood | P/F | ▫ not run | attack pack: burst allowed / overflow denied (counts recorded) |
| FT-SC-14 | flood | P/F | ▫ not run | legitimate burst — **passes together with SC-13** |
| FT-SC-PAIR | flood | P/F | ▫ not run | paired verdict: SC-13 and SC-14 both pass |
| FT-SC-15 | ci | P/F | ▫ not run | pipeline halts on `gate`, resumes on answer |
| FT-SC-16 | ci | P/F | ▫ not run | deterministic exit matrix, idempotent retry |
| FT-SC-16-LIVE | live | P/F | ▫ not run | real gate exit matrix 0/2/3/5 |
| FT-SC-17 | governance | P/F | ▫ not run | self-review denied (+ allowed/audited variant) |
| FT-SC-18 | cross-channel | P/F | ▫ not run | channel failover, no duplicate notify |
| FT-SC-19 | cross-channel | P/F | ▫ not run | late answer = visible no-op |
| FT-SC-20 | evidence | P/F | ▫ not run | reconstruction + chain, tamper names `seq` |
| FT-SC-21 | evidence | P/F | ▫ not run | 0 scanner findings, receipts complete |
| FT-SC-22 | attacks | P/F | ▫ not run | **release-gating** — 10 spoof/replay/forge attacks |
| FT-SC-23 | attacks | P/F | ▫ not run | **release-gating** — 10 poisoned cards, 0 approvals |
| FT-SC-24 | faults | P/F | ▫ not run | **release-gating** — fail-closed matrix, 0 silent allows |
| FT-SC-24-LIVE | live | P/F | ▫ not run | corrupt + locked store each fail closed (4) |
| FT-SC-25 | adapters | P/F | ▫ not run | LangGraph round-trip + crash-resume, one execution |
| FT-SC-26 | offline | P/F | ▫ not run | offline day, doctor green, no outbound attempts |
| FT-SC-68 | readiness | P/F | ▫ not run | pre-write bounce, nothing stored, repair contract |
| FT-SC-69 | readiness | P/F | ▫ not run | contradiction visible / reject-on-ingest |
| FT-SC-70 | readiness | P/F | ▫ not run | same weak ask, different class bands |
| FT-SC-71 | constrained | P/F | ▫ not run | one-click constrained allow + constraint set |
| FT-SC-72 | constrained | P/F | ▫ not run | repair packet round trip, no human re-teach |
| FT-SC-73 | constrained | P/F | ▫ not run | edit re-fingerprints, enforcer runs edited form |
| FT-SC-74 | constrained | P/F | ▫ not run | unbindable = advice only, cannot be picked |
| FT-SC-75 | operations | P/F | ▫ not run | 20-ask bundle: one screen, 20 answers, no approve-all |
| FT-SC-76 | operations | P/F | ▫ not run | shift handoff preserves TTL + notes |
| FT-SC-77 | operations | P/F | ▫ not run | incident mode, denies still deny |
| FT-SC-78 | operations | P/F | ▫ not run | narrative reproduces a 3 a.m. denial |
| FT-SC-79 | outcomes | P/F | ▫ not run | executed closure + offline-verifiable packet |
| FT-SC-80 | outcomes | P/F | ▫ not run | exceeded manifest loud, never absorbed |
| FT-SC-81 | outcomes | P/F | ▫ not run | rollback leaves the decision untouched |
| FT-SC-82 | outcomes | P/F | ▫ not run | packet-only reviewer reconstructs end-to-end |
| FT-SC-83 | grants | P/F | ▫ not run | 12-ask compressed view, 12 answers, export complete |
| FT-SC-84 | grants | P/F | ▫ not run | window expires mid-burst → per-ask, 0 silent allows |
| FT-SC-85 | grants | P/F | ▫ not run | owner revocation is immediate + loud |
| FT-SC-86 | grants | P/F | ▫ not run | repeated denials → insight, no auto-hardening |
| FT-SC-87 | insights | P/F | ▫ not run | 20 approvals → one redacted insight |
| FT-SC-88 | insights | P/F | ▫ not run | noisy policy → named tuning diff (PR to apply) |
| FT-SC-89 | insights | P/F | ▫ not run | calibration aggregate; per-principal gated + logged |
| FT-SC-90 | insights | P/F | ▫ not run | divergence → proposal only, nothing applies itself |

**Harness cases (P/F|B — plan §S14):**

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-T1-CLAUDE | harness | P/F|B | ▫ not run | Claude Code `PreToolUse` live — journal: version, transcript, gate outcome |
| FT-T1-CODEX | harness | P/F|B | ▫ not run | Codex CLI wrapper live — deny + expiry behavior recorded |

---

## Per-Suite Results

*(fills by group: suite → cases run, pass rate, where the evidence lives, and what was deep-verified vs
spot-checked. A suite is complete only when every case in it has a verdict.)*

---

## Root Cause Analysis

*(one entry per FAIL or regression, entered when found: symptom → root cause → fix commit → regression
test that now guards it. No entry may be closed without all four. At authoring: none — nothing has run.)*

---

## Defect Catalogue

| # | Case | Defect | Cause | Fix | Regression | Owner | Status |
|---|---|---|---|---|---|---|---|
| *(none yet — empty is the honest state)* | | | | | | | |

---

## Field Notes — Findings, Learnings, and Observations

*(hand-written as the sweep runs: what surprised us, what the fixtures could not reproduce, where the
harness — not the product — broke. Numbered, dated, never summarized away. At authoring: intentionally
empty.)*

---

## Coverage, Gaps, and Declared Limitations

Status vocabulary: **not run | PASS | FAIL | BLOCKED** — this run so far: **0 PASS · 0 FAIL · 0 BLOCKED ·
55 not run** (plan frozen; sweep pending).

- **Coverage so far:** none — the plan ([FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md)) is frozen and reviewed,
  but no field case has executed. The L0 deterministic suites (924 tests) are green at authoring; they are
  the backstop under every case, not a substitute for it.
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
| Attack packs | 0 crafted allows (SC-22/23/24) | ▫ pending | pack result files |
| Evidence hygiene | 0 scanner findings over any result | ▫ pending | per-case leak gate |
| Harness journal | both recipes: version + transcript + outcome | ▫ pending | `field-test/v0.1.0/journal/` |
| LLM capture (Tier-1) | every real call logged: balanced, 2xx, secret-free | ▫ pending | `artifacts/llm/` + deep-validation gate |

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