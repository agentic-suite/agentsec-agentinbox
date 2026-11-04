# PRD 08 — Risks & Mitigations

**BLUF:** The top risks are **rubber-stamping** (the human becomes the bypass), **spoofed approvals** (the gate
becomes the exploit), **adoption friction** (the gate gets disabled), **the agentpolicy-only producer trap**
(no ecosystem = no product), and **single-maintainer bus factor**. Each risk has an owner, a mitigation, and —
where possible — a CI-testable tripwire.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Risk register

| # | Risk | Likelihood | Impact | Mitigation | Tripwire |
|---|---|---|---|---|---|
| **R-R1** | **Rubber-stamping** — approvers tap Approve without reading; the inbox launders unsafe actions into "human-approved" ones | **High** (observed in every approval system) | Critical | The 15-second spine invests in *decision-relevant* context; typed confirmation for irreversible classes; deny-reason required; anti-metric deny-rate≈0 watched ([PRD 07 §F](07-success-metrics.md)) | deny-rate on irreversible < 5% sustained → alert the policy owner |
| **R-R2** | **Spoofed/forwarded/replayed approvals** | Medium | Critical | E3/E4 claim-token model; Slack signature verification; roster checks; single-use; first-wins; late answers are no-ops | SC-07/08/22 packs in CI; any `answer-rejected` surge → investigate |
| **R-R3** | **Prompt injection through the ask text** drives an approval | High (agents read attacker text) | High | Untrusted rendering (E5); trusted fields only from signed adapters; injection corpus with **0-approval** gate in CI | corpus regression in every release |
| **R-R4** | **Adoption friction** — install/config too heavy, first ask never happens; users disable gates to ship | Medium-High | High | CUJ-1 < 5 minutes; `init` writes working defaults; `doctor` diagnoses; zero-cloud mode; Slack optional | field-test: median install→first-approval time; drop-off survey |
| **R-R5** | **No producers besides agentpolicy** → the "harness-agnostic" claim is hollow | Medium | High (blocks the ecosystem) | Stable contract + CLI/HTTP + example adapters (LangGraph interrupt, OpenAI Agents SDK interruption, `human_input`, generic hook); conformance fixtures | [PRD 19](19-harness-compatibility.md) matrix ≥ 6 producers by v0.3.0 |
| **R-R6** | **Noise → muting** — asks too frequent (mis-scoped policy), approvers turn notifications off | Medium-High | High (the product's death) | Flood digest; severity routing; standing-approval roadmap (R10); policy-tuning feedback loop (deny reasons flow back) | no-action rate on delivered cards climbing → tuning alert |
| **R-R7** | **Escalation theater** — ladder configured wrong, on-call never really reachable at 3 a.m. | Medium | High | Drill scenario (SC-11/12) in field test; ladder preview in `doctor`; config validation (tiers non-empty, delays sane) | 3 a.m. drill pass/fail documented honestly in the field report |
| **R-R8** | **Store corruption / migration breaks evidence** | Low-Medium | High | Hash chain + `verify-log`; forward-compatible migrations; corrupt store refuses (not guesses); atomic writes | chain verification in CI against fixtures + a corruption fixture |
| **R-R9** | **Slack API/policy changes** break the channel (API deprecations, Block Kit changes, enterprise app approvals) | Medium | Medium | Channel isolation: Slack is one adapter behind a stable interface; signature-verification code centralized; adapter tests + a `doctor` reachability check; terminal/CI unaffected by Slack breakage | adapter conformance suite in CI; `doctor` red on reachability loss |
| **R-R10** | **agentpolicy contract drift** — ask/decision contract changes under us | Low (both in-suite) | Medium | Shared conformance fixtures in both repos; versioned contract `ask/1.0`; contract tests in CI on both sides | cross-repo contract CI |
| **R-R11** | **Performance on pathological sessions** (10k asks, 500 pending) degrades the interactive path | Low-Medium | Medium | SQLite WAL + indexes; pending set is naturally small (TTLs); delivery async; bench fixtures in CI | latency bench regression |
| **R-R12** | **Scope creep toward a workflow product** (ITSM clones, RBAC, UI) eats the small-team core | High (gravity is real) | Medium | [PRD 14](14-non-goals.md) is the contract; enterprise features land in the server-mode track, never by complicating local-first | every PRD change must name its requirement ID |
| **R-R13** | **Single-maintainer bus factor** | High today | Medium | Docs-first (this PRD set), conformance fixtures over hand-tests, ADRs for every frozen decision, the org floor (CODEOWNERS, DCO) | ADR count; test coverage without manual steps |
| **R-R14** | **Legal/compliance overreach** — buyers assume SOC 2 / Art. 14 conformance from marketing | Medium | Medium-High | Claims vocabulary + claims linter ([PRD 20 §G](20-standards-and-claims.md)); docs state v0.1.0 gaps explicitly (CUJ-14) | claims lint in CI |
| **R-R15** | **Approver identity is weak at v0.1.0** (Slack user ≠ verified employee; terminal = OS user) | Medium | High for regulated buyers | Honest statement of assurance level per channel; step-up design fixed now, shipped v0.1.x; enterprise SSO in the server track | documented assurance table, no over-claim |

## Dismissed risks (with reasons)

- *"The approver's machine is compromised"* — out of scope: with a local-first tool on the approver's laptop, a
  compromised laptop owns everything anyway; the server/SSO mode is the answer for that threat, and it is
  roadmap, not v0.1.0.
- *"We must encrypt the local store at rest"* — the store contains only redacted metadata; file permissions +
  0600 default; full-disk encryption is the platform's job. Revisit if producers ever send unredacted content
  (they must not — E6 forbids it).

## Risk review cadence

Re-graded at each release: the field-test report carries a risk section with any likelihood/impact changes and
the tripwires' observed values.
