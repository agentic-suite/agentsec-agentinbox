# PRD 21 — Evidence Register & Method

**BLUF:** Every headline claim has a named method, an artifact, and a checksum: contract conformance (CI
fixtures), lifecycle correctness (SC-01–SC-26 with a published verdict per scenario), attack resistance
(release-gating packs), the 15-second spine (a recorded user study with a frozen corpus), and the harness
matrix (regenerated from field-test runs). Evidence is **reproducible by a third party from this repo** —
fixtures, scripts, and protocols all ship.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Evidence register (claim → method → artifact)

| ID | Claim | Method | Artifact (published per release) |
|---|---|---|---|
| **EV-1** | The ask contract is stable and any producer can integrate | Conformance fixtures round-trip (ask/1.0, resolve/1.0, exit codes, event schema) | `tests/fixtures/conformance/` + CI run log + contract report |
| **EV-2** | Lifecycle correctness: raise→deliver→warn→escalate→answer/expire with exactly-once transitions | SC-01, SC-02, SC-06, SC-09, SC-10, SC-19 fixtures | Field-test report, per-scenario verdict + event trace |
| **EV-3** | Approvals are identity-bound and single-use | SC-22 spoof/replay/forge matrix (10 attacks) | Attack-pack output + `answer-rejected` event log |
| **EV-4** | Injected content never drives an approval | SC-23 corpus (10 poisoned cards, 0-approval gate) | Corpus checksum + render captures + CI gate |
| **EV-5** | Timeout = deny, always | Expiry fixtures + restart + clock-skew + the runtime zero-allow counter | Fixture logs + counter export |
| **EV-6** | Floods produce one event and one digest, and legitimate bursts survive | SC-13 + SC-14 executed together + agentdrill flood pack | Pack report |
| **EV-7** | CI gates are deterministic | Exit-code matrix (SC-16) across retry/offline | Runner transcripts |
| **EV-8** | Audit reconstructs and verifies | SC-20 export + `verify-log` + tamper fixture | Exported JSONL + verification output |
| **EV-9** | No secrets in any artifact | SC-21 evidence scanner over store/payload/audit dumps | Scanner findings (target: 0) + receipts |
| **EV-10** | A zero-context approver decides correctly in < 15 s | **User study protocol B** below | Raw timings + corpus checksum + decisions sheet |
| **EV-11** | Compatible with Claude Code / Codex CLI | Live field-test runs (CUJ-1/3/7 through their hooks) | Field-test run journal (dates, versions, transcripts) |
| **EV-12** | Framework adapter pattern works end-to-end | SC-25 LangGraph round-trip + crash-resume | Fixture + example repo output |
| **EV-13** | Offline mode is complete | SC-26 with network disabled | Doctor output + scenario transcripts |
| **EV-14** | Fail-closed under faults | SC-24 fault matrix | Matrix verdict table |

## Method B — the zero-context user study (EV-10; this is the R1 acceptance)

- **Corpus:** 12 cards + 12 degraded cards, pre-registered correct answers by the policy owner, frozen with a
  checksum before any participant is run. Card mix: approve-correct ×3, deny-correct ×4, "insufficient info →
  deny" ×3 (degraded), escalation-timing ×2.
- **Participants:** ≥ 10 approvers who did not author the corpus; no prior session context provided (that is
  the point of "zero-context").
- **Protocol:** each participant gets the corpus in randomized order via the narrowest realistic surface (a
  phone through the webhook/Matrix recipe when configured; otherwise the desktop-alert → terminal flow — the
  worst realistic screen); time-to-decision instrumented by the card's own delivered→answered timestamps;
  decisions compared to pre-registered answers; no coaching before, debrief after.
- **Pass bar (pre-registered):** ≥ 9/10 participants ≥ 10/12 correct; median time < 15 s; p90 < 25 s; 100% of
  degraded cards answered deny-or-insufficient (never a confident wrong allow).
- **Publication:** raw per-card timings + decisions + corpus checksum; misses reported, not averaged away.

## Method C — field test (the scenario catalog run)

[PRD 17](17-scenarios.md) executed on the field-test box with the report published under
`docs/field-test/v0.1.0/` — verdicts per scenario, run journal (versions, clock, environment), and a
**misses section** (the org's rule: honest reports only; automation never overwrites the hand-maintained
report). Attack packs (SC-22/23) and the flood pack are **release gates**: red pack = no release.

## Method D — compatibility evidence

Each matrix row in [PRD 19](19-harness-compatibility.md) carries its label's source: *field-tested* → a run
journal entry (harness version, date, transcript); *conformance-tested* → the CI fixture name; *documented* →
the doc path; *not supported* → the blocking reason. The table is generated from these sources at release
time — an unlabeled row is a build error.

## Reproducibility kit (shipped in-repo)

1. `tests/fixtures/conformance/` — the contract truth (ask/resolve payloads, expected events).
2. `tests/packs/` — the attack corpora: spoof/replay/forge matrix, injection cards, flood pack, fault matrix.
3. `scripts/` — evidence scanner (secrets over dumps), `verify-log` export checker, report generator
   (writes to `docs/release/v0.1.0/`, never to hand-maintained field-test reports).
4. `docs/field-test/v0.1.0/FIELD_TEST_PLAN.md` — the protocol for Method C, authored before the run.

## What evidence we deliberately do NOT have at v0.1.0 (stated up front)

- No third-party audit (SOC 2/ISO) — ladder starts at v0.2.x server mode ([PRD 20 §E](20-standards-and-claims.md)).
- No population statistics on approval fatigue — only our study's small-n; published as small-n.
- No enterprise-scale deployment evidence — the field test is a single-box, small-team run; claims stay scoped
  to it.
- No formal verification of the claim-token construction — the construction is simple (random + hash +
  constant-time compare) and **attack-tested**, not proven; we claim the tests, not a proof.
