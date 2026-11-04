# PRD 00 — Press Release / FAQ

**BLUF:** agentinbox is the **approval control plane for consequential agent actions** — the human half of
every agent `ask` decision, and one place to **review, constrain, route, and audit** risky agent work across
harnesses, frameworks, CI, and local tools. It takes the
`ask` that agentpolicy emits, turns it into a decision-ready notification (what the agent wants to do, which
policy fired, the blast radius, the session so far), routes it to where the human actually is (terminal,
desktop notification, CI checkpoint, signed webhooks — Matrix next, chat platforms optional), enforces
**timeout = deny**, escalates what nobody answers, throttles ask-floods, and records
every ask/answer/timeout/escalation in the agentwatch schema. v0.1.0 ships terminal + desktop + CI + webhook,
local-first, with unforgeable answer tokens and a reconstructable audit trail — **and needs no chat platform
at all**.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Press release

### agentinbox — every agent gate, answered in 15 seconds

*Open-sourced today, agentinbox turns the agent "ask" outcome into a human decision that is fast, safe by
default, and fully auditable — from the terminal, a desktop notification, or a CI pipeline.*

Agents are now trusted with actions that cannot be undone: dropping a production table, force-pushing `main`,
sending the customer list to an external endpoint, rotating a live credential. The policy layer can already say
**"a human must decide"** — but until now that sentence ended in a harness prompt that only one person in one
session on one machine ever sees. Headless and CI agents get nothing at all. The result is predictable:
approvers approve blindly to unblock themselves, or teams disable the gate to ship.

agentinbox is the missing destination. It receives the ask with **full decision context**, delivers it to a
channel the approver already watches, accepts an answer only from an authenticated approver bound to that exact
action, and closes the loop with agentpolicy so the agent gets a real outcome. If nobody answers in time, the
action **does not happen** — timeout is a deny, the safe default, with a pre-expiry warning and an escalation
ladder so a 3 a.m. prod deploy request reaches on-call instead of dying in a muted channel.

> *"A gate nobody answers is not a control. It is a denial generator."*

**How it works**

1. agentpolicy evaluates an action as `ask` and hands agentinbox the ask id, the action identity
   (`tool` + `action` + canonical arguments), the matched policy clause, the blast radius, and the TTL.
2. agentinbox renders a **decision card**: what will happen, why the gate fired, what it touches, how bad it
   is if wrong, and what the alternatives are — with all agent-supplied text treated as untrusted and escaped.
3. The card goes to the approver's channel. The answer is a **single-use claim token** bound to the ask and to
   an authenticated human; a link that is forwarded, replayed, or answered late changes nothing.
4. Every state change — raised, delivered, warned, escalated, answered, timed out, flood-denied — is written to
   an append-only, hash-chained local audit log and emitted as agentwatch security events.
5. agentpolicy resolves: approval → allow (identity-bound), deny → deny, timeout → deny with
   `human_gate_timeout` and a **rescope hint** the agent can act on.

**Availability:** `pip install agentsec-agentinbox`; Apache-2.0 on GitHub. v0.1.0 targets **terminal,
desktop notifications, CI checkpoints, and signed webhooks**, with **Matrix** as the next interactive
surface and chat platforms (Slack/Teams) as optional community adapters — the product is **complete with no
chat platform at all**. It is harness-agnostic by construction: it consumes the agentpolicy ask contract and
the agentwatch event schema, so any harness whose enforcer can ask a human can use it.

## FAQ

**Is this a chat bot?**
No. v0.1.0 ships **no free-text decision surface**. Approval happens through a structured action (a terminal
keypress, a CI process exit, or — when a chat adapter is configured — a platform-signed button) bound to an
unforgeable token. Chat is where approvals die: it is spoofable, it loses structure, and it leaves no
trustworthy record ([PRD 14](14-non-goals.md)). Chat is a *rendering surface*, not a command interpreter —
and it is optional.

**Does a model ever answer a gate?**
Never. There is no ML in the decision path, and no "auto-approval agent" in v0.1.0. An approval answered by
automation is a standing policy, not an approval, and it must be configured, scoped, and logged as such
(PRD R9/R10, later versions) ([PRD 14](14-non-goals.md)).

**What if the approver is asleep or the channel is down?**
Timeout is deny. The agent does not hang forever: it gets a deny it can rescope, retry with narrower scope, or
surface to its user. Escalation re-notifies the next tier before expiry — it never silently extends the TTL.

**What happens when the rules conflict?**
There is one fixed, published **precedence lattice** — deny-shaped outcomes outrank allow-shaped ones; a human
answer beats every convenience rule, but loses to freshness, provenance, window, and dependency failures
([PRD 30 §1](30-correctness-conflict-abuse-hardening.md)). A standing rule cannot outvote a freeze; a session
grant cannot outvote a minimum-provenance tier. The lattice is a tested total order, not a config engine —
which is exactly why you can trust it.

**Is it just approve/deny?**
No — the approver can **shape the action**: approve *narrowed* (staging only, dry-run only, capped at 100 rows,
time-boxed), approve an **edited** form (trimmed recipient list), **request changes** as a real outcome
(`needs_changes` with a structured review loop, inside a running clock that never extends), and see evidence
that makes the decision real (diffs, plans, previews, "why this ask" deltas, a trust block, an evidence-quality
score, confidence-labeled blast radius). Every decision records a **provenance tier** — not just who approved,
but *how strongly they were verified* — and exports as a **signed attestation** a third party can verify
offline. Constraints are recorded by agentinbox and enforced by the policy layer ([PRD 24](24-constrained-approvals-and-effects.md),
[PRD 25](25-evidence-and-decision-quality.md), [PRD 28](28-review-loops-and-orchestration.md),
[PRD 29](29-trust-maturity-writeback-performance.md)).

**Is this only for agentpolicy?**
No. agentpolicy is the first and reference producer, but the ask contract is a small JSON document. Anything
that can emit an ask — a LangGraph `interrupt`, an OpenAI Agents SDK tool-approval, a CI script, an MCP
elicitation bridge — can call agentinbox and get the same lifecycle, audit, and enforcement semantics
([PRD 19](19-harness-compatibility.md)).

**Do I need Slack (or any chat platform)?**
No — and this is a design decision, not a gap ([PRD 16 §A.2](16-channel-and-harness-adapters.md)). The
default install is **terminal/TUI + desktop notifications + CI checkpoints + signed webhooks**: no workspace,
no third-party account, no external trust boundary, works air-gapped. Remote/phone approval comes via **Matrix**
(an open protocol) in v0.1.x; Slack/Teams adapters exist for teams that want them, behind the same security
contract — none of them is load-bearing for correctness.

**How is a remote approval not spoofable?**
Three independent checks: the channel's authenticity proof (an OS session for terminal, a platform signature
for chat adapters, when configured), an approver identity allowlist for that action class, and a single-use
claim token bound to the ask's `action_identity`. A screenshot, a forwarded message, a replayed request, or an
approval for a *similar* action does not release anything ([PRD 18](18-approval-integrity.md)).

**Where is the inbox? (Do I have to check another thing?)**
No. The inbox is **a state, not a place**: the ask comes to where you already are — a blocking card in your
terminal session, a desktop notification, a chat card (if you run a chat adapter), or a halted CI step. There
is no dashboard to visit in v0.1.0 ([PRD 14 N-13](14-non-goals.md)); the only pull surface is the
`agentinbox inbox` triage view ([PRD 16 §B.1](16-channel-and-harness-adapters.md)). The record of truth is
local — `~/.agentinbox/inbox.db` ([PRD 15](15-data-model.md)) — and every channel renders the same card from
the same store. Under the hood, a **filesystem spool bus** moves delivery jobs (inspectable with `cat` and
`tail -f`) while the store holds the truth — movement and truth are deliberately separate
([PRD 16 §C](16-channel-and-harness-adapters.md)).

**What is stored?**
Ask metadata, the redacted action context, the decision, the approver identity, and timing. Never secrets, API
keys, or full customer records: argument values pass a redactor before storage and before rendering, and the
audit log records the redaction receipt ([PRD 06](06-security-baseline.md)).

**What does it not do?**
It does not decide policy (agentpolicy does), does not enforce in the harness (the enforcer does), does not
replace the harness's own prompt in v1, and does not run a shared multi-tenant SaaS in v0.1.0
([PRD 14](14-non-goals.md)).
