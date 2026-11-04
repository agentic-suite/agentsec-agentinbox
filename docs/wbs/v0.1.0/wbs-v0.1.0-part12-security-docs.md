# WBS v0.1.0 — Part 12: Security Sweep & Docs (M22–M23)

**BLUF:** **M22 is the security close-out**: the evidence scanner (0 secrets over store dumps, channel payload
captures, and audit exports — SC-21's gate), the spoof/replay/forge and injection corpora wired as
**release-blocking packs**, input/log hardening, constant-time/uniform-timing verification, permission
defaults, and the own-posture checks (PRD 06's invariants each with a test that would catch its violation).
**M23 makes the product usable by strangers**: the reference docs (CLI, config, contracts, events), the
5-minute quickstart, the eight runbooks (RB-1..RB-8), the adapter recipes, and the guides — docs complete
enough that M24's field test and M25's release claims point at real pages.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M22 — Security hardening sweep + evidence scanner (PRD 06/18)

**Goal:** the [PRD 06](../../prd/06-security-baseline.md) invariants (I-1..I-5) each enforced by a test that
fails on violation; the [PRD 18](../../prd/18-approval-integrity.md) pipeline re-audited end-to-end; and the
**evidence scanner** — the tool that greps every artifact class (store dumps, rendered channel payloads,
audit exports, backup archives) for secret patterns and must find **zero** — wired into CI as a release gate.

**CUJ:** — (security) · **Requirements:** [PRD 06](../../prd/06-security-baseline.md) (all),
[PRD 18](../../prd/18-approval-integrity.md) (all), E6, [PRD 21](../../prd/21-evidence-register-and-method.md) (EV-9),
[PRD 13](../../prd/13-non-functional-requirements.md) (N-22..N-26).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 22.D0 | **Design docs first** | Security-closeout design: the invariant→test map, scanner scope (artifact classes + pattern set), pack wiring (release-blocking), timing/perm hardening list | docs | reviewed before code | #74 | — | — |
| 22.1 | **Evidence scanner** | Pattern + shape scanner over store dumps, channel payload captures (desktop/webhook renders), audit exports, backup archives; seeded-corpus mode for tests; findings = build failure | scanner | SC-21: seeded secrets across args/reasons/evidence → **0 findings** anywhere, receipts everywhere; a seeded leak **fails** the gate | #75 | — | E6, EV-9 |
| 22.2 | Attack packs as release gates | The SC-22 spoof/replay/forge matrix + the SC-23 injection corpus + the M12 flood pack wired as CI jobs: **red pack = no release**; packs runnable standalone (`agentinbox` test entry) for the M24 drills | CI gates | all packs green in CI; a deliberately broken gate fixture fails the build | #76 | — | E3, E4, E5, R7 |
| 22.3 | Invariant tests (I-1..I-5) | One test per [PRD 06](../../prd/06-security-baseline.md) invariant: no answer without claim+principal; identity binding; timeout-never-allows (runtime counter); untrusted text inert; no secret persisted — each written to **fail on violation** | invariant suite | all five green; mutation-style negative fixtures prove each test can fail | #77 | — | PRD 06 |
| 22.4 | Timing + comparison hardening | Constant-time compares everywhere; uniform error responses/timing envelopes on public answer paths (distinct causes recorded internally, shown only to authenticated approvers); per-endpoint rate limits re-verified | hardening | timing fixtures (no distinguishable envelopes); guessing lockout re-tested (M6 interplay) | #78 | — | E3, E4 |
| 22.5 | Input/log/permission sweep | Log-injection sanitization (newline control); per-field caps re-audited; store/keys 0600, dirs 0700 enforced on every path that creates them; `--force`/`--yes` absence asserted in the CLI surface test | sweep | negative fixtures: crafted log lines inert; loose-perm paths corrected on creation | #79 | — | N-22..N-25 |
| 22.6 | Own-posture checks | No-ML dependency manifest check (nothing model-shaped in the decision path), SBOM generation dry-run, `security.txt` live, disclosure SLAs documented | posture | manifest check green; SBOM builds; security.txt reachable | #80 | — | N-1, PRD 20 §D |
| 22.T | Tests | Scanner, packs, invariants, timing, sweep, posture | tests | coverage ≥ 95% | #81 | — | — |
| 22.C | Coverage gate | ≥95% | report | ≥95% | #82 | — | — |
| 22.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #83 | — | — |
| 22.CR | Code review | Findings resolved | log | no open findings | #84 | — | — |
| 22.D | Docs | Security reference (invariants, packs, scanner, disclosure) | docs | updated + linked | #85 | — | — |
| 22.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 22.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Evidence scanner green over every artifact class; attack packs block releases in CI
- [ ] All five security invariants enforced by tests proven able to fail

---

## Milestone M23 — Docs completion (reference, quickstart, runbooks, recipes)

**Goal:** a stranger succeeds from the docs alone: the **5-minute quickstart** (CUJ-1's promise, step-tested),
full CLI + config references, the `ask/1.0`/`resolve/1.0`/event-set contract references, the eight
**runbooks** (RB-1 channel outage → RB-8 upgrade day, [PRD 22 §H](../../prd/22-operations-and-governance.md)),
adapter recipes (Claude Code hook, Codex wrapper, CI systems, MCP tool-gating, Temporal), and the approver
guide — plus the `docs/reference/screenshots/` fills and the README's install/usage go live.

**CUJ:** CUJ-1 (docs leg), CUJ-14 (honest-gap docs) · **Requirements:** [PRD 22 §H](../../prd/22-operations-and-governance.md),
[PRD 21 §C](../../prd/21-evidence-register-and-method.md) (method docs), [PRD 23 §A](../../prd/23-enterprise-adoption-and-governance-hardening.md)
(honest starting point), N-31..N-33.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 23.D0 | **Design docs first** | Docs-plan: page inventory mapped to CUJs/PRDs, the step-test protocol (a fresh-box run of the quickstart), screenshot list | docs plan | reviewed before writing | #86 | — | — |
| 23.1 | **5-minute quickstart** | Step-tested install → init → first recorded approval (terminal-only), written as copy-paste; measured again post-docs (the M18 fixture, re-run) | guide | a fresh-box step-test completes < 5 min exactly as written | #87 | CUJ-1 | N-31 |
| 23.2 | Reference docs | CLI (all commands + exit codes), config (every key + effective-config explanation), contracts (`ask/1.0`, `resolve/1.0`, event set + versioning), card reference, channel adapters | references | every M0–M22 feature documented; no undocumented flag exists (doc-coverage test) | #88 | — | — |
| 23.3 | **Runbooks RB-1..RB-8** | Channel outage · secret rotation · store corruption · live flood · config drift · clock incident · escalation misfire · upgrade day — each with symptoms/steps/verification, matching the M20/M21 behaviors | runbooks | each runbook's steps reproduce against an injected fault (spot-check in fixtures) | #89 | — | PRD 22 §H |
| 23.4 | Adapter recipes | `docs/adapters/`: Claude Code `PreToolUse` hook, Codex CLI wrapper, GitHub Actions/GitLab/Jenkins/Argo gates, MCP ask-gating tool recipe, Temporal signal recipe — each ending in "verify with `agentinbox conformance`" | recipes | recipes kit-green; ready for the M25 compatibility matrix | #90 | — | PRD 19 |
| 23.5 | Approver + producer guides | The approver guide (cards, keys, confirmations, inbox views) and the producer guide (M18's, polished) + the **honest enterprise page** (what v0.1.0 is not — [PRD 23 §A](../../prd/23-enterprise-adoption-and-governance-hardening.md)) | guides | CUJ-14's reviewer finds the gap matrix, not marketing | #91 | CUJ-14 | — |
| 23.6 | Screenshots + README live | Terminal card, inbox list, doctor output, export sample; README Install/Usage switch from "coming soon" to real | assets | screenshots current; README commands copy-paste-true | #92 | — | — |
| 23.T | Tests | Doc-coverage test (flags/commands/config keys documented); step-test script committed | tests | doc-coverage green; step-test reproducible | #93 | — | — |
| 23.C | Coverage gate | ≥95% (code; docs checked by the doc-coverage test) | report | ≥95% | #94 | — | — |
| 23.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #95 | — | — |
| 23.CR | Code review | Findings resolved | log | no open findings | #96 | — | — |
| 23.D | Docs | This milestone *is* docs; traceability rows updated for doc-linked requirements | docs | complete; linked from the index | #97 | — | — |
| 23.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 23.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Quickstart step-tests < 5 min on a fresh box; every flag/command/config key documented
- [ ] All eight runbooks + recipes + honest-gap pages complete for M24/M25 to reference

---

Part 12 green ⇒ the product is hardened and legible; proceed to
[Part 13 (M24–M25)](wbs-v0.1.0-part13-fieldtest-release.md).
