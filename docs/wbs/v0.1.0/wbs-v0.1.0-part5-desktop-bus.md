# WBS v0.1.0 — Part 5: Desktop Notifications & AskBus (M8–M9)

**BLUF:** **M8 delivers the no-chat remote path**: desktop notifications (macOS Notification Center via
`osascript`/UserNotifications; Linux `notify-send`/Freedesktop) — a **wake-up, never a decision surface**; the
answer happens in the terminal under the OS session. No third-party account, no network, no external trust
boundary — the 3 a.m. story for the no-Slack/no-Matrix install. **M9 delivers the movement layer**: the
**AskBus** contract and its first two drivers — in-proc (default; jobs are function calls) and the
**filesystem spool** (atomic tmp→rename, fsync, `flock` single-owner, inotify/poll ≤1 s) — jobs are
at-least-once with **idempotent consumers**, and the store holds the truth (E12, D-13, D-14).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M8 — Desktop notification channel (R2)

**Goal:** an ask away from the terminal still reaches the human *on the same machine*: a notification carrying
the ask fingerprint, class, and remaining TTL; the full card opens via `agentinbox inbox`/`answer`. Escalations
re-notify once per tier; floods notify once (the digest); notification actions are **never** wired to answers
(platform buttons are spoof-prone). Unavailability (headless SSH, no daemon) is a `doctor` finding, never a
silent gap.

**CUJ:** CUJ-3 (surface), CUJ-5 (surface) · **Requirements:** R2, [PRD 16 §B.2](../../prd/16-channel-and-harness-adapters.md),
[PRD 06](../../prd/06-security-baseline.md) (channel table), [PRD 13](../../prd/13-non-functional-requirements.md) (N-3a, N-34).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 8.D0 | **Design docs first** | Desktop channel design: per-OS mechanics, content rules (fingerprint/class/TTL only), answer-path redirection to terminal, re-notify/once-per-tier rules, unavailability handling | docs | reviewed before code | #192 | — | — |
| 8.1 | macOS notifier | `osascript`/UserNotifications path; titles/threads/body per the content rules; activation opens the inbox | notifier | fixture-rendered notification matches content rules (no args, no secrets) | #193 | — | R2 |
| 8.2 | Linux notifier | `notify-send`/Freedesktop path (actions intentionally unused); same content rules | notifier | same | #194 | — | R2 |
| 8.3 | Wake-up-not-decision enforcement | The channel implements `deliver()` only; its adapter exposes **no** answer path — any notification tap routes to the terminal answer flow | adapter | channel conformance suite: desktop has deliver, no answer; spoofed notification cannot forge the terminal principal | #195 | — | E4 |
| 8.4 | Escalation/flood hygiene | Re-notify once per tier with tier context; a flood produces the single digest notification; quiet behavior per config | delivery rules | SC-11/SC-13 notification-count fixtures: exactly once per tier, exactly one digest | #196 | CUJ-5 | R4, R7 |
| 8.5 | Reachability + `doctor` | Daemon detection for each OS surfaced in `doctor` (green/red, exit-coded); unavailability = pending + TTL unaffected (E9 interplay) | doctor checks | headless fixture: doctor red, ask still expires correctly | #197 | — | E9 |
| 8.T | Tests | Notifier rendering (mocked backends), content rules, conformance, count fixtures | tests | coverage ≥ 95% | #198 | — | — |
| 8.C | Coverage gate | ≥95% | report | ≥95% | #199 | — | — |
| 8.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #200 | — | — |
| 8.CR | Code review | Findings resolved | log | no open findings | #201 | — | — |
| 8.D | Docs | Desktop channel reference (per-OS setup, limits, honesty about buttons) | docs | updated + linked | #202 | — | — |
| 8.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 8.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Notifications carry class + fingerprint + TTL only; answers exist only in the terminal flow
- [ ] Once-per-tier re-notify + single-digest-on-flood fixtures green; unavailability is a doctor finding

---

## Milestone M9 — AskBus: contract + in-proc + filesystem spool (E12)

**Goal:** the movement layer, built as a driver contract so single-box today and server-mode brokers later are
the **same core**: `AskBus` with typed jobs (`deliver`/`renotify`/`escalate`/`digest`/`expire`),
at-least-once delivery + **idempotent consumers** (a redelivered job against a resolved ask is a logged no-op),
`not_before` honored; in-proc driver default; **filesystem spool** driver (tmp→rename atomicity, fsync
file+dir, `flock` one writer per spool, inotify/FSEvents with ≤1 s bounded-poll fallback, `jobs/`/`done/`/
`locks/` layout, aggressive pruning). Movement never becomes truth (D-13); the spool is honestly one box
(D-14).

**CUJ:** — (infrastructure) · **Requirements:** E12, [PRD 16 §C](../../prd/16-channel-and-harness-adapters.md),
[PRD 15 §storage](../../prd/15-data-model.md), [PRD 13](../../prd/13-non-functional-requirements.md) (N-3c, E15-posture).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 9.D0 | **Design docs first** | Bus design: job types/payloads, at-least-once + idempotent-consumer rules, spool layout + atomicity/locking protocol, driver selection, future Redis/NATS drivers | docs | reviewed before code | #203 | — | — |
| 9.1 | AskBus interface | `publish(job)`, `consume(handler)`, `not_before` scheduling; jobs typed + dedupable; every consumer idempotent **by ask state** | interface | mypy-clean; the same job delivered 3× = one effect + 2 logged no-ops | #204 | — | E12 |
| 9.2 | In-proc driver (default) | Jobs as function calls with the same semantics; the common single-box case needs nothing else | driver | conformance green; zero moving parts | #205 | — | E12 |
| 9.3 | **Filesystem spool driver** | tmp→rename publishes; fsync file + dir; `flock` single-owner (second daemon **refuses loudly**); inotify/FSEvents wakeups with ≤1 s poll fallback; `done/` move-on-consume; `.tmp` sweep on boot; aggressive pruning (movement ≠ evidence) | driver | SC spool fixtures: atomicity, crash mid-job, lock refusal, ≤1 s pickup (N-3c) | #206 | — | E12, D-14 |
| 9.4 | **Bus conformance suite** | At-least-once + idempotent-consumer, crash-mid-job, rename-CAS, lock, poll-latency — run against every driver (in-proc + spool now; brokers later inherit) | fixtures | both drivers green; a fake broken driver fails the suite | #207 | — | E12 |
| 9.5 | Flood-before-bus rule | The M12 flood guard (built next) hooks the publisher: throttled floods publish **1 digest job**, never N deliveries — enforced at the bus contract level | publisher rule | 200-ask flood → 1 digest job in the spool (fixture) | #208 | — | R7, E12 |
| 9.6 | Delivery wiring | Channels subscribe per job type: terminal/desktop/webhook (M13) consumers; every delivery attempt becomes a Delivery record + event (E7 groundwork) | wiring | delivery-failure path produces `delivery-failed` events + bounded retries | #209 | — | E7 |
| 9.T | Tests | Contract, both drivers, crash/lock/latency fixtures, consumer idempotency | tests | coverage ≥ 95% | #210 | — | — |
| 9.C | Coverage gate | ≥95% | report | ≥95% | #211 | — | — |
| 9.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #212 | — | — |
| 9.CR | Code review | Findings resolved | log | no open findings | #213 | — | — |
| 9.D | Docs | Bus reference (jobs, drivers, spool protocol, one-box honesty, broker roadmap) | docs | updated + linked | #214 | — | — |
| 9.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 9.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Queue moves, store decides: no job can answer an ask, reorder the store, or lose silently
- [ ] Spool atomicity/lock/latency fixtures green; a flood publishes one digest job; both drivers pass conformance

---

Part 5 green ⇒ reach without a platform (M8) and movement without truth (M9); proceed to
[Part 6 (M10–M11)](wbs-v0.1.0-part6-ci-escalation.md).
