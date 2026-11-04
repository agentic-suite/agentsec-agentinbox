# PRD 14 — Non-Requirements (What This Tool Is Not)

**BLUF:** agentinbox is a **consumer of `ask` decisions and the human's answer** — not a policy engine, not a
harness prompt, not a chat bot, not an ML anything, not a SaaS. Every line below is a hard boundary for v0.1.0
(and mostly forever); several are security properties dressed as product decisions. Where a boundary might
move later, the note says when and under what condition.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Hard non-requirements (security properties)

| # | We do **not** | Why it's a boundary |
|---|---|---|
| **N-1** | **No ML/AI anywhere in the decision path.** No model "assesses" an ask, drafts the decision, or pre-approves. (Drafting *card text* from structured fields is rendering, not modeling — and v0.1.0 does not do even that: templates only.) | The anti-requirement from the consolidated PRD. A gate answered by a model is a gate answered by the attack surface. This is auditable: no ML dependencies in the manifest, no model calls in the decision path (CI-checked). |
| **N-2** | **No chat-bot decision surface.** No "reply APPROVE to the bot", no free-text intents, in v0 — and structured actions are the *only* permanent approval mechanism on chat surfaces. | Free text is spoofable, ambiguous, and unauditable ("yes" — to what, exactly?). The injection lesson applies to our own UX: whatever the attacker can write must be inert. Text *input* has exactly one sanctioned use: the deny/approve **reason** field, escaped and length-capped, human-authored. |
| **N-3** | **No auto-approving links.** A URL cannot answer an ask by being clicked/GET'd. Answers are POSTs carrying a single-use claim + an authenticated principal. | Link-based approval is the forwarded-screenshot hole. A preview-unfurl or a camera-tapped link must do nothing. |
| **N-4** | **No `--force` / `--yes` / `--assume-approved`.** Not on the CLI, not in config, not as an easter egg. | Any flag that manufactures an approval is a backdoor with a friendly name. Break-glass needs are real — they are served by agentpolicy's break-glass (audited elevation), never by the inbox inventing one. |
| **N-5** | **No TTL extension by escalation, retry, or channel.** | The deadline is the security property (D-11). "It was almost approved" is not a state. |
| **N-6** | **No approvals that outlive their action.** Claims expire with the ask; an approved identity is single-use by construction. | Standing approvals are R10 (v1.x) — a *policy*, created and expiring explicitly, never an emergent property of a record. |
| **N-7** | **No unredacted persistence.** Not in the store, not in Slack payloads, not in audit exports, not "just for debugging". | The inbox is the *narrowest* place secrets should ever pass; approving must not become exfiltration (T8). |

## Product-boundary non-requirements

| # | We do **not** | Where it lives instead / when it might move |
|---|---|---|
| **N-8** | **No policy authoring or evaluation.** The inbox renders the clause agentpolicy matched; it never decides, re-decides, or edits policy. | agentpolicy. The card *links* to the clause for one-click reading; tuning feedback (deny reasons) flows out as data, not as edits. |
| **N-9** | **No harness-side UI replacement in v1.** We are the shared destination; the harness prompt stays for its own session-local, unimportant asks. (A harness that routes *its* ask to us via hook is compatible, not replaced.) | Consolidated-PRD boundary. Revisit only if a harness asks us to own its prompt wholesale. |
| **N-10** | **No enforcement.** The inbox records and returns decisions; the enforcer (harness hook, agentgate, agentkeys, agentseatbelt) holds the capability and executes. | The PDP/PEP split (agentpolicy PRD 02). An inbox that enforced would be two products and would inherit every harness's execution surface. |
| **N-11** | **No multi-tenant SaaS, no hosted mode, in v0.1.0.** | Local-first by identity (D-8). A server mode is v0.2.0 *of the same core*; hosted is post-v1.0 and optional. |
| **N-12** | **No SSO/RBAC/SCIM at v0.1.0.** Rosters are config lists; principals are channel identities. | Documented honestly (CUJ-14). Pretending at identity is worse than absence — see [PRD 19](19-harness-compatibility.md) and [PRD 22](22-operations-and-governance.md). |
| **N-13** | **No web dashboard in v0.1.0.** Terminal/TUI + desktop notifications are the surfaces; chat cards are optional adapters. | If field evidence says cards are insufficient for approver workload, a read-only dashboard is the first candidate — *after* the 15-second spine passes. |
| **N-14** | **No workflow-engine ambitions** — no DAGs, no conditions/branches on approvals, no "approval pipelines". | ITSM/SOAR own that world (and it is not what an agent gate needs — [PRD 03 §B/F](03-landscape.md)). Our ladder is a routing list, deliberately dumb and testable. |
| **N-15** | **No notification-platform ambitions** — we are not a pager, not email, not a calendar. We occupy exactly three channels at v0.1.0, then push. | Every added channel multiplies the spoofing surface; a channel must earn its security model first ([PRD 18](18-approval-integrity.md)). |
| **N-16** | **No generic task-management** — no to-dos, no assignments, no follow-up tasks. | An ask is not a ticket; it has one decision and a deadline. Ticket linkage is `correlation_id` + webhooks (v0.1.x), feeding real ITSM. |
| **N-17** | **No standing approvals in v0.1.0** despite the convenience pull. | R10 (v1.x) with mandatory expiry + recertification; shipping them early would re-create the durable-approval permission fatigue this product exists to fix. |
| **N-18** | **No BYO-model "summarize this ask for me" feature.** | Adjacent to N-1: the card is deterministic templates; a summary is a model telling the approver what to think about a security decision. |
| **N-19** | **No rewriting agentpolicy's decision after the fact.** The inbox reports; it cannot upgrade a deny to an ask or ask to an allow. | The decision contract is one-way here: policy decides, inbox transports, enforcer enforces. |
| **N-20** | **No batch/bulk approvals in v0.1.0.** No "approve all", no multi-select, no "approve everything from this agent" — even where a digest shows many asks. | A bulk approval is a scope grant wearing a button's clothes: each approved ask must be an individually confirmed, individually bound decision. The v0.1.x queue UX may *display* grouped asks and pre-fill, but **each ask requires its own confirm action**, and "approve all" as a one-tap action stays a non-goal permanently. |

## Things explicitly confused with this product (disambiguation)

| Confusion | Why it's not us |
|---|---|
| "It's a chat bot" | Chat is one **optional** adapter family. The product's truth is the ask record + claim model + audit; the complete product exists with **no chat platform at all** (CUJ-12) — terminal, desktop notifications, CI, and webhooks carry it. |
| "It's a policy tool" | It has no opinions about what should gate. It consumes the gate decision and serves the human. |
| "It's an approval workflow platform" | It has exactly one workflow: ask → human → answer → record. No forms, no stages, no parallel branches. |
| "It's monitoring/telemetry for approvals" | The event stream is evidence, not analytics-for-its-own-sake; metrics are local-only (N-26). |
| "It will replace the harness's permission prompt" | It is the destination the prompt *escapes to* when the answer isn't at the keyboard (N-9). |
