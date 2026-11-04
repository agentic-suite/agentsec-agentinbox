# PRD 10 — Feature Parity & Gap-Closure Matrix (OSS and Commercial)

**BLUF:** Nothing in OSS or commercial today covers the **agent-action approval lifecycle** end-to-end. Harness
prompts own the moment but not the reach; HITL SDKs own the pause but not the routing, identity, or audit;
chat bots own the reach but not the authorization semantics; enterprise workflow products own the governance
but not the agent or the local machine. This matrix is the honest inventory: for each control, who has it, what
agentinbox does at v0.1.0, and when the gap closes.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## How to read this

- **Existing coverage**: ●●● full · ●●○ partial · ●○○ minimal · ○○○ absent.
- **Competitors/tools named** are the best current representative, not exhaustive.
- The "closes" column is the version where agentinbox reaches the stated bar. Where we never will, it says so
  and why.

## A. Harness-native approvals (what the coding agents themselves have)

| Capability | Claude Code | Cursor | Codex CLI / Copilot agent mode | Gemini CLI | agentinbox v0.1.0 |
|---|---|---|---|---|---|
| Prompt before risky tool call | ●●● (permission modes: `default`, `acceptEdits`, `plan`, `bypassPermissions`; `allow`/`ask`/`deny` rules) | ●●● (permissions prompts + auto-allow) | ●●○ (approval prompts, sandbox trust) | ●●○ (approval/YOLO mode) | — (not our job; we are the destination) |
| Hook to externalize the decision | ●●● `PreToolUse` hook can **allow/deny/ask** externally | ●○○ (limited config; no headless/evidence hook on the field-test box) | ●○○ | ●○○ | ●●● we are that external consumer; hooks call us |
| Remote answer | ○○○ | ○○○ | ○○○ | ○○○ | ●●● second-surface (desktop/webhook; Matrix/chat optional) + CI |
| TTL on pending approval | ○○○ (blocks session) | ○○○ | ○○○ | ○○○ | ●●● per-class TTL, expiry = deny |
| Escalation | ○○○ | ○○○ | ○○○ | ○○○ | ●●● tier ladder |
| Audit record of approval | ●○○ (session log only) | ●○○ | ●○○ | ●○○ | ●●● hash-chained + agentwatch |
| Headless/CI approval | ○○○ | ○○○ | ○○○ | ○○○ | ●●● `gate` + exit codes |
| Anti-spoofed approval | ○○○ (local trust) | ○○○ | ○○○ | ○○○ | ●●● claims + signed callbacks |

**Take:** harness prompts are strong at the moment of interruption and weak at everything after it. They also
*force* the gate into one session — our contract lets a `PreToolUse` hook say `ask` and hand the decision to
the inbox.

## B. HITL SDKs / frameworks (LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, PydanticAI, smolagents, kagent)

| Capability | LangGraph `interrupt()` | OpenAI Agents SDK interruptions | CrewAI `human_input` | AutoGen/AG2 `human_input_mode` | kagent HITL | agentinbox v0.1.0 role |
|---|---|---|---|---|---|---|
| Durable pause/resume with checkpointer | ●●● | ●●● (resumable RunState) | ●○○ (blocks console) | ●○○ (console I/O modes) | ●●● (K8s-native pending call) | — (the framework's job) |
| Declares *which* calls need approval | ●●○ (per-tool/interrupt authoring) | ●●● (`needs_approval` on tools) | ●●○ (per-task flag) | ●●○ | ●●○ | — (agentpolicy's job) |
| Approval reaches a human off-box | ○○○ — your app builds it | ○○○ — "your approval surface" per docs | ○○○ — console input | ○○○ — console input | ●●○ (app/webhook must render) | **This is the gap we fill** |
| Answerer identity recorded | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ | ●●● authenticated principal |
| TTL / safe default on no-answer | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ | ●●● timeout=deny |
| Escalation, flood control, audit | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ | ●●● |
| Restart survives a pending approval | ●●○ (with checkpointer — approval state itself is your problem) | ●●○ | ○○○ | ○○○ | ●●○ | ●●● durable ask; resume-by-id is idempotent |

**Take:** frameworks standardized *pausing*. None standardized *the human side*. Every framework's docs say
some version of "the approval surface is left to the developer" — that developer is our integrator, and the
interrupt → ask / resume → resolve mapping is a thin adapter ([PRD 16](16-channel-and-harness-adapters.md)).

## C. OSS HITL products (HumanLayer-class SDKs, Pushary, approval utilities)

| Capability | HumanLayer (classic SDK, now deprecated in favor of their IDE) | Pushary | Orako / similar | agentinbox v0.1.0 |
|---|---|---|---|---|
| SDK to route approvals to a human | ●●● (was the category creator: tool-call → human approval, contact channels) | ●●● (Slack/Teams phone approvals for agents) | ●●● (Slack/Teams approvals) | ●●● (contract + adapters) |
| Channels | Slack, email, web | Slack/Teams + mobile | Slack/Teams | Terminal, desktop, CI, webhook (v0.1.0); Matrix (v0.1.x); push (v1.x); chat platforms optional |
| Local-first, no cloud | ○○○ (hosted control plane) | ○○○ (SaaS) | ○○○ (SaaS) | **●●●** |
| Open, stable contract for any harness | ●●○ (SDK-shaped) | ●○○ | ●○○ | **●●● contract-first, SDK-agnostic** |
| Identity-bound, single-use approvals | ●●○ | ●●○ | ●●○ | ●●● claim model |
| Timeout = deny + escalation | ●○○ | ●●○ | ●○○ | ●●● |
| Audit as evidence (chain + schema) | ○○○ | ○○○ | ○○○ | ●●● |
| Flood control | ○○○ | ○○○ | ○○○ | ●●● |
| Ecosystem integration (policy + events) | ○○○ | ○○○ | ○○○ | **●●●** agentpolicy ask contract + agentwatch schema |

**Take:** the OSS HITL category exists but is **SaaS-shaped and SDK-shaped**. agentinbox differentiates on:
local-first, contract-first (any harness, not any SDK), evidence-grade audit, and being the *consumer of the
policy engine's own decision* rather than a parallel permission world.

## D. Commercial / enterprise approval products

| Capability | GitHub environments | ServiceNow/Jira SM | PagerDuty/Opsgenie | Okta Access Requests / Azure PIM | Slack-native workflow apps (Approveit-class) | SOAR | agentinbox v0.1.0 → closes |
|---|---|---|---|---|---|---|---|
| Required reviewers | ●●● (≤6, any-one) | ●●● | ●●○ (ack, not approve) | ●●● | ●●○ | ●●○ | ●●● roster, any-one v0.1.0; **quorum v0.2.0** |
| Prevent self-review | ●●● | ●●○ | ○○○ | ●●● | ●○○ | ○○○ | ●●● v0.1.0 |
| Wait timer | ●●● | ●●● (SLA) | ●●○ | ●●○ | ●○○ | ●●○ | ●●● TTL v0.1.0; **min-observation window v0.1.x** |
| Escalation ladder | ○○○ | ●●○ | ●●● | ●●○ | ●○○ | ●●○ | ●●● v0.1.0; **schedule sync v0.1.x** |
| Time-bound grants | ●○○ | ●●○ | ○○○ | ●●● (PIM activation windows) | ●○○ | ○○○ | ●●● per-ask TTL v0.1.0; **standing+expiry v1.x** |
| Justification required | ○○○ | ●●● | ○○○ | ●●● | ●○○ | ●●○ | ●●● deny-reason required on irreversible v0.1.0 |
| Delegation / OOO | ○○○ | ●●● | ●●○ | ●●● | ●○○ | ●●○ | v0.2.0 |
| SSO / RBAC | ●●● | ●●● | ●●● | ●●● | ●●● | ●●● | **v0.2.0 server mode** (documented honestly at v0.1.0) |
| Tamper-evident evidence | ●●○ (audit API) | ●●● | ●●○ | ●●● | ●○○ | ●●○ | ●●● hash chain v0.1.0; **WORM/notarized v0.2.0** |
| API-triggerable per action | ●●○ (per environment) | ●●● (per change) | ●●○ (per incident) | ●●● (per request) | ●●○ | ●●● (per task) | ●●● per ask, contract-first v0.1.0 |
| Agent action as first-class unit | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ | **●●● — the category definition** |

**Take:** every enterprise control has a proven pattern we port; none of them understand an *agent tool call*
as the thing being approved. Our parity target is the **pattern**, not the product.

## E. Protocols & standards (what we bind to rather than reinvent)

| Standard | What it gives | agentinbox use |
|---|---|---|
| **MCP elicitation** (2025-06-18) | server→client structured user input, `accept`/`decline`/`cancel`, rate-limit guidance | Presentation bridge only; authoritative lifecycle + audit ours (PRD 03 §G) |
| **OAuth CIBA (RFC 9200)** | Decoupled, cross-device authorization pattern (binding code, polling/claim) | The architecture pattern we mirror, action-scoped; claim token ≈ binding code |
| **AuthZEN (Authorization API 1.0)** | PDP↔PEP JSON decision shape | agentpolicy↔inbox resolve shape stays aligned with it ([PRD 20](20-standards-and-claims.md)) |
| **agentwatch security-event schema** | The ecosystem's event vocabulary | Every ask/answer/timeout/escalation/flood event (R5) |
| **OpenTelemetry GenAI conventions / W3C traceparent** | Correlation across the harness→policy→inbox chain | `session_id` + traceparent on the card and audit for cross-tool joins |
| **Agent2Agent (A2A) / CHAP-class research protocols** | Emerging inter-agent task and human-coordination protocols | Watchlist; bridge when stable (v0.3.0+) — not a dependency at v0.1.0 |

## F. The honest "we are behind on" list (v0.1.0)

| Where we trail | Who leads | Our plan |
|---|---|---|
| Hosted/managed, zero-ops | SaaS HITL products | Not a v0.x goal — local-first is the point; a hosted mode can come after v1.0 without changing the core |
| Rich web dashboard | everyone | TUI + Slack cards at v0.1.0; dashboard only if field test proves cards insufficient |
| Workflow/ticket product depth (SLAs, calendars, forms) | ITSM | v0.1.x calendar TTLs; the rest via `correlation_id` + webhooks into real ITSM |
| SSO/RBAC/SCIM | every enterprise product | v0.2.0 server mode; explicitly documented as absent at v0.1.0 |
| Framework SDK polish per framework | the frameworks' own HITL | thin adapters over one contract — never N bespoke approval logics |
