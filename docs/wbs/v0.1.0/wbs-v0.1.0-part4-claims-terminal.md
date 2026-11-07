# WBS v0.1.0 — Part 4: Claims & Terminal Channel (M6–M7)

**BLUF:** **M6 is the anti-spoofing core**: single-use claim tokens (hashed, bound to ask + action identity +
channel + tier, expiring with the ask) and the six-step answer-verification pipeline — channel authenticity,
claim validity, binding, ask state, principal authorization (roster + self-review), first-wins commit. Nothing
answers without **both** a valid claim and an authenticated principal (E3, E4, D-3). **M7 is the primary human
surface**: the terminal/TUI channel — blocking card, one-keystroke-pair answers, typed confirm for
irreversible, OS-session principal, and the non-interactive mode where **a script can never approve**.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M6 — Claims + answer-verification pipeline (E3, E4)

**Goal:** make "approved" mean exactly one thing: this principal, this claim, this ask, this instant, first
winner. Replays, forwards, late taps, off-roster users, forged principals, and guesses are all logged
`answer-rejected` with distinct causes (SC-22's matrix, CUJ-8's deny-with-reason).

**CUJ:** CUJ-8 · **Requirements:** E3, E4, [PRD 18](../../prd/18-approval-integrity.md) (pipeline, claim design,
guessing resistance), [PRD 06](../../prd/06-security-baseline.md) (T1/T4/T10/T13/T14), D-3, D-5.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 6.D0 | **Design docs first** | Claim design (format, hashing, binding, revocation) + the pipeline order + per-channel principal extraction rules | docs | reviewed before code | #169 | — | — |
| 6.1 | Claim lifecycle | Mint (`cl_<hex>` + 128-bit secret, stored hashed), bind (ask_id + action_identity + channel + tier + expires_at), single-use CAS consume, revoke (escalation tier change), expire with the ask | claims module | all claim properties fixture-tested (E3) | #170 | — | E3 |
| 6.2 | **Answer pipeline (6 steps)** | Channel authenticity → claim validity → binding → ask state → principal authorization (roster + `self_review=deny` on irreversible) → first-wins commit; every failure = `answer-rejected` with a distinct cause, state untouched | verifier | SC-22 matrix: 10 attacks (replay, forge, stale, off-roster, wrong binding, used/revoked claim, self-review, raw-API) all rejected + logged | #171 | — | E4 |
| 6.3 | First-answer-wins + races | CAS on status; concurrent answers → exactly one winner; loser recorded `late` with winner identity + time; resolve called twice → same single decision (idempotent) | CAS wiring | SC-08 race fixture: one `ask-answered`, one logged no-op, no double-execution path | #172 | — | E4, E11 |
| 6.4 | Deny-with-reason + typed confirm | Deny reason **required** on irreversible classes (escaped, capped); approve on irreversible requires typed confirmation of the action's short name | answer UX rules | reason flows to producer (M17); typed-confirm fixture blocks muscle-memory approve | #173 | CUJ-8 | R1 |
| 6.5 | Guessing resistance | Per-claim attempt counters + lockout, per-endpoint rate limits, uniform error responses/timing (constant-time compares); a burst of bad claims is itself an `answer-rejected(guessing)` event | rate limit | online-guessing fixtures: bounded, noisy, recorded | #174 | — | E3, E9 |
| 6.6 | Local-adversary hardening | Loopback socket token; answers via raw API require claim + configured channel principal (no client-supplied `approver` string is ever trusted); producer uid recorded | API guards | T13/T14 fixtures: raw-API forge rows rejected | #175 | — | E4, T13/T14 |
| 6.T | Tests | Claims, pipeline matrix, races, confirm/reason, guessing, local-adversary | tests | coverage ≥ 95% | #176 | — | — |
| 6.C | Coverage gate | ≥95% | report | ≥95% | #177 | — | — |
| 6.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #178 | — | — |
| 6.CR | Code review | Findings resolved | log | no open findings | #179 | — | — |
| 6.D | Docs | Approval-integrity reference (pipeline, claim design, causes) | docs | updated + linked | #180 | — | — |
| 6.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 6.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] SC-22's full spoof/replay/forge matrix green with distinct causes; races resolve once
- [ ] No answer path exists without claim + authenticated principal; guessing is bounded and noisy

---

## Milestone M7 — Terminal/TUI channel (R2)

**Goal:** the channel the product lives in daily: a blocking card in the caller's terminal, `a`/`d` answers
(`?` detail, `q` leaves pending), typed confirm + reason per M6 rules, OS-user principal with TTY ownership,
`--as` only when loudly configured — and non-interactive mode returning structured JSON + exit `5`
(**a script can never approve**, CUJ-1's surface).

**CUJ:** CUJ-1 (surface), CUJ-9 (surface) · **Requirements:** R2, [PRD 16 §B.1](../../prd/16-channel-and-harness-adapters.md),
[PRD 18 §assurance](../../prd/18-approval-integrity.md), [PRD 13](../../prd/13-non-functional-requirements.md) (N-2, N-35, N-42).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 7.D0 | **Design docs first** | Terminal channel design: TTY detection/ownership, blocking loop + poll interval, key handling, non-interactive contract, `--as` semantics | docs | reviewed before code | #181 | — | — |
| 7.1 | Blocking card loop | Render the M5 card; refresh on warn; answer keys `a`/`d` (+typed confirm / reason via M6 rules); `q` = leave pending (documented) | terminal channel | card renders <100 ms (N-2); answers flow through the M6 pipeline only | #182 | CUJ-1 | R2 |
| 7.2 | Principal = OS session | uid + TTY ownership as the principal; `--as <name>` only with `[channels.terminal]` config and recorded as an assumed principal (audited loudly) | principal extraction | `--as` unconfigured → refused; assumed principal visible in the transition | #183 | — | E4 |
| 7.3 | Non-interactive mode | No TTY → no prompt ever: structured JSON to stdout + exit `5`; exit-code mapping (0/2/3/4/5) per M0's frozen contract | CLI contract | piped/scripted invocation never prompts and **never approves** | #184 | — | R6, D-5 |
| 7.4 | Channel-adapter conformance | The InboxChannel contract (deliver + authenticate + return `(claim, principal)`; never decide) — terminal as the reference implementation + the parity fixture harness all channels share | adapter base + fixtures | terminal passes the channel conformance suite | #185 | — | R2 |
| 7.5 | Accessibility | Full keyboard operability, ASCII-safe rendering, NO_COLOR honored, screen-reader-linear layout (N-40..N-42) | UX rules | keyboard-only fixture passes; color never the sole signal | #186 | — | N-40..42 |
| 7.T | Tests | Blocking loop (pty fixtures), principals, non-interactive contract, conformance, accessibility | tests | coverage ≥ 95% | #187 | — | — |
| 7.C | Coverage gate | ≥95% | report | ≥95% | #188 | — | — |
| 7.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #189 | — | — |
| 7.CR | Code review | Findings resolved | log | no open findings | #190 | — | — |
| 7.D | Docs | Terminal channel reference + the channel-adapter contract | docs | updated + linked | #191 | — | — |
| 7.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 7.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · tests · coverage measured 95.61% · lint clean · docs · committed+pushed
- [x] SC-01 (terminal first ask) green; scripts can never approve; assumed principals audited
- [x] The InboxChannel contract + shared parity fixtures exist (all later channels inherit them)

**Closed 2026-11-08 except 7.C.** Design: [terminal](../design/v0.1.0/terminal.md) · Reference:
[terminal](../reference/terminal.md) · Gate: 379 tests, coverage 95.61%, `ruff` + `mypy --strict` clean.
**7.C (#188, coverage gate) is intentionally left open by the owner.**

---

Part 4 green ⇒ answers are unforgeable and the primary surface answers them; proceed to
[Part 5 (M8–M9)](wbs-v0.1.0-part5-desktop-bus.md).
