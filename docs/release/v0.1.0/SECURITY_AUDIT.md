# agentinbox v0.1.0 — Security Audit & Risk Re-grade

> **M33 33.6 (#117).** This note restates the PRD 06 security invariants against
> the M22 fixtures and the M32 field evidence, dispositions every M32 finding,
> and re-grades the PRD 08 risk register with the observed tripwire values.
>
> **Scope:** the local-first v0.1.0 product on a single box. It is **not** a
> third-party audit, a formal proof, or a population study. Non-claims are
> stated below, not hidden.

## 1. Security invariants (PRD 06)

| Invariant | Enforcement fixture | M32 field evidence | Verdict |
|---|---|---|---|
| **I-1** — no answer without a valid claim + authenticated principal | `tests/security/test_invariants.py`, `tests/answers/test_pipeline.py` | SC-17 self-review, SC-22 spoof/replay/forge; all rejected and logged | GREEN |
| **I-2** — an approval binds to exactly one action identity | `tests/answers/test_pipeline.py`, `tests/security/test_invariants.py` | SC-22 matrix; identity-mismatch rows rejected; SC-24-LIVE locked-store path failed closed | GREEN |
| **I-3** — timeout = deny, always | `tests/scheduler/test_expiry.py`, `tests/scheduler/test_recovery.py`, `tests/scheduler/test_clock.py` | SC-09/10 expiry and clock cases; no zero-allow path observed | GREEN |
| **I-4** — all agent-derived text is inert data | `tests/card/test_card.py`, poisoned corpus fixtures | SC-23 injection corpus: 0 approvals; unverified trusted fields labelled | GREEN |
| **I-5** — no secret persisted or rendered | `tests/security/test_scanner.py`, `tests/security/test_packs.py` | SC-21 evidence scan; release evidence scan 0 findings; leak gate caught one token pre-commit and it was removed | GREEN |

The invariants are code-enforced, not aspiration. A red invariant is a release
blocker.

## 2. M32 findings — every one dispositioned

| Finding | Disposition | Evidence |
|---|---|---|
| **Defect #5** — a permission-locked store silently self-healed (exited 0) | **FIXED** in `SqliteStore.__init__`; chmod on create only, owner-unreadable raises `StoreError`; regression test; field re-run **PASS** | `agentinbox/store/sqlite.py`, `tests/store/test_locked_store.py`, `FT-SC-24-LIVE` |
| `FT-SC-20`, `FT-SC-21`, `FT-SC-24`, `FT-SC-26` container reds | **ACCEPTED** as KNOWN test-setup/env, not product failures: the product assertions pass; the tests' own `sqlite3.connect` leaks are promoted by pytest 9.2/Py3.13; the same suite is 931 tests green locally | field report §Known issues; Justification section; `make gate` |
| `FT-SC-03`, `FT-SC-04` study cases | **BY DESIGN ❌** — no human cohort will run; the 15-second/study claim is **not made** | field report; release plan §3/§11 |
| s15-harness removed | **REMOVED WITH RATIONALE** — pty answerer long-running/brittle, duplicated LIVE coverage; 11/11 LLM pairs retained; Claude Code/Codex are **not field-tested** | plan §6 "Suite removals"; `docs/release/v0.1.0/evidence/harness/` |
| Codex plugin-clone token | **REMOVED BEFORE COMMIT**; final scanner clean; vendor caches excluded from capture | field report finding 8; release evidence scan |
| Local test conflicts (audit/outcomes/migrations) | **FIXED** — `contextlib.closing` + explicit commit, store-close stubs, chmod policy reconciled | `tests/cli/test_audit_cli.py`, `tests/outcomes/test_outcomes.py`, `tests/store/test_migrations.py` |
| M32 report 47 PASS / 6 FAIL | **PUBLISHED HONESTLY** — not reclassified; M33 consumes it | `docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` |

**No open blocking product finding remains.** The four container reds are a
test-environment debt (pin/cleanup), recorded as follow-up, not a product risk.

## 3. Non-claims

We deliberately do **not** claim:

- a third-party security audit, SOC 2, ISO 27001, or ISO 42001 certification;
- a formal proof of the claim-token construction (it is attack-tested, not
  proven);
- population statistics on approval fatigue; the human study was **not run**,
  so no 15-second/accuracy claim is made;
- external notarization or WORM audit — the hash chain is tamper-evident and
  locally verifiable, not court-proof against a determined local admin;
- enterprise-scale, multi-tenant, SSO, quorum, or server-mode readiness;
- harness field compatibility: Claude Code/Codex CLI are **not field-tested**
  (only LLM captures; the end-to-end suite was removed);
- detection of prompt injection — injected text is made inert in our surface;
- platform-level unforgeability; our claims are single-use, identity-bound
  tokens and verified callbacks.

## 4. Risk re-grade (PRD 08)

Grades are **likelihood / impact**. “Pre” is the PRD 08 grade; “Post” is after
the M32 field test and the M33 release work.

| Risk | Pre | M32 observation / tripwire | Post |
|---|---|---|---|
| **R-R1** Rubber-stamping | High / Critical | **Study not run**; deny-rate not measured; no anti-metric evidence | **High / Critical** (unchanged) |
| **R-R2** Spoofed/replayed approvals | Medium / Critical | SC-22 pack green; no `answer-rejected` surge; single-use claims verified | **Medium / Critical** |
| **R-R3** Prompt injection drives approval | High / High | SC-23 corpus green, 0 approvals; unverified fields labelled | **Medium / High** |
| **R-R4** Adoption friction | Medium-High / High | Quickstart step-tested; fresh-box install on the release candidate is pending 33.T | **Medium-High / High** |
| **R-R5** No producers beyond agentpolicy | Medium / High | agentpolicy demo field-tested; LangGraph conformance; harness recipes only documented | **Medium / High** (honest matrix) |
| **R-R6** Noise → muting | Medium-High / High | Flood pack green (burst allowed, remainder denied, one event/digest); no user study | **Medium-High / High** |
| **R-R7** Escalation theater | Medium / High | SC-11/12 pass; 3 a.m. drill evidence in the field report | **Low-Medium / High** |
| **R-R8** Store corruption/migration | Low-Medium / High | Fault matrix product-green; Defect #5 fixed; 4 container reds are test-fixture debt | **Low-Medium / High** |
| **R-R9** Chat platform changes | Medium / Medium | No chat adapter at v0.1.0; terminal/CI unaffected | **Medium / Medium** |
| **R-R10** agentpolicy contract drift | Low / Medium | Cross-repo contract tests + Wave-0 demo round-trip pass | **Low / Medium** |
| **R-R11** Pathological-session performance | Low-Medium / Medium | Benches cited; no regression observed in the release gate | **Low-Medium / Medium** |
| **R-R12** Scope creep to workflow product | High / Medium | PRD 14 non-goals unchanged; M33 is release-only | **High / Medium** |
| **R-R13** Single-maintainer bus factor | High / Medium | Docs-first, conformance fixtures, ADRs, DCO; unchanged by M32 | **High / Medium** |
| **R-R14** Compliance overreach | Medium / Medium-High | Claims lint + generated matrix now enforce the vocabulary; gaps stated | **Medium / Medium** (improved control) |
| **R-R15** Weak approver identity | Medium / High | Terminal = OS user; assurance table documented; no SSO at v0.1.0 | **Medium / High** (unchanged) |

**No risk grade was raised by M32.** R-R1 remains the top risk because the study
was not run; M33 does not claim otherwise.

## 5. Git-history secret scan

Run 2026-11-07 on the release branch, full history (`file://` scan of every commit):

| Scanner | Version | Result |
|---|---|---|
| TruffleHog | 3.99.8 | **0 verified secrets**; 3 unverified hits, all deliberate test/docs placeholders |
| gitleaks | (brew current) | **8 hits, all the same false positive** (`prompt_cache_key` UUIDs in Codex request JSON) |

Unverified/false-positive dispositions (none is a live credential):

- `tests/ask/test_redaction.py` — fake Postgres URL used by the redaction tests.
- `tests/bus/test_delivery.py` — fake URI credential used by the delivery-redaction test.
- `docs/reference/ask-contract.md` — redaction-pattern example strings.
- `prompt_cache_key` UUIDs in `docs/release/v0.1.0/evidence/harness/FT-T1-CODEX/` — Codex request
  metadata, not a secret.

## 6. Release decision

The security audit supports the release **with the stated non-claims and the
four accepted container-test reds**. The one product defect found in the field
is fixed, regression-locked, and field-verified. If a reviewer does not accept
the non-claims or the accepted env reds, the release is blocked until the issue
is resolved or explicitly waived here.

Linked from the release index: [README.md](README.md). The field evidence is
[FIELD_TEST_REPORT.md](../../field-test/v0.1.0/FIELD_TEST_REPORT.md).
