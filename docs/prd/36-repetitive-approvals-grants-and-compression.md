# PRD 36 — Repetitive Approvals, Grants & Compression

**BLUF:** some approval pain is not risk — it is **repetition**. This PRD makes repetitive work tolerable
without weakening accountability: **repeated-ask compression** (one view, per-ask truth intact), **narrow
timeboxed approval windows** and **session grants** with hard ceilings, and **burn-down visibility** — what
the grant covers, how much is left, when it ends. Delegation becomes explicit, governed, and observable instead
of hidden rubber-stamping.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

Ten identical safe approvals in an afternoon train a human to click `a`. That reflex is the vulnerability this
PRD removes: if the product offers a **tiny, visible, expiring grant** instead, the safer path is also the
easier one. This extends [PRD 27](27-governance-identity-extensibility.md)'s standing rules (R37) with the
ergonomics that make governed delegation *preferable* to habit, and shares PRD 28's one-grant-shape rule.

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-22** | "Approve one thing, not the next ten that look similar" — compression + a narrow window instead of ten clicks | P0 |
| **CUJ-41** | "Stop making me approve the same safe thing all afternoon" — grouped view, per-ask truth beneath | P0 |
| **CUJ-42** | "Grant a tiny window, not a blanket exception" — class-scoped, ceiling-bounded, expiring | P0 |
| **CUJ-43** | "Show me the burn-down" — uses consumed, time remaining, scope covered | P0 |
| **CUJ-44** | "No invisible policy drift" — compression/grants stay explicit, timeboxed, evidence-bearing | P0 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R108** | **Repeated-ask compression.** Materially identical asks (same class+tool+canonical arguments modulo whitelisted variance) arriving within a window render as **one compressed view** with per-ask rows beneath. Compression is a *view*, never a truth: each ask keeps its own record, claim, and audit rows. | v0.1.0 | 12 identical asks render as 1 group + 12 rows; answering the group answers **each** ask individually via N verifications (no group decision) |
| **R109** | **Timeboxed approval windows.** An approver may grant a window: class-scoped, ceiling-bounded (`max_uses`, `max_per_minute`), time-expiring, principal-bound for issue but not for use. Answers under a window carry `authorization.source=window-grant` and count against its burn-down. | v0.1.0 | An ask under a live window resolves allow without a per-ask human action; window expiry mid-burst reverts to per-ask approval with zero silent allows |
| **R110** | **Session grants.** Same shape, session-scoped: a producer session may hold at most one active grant; grants never outlive the session; `standing_rules` config (PRD 27 R37) governs scope/owner/expiry/recert. | v0.1.0 | A second grant for the same session is refused; the session ending expires the grant loudly |
| **R111** | **Grant burn-down UI.** Every surface that renders a window-covered ask shows the grant: what it covers, uses used/ceiling, time remaining, issuing principal. `doctor --explain` prints active grants. | v0.1.0 | Burn-down fields render on card + doctor; a spent grant renders spent, not absent |
| **R112** | **Compression ≠ truth loss.** Compressed views always disclose N and link each row; exports contain every ask; the audit chain is unchanged by compression. | v0.1.0 | An export of a compressed group contains N asks; verification passes identically |
| **R113** | **Repeated-deny escalation.** A pattern of repeated *denies* (or non-decisionable rejections, PRD 32) for the same intent is **not compressed away** — it surfaces as a tuning/insight item (PRD 37) and may harden the class (mandatory review) per config. | v0.1.0 | 5 identical denials trigger the insight; nothing auto-approves or auto-hardens without config |
| **R114** | **Grant governance.** Windows/grants require owner + reason on issuance, are audited (`grant-issued/used/expired` events), appear in the PRD 37 insights, and can be revoked by their owner or a configured governance principal — revocation is immediate and loud. | v0.1.0 | Revoked window → covered asks revert to per-ask approval instantly; every use is a chained event |

## Non-goals

- No unbounded or unobservable delegation; every grant has ceilings and expiry.
- No silent grant adoption: issuance is a deliberate human act with recorded reason.
- Compression never creates group-level decisions (per-ask truth holds, N-20).

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-83** | A 12-ask burst reviews compressed, answers individually, exports complete |
| **SC-84** | A window grant mid-burst: first 5 allow without interruption, expiry reverts to per-ask, zero silent allows |
| **SC-85** | Owner revokes a live grant; covered asks immediately demand fresh approval |
| **SC-86** | Repeated denials surface as insight, never as compression noise |

## Traceability

| Requirement | Test |
|---|---|
| R108, R112 | `tests/grants/test_compression.py` |
| R109–R111 | `tests/grants/test_windows.py`, `test_burndown.py` |
| R110 | `tests/grants/test_session_grants.py` |
| R113–R114 | `tests/grants/test_repeated_denies.py`, `test_governance.py` |
