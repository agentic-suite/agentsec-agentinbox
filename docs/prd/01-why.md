# PRD 01 — Why

**BLUF:** Every material agent-security control eventually reduces to a human decision about an irreversible
action. The ecosystem already emits that decision — agentpolicy's `ask` — but **nobody consumes it**. Approvals
today are harness-native, single-session, unaudited, un-escalated, and unavailable to headless agents. That is
not a UX gap; it is the failure mode that turns a security product into a denial generator, and the reason
gate coverage gets disabled in practice. agentinbox is the missing consumer: one inbox, many channels, safe
defaults, real audit.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## The problem in one paragraph

A policy engine that returns `ask` has delegated a security decision to a human and then abandoned it. The
human is usually not at the keyboard, not in the same session, and not the person the harness prompt was
written for. If the ask is a modal dialog, it interrupts and gets rubber-stamped. If it is a Slack message, it
scrolled away. If the agent is headless, it never appears at all. If an attacker can shape the text the approver
reads, the approval itself becomes the exploit. And when the answer is delayed, the agent either blocks forever
or (worse) proceeds by timeout. **A gate is only a control if it has a destination, an identity, a deadline, and
a record.** agentinbox exists to provide those four things.

## Four failure modes, with evidence

| # | Failure mode | What happens today | Evidence | Consequence |
|---|---|---|---|---|
| **F1** | **The gate has no consumer** | agentpolicy returns `ask`; the only surfaces are harness-native prompts (Claude Code's permission dialog, Cursor's prompt) — single harness, single session, no routing | Ecosystem PRD 11 §1; harness-native approval UX is per-product by construction | `ask` is unimplemented in practice; teams either disable it or hard-deny, and hard-deny kills adoption |
| **F2** | **The human is not where the gate is** | A CI agent, a cron job, or a 3 a.m. deploy asks in a terminal nobody is watching; there is no escalation, no push, no on-call route | Enterprise approval systems all ship escalation ladders and on-call routes (PagerDuty escalation policies; ServiceNow approval/change workflows) — agents have none of it | Irreversible actions are either blocked forever or approved by whoever happens to be online |
| **F3** | **The approval is not an identity or an audit record** | A click, a "yes", or a forwarded link is treated as consent; nothing binds the answer to the exact action, the approver, or a tamper-evident record | OWASP Top 10 for Agentic Applications 2026 — **ASI09 Human-Agent Trust Exploitation**; EU AI Act **Art. 14** human oversight requires effective, not theatrical, oversight | Replay, confusion, and rubber-stamping; no defensible evidence for auditors or incident review |
| **F4** | **The approval surface is attackable** | The ask text is attacker-influenced (agent or tool output). A link can be forwarded; a Slack message can be forged; a flood can exhaust the approver until they approve anything | Prompt injection is unsolved; the research base's own lesson is that *our* approval UX is part of the attack surface (ADR/PRD 11 §3 non-requirements) | The gate becomes the exploit path — an attacker who can write the question writes the answer |

### Why "ask" is the hardest outcome to ship

`allow` and `deny` are deterministic. `ask` is a **distributed system with a human in it**: it needs durable
state, delivery, identity, deadlines, escalation, idempotency, and evidence — across channels that were not
designed to agree with each other. That is why every commercial platform solves it with a workflow product
(ServiceNow, PagerDuty, Splunk SOAR, Okta Access Requests, Azure PIM) and why the OSS agent ecosystem has
skipped it. agentinbox is the small, local-first version of that workflow product, purpose-built for agent
actions and wired into the ecosystem's decision and event contracts.

## What exists today (and why it is not enough)

| Existing surface | What it does well | Why it is not the answer |
|---|---|---|
| **Harness permission prompts** (Claude Code, Cursor, Copilot, Codex) | Zero setup; inline context; blocks the session | Single-harness, single-session, no remote answer, no escalation, no durable record, nothing for headless/CI |
| **Chat approvals** (Slack messages, Teams cards, bots) | Ubiquitous; mobile by default | Free text is spoofable and structureless; "yes" in a channel is not an authenticated approval of a specific action; no binding to arguments |
| **CI/CD deployment gates** (GitHub Actions environments, GitLab protected environments) | Real precedent: required reviewers, prevent self-review, wait timers, secrets withheld until approval | Scoped to deployments inside one CI vendor; no agent action context, no ask identity, no TTL-per-action-class, no cross-channel consistency |
| **ITSM / workflow approvals** (ServiceNow, Jira Service Management) | Mature approvals: rationale, delegation, SLAs, audit | Heavy, ticket-shaped, not agent-shaped; no notion of `action_identity`, no real-time gate, no agent-facing contract |
| **On-call / incident tools** (PagerDuty, Opsgenie) | Escalation ladders, schedules, 3 a.m. routing | Paging is not approval; no per-action binding, no approve/deny lifecycle, no agent policy context |
| **SOAR / security automation** (Splunk SOAR, Tines, Torq) | Approval tasks inside playbooks; audit | Playbook-scoped, enterprise-only, not local-first, not usable by a coding agent mid-session |
| **PAM / access-request tools** (Okta Access Requests, Azure PIM) | Time-bound elevation, justification, approvals, delegation | Human-access-shaped, not agent-action-shaped; requires an IdP and a joiner/mover/leaver process |
| **MCP elicitation** (MCP 2025-06-18) | Standardized server→client user input with `accept`/`decline`/`cancel` | Information collection, not authorization: no durable ask, no identity binding, no audit, no escalation, no timeout semantics; the spec explicitly tells clients to rate-limit and to make the requesting server clear |

The gap is not "a nicer prompt". The gap is the **lifecycle**: raise → deliver → warn → escalate → answer →
resolve → audit, with identity and deadlines on every transition.

## Why now

1. **The producer exists.** agentpolicy shipped the ask contract in v0.1.0 — `ask_id`, `action_identity`,
   `expires_at`, approve/deny/expire, and **timeout = deny** (`src/agentpolicy/ask.py`, reason codes
   `human_gate_required` / `human_gate_timeout`). Until agentinbox, that contract has no consumer and the
   Wave 0 "Replit rule fires" demo has no ending.
2. **The event vocabulary exists.** agentwatch's security-event schema is the single place to record security
   events, and the agent-record schema already carries `authorization.source` (`human-once`,
   `human-remembered`) — the exact provenance an inbox answer produces. Ask lifecycle events are the additive
   extension this PRD specifies with agentwatch as owner.
3. **The protocol layer standardized user interaction.** MCP elicitation (2025-06-18) legitimized
   server→human requests, but deliberately covers *information collection*. Approval remains an application
   concern — and that application is missing.
4. **Enterprise buyers already expect the controls.** Required reviewers, prevent-self-review, wait timers,
   escalation policies, and time-bound approvals are table stakes in CI, ITSM, PAM, and on-call products. An
   agent gate without them is not procurable, no matter how good the policy engine is.
5. **The incident record is fresh.** Irreversible agent actions (the Replit production-database deletion during
   a code freeze) are now the canonical cautionary tale. The fix is architectural: gate the action, make the
   human answer fast, and record it.

## What agentinbox is (and is not)

> **"One inbox for every agent gate — answered from where you are, safe if you are not."**

It is the **consumer** of `ask`, not a policy engine; the **destination**, not a harness UI replacement; the
**record**, not a SIEM. It is local-first: a single binary/CLI plus a local store, no cloud dependency, so a
solo developer and an air-gapped enterprise get the same semantics. **Matrix is the second interactive
surface (an open federation protocol — v0.1.x); Slack/Teams are optional community adapters**, not
requirements for correctness — the product is complete for users who run no chat platform at all.

## What success looks like

- An approver with **zero prior context** makes the correct call in **under 15 seconds** on a real ask
  (the PRD's R1 user test), because the card answers four questions: *what will happen, why now, what does it
  touch, what happens if I say no.*
- A 3 a.m. ask reaches the configured on-call tier **within the escalation window** or resolves to **deny** —
  never to "still pending".
- An auditor can reconstruct a full gate history for a session from one store, with every transition attributed
  to an authenticated principal.
- A flood of asks is neutralized as **one event and one digest**, not a hundred notifications.
- Approvers do not mute the inbox. If they do, the product has failed regardless of coverage metrics.

See [PRD 04](04-users-and-cujs.md), [PRD 07](07-success-metrics.md), and the scenario catalog in
[PRD 17](17-scenarios.md).

## Non-goals

No approvals by ML; no chat-bot decision surface in v0; no harness-side UI replacement in v1; no shared
multi-tenant SaaS in v0.1.0. Full list in [PRD 14](14-non-goals.md).
