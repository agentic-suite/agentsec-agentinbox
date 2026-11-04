# PRD 26 — Approver Experience, Teams & Operations

**BLUF:** The gate competes with muscle memory — so the inbox behaves like a real operator tool, not a popup:
**grouped review** of similar asks (answered one-by-one — never bulk-approved), **claim / assign / handoff**
for teams, **quiet hours + workload caps + incident/freeze mode** so the human stays sane, **persona-tuned
views** and **saved filters**, **precedent on cards** (advisory only), **SLA/latency accountability**, **search
& replay**, and a **localhost-only web UI** as a first-class (optional) surface — same store, same claims, same
audit. If approvers mute this product, every other requirement is worthless; this PRD is the muting defense.

**Status:** Draft — v0.1.x–v0.2.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

Every approval product dies the same death: volume. 40 raw interrupts a day → auto-approve → the gate is now
an attack surface with a rubber stamp on it. The defenses are structural: group what is similar, route what
belongs to someone else, silence what can wait, and be honest about who is actually answering. None of this
is decoration — notification hygiene is a security property ([PRD 05 E7](05-features.md)).

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R27** | **Grouped review.** Near-identical asks (same session + effect target + reason code + class) cluster in the queue and on cards: "17 similar asks from migration job X". Safe default is **review individually** with next/prev, prefilled deny reasons, and apply-reason-to-each — display groups, decisions stay per-ask ([PRD 14 N-20](14-non-goals.md) is the regression test). | v0.1.x | A 17-ask cluster renders as one group with 17 individual decisions; a scripted bulk-answer attempt fails; grouping is deterministic (same inputs → same groups) |
| **R28** | **Persona/mode-tuned views.** Rendering policies per inbox mode — solo (blocking card), on-call (severity-first, countdown-first, minimal chrome), CI/release (one-line summaries + job links), security-review (full context, trace ids, evidence drawer). Same truth, different presentation; mode is a view, never a different decision path. | v0.2.0 | Each mode renders from the same card object (fixture parity); no mode hides a required context block (the four blocks always render) |
| **R29** | **Saved views & filters.** Approvers define named filters: `critical-prod`, `external-send`, `ci-releases`, `pending-by-expiry`, `asks-from-agent-X` — usable in the TUI and the local web UI; shareable as config. | v0.2.0 | A saved view round-trips via config; export of a view's asks matches filter semantics exactly |
| **R30** | **Claim / assign / handoff.** Team semantics *around* the decision: an approver can **claim** ("I'm handling this" — visible to others, cancels nothing), be **assigned** by a roster peer, and pass a **handoff note** up the escalation ladder ("tier 1 checked runbook RB-7, still unclear"). These are recorded states/events, never decisions: `claimed` ≠ `approved`. | v0.1.x | Claim/assign/handoff recorded with principals; two approvers see who owns it; claiming does not stop the clock or the ladder (SC-31) |
| **R31** | **Workload controls.** Per-class **quiet hours** (non-urgent asks queue silently for the window), **max concurrent visible asks** per approver (overflow routes to the backup roster), and **pause low-priority during incidents** — all config, all audited, and none of them touch irreversible-class TTLs (silence never extends or softens a deadline). | v0.1.x | Quiet-hours fixture: low asks wait visibly, urgent asks still deliver; overflow reaches backup roster; irreversible asks are never quieted (SC-32 sibling fixture) |
| **R32** | **Incident/freeze mode.** One audited toggle that tightens the whole inbox: shorter TTLs, self-review bans widen, more classes escalate immediately, some classes go **deny-only** for the window (mirrors agentpolicy's freeze posture R33 — the inbox displays and gates, policy still decides). On/off are events; the mode carries an owner and a reason. | v0.1.x | Freeze mode flips all listed behaviors at once (SC-32); exit is audited; no class silently loosens |
| **R33** | **SLA / latency accountability.** Per ask: who was asked (every tier), when it was delivered, when **claimed** (the only honest "seen" signal we have — we do not fake read receipts), when answered, and where time went. Team report: response percentiles by class/tier/approver-group, escalation bottlenecks. | v0.2.0 | The timeline reconstructs ask→deliver→claim→answer for every ask; the report names the slowest tier without inventing read data |
| **R34** | **Search, replay & ask analytics.** Local search over asks (agent, rule, target, reason, class, outcome); **replay any historical card** exactly as rendered (the store keeps render digests); weekly ask-analytics: which rules generate fatigue, which classes always approve (rubber-stamp detector — feeds R11 and policy tuning). | v0.2.0 | Search over 10k asks returns in < 1 s locally; replay byte-matches the original render digest; rubber-stamp report flags an always-approved class in a fixture corpus |
| **R35** | **Local web UI (localhost-only).** An optional, loopback-served UI: queue, evidence drawer, answer actions, audit timeline, search, saved views. No SaaS, no remote bind, no accounts — the same daemon, same claims, same audit; the browser is just another InboxChannel with the **OS session as principal**. | v0.2.0 | UI answers an ask end-to-end via the claim+principal pipeline (it is a channel, not a bypass); remote bind attempts refused; [PRD 14 N-13](14-non-goals.md) is superseded *only* for this localhost surface, documented as such |
| **R36** | **Precedent on cards (advisory only).** Where history exists, the card shows: "last similar ask: denied 2 days ago by Ravi (freeze window)", "this target: approved 8× in staging, never in prod", "same agent denied twice today under this rule". Deterministic lookups, clearly labeled **advisory** — there is **no** path from precedent to auto-answer, and the trust block separates precedent from facts. | v0.2.0 | Precedent renders for asks with history; no-history renders nothing (never invented); an attempt to use precedent as an answer is rejected (it is display, not input) |

## The honesty rules that keep this from becoming surveillance

- **No read receipts.** "Claimed" is the only seen-signal; SLA metrics say so rather than guessing attention.
- **Metrics are local.** All analytics compute over the owner's store via `report`; nothing phones home
  ([PRD 13 N-26](13-non-functional-requirements.md)).
- **Grouping is for humans, not for policy.** Flood math (R7) stays independent of display grouping — a
  deterministic cluster that hides 100 asks behind 1 row would be a notification lie; the group header always
  states the count.

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-31 · Claim ≠ approve, handoff up the ladder.** Dana claims an escalated ask (visible; clock runs); she
cannot finish; handoff note travels to tier 3 with the claim history; tier 3 denies. Events: claimed →
handoff-noted → escalated → answered; **no** `ask-answered` until the deny.

**SC-32 · Incident mode + quiet hours.** Freeze toggled on (audited, with owner+reason): TTLs shorten,
low-priority queues silently, `irreversible` still rings immediately; toggle off is audited; the
rubber-stamp-friendly classes are deny-only for the window. Quiet-hours sibling: nothing irreversible is ever
silenced.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R27 | CUJ-6 | SC-13/SC-34 + grouping fixture | `test_grouping.py` |
| R28/R29 | CUJ-2, CUJ-7 | mode-parity fixtures | `test_views.py` |
| R30 | CUJ-5 | SC-31 | `test_claim_assign.py` |
| R31/R32 | CUJ-5, CUJ-6 | SC-32 | `test_quiet_hours.py`, `test_incident_mode.py` |
| R33 | CUJ-10 | SLA timeline fixture | `test_sla_timeline.py` |
| R34 | CUJ-10 | replay/search fixtures | `test_search_replay.py` |
| R35 | CUJ-1, CUJ-9 | web-UI channel conformance | `test_webui_channel.py` |
| R36 | CUJ-2 | precedent fixtures | `test_precedent.py` |
