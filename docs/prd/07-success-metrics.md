# PRD 07 — Success Metrics

**BLUF:** agentinbox succeeds when three things are true: **approvers are fast** (p50 seconds, zero-context
correct in < 15 s), **the gate is trustworthy** (every transition recorded; no spoof/replay path works; timeout
never allows), and **humans do not mute it** (escalations reach on-call; floods produce one digest, not a
hundred pings). Every metric below is measurable from the product's own event stream or a scripted drill — no
vanity metrics.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## A. The headline metrics (from the consolidated PRD)

| Metric | Definition | Healthy | Where measured |
|---|---|---|---|
| **Ask response time p50** | `delivered → answered` on approved+denied asks | **< 60 s** (interactive terminal: < 15 s) | event timestamps |
| **Ask response time p99** | same, p99 — the escalation-path health number | **< escalation window + 2 min** | event timestamps + ladder drill |
| **% answered by standing policies** | asks auto-answered by standing approvals (v1.x feature R10) over total | **rising over time** | resolution source counters |
| **Approver satisfaction** | 2-week survey of daily approvers (1–5) + a mute/ignore proxy (delivery → no read action) | **≥ 4/5, no muting** | user study + instrumented no-action rate |

## B. The 15-second spine (R1 acceptance)

| Measure | Protocol | Target |
|---|---|---|
| **Zero-context correct call** | 10 approvers × 12-card scenario corpus; correctness pre-registered per card by the policy owner; time-to-decision instrumented | **≥ 9/10 correct in < 15 s** median, **< 25 s** p90 |
| **Missing-context honesty** | 12-card degraded corpus (fields stripped) — correct call is "not enough info → deny/ask", never a guess | 100% render `unknown`; 0 guessed-safe |
| **Injection resistance** | 10-card poisoned corpus (embedded instructions, fake urgency, CISO-impersonation) | **0 approvals caused by** embedded text; every card labels the source untrusted |

## C. Gate-trust metrics (security properties, all CI-able)

| Metric | Definition | Target |
|---|---|---|
| **Timeout integrity** | expiries that resolved to allow | **0 — ever** (test matrix + runtime counter) |
| **Spoof/replay/forward attempts** that altered state | forged callback, replayed token, off-roster tap, late answer, identity mismatch | **0** — each rejected + `answer-rejected` logged |
| **Single-use claims** | claims accepted twice | **0** |
| **Audit completeness** | terminal-state asks with a full transition timeline (ingest → … → terminal) | **100%** (reconstruction test per session) |
| **Chain integrity** | `verify-log` failures on an untouched store | **0**; tampering fixture **must** be detected |
| **Secrets in evidence** | evidence scanner over store dumps, channel payloads, audit exports | **0 findings** |
| **Fail-closed coverage** | fault-injection matrix paths resolving allow or silently skipping | **0** |

## D. Product-health metrics

| Metric | Definition | Healthy signal |
|---|---|---|
| **Time to first approval** | install → first recorded approval (field test + docs promise) | **< 5 min** (CUJ-1) |
| **Flood digest ratio** | notifications per flood event | **= 1** (plus the pre-flood pendings) |
| **Escalation reach** | 3 a.m. drill: configured tier notified within window | **100%**, with events reconstructing the ladder |
| **Channel parity defects** | same ask answered on different channels producing different records | **0** (byte-parity modulo channel/principal) |
| **Late answers** | answers after resolution | logged no-ops, approver informed — trend **down** as poll UX improves |
| **CI determinism** | `gate` exit codes across retry/offline matrices | **stable and documented** — `2/3/4` never proceed |
| **Constraint usage** (forward slate) | % of approvals on irreversible classes carrying constraints or edits (R14/R15) rather than raw approve | **rising** — the approver is shaping actions, not rubber-stamping them |
| **Evidence completeness at decision time** (forward slate) | share of answered `high`-tier asks whose card scored `Evidence: complete` (R23) | **rising**; decisions on partial evidence trend toward deny |
| **Review-loop health** (forward slate) | % of `needs_changes` asks that return revised and get decided vs. lapse (R48) | **decided, not lapsed** — the loop teaches, the clock disciplines |
| **Deny-taxonomy coverage** (forward slate) | % of denies/needs_changes carrying ≥ 1 structured reason code (R61) | **→ 100%** on mandatory classes; top codes feed policy tuning monthly |

## E. Adoption/compatibility metrics

| Metric | Definition | Target |
|---|---|---|
| **Producer integrations** | distinct harnesses/frameworks that can emit an ask end-to-end (agentpolicy + adapters + CLI/HTTP) | **≥ 2 at v0.1.0** (agentpolicy + any generic), **≥ 6 by v0.3.0** ([PRD 19](19-harness-compatibility.md)) |
| **Contract stability** | breaking changes to the ask contract/exit codes within v0.x | **0** (additive only, E10) |
| **Zero-cloud install** | setups completed without any cloud credential | **100% of v0.1.0 installs** (terminal-only mode is complete) |

## F. What failure looks like (anti-metrics, watched deliberately)

- Approvers **mute** the channel / ignore DMs → the tool has failed regardless of any other number.
- Deny-rate **≈ 0%** on irreversible asks → rubber-stamping (approvals without reading; card context too weak).
- Ask volume **explodes** while standing-approval usage stays flat → policy is mis-scoped; the inbox is paying
  for agentpolicy's over-triggering (feed the tuning loop, [PRD 22](22-operations-and-governance.md)).
- p99 grows while escalation fires less → the ladder is broken or quiet.

## G. Measurement infrastructure

All metrics derive from the same three sources — no side-channel analytics:

1. **The event stream** (R5): every state transition, timestamped, attributed.
2. **The export format** (R5): `agentinbox export` → JSONL; a small `report` command computes A–D locally.
3. **The drill packs** ([PRD 17](17-scenarios.md) + agentdrill flood pack): scripted scenarios with pass/fail
   assertions — the C/E metrics run in CI, not by hand.

**Privacy rule:** metrics are computed on the approver's machine from their own data; nothing is reported
anywhere by default. `agentinbox report --json` is the artifact a team can share if it wants to.
