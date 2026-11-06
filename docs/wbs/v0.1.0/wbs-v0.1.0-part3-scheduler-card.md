# WBS v0.1.0 — Part 3: Scheduler & Decision Card (M4–M5)

**BLUF:** **M4 is the security property**: the crash-safe scheduler that makes **timeout = deny** real —
absolute-UTC timers (TTL/warn/escalate), exactly-once recovery after crash, and clock-jump fail-closed
semantics (E2, E8, D-1). **M5 is the human property**: the decision-card renderer — the four context blocks,
unknown-labeling, untrusted/inert rendering — the component the 15-second spine (R1) lives or dies on.

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M4 — Scheduler, TTL/expiry + crash-safe recovery (E2, E8)

**Goal:** an ask nobody answers **cannot happen**, no matter what the process, the clock, or the laptop does:
timers derive from persisted absolute instants; boot recomputes and fires overdue transitions **exactly once**
with a `scheduler-recovered` marker; backwards clock jumps cannot extend a TTL; forwards jumps cannot
resurrect an expired ask. Expiry resolves deny with `human_gate_timeout` and a rescope hint
(SC-09, SC-10, CUJ-4).

**CUJ:** CUJ-4 · **Requirements:** R3, E2, E8, [PRD 03 §C-D](../../prd/03-landscape.md) (T9), D-1.

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 4.D0 | **Design docs first** | Scheduler design: timer model (absolute instants + monotonic deltas), boot recovery pass, per-class TTL/warn resolution from config, rescope-hint shape | docs | reviewed before code | #147 | — | — |
| 4.1 | Timer engine | Per-class `expires_at`/`warn_at`/`escalate_at` computed at ingest from config (floors/ceilings enforced); a wake loop or timer wheel firing at the instant with ≤1 s jitter | scheduler | warn fires at `T-60s`, expiry at `T` (N-5); SC-09 passes | #148 | — | R3, E8 |
| 4.2 | **Timeout = deny** | Expiry → terminal `expired` → resolve deny + `human_gate_timeout` + `retryable=false` + `rescope_hint`; **no config, channel, or retry path converts expiry to allow**; a runtime zero-allow-on-expiry counter exists and is tested | expiry path | SC-09 green; counter reads 0 in every fixture | #149 | CUJ-4 | R3, D-1 |
| 4.3 | Crash-safe recovery | On boot: recompute all timers from the store; overdue transitions fire **exactly once** with `scheduler-recovered`; late warnings fire once, never skipped silently; adopted-pending semantics for CLI-created asks | recovery | kill -9 at T-30s → restart at T+10s → one expiry, one event, correct time (SC-10) | #150 | — | E2 |
| 4.4 | Clock correctness | Absolute UTC persisted; monotonic deltas for firing; backwards jump cannot extend TTL; forwards jump past expiry cannot resurrect; `doctor` warns beyond the signature window | clock handling | SC-10 clock-jump variants green; skew fixtures fail closed (E8) | #151 | — | E8 |
| 4.5 | Pre-expiry warning | `ask-warned` transition + channel re-render with remaining time on every active channel | warning path | both-channel warning fixture (SC-09) | #152 | — | R3 |
| 4.T | Tests | Timer firing, expiry, restart recovery, clock jumps, warning | tests | coverage ≥ 95% | #153 | — | — |
| 4.C | Coverage gate | ≥95% | report | ≥95% | #154 | — | — |
| 4.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #155 | — | — |
| 4.CR | Code review | Findings resolved | log | no open findings | #156 | — | — |
| 4.D | Docs | Scheduler reference (timers, recovery, clock rules, rescope hints) | docs | updated + linked | #157 | — | — |
| 4.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 4.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [x] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [x] Timeout = deny demonstrated, logged, with rescope-not-failure to the producer; zero-allow counter at 0
- [x] Crash and clock-jump fixtures all fire exactly once and never extend or resurrect

**Closed 2026-11-06.** Design: [scheduler](../design/v0.1.0/scheduler.md) · Reference:
[scheduler](../reference/scheduler.md) · Gate: recorded in the [index](wbs-v0.1.0-index.md).

---

## Milestone M5 — Decision-card renderer + untrusted rendering (R1, E5)

**Goal:** the card that makes a zero-context approver correct in <15 seconds: the four context blocks
(action / policy / blast radius / session-so-far), explicit **`unknown`** for every missing field (never blank,
never guessed), untrusted agent/tool text rendered **inert** (escaped plain text, length caps, source labels,
no markup, no links-that-do-anything), and redaction receipts rendered. One renderer core feeds every channel
(CUJ-2, CUJ-11; SC-03/04/05 fixtures, SC-22/23 corpora authored here).

**CUJ:** CUJ-2, CUJ-11 · **Requirements:** R1, E5, [PRD 18 §anti-injection](../../prd/18-approval-integrity.md),
[PRD 25 R24/R25-posture](../../prd/25-evidence-and-decision-quality.md) (delta/trust-block groundwork),
[PRD 06](../../prd/06-security-baseline.md) (T2/T3).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 5.D0 | **Design docs first** | Card design: the four blocks, unknown-labeling rules, untrusted-content rules (escape/cap/label), layout parity across surfaces, the 15-second study's card corpus | docs | reviewed before code | #158 | — | — |
| 5.1 | Card model + renderer core | Structured card object (action, policy clause + reason code + policy version, blast radius + reversibility label, session tail, flags, alternatives, TTL) → a **surface-neutral** render; one core, per-surface frontends | renderer | same ask renders the four blocks on every surface (fixture) | #159 | CUJ-2 | R1 |
| 5.2 | Unknown-labeling | Missing/stripped fields render a visually distinct **`unknown`**; ambiguity (reversibility unknown) labels as unknown-irreversible-class, never guesses | renderer | degraded-corpus fixture: 100% explicit unknown, 0 blanks, 0 guessed (SC-04) | #160 | CUJ-2 | R1 |
| 5.3 | **Untrusted/inert rendering** | Agent/tool-derived strings: plain text only, escaped, per-field + per-card caps with visible truncation, `[untrusted: tool output]` labels, no markdown/HTML/link-expansion, buttons only in trusted chrome | renderer | injection corpus (markdown "buttons", fake links, CISO-impersonation, "ignore previous", zero-width) renders **inert** — 0 approvals, 0 navigation (SC-22/23 fixtures) | #161 | CUJ-11 | E5 |
| 5.4 | Redaction receipts on card | Every redacted field shows a receipt marker (class/count), never the value | renderer | card fixtures carry receipts; scanner finds no raw values | #162 | — | E6 |
| 5.5 | Card corpora + study fixtures | The zero-context corpus (12 cards + 12 degraded + 10 poisoned) authored with pre-registered answers, checksummed, for M24's study (Method B) | fixtures | corpus frozen with checksum; injection corpus gates releases | #163 | CUJ-2 | R1, E5 |
| 5.T | Tests | Render parity, unknown-labeling, inert-rendering corpora, truncation receipts | tests | coverage ≥ 95% | #164 | — | — |
| 5.C | Coverage gate | ≥95% | report | ≥95% | #165 | — | — |
| 5.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #166 | — | — |
| 5.CR | Code review | Findings resolved | log | no open findings | #167 | — | — |
| 5.D | Docs | Card reference (blocks, rules, corpora) | docs | updated + linked | #168 | — | — |
| 5.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 5.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Four blocks render on every surface; missing context renders `unknown`, never guessed
- [ ] Injection corpus produces 0 approvals and 0 navigation; corpora frozen for the M24 study

---

Part 3 green ⇒ the gate is safe (M4) and legible (M5); proceed to
[Part 4 (M6–M7)](wbs-v0.1.0-part4-claims-terminal.md).
