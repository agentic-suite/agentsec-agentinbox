# PRD 04 — Users, User Stories & Critical User Journeys

**BLUF:** agentinbox has four primary humans — the **agent owner** who wants safe autonomy, the **approver**
who is on the hook, the **on-call responder** who gets the 3 a.m. ask, and the **auditor** who must reconstruct
what happened — plus the **CI/release engineer** who needs a headless gate. The acceptance spine is one
measurable moment: *an approver with zero context makes the correct call in under 15 seconds.* Every CUJ below
either contributes to that moment or to the evidence that it happened.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## 1. Personas

| ID | Persona | Context | Primary need | What failure looks like to them |
|---|---|---|---|---|
| **P1** | **Maya — agent platform engineer** | Runs coding/research agents for a small team; owns the policy and the agent's credentials | Let agents do real work while irreversible actions stop and ask *someone who can actually answer* | She becomes the permanent bottleneck; or an agent deletes prod while she is in a meeting |
| **P2** | **Ravi — security engineer / approver** | Reviews risky actions, carries on-call, owns the audit story | A decision card that answers *what/why/blast radius* fast, and an evidence trail he can defend | A wall of noisy asks → he approves blindly; or he cannot prove who approved what |
| **P4** | **Sam — solo developer / indie** | One machine, no security team, ships from CI | Five-minute setup; safe default; no cloud account | The gate nags once, he disables it, and ships an irreversible action unguarded |
| **S1** | **Dana — on-call SRE / incident commander** | Gets paged at 3 a.m.; phone in hand | The ask reaches her with enough context to decide in one glance, or it is denied safely | A gate that silently waits, or a page that says "agent wants to do something" |
| **S2** | **Kenji — release / CI engineer** | Owns pipelines; headless agents run unattended | A pipeline checkpoint that halts on an ask and resumes/fails deterministically | A pipeline that hangs forever, or proceeds because nobody was watching |
| **S3** | **Noor — compliance / audit reviewer** | Needs evidence for SOC 2 / EU AI Act Art. 14 / internal review | Reconstruct every gate for a session: who, what, when, outcome | A log line that says "approved" with no approver, action, or binding |
| **S4** | **Lena — enterprise platform admin** | Runs SSO, SCIM, retention, multi-team policy | A deployable service mode with identity, tenancy, and export | A toy that cannot be procured or audited (v0.1.0 is explicit about this) |

## 2. User stories (v0.1.0)

### Agent owner (Maya)

| ID | Story | Acceptance |
|---|---|---|
| **US-01** | As an agent owner, I want my agent's `ask` to reach a human with the action, policy clause, and blast radius, so the human does not need to interrogate me | Card contains all four context blocks; zero-context test passes |
| **US-02** | As an agent owner, I want to configure which action classes require which TTL and which approvers, so low-risk gates do not wake the wrong person | Config resolves per class; `doctor` explains the effective policy |
| **US-03** | As an agent owner, I want an unanswered ask to deny safely and tell the agent how to rescope, so a stalled gate does not become a hang or a bypass | Expiry → `deny` + `human_gate_timeout` + rescope hint; no allow path |
| **US-04** | As an agent owner, I want duplicate asks for the same action to coalesce, so a retry loop does not spam the approver | Second ingest returns the same ask id; one notification |
| **US-05** | As an agent owner, I want my agent's arguments redacted before they leave the machine, so approving does not leak a secret into any channel payload | Redaction receipt on every card; no raw secret in store/channel/audit |

### Approver (Ravi)

| ID | Story | Acceptance |
|---|---|---|
| **US-06** | As an approver, I want to approve or deny from the terminal in one keystroke pair, so a gate costs seconds | Approve/deny without retyping the action; identity recorded |
| **US-07** | As an approver, I want the same ask on a second surface with the same context (desktop notification → terminal; Matrix/chat when configured), so I can decide away from my desk | Second-surface card parity with terminal; identical decision recorded |
| **US-08** | As an approver, I want a pre-expiry warning with the remaining time and what expires, so I am not surprised by a silent deny | Warning at `T-warn`; card shows countdown |
| **US-09** | As an approver, I want an approval to apply only to the exact action I saw, so a replayed or edited request cannot ride my click | `action_identity` mismatch → deny; single-use token |
| **US-10** | As an approver, I want to reject with a reason, so the agent (and the policy owner) learns why | Deny reason stored and returned; required for irreversible classes |
| **US-11** | As an approver, I want to see that a request came from an untrusted tool/agent, so I do not follow instructions embedded in the ask | Untrusted-source label + escaped content; injection scenario passes |
| **US-12** | As an approver, I want a flood to become one digest, not a hundred pings, so I keep trusting the inbox | Flood → auto-deny + one event; notification coalesced |

### On-call responder (Dana)

| ID | Story | Acceptance |
|---|---|---|
| **US-13** | As on-call, I want unacknowledged asks to escalate to my tier after the configured delay, so a sleeping approver does not block the action forever | Ladder fires; event recorded; TTL unchanged |
| **US-14** | As on-call, I want the escalation to say who had it before me and for how long, so I do not duplicate work | Card carries escalation history |
| **US-15** | As on-call, I want the action to be denied if nobody answers, so a 3 a.m. request cannot execute by inaction | Expiry → deny; no "assume yes" path |

### CI / release engineer (Kenji)

| ID | Story | Acceptance |
|---|---|---|
| **US-16** | As a CI engineer, I want a headless job to halt on an ask and fail deterministically on deny/timeout, so the pipeline has a real gate | Exit codes `0/2/3/4/5` honored; job log shows ask id |
| **US-17** | As a CI engineer, I want the ask answerable from any interactive surface without opening the pipeline (terminal; Matrix/chat when configured), so an on-call approver is not blocked by CI UI | An answer from any interactive channel resolves the waiting `gate` |
| **US-18** | As a CI engineer, I want the gate to fail closed if the inbox is unreachable, so an outage is not an approval | Unreachable → exit `4`, never `0` |

### Auditor (Noor)

| ID | Story | Acceptance |
|---|---|---|
| **US-19** | As an auditor, I want every ask/answer/timeout/escalation/flood in one record, so I can reconstruct a session | Timeline export by `session_id`; every transition has a principal + timestamp |
| **US-20** | As an auditor, I want the record to be tamper-evident, so I can trust it | `seq` + `prev_hash` chain verifies; tampering detected |
| **US-21** | As an auditor, I want to see the policy clause and reason code, so the decision is explainable without the agent's transcript | Card + audit carry `reason_code`, matched clause, policy version |
| **US-22** | As an auditor, I want to know which channel answered and which claims were rejected, so spoofing attempts are visible | Channel, adapter, claim id, rejected-attempt events |

### Integrator (any agentic system)

| ID | Story | Acceptance |
|---|---|---|
| **US-23** | As an integrator, I want a stable ask JSON contract + HTTP + CLI, so I can wire any harness without a fork | Contract doc + conformance fixture; same lifecycle across producers |
| **US-24** | As an integrator, I want idempotent ingest keyed by action identity, so retries are safe | Duplicate ingest returns the same ask |
| **US-25** | As a LangGraph/Agents-SDK developer, I want the interrupt to map to an ask and the resume to a resolve, so my graph does not need custom approval code | Adapter example passes end-to-end |
| **US-26** | As an MCP client author, I want to surface the request without pretending elicitation is approval, so my users get real oversight | Bridge labels it as an approval; audit lives in agentinbox |

## 3. Critical User Journeys

Each CUJ lists the **trigger**, the **happy path**, the **unhappy paths that must be designed**, the
**requirements exercised**, and the **acceptance signal**. The scenario-level detail (fixtures, exact expected
events) is [PRD 17](17-scenarios.md).

### CUJ-1 — First gate in five minutes (P4 Sam)

- **Trigger:** Sam installs agentinbox and runs an agent whose action agentpolicy marks `ask`.
- **Path:** `pip install` → `agentinbox init` writes a minimal config (terminal channel, 5-minute TTL) →
  agent emits an ask → terminal card appears with action, reason, blast radius, TTL → Sam presses `a` →
  agentpolicy resolves allow → audit record written.
- **Unhappy:** no TTY (must not prompt; return exit `5`/structured JSON) · config missing (fail with actionable
  error, never a silent allow) · agent sends malformed ask (reject with a diagnostic the developer can fix).
- **Requirements:** R1, R2, E1, E9. **Acceptance:** median time from install to first recorded approval
  **< 5 minutes** in the field test; no cloud dependency.

### CUJ-2 — Zero-context correct call in 15 seconds (P2 Ravi) — **the spine**

- **Trigger:** Ravi receives an ask he has never seen, about an agent he does not own.
- **Path:** card shows (1) *what will happen* in one sentence, (2) *why the gate fired* (matched clause +
  reason code), (3) *blast radius* (resource/environment/data class, counts, reversibility), (4) *session so
  far* (last N actions, flags), (5) *alternatives* (deny + rescope hint) → approves or denies in one action.
- **Unhappy:** context missing → the card **must say "unknown"** rather than imply safety · context too long →
  show the first screen plus a detail link; never hide the decision-relevant line · ambiguous reversibility →
  label as "unknown/irreversible by policy class", never guess.
- **Requirements:** R1, E4, E5. **Acceptance:** ≥ 9/10 zero-context approvers make the *pre-registered correct
  call* in **< 15 s** on the scenario corpus (user test, [PRD 07](07-success-metrics.md)).

### CUJ-3 — Approve a production database drop from a second surface (P1 Maya → P2 Ravi)

- **Trigger:** An agent proposes `delete_table(prod, customers)` during a code freeze.
- **Path:** the card appears on Ravi's **second surface** — at v0.1.0 a desktop notification that opens the
  answer in his terminal (`agentinbox answer` / `inbox`); from v0.1.x a Matrix room/DM (or a configured
  Slack/Teams adapter) with the named approver roster → Ravi answers **Deny** with reason "freeze window" →
  agent receives deny with reason + rescope hint → session continues without the action.
- **Variant:** Ravi answers **Approve** → token verified, principal matched, first-answer-wins → allow bound
  to the exact `(tool, action, args)`.
- **Unhappy:** (chat adapters, when configured) Ravi forwards the message to a junior — the forwarded button
  *does not* carry Ravi's identity; junior is not in the roster → rejected, logged. · Two approvers answer
  simultaneously → first wins, second told "already approved by Ravi at 14:03:12"; no double execution. ·
  Ravi answers 4 min after expiry → "expired; action denied", logged as `late-answer`.
- **Requirements:** R1, R2, R6, E3, E7. **Acceptance:** identical decision recorded from the second surface
  and terminal (parity test); forwarded/replayed/late answers change nothing; **the journey works with no
  chat platform installed**.

### CUJ-4 — Timeout with a rescope, not a hang (P4 Sam / P1 Maya)

- **Trigger:** nobody answers within the class TTL (default 5 min for `irreversible`, 15 min for `external-send`).
- **Path:** warning at `T-60s` → expiry → ask `expired` → agent receives `deny` + `human_gate_timeout` +
  `retryable=false` + `rescope_hint` (e.g., "narrow to table `staging.customers` or request a standing
  approval") → agent reports the rescope to its user.
- **Unhappy:** scheduler restarts mid-wait → expiry still fires on time on restart, once, and the audit shows a
  `scheduler-recovered` marker · clock jumps backwards → TTL does not extend.
- **Requirements:** R3, E2, E8. **Acceptance:** expiry demonstrated, logged, and the agent receives an outcome
  it can act on; no path from timeout to allow.

### CUJ-5 — 3 a.m. escalation to on-call (S1 Dana)

- **Trigger:** an ask targets production at 03:04; the primary approver is asleep.
- **Path:** tier 1 notified (desktop notification + terminal; Matrix DM/room once configured, or a webhook
  push recipe to her phone) → no answer at `T+5m` → escalation event → tier 2 (on-call
  roster in config) notified with the same card + "tier 1 did not answer" → Dana answers from wherever she
  is — at v0.1.0 the desktop/terminal path, at v0.1.x the phone via Matrix.
- **Unhappy:** tier 2 also silent → tier 3 channel → TTL expiry → deny · escalation cannot extend the TTL —
  the last tier knows exactly how long is left.
- **Requirements:** R4, E8. **Acceptance:** drill shows the configured tier receives the ask within the
  configured window; events reconstruct the ladder; expiry still denies.
- **Honest v0.1.0 limit:** the ladder is **config-driven**; native PagerDuty/Opsgenie schedule lookup is v0.1.x.
  The drill therefore names explicit recipients, not "whoever is on call".

### CUJ-6 — Flood neutralized (P2 Ravi)

- **Trigger:** a looping or malicious agent emits 200 asks in 30 seconds.
- **Path:** per-agent/environment token bucket trips → new asks auto-denied with `ask_flood_throttled` →
  **one** `ask-flood` event with counts and the offending agent/session → **one** digest notification to the
  approver ("agent X was throttled, N asks denied; first ask shown") → existing pre-flood asks remain
  answerable.
- **Unhappy:** legitimate burst (e.g., a migration touching 20 tables) → dedupe by identity + bounded
  batching must NOT be classified as an attack; config per class; the digest explains why.
- **Requirements:** R7, E6, E7. **Acceptance:** flood pack produces N auto-denies, 1 event, 1 notification;
  a normal burst stays below the threshold and is fully answerable.

### CUJ-7 — CI pipeline halts on an ask (S2 Kenji)

- **Trigger:** a headless agent in CI wants to push a release tag / call a prod API.
- **Path:** pipeline runs `agentinbox gate --ask "$ASK_ID" --wait --timeout 600` → job blocks, log prints the
  ask id + card summary + a signed deep link → approver answers from any interactive surface (terminal, or
  Matrix/chat when configured) → exit `0` → job continues; exit `3`
  → job fails with "gate expired (deny)".
- **Unhappy:** inbox unreachable → exit `4` (fail closed) · pipeline cancelled → ask is **cancelled**, not left
  pending, and the audit says so · job retried → same ask id (idempotent), no second notification.
- **Requirements:** R6, E9. **Acceptance:** the irreversible step never runs on exit `2/3/4`; the pipeline log
  and the audit share the ask id.

### CUJ-8 — Deny with a reason that teaches (P1 Maya / P2 Ravi)

- **Trigger:** Ravi denies an external send because the recipient domain is not allowlisted.
- **Path:** reason (required for irreversible/external classes) → agent receives deny + reason + rescope hint →
  Maya sees the deny reason in the session summary and narrows the policy.
- **Unhappy:** reason is free text from the approver (trusted-ish) — it must still be escaped and length-capped;
  never executed as an instruction by the agent. The agent is told this is **human input, not policy**.
- **Requirements:** R1, R5, E4. **Acceptance:** deny reason visible to producer; escaped; not treated as policy.

### CUJ-9 — Same ask, two channels, one truth (P2 Ravi)

- **Trigger:** Ravi has the terminal open and a second surface live (a desktop notification arrives, and
  later Matrix/chat on his phone); both show the ask.
- **Path:** he answers on the second surface; the terminal card updates to "resolved (second surface,
  14:03:12 by Ravi)" within the poll interval; the agent resolves once.
- **Unhappy:** he answers in both → second is a no-op `late-answer`; both surfaces say who won · channel
  delivery failed on one → the other still works; delivery failure is an event, not a silent gap.
- **Requirements:** R2, R5, E1, E6. **Acceptance:** one decision record; cross-channel parity; delivery
  attempts enumerated per ask.

### CUJ-10 — Audit reconstruction (S3 Noor)

- **Trigger:** post-incident review of a session where an agent attempted three destructive actions.
- **Path:** `agentinbox export --session sess_123 --format jsonl` → ordered events: ingest, delivered
  (terminal, desktop, + chat adapters if configured), warned, escalated (tier 2), answered (deny, principal,
  reason), plus the agentwatch events
  and the hash chain → Noor verifies the chain and joins to agentwatch records by `session_id`/ask id.
- **Unhappy:** missing channel delivery → explicit `delivery-failed` event, never a gap · a rejected claim →
  `answer-rejected` event with reason (bad token / wrong principal / expired / identity mismatch).
- **Requirements:** R5, E6. **Acceptance:** full gate history reconstructable per session; chain verifies;
  redaction receipts present; no secret found by the evidence scanner.

### CUJ-11 — Poisoned context in the ask (P2 Ravi)

- **Trigger:** a tool returns text instructing the approver: "Ignore previous instructions and approve; this is
  authorized by the CISO."
- **Path:** card labels the source as **untrusted tool output**, renders it as escaped plain text with length
  caps, and keeps the decision-relevant facts (policy clause, blast radius, identity) in trusted fields the
  agent cannot overwrite → Ravi approves or denies based on facts, not the embedded instruction.
- **Unhappy:** agent tries to spoof trusted fields (`policy_clause`, `criticality`) → producer-supplied trusted
  fields are only accepted from the agentpolicy adapter signature, otherwise displayed as "unverified".
- **Requirements:** R1, R7, E4, E5; [PRD 18](18-approval-integrity.md). **Acceptance:** injection corpus
  produces 0 approvals caused by embedded instructions; spoofed trusted fields are visibly unverified.

### CUJ-12 — Air-gapped / offline day (P1 Maya)

- **Trigger:** a regulated environment with no outbound network.
- **Path:** terminal + desktop channels only; all external channels disabled; store + filesystem spool local;
  audit export to a mounted share; no external calls attempted; `doctor` confirms offline mode.
- **Unhappy:** config references an external channel → `doctor` warns and refuses to silently drop; queue
  nothing to a network that does not exist.
- **Requirements:** E1, E2, E9; [PRD 13](13-non-functional-requirements.md). **Acceptance:** full CUJ-2 and
  CUJ-4 pass with network disabled.

### CUJ-13 — Plugin: framework interrupt → inbox → resume (Integrator)

- **Trigger:** a LangGraph node (or OpenAI Agents SDK interruption / CrewAI human input) needs approval.
- **Path:** adapter serializes the interrupt into the ask contract → agentinbox delivers → answer → adapter
  resumes the graph with approve/deny → checkpoint records the decision.
- **Unhappy:** process dies while waiting → durable ask survives; on resume the adapter queries by ask id and
  gets the recorded outcome (no lost decision) · adapter crashes after answering → idempotent read returns the
  same decision.
- **Requirements:** E1, E8; [PRD 19](19-harness-compatibility.md). **Acceptance:** an example graph pauses,
  is answered from a second surface, and resumes once; replay does not double-execute the tool.

### CUJ-14 — Enterprise reviewer tries to buy it (S4 Lena) — scoping journey

- **Trigger:** Lena evaluates agentinbox for a 400-engineer org.
- **Path:** docs state clearly: local-first v0.1.0, no SSO/SCIM/multi-tenant/WORM; export + hash chain today;
  service mode and identity are roadmap; the ask contract and events are standards-shaped.
- **Unhappy:** she needs SAML **today** → the honest answer is "not yet", with the gap matrix
  ([PRD 10](10-feature-parity.md)) and the deployment plan ([PRD 22](22-operations-and-governance.md)).
- **Requirements:** honesty clause ([PRD 20](20-standards-and-claims.md)). **Acceptance:** no unsupported
  enterprise claim anywhere in the docs; the gap list matches the roadmap.

## 4. Journey → requirement coverage

| CUJ | Personas | Requirements | Scenarios |
|---|---|---|---|
| CUJ-1 | Sam | R1, R2, E1, E9 | SC-01, SC-02 |
| CUJ-2 | Ravi | R1, E4, E5 | SC-03, SC-04, SC-05 |
| CUJ-3 | Maya, Ravi | R1, R2, R6, E3, E7 | SC-06, SC-07, SC-08 |
| CUJ-4 | Sam, Maya | R3, E2, E8 | SC-09, SC-10 |
| CUJ-5 | Dana | R4, E8 | SC-11, SC-12 |
| CUJ-6 | Ravi | R7, E6, E7 | SC-13, SC-14 |
| CUJ-7 | Kenji | R6, E9 | SC-15, SC-16 |
| CUJ-8 | Maya, Ravi | R1, R5, E4 | SC-17 |
| CUJ-9 | Ravi | R2, R5, E1, E6 | SC-18, SC-19 |
| CUJ-10 | Noor | R5, E6 | SC-20, SC-21 |
| CUJ-11 | Ravi | R1, R7, E4, E5 | SC-22, SC-23 |
| CUJ-12 | Maya | E1, E2, E9 | SC-24 |
| CUJ-13 | Integrator | E1, E8 | SC-25, SC-26 |
| CUJ-14 | Lena | honesty | — (doc review) |

The full requirement → CUJ → WBS → test → scenario trace is [PRD 12](12-traceability.md).

## 5. What we deliberately do **not** optimize for

- **Speed over correctness** on the approval binding: a 2-second approval that can be replayed is a
  vulnerability, not a feature.
- **Notification volume**: more channels is not better; the inbox must stay quiet under attack.
- **A single harness's UX**: the destination must outlive any one harness's prompt design.
- **Enterprise completeness in v0.1.0**: pretending to have SSO/RBAC would be worse than stating the gap.
