# PRD 11 — agentinbox (the ask-gate)

**Status:** Draft · **Priority:** P1 (ships with agentpolicy — it has no product without this) · **Personas:** P1 Maya, P2 Ravi, P4 Sam

## 1. Why (problem + evidence)

1. Every PRD's `ask` outcome (human gate for irreversible actions) currently has no consumer — a gate nobody
   answers is either a denial generator or a nagging dialog; either kills adoption (PRD 02 open question).
2. The Five-Eyes-consensus guidance from the research is human oversight at consequential decisions — but
   nobody has built the actual experience of being that human.
3. Every existing approval UX is harness-native (Claude Code's permission prompt) — single-harness,
   single-session, no escalation routing, no audit, nothing for headless/CI agents at all.

## 2. What (requirements)

### P0 — Must have (v1.0, co-released with agentpolicy)

| # | Requirement | Acceptance criterion |
|---|---|---|
| R1 | Receive every `ask` decision as a notification with full context: what the agent wants to do, which policy fired, the action's blast radius, the session so far | An approver with zero context makes a correct call in <15 seconds (user test) |
| R2 | Answer from where the human actually is: terminal, desktop notification, Slack — same decision, all channels | Approval from any channel recorded identically in the audit trail |
| R3 | Timeout = deny (the safe default), configurable per action class, with a pre-expiry warning | Timeout behavior demonstrated, logged, and the agent receives a rescope-not-failure outcome |
| R4 | Escalation: unanswered asks route up (buddy → on-call → channel) per configurable ladder | A drill asking at 3am routes to on-call within the configured window |
| R5 | Every ask/answer/timeout/escalation in the agentwatch schema | Full gate history reconstructable per session |
| R6 | CI/headless agents supported: asks surface as CI checkpoints (a PR-style gate), not just push notifications | A CI agent's irreversible action halts the pipeline on an ask |
| R7 | Rate protection: a misbehaving agent cannot spam the inbox (ask-flood throttling + auto-deny on flood = an event) | Flood attack pack neutralized without overwhelming the approver |

### P1 — Should have (v1.x)

- R8: Mobile push (the 3am scenario done right).
- R9: Approval policies: certain ask classes delegatable to a second agent/automation under narrower policy
  (approved-by-machine, logged as such).
- R10: Standing approvals: "always allow this class from this project" with expiry — convenience without
  permanence.

### P2 — Nice to have

- R11: Approver analytics: what you approve most (feeds policy refinement — those classes need better rules,
  not more approvals).
- R12: Shared inbox for teams: round-robin ask distribution.

## Harness Compatibility — REQUIRED (agnostic or explicitly compatible)

> **Non-negotiable:** this tool must be agentic-harness-agnostic or explicitly harness-compatible. It may never
> be built for a single harness — it either works across harnesses by construction (protocol/kernel/OTel/identity
> layers) or ships named adapters with a published compatibility table. agentdrill verifies compatibility with
> per-harness attack packs.

**Compatibility targets — most popular agentic harnesses/ecosystems (ordered by user base; full matrix:
`research/agent-security/ecosystem/00-harness-compatibility.md`):**

| Tier | Harness / Ecosystem | Requirement |
|---|---|---|
| 1 — Coding agents | **Claude Code** · **Cursor** · **GitHub Copilot** (agent mode) · **OpenAI Codex CLI** · **Gemini CLI** | ≥2 Tier-1 at v0.1.0; all 5 by v0.3.0 (or documented lower-layer coverage where closed, e.g. Copilot) |
| 2 — Agent frameworks | **LangChain/LangGraph** · **CrewAI** · **OpenAI Agents SDK** · **AutoGen/AG2** · **LlamaIndex** · **PydanticAI** · **smolagents** | ≥3 framework adapters by v0.3.0 where the tool has an SDK surface (agentwatch, agentdrill, agentcomply) |
| 3 — Protocol/enterprise | Generic **MCP clients** (incl. Claude Desktop) · enterprise platforms (Copilot Studio, Agentforce, Bedrock agents) | MCP-layer tools are harness-agnostic by construction; enterprise platforms via standards, v2.x |

This tool's specific per-tier minimums: see the per-tool compatibility table in
`research/agent-security/ecosystem/00-harness-compatibility.md`. agentinbox is channel-based
(Slack/terminal/CI/mobile) and harness-agnostic: it works for any harness emitting asks, with CI
checkpoints for headless agents.

## 3. Explicit non-requirements

- No approvals-by-ML (a model never answers a gate — that's the anti-requirement).
- No harness-side UI replacement in v1 — we are the shared destination, not each harness's prompt clone.
- No chat-bot decision surface in v0 (too spoofable; the research's injection lesson applies to our own UX).

## 4. Standards it must meet

agentwatch event schema (ask/answer/timeout as first-class events); the agentpolicy decision contract;
escalation timing semantics documented and tested (it's a security property, not a UX preference).

## 5. Fit in the ecosystem

The human half of every ask-gate: agentpolicy asks, agentinbox answers; without it, Wave 0's headline demo
("Replit rule fires") has no ending. Also the highest-touch daily-use tool — the ecosystem's UX beachhead and
the place attachment (and retention) forms.

## 6. Success metrics

- Ask response time p50 (healthy: seconds) and p99 (escalation path health).
- % of asks answered by standing policies over time (convenience growing).
- Approver satisfaction after 2 weeks (the tool fails if humans mute it).

## 7. Open questions

- Timeout default: deny vs. pause-the-session (pause is safer; deny is simpler — needs design-partner
  resolution; PRD 02 asks this too).
- Anti-spoofing for approval channels (especially Slack) — approval links must be unforgeable (it's a security
  boundary, per the ecosystem's own threat model).
