# PRD 03 — Landscape: What Enterprises Already Solved, and What Agents Still Lack

**BLUF:** Human-approval workflow is a solved problem **in every adjacent category except agent actions**. CI has
required reviewers and wait timers; ITSM has rationale, delegation, and SLA clocks; PAM has time-bound
elevation and approvals; on-call has escalation ladders; SOAR has approval tasks inside playbooks. Agents have a
modal dialog. agentinbox's job is to port the *proven control patterns* — not the enterprise weight — into the
agent decision path, and to be explicit about which patterns v0.1.0 implements versus defers.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## How to read this survey

Each row answers three questions: *what control exists in the enterprise*, *what it is actually protecting
against*, and *what agentinbox adopts*. "Adopted" means it appears as a requirement in
[PRD 05](05-features.md) with a test; "deferred" means it is designed but not claimed at v0.1.0
([PRD 09](09-roadmap.md)).

## A. CI/CD deployment gates — the closest existing model

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Required reviewers** | GitHub Actions environments allow up to six people/teams as required reviewers; **any one** approval releases the job. GitLab protected environments and manual deploy jobs offer the same idea | Prevent an unattended pipeline from deploying to prod | **v0.1.0:** approver allowlist per action class/channel; one valid answer releases. Quorum is deferred |
| **Prevent self-review** | GitHub environments can disallow approving a run you triggered | Separation of duties; prevents "I'll just approve my own deploy" | **v0.1.0:** ingest records `requested_by` (agent owner / session principal); config `self_review = deny` on irreversible classes |
| **Wait timer / cooling-off** | GitHub environments can require a wait before the job proceeds | Defeats impulsive approvals and gives a window to notice an attack | **v0.1.0:** pre-expiry warning only; **minimum-observation window** deferred (v0.1.x) |
| **Environment secrets withheld until approval** | GitHub withholds environment secrets until protection rules pass | The approval gates *capability*, not just a log line | **v0.1.0:** approval token is what agentpolicy resolve accepts; the enforcer holds the capability. No secret is ever in the card |
| **Bypass is explicit and auditable** | GitHub lets admins bypass protection rules unless disabled; bypass is visible | Emergency access must exist but never be invisible | **v0.1.0:** `--force` is not supported; break-glass is deferred and designed as an audited, time-boxed elevation (v0.2.0) |
| **Deployment branch/tag policy** | GitHub environments restrict which refs may deploy | Limits reachable states | Analogue: action-class scope in config (which tools/verbs/classes may even ask vs. hard-deny) |

**Gap agentinbox closes:** CI gates are per-vendor and only understand deployments. An agent action is not a
deployment, has no commit, and may happen mid-session. agentinbox provides the same controls around the
**action identity**, independent of CI vendor.

## B. ITSM / change management — the audit and process model

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Approval record with state** | ServiceNow change/approval records; Jira Service Management request approvals | One durable object that is the source of truth for "who approved what, when" | **v0.1.0:** the ask record *is* that object (D-4 in [PRD 11](11-decisions.md)); every transition is an event |
| **Requested / approved / rejected / expired states** | ITSM approval state machines | Ambiguity is the enemy of audit | **v0.1.0:** identical five terminal states + delivery sub-states ([PRD 15](15-data-model.md)) |
| **Justification on decision** | Change approvals require a reason, especially on rejection | Forces accountability; feeds policy tuning | **v0.1.0:** rejection reason required for irreversible classes; approval reason optional but recorded |
| **Delegation and out-of-office** | ITSM/IdP delegate approver rights for a window | The named approver is on vacation; work must not stall | **Deferred (v0.1.x):** requires an identity model; v0.1.0 uses explicit channel rosters |
| **SLA clocks and business hours** | ITSM SLA engines; on-call schedules | A 4-hour approval at 2 a.m. is not a 4-hour approval | **Deferred (v0.1.x):** v0.1.0 uses wall-clock TTL per action class; business-calendar TTL is a named gap |
| **Change calendar / freeze windows** | ITSM change schedules | "Don't deploy during freeze" is a policy condition | agentpolicy owns the freeze decision (its R33); agentinbox merely displays it and gates |
| **Ticket linkage** | Every approval is linked to a change/incident | Evidence joins to the business record | **v0.1.0:** `correlation_id` + open `external_ref` field; native ServiceNow/Jira links deferred |

**Gap agentinbox closes:** ITSM is ticket-shaped and minutes-to-days. Agent gates are **seconds-to-minutes** and
must not require creating a ticket to unblock a coding session.

## C. On-call and incident response — the escalation model

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Escalation policy with levels** | PagerDuty/Opsgenie escalation policies: notify level 1, escalate after N minutes if unacknowledged, then level 2… | A page nobody acknowledges must reach someone else | **v0.1.0:** ordered ladder with per-tier delay and re-notification; escalation events; "answered" cancels the ladder |
| **Acknowledge vs. resolve** | Incident tools distinguish "I saw it" from "it is fixed" | Seeing is not deciding | **v0.1.0:** `warned`/`escalated` are not decisions; only approve/deny resolve |
| **Schedules and rotations** | On-call schedules, overrides | Routing at 3 a.m. requires knowing who is on call | **Deferred (v0.1.x):** native schedule sync (PagerDuty/Opsgenie API) and calendar-aware routing |
| **Incident linkage** | Page → incident → timeline | Post-incident review needs one timeline | **v0.1.0:** ask events carry `session_id`/`correlation_id`; incident link deferred |
| **Quiet hours / suppression** | On-call tools suppress non-urgent pages | Protect the human from noise | **v0.1.0:** flood coalescing + severity routing; quiet hours deferred |

**Gap agentinbox closes:** paging tells a human "something is wrong". It does not ask "may this specific action
proceed, with these arguments?" — and it cannot answer for the agent.

## D. PAM / identity governance — the identity and time-bound model

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Time-bound elevation** | Azure PIM eligible assignments activated for a window; Okta access requests with expiry | Standing privilege is the root of most breaches | **v0.1.0:** every ask is time-bound (TTL = deny); **standing approvals** are PRD R10 (v1.x) with mandatory expiry |
| **Justification + approval before activation** | PIM activation can require approval, MFA, and a ticket reference | Evidence and friction proportional to risk | **v0.1.0:** context card includes requested scope; approval binds to the exact action identity |
| **Approver separation** | Requester cannot approve own elevation | Separation of duties | **v0.1.0:** self-review config; identity-bound approver |
| **Delegation with expiry** | PIM/IGA delegation windows | Coverage without permanent privilege | **Deferred (v0.1.x)** |
| **Access reviews / recertification** | IGA campaigns | Standing grants decay | **Deferred (v0.2.0+):** standing approvals need recertification by design |
| **Phishing-resistant step-up** | WebAuthn/passkeys; NIST SP 800-63B authenticator assurance | A stolen session must not approve a destructive action | **v0.1.0:** channel authentication + unforgeable claim; **step-up re-auth deferred** (v0.1.x) |

**Gap agentinbox closes:** PAM models *human access to systems*. agentinbox models **agent action approval**,
where the "principal" is a workload and the approver is authorizing a one-shot act, not a session.

## E. Chat and collaboration surfaces — the delivery model

> **agentinbox's stance:** chat platforms are **optional adapters**, not the product. The v0.1.0 surface set
> (terminal, desktop notifications, CI, webhook) needs no chat platform at all; Matrix is the second
> interactive surface because it is the **open** protocol; Slack/Teams adapters serve teams that already run
> them. The adoption column below is what we take from each chat capability, when configured
> ([PRD 16 §A.2](16-channel-and-harness-adapters.md)).

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Signed interactive callbacks** | Slack signs requests (`X-Slack-Signature`, HMAC-SHA256, timestamp window); Teams/Power Automate approvals use their own callback auth | Prevent forged approvals | **v0.1.0:** verify Slack signature + timestamp before parsing; reject unsigned |
| **Structured cards, not free text** | Block Kit / Adaptive Cards buttons and inputs | Structured decisions are auditable and unambiguous | **v0.1.0:** Block Kit card with explicit Approve/Deny actions; free-text messages never approve |
| **Mobile by default** | Slack/Teams apps | The approver is often away from the desk | **v0.1.0:** desktop notifications + signed webhook recipes (ntfy/Pushover) cover the away-from-desk case with **no chat platform required**; Matrix mobile is the v0.1.x path; native push is R8 (v1.x) |
| **Channel-wide vs. named approvers** | Enterprise chat apps support both | Named approvers are stronger; channel-wide is convenient | **v0.1.0:** named approver roster by default; channel-wide requires explicit config and is audited with the channel id |
| **Link previews / forwarded links** | Chat clients unfurl and forward | A forwarded approval link is a classic spoof | **v0.1.0:** links never auto-approve (POST confirm), tokens are one-time and bound; action fingerprint shown on the card |
| **Chat as decision surface (free text)** | Bots that accept "yes" | Convenient | **Rejected by design** in v0 ([PRD 14](14-non-goals.md)) |

**Gap agentinbox closes:** chat is where humans are, but chat was never an authorization protocol. agentinbox
keeps chat as a **rendering and transport** layer with an authorization layer underneath.

## F. Security automation / SOAR — the playbook model

| Capability | Where it comes from | Why it exists | agentinbox adoption |
|---|---|---|---|
| **Approval task in a playbook** | SOAR platforms (Splunk SOAR, Tines, Torq) pause a workflow for a human task | Automations need a human checkpoint before destructive steps | **v0.1.0:** `agentinbox gate` is exactly that checkpoint, usable from any pipeline/playbook |
| **Evidence attached to the task** | SOAR tasks carry artifacts/observables | The approver decides with evidence | **v0.1.0:** decision card carries action, clause, blast radius, session tail, redaction receipt |
| **Case/ticket creation on approval** | SOAR creates cases for follow-up | Not every approval should be silent | **Deferred (v0.1.x):** webhook on resolve enables ticket creation |
| **Playbook-level retries/timeouts** | SOAR has step timeouts | A stuck playbook must fail predictably | **v0.1.0:** TTL=deny + exit code `3`; bounded retries for delivery, not for decisions |

## G. Protocol and framework surfaces — where agents are built

| Surface | What it provides today | What it lacks for approval | agentinbox's role |
|---|---|---|---|
| **MCP elicitation** (2025-06-18) | `elicitation/create` with `accept`/`decline`/`cancel`, JSON-schema-constrained input, client controls | No durable ask, no identity binding, no audit, no escalation, no TTL semantics; spec says clients SHOULD rate-limit and clearly identify the server | **Bridge (v0.1.0 design):** MCP elicitation can relay the ask presentation, but the authoritative decision + audit live in agentinbox |
| **OAuth CIBA** (OpenID CIBA Core) | Decoupled authentication: a client initiates, the user approves on another device | Authenticates a *login*, not an action; no policy/context/audit for agent actions | **Pattern source:** decoupled approval + explicit binding; agentinbox is CIBA-shaped but action-scoped |
| **LangGraph interrupts** | Graph pauses at a node; a checkpointer resumes with human input | No standard cross-harness transport, identity, or audit | **Adapter:** interrupt payload → ask; resume ← resolve ([PRD 19](19-harness-compatibility.md)) |
| **OpenAI Agents SDK approvals** | Tool-approval interruptions (approve/reject before a tool runs) | In-process only; no remote approver, escalation, or event trail | **Adapter:** interruption → ask; continue/stop ← resolve |
| **CrewAI `human_input` / AutoGen human-in-the-loop** | Agent/task pauses for console input | Console-bound, single-session, unaudited | **Adapter:** same contract, non-blocking |
| **Temporal / durable workflows** | Durable timers and signals; a workflow can wait days | No approval semantics, identity, or evidence | **Pattern source:** agentinbox's scheduler is a small durable-timer engine; Temporal users can bridge via signal |
| **WebAuthn / passkeys** | Phishing-resistant user verification | Not an approval protocol by itself | **Step-up path (later):** re-authenticate the approver for critical classes |

## H. Where the market leaves a gap (the whitespace agentinbox occupies)

| Dimension | Enterprise workflow products | Harness prompts | **agentinbox** |
|---|---|---|---|
| Unit of approval | Ticket / change / access grant | One tool call in one session | **Action identity** (`tool`+`action`+args) across sessions |
| Time scale | Hours–days | Seconds (blocking) | **Seconds–minutes**, with TTL and escalation |
| Reach | Web console, email, chat | One terminal | **Terminal, desktop, CI, webhook** (v0.1.0); Matrix/chat + push later |
| Headless agents | Possible but heavy | **Not supported** | **First-class** (CI checkpoint) |
| Identity binding | Strong (SSO, named approvers) | Weak (local session) | **Claim token + authenticated principal** |
| Audit | Strong, but in a separate system | None / harness-local | **agentwatch schema + hash-chained local log** |
| Local-first / air-gap | Rare | Yes | **Yes** |
| Attack surface of the ask itself | Considered in mature products | Not considered | **Treats agent text as untrusted; no chat-bot decisions** |
| Cost to first approval | Procurement + integration | Zero | **`pip install`, one config file** |

## I. Honest gaps at v0.1.0 (what we do **not** close yet)

| Gap | Enterprise precedent | Status | Why deferred |
|---|---|---|---|
| On-call schedule sync | PagerDuty/Opsgenie | v0.1.x | Needs an external API + credential; the ladder works without it |
| SSO / SCIM / RBAC | Every enterprise product | v2.x | v0.1.0 is single-principal local-first; a fake RBAC would be worse than none |
| Quorum / dual control | ITSM, PAM | v0.2.0 | agentpolicy R41 defines the decision; inbox needs multi-principal support first |
| Delegation / OOO | ITSM/IGA | v0.1.x | Requires an identity directory |
| Business-hours SLA | ITSM | v0.1.x | Wall-clock TTL is honest and testable; calendars are a scheduling product |
| WORM / legal hold | Compliance archives | v0.2.0 | Hash-chained append-only log is the v0.1.0 floor |
| Mobile push | PagerDuty, Slack native | v1.x (R8) | Desktop notifications + webhook recipes cover the away-from-desk case at v0.1.0; Matrix (v0.1.x) adds phone taps |
| Step-up / phishing-resistant re-auth | PAM, WebAuthn | v0.1.x | Design fixed in [PRD 18](18-approval-integrity.md); implementation follows |
| Ticket/incident linkage | ITSM/SOAR | v0.1.x | `correlation_id` + webhook is the seam |

The full gap-closure matrix, with requirement IDs and versions, is [PRD 10](10-feature-parity.md).
