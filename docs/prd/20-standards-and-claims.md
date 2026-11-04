# PRD 20 — Standards, Events & Claims

**BLUF:** agentinbox is built **on** four load-bearing standards — the agentpolicy ask/decision contract, the
agentwatch security-event schema, MCP elicitation (presentation only), and OAuth CIBA's decoupled-approval
pattern — and **aligns to** the security/governance frameworks (OWASP ASI/LLM, MITRE ATLAS, NIST AI RMF,
ISO/IEC 42001, EU AI Act, OpenSSF/SLSA). This document fixes the **event vocabulary** we add to agentwatch,
the **claims vocabulary** that keeps marketing honest, and the **certification ladder** with its evidence.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## A. Standards agentinbox implements/consumes

| Standard | Status | agentinbox's use |
|---|---|---|
| **agentpolicy ask/decision contract** (in-suite, public shape) | shipped (agentpolicy v0.1.0: `AskBroker`, `action_identity`, approve/deny/expire, `human_gate_timeout`) | The producer-side contract: we consume `ask` records and return resolutions in its reason-code vocabulary |
| **agentwatch security-event schema** (event_version 0.1.0/0.2.0; additive process) | shipped | Every ask lifecycle transition is an event (R5); the ask lifecycle set is proposed below under the schema's additive rules |
| **AuthZEN Authorization API 1.0** (Final, Jan 2026) | Final | Decision-shape alignment: our `resolve/1.0` stays mappable to `decision` + `context`(reasons) so an AuthZEN-shaped PEP can consume outcomes |
| **MCP elicitation** (spec 2025-06-18) | Stable-ish (newly introduced) | Presentation bridge only (PRD 03 §G): `accept`→approve, `decline`→deny, `cancel`→leave pending; we never treat elicitation as the audit record |
| **OAuth CIBA (RFC 9200)** — *pattern*, not wire protocol | Final | The decoupled, cross-device approval pattern: our claim token ≈ binding code (single-use, bound, expiring); polling ≈ our long-poll read |
| **Platform callback signing** (Slack `v0` HMAC, Matrix event signatures, Teams callback auth — for optional chat adapters) | Platform standards | Chat-adapter authenticity (E4) — verified before parsing, when an adapter is configured |
| **W3C Trace Context** (`traceparent`) | Recommendation | Correlation across harness→policy→inbox for cross-tool evidence joins |
| **OpenTelemetry GenAI semantic conventions** | Stable-ish | Telemetry substrate alignment (events ride agentwatch; OTel is agentwatch's transport) |

## B. The ask lifecycle event set (the additive proposal to agentwatch)

Proposed under the schema's **additive minor-version** process (owner: agentwatch; PRD reference: this doc;
fixture responsibility: agentinbox):

| Event type | Added fields (in `evidence`) | Notes |
|---|---|---|
| `ask-raised` | `ask_id`, `action_identity`, `class`, `criticality`, `expires_at`, `requested_by` | The gate opened |
| `ask-delivered` / `ask-delivery-failed` | `channel`, `attempt`, `error?` | Delivery accounting (E7) |
| `ask-warned` | `remaining_s` | Pre-expiry warning fired |
| `ask-escalated` | `tier`, `targets_count`, `revoked_claims` | Routing change, never a deadline change |
| `ask-answered` | `outcome`, `principal`, `channel`, `reason?` | The human decision, identity-attached |
| `ask-expired` | `ttl_s` | Timeout = deny, as an event |
| `ask-cancelled` | `by` | Producer withdrew (e.g., CI cancel) |
| `ask-flood` | `window`, `denied_count`, `first_ask_id` | One event per throttle trip, never per ask |
| `answer-rejected` | `cause` (`bad_signature`/`unknown_claim`/`expired_claim`/`revoked_claim`/`used_claim`/`binding_mismatch`/`late`/`off_roster`/`self_review`) | Spoof attempts are evidence |

**Forward event set (PRDs 26–30, additive when those requirements ship):** `ask-claimed` / `ask-assigned` /
`ask-handoff` (R30), `incident-mode-changed` (R32), `standing-approval-applied` (R37), `hook-fired` /
`hook-failed` / `writeback-failed` (R44/R64), `ask-needs-changes` (R48), `grant-minted` / `grant-expired` /
`grant-revoked` (R51–R53, R74), `suppression-changed` (R53), `attestation-exported` (R63),
`drill-completed` (R67), `illegal-transition-rejected` (R69), `systemic-coverage-failure` (R77) — all
following the same additive-process rules (owner: agentwatch, version bump, fixtures in this repo).

All carry `emitter: "agentinbox"` and the shared join keys (`session_id`, `agent_id`, `traceparent`). The
agentwatch record's existing `authorization.source` (`human-once`) is exactly what an `ask-answered` outcome
asserts — the inbox is the *producer* of that provenance, closing the loop the schema already opened.

## C. Security & governance framework alignment

| Framework | agentinbox alignment |
|---|---|
| **OWASP Top 10 for Agentic Applications 2026** — **ASI09** Human-Agent Trust Exploitation | Direct control: identity-bound approvals, no chat-bot surface, untrusted rendering. **ASI10** Rogue Agents: flood auto-deny + fail-closed. **ASI02** (tool misuse) indirectly via the gate itself |
| **OWASP Top 10 for LLM Applications 2025** — **LLM01** prompt injection | Architectural mitigation in *our own* UX (E5) — we claim inertness of injected text, not detection. **LLM02** disclosure: redaction-before-persistence. **LLM06** excessive agency: the gate + TTL + no-standing-grants |
| **MITRE ATLAS** | Flood/pack scenarios tagged (AML.T0049-class destructive targets, T0057 exfil via unredacted context — our redaction kills it); full mapping in `docs/compliance/` |
| **NIST AI RMF 1.0 + GenAI Profile** | **Govern/Manage** functions: human oversight with evidence (Art. 14-style), measurable metrics ([PRD 07](07-success-metrics.md)) |
| **ISO/IEC 42001** | Controls-mapping appendix for buyers (human oversight, logging, incident evidence) |
| **EU AI Act — Art. 14 (human oversight), Art. 12 (logging)** | The ask record + events + chain are precisely an Art. 12/14 evidence shape; claims restricted to what's demonstrable |
| **NIST SP 800-63B thinking** (authenticator assurance) applied to approvals | Channel assurance table ([PRD 18 §per-channel](18-approval-integrity.md)); step-up ladder defined for critical classes |

## D. Product security & supply chain (our own posture)

NIST SSDF (SP 800-218) development practices · OWASP ASVS L2 target for the local attack surface · OpenSSF
Scorecard/Best Practices badge · SLSA build provenance + Sigstore-signed releases · pinned deps + SBOM ·
CVE program + `security.txt` with SLAs · `doctor` as a shipped security posture check. (Org floor — identical
to agentpolicy/agentwatch.)

## E. Certification ladder (cost-ordered, evidence-named)

| Rung | Target | When | Evidence |
|---|---|---|---|
| OpenSSF Best Practices badge | Passing → Silver | v0.1.0 | Badge |
| SLSA provenance + Sigstore signing | L2 | v0.1.0 | Attestations per release |
| `security.txt` + disclosure SLAs | Live | v0.1.0 | Public URL |
| Published OWASP ASI/LLM + ATLAS coverage matrix | Published | v0.1.0 | Regenerated per release from tags |
| Contract conformance report (ask/1.0, exit codes, events) | Published | v0.1.0 | CI fixtures + report |
| SOC 2 Type I → Type II | Audited | v2.x (server mode) | Audit letter (Type II needs 6–12 months of evidence — pipeline starts with server mode) |
| ISO/IEC 27001 / 42001 | Certified | later | Certificate |

## F. Interop claims we make (and their proof)

| Claim | Proof required |
|---|---|
| "Works with any harness that can pause for a human" | The `--exec`/CLI/HTTP path + contract fixtures (any-process test) |
| "Answers are identity-bound and single-use" | SC-22 attack matrix green in CI |
| "Timeout = deny" | Expiry fixtures + the runtime zero-allow-on-expiry counter |
| "Approval from any channel recorded identically" | SC-07/08 byte-parity fixtures |
| "Floods produce one event, one digest" | SC-13 + the agentdrill flood pack |
| "Field-tested with Claude Code / Codex CLI" | The field-test report's run journal |
| "Chat-bot decision surface" / "ML-assisted approval" | **Never claimable** (forbidden vocabulary) |

## G. Claims vocabulary (the honesty rule — lint-enforced)

| Claim | Status |
|---|---|
| "Unforgeable approvals" | **Restricted** — allowed only as "spoof/replay/forward attempts are rejected and logged (SC-22)" — we never claim platform-unbreakability |
| "Prevents prompt injection" | **Forbidden** — we make injected text *inert in our surface*, a scoped, testable claim |
| "SOC 2 / ISO certified" | **Only** with the letter in hand |
| "Human oversight (EU AI Act Art. 14)" | **Allowed** as *alignment*, never as *conformance*, until audited |
| "Enterprise-ready" | **Forbidden** for v0.1.0 (local-first single-principal; the server mode is the v0.2.0 story) |
| "Works with Claude Code / Codex" | Allowed with the field-test label attached |
| Performance numbers | Only with the CI measurement published |

The machine-readable **claims linter** (the ecosystem's claims-ledger pattern) runs against docs/READMEs in
CI — a claim without its evidence row is a build failure.

## H. Coverage matrix (generated, not hand-edited)

Every control carries machine-readable tags; the matrix is regenerated per release:

| Control | OWASP ASI | OWASP LLM | ATLAS | NIST/EU |
|---|---|---|---|---|
| Identity-bound claims (E3/E4) | ASI09 | LLM06 | — | Art. 14 |
| Injection-inert rendering (E5) | ASI09 | LLM01 | AML.T0059-class | — |
| Timeout=deny (R3) | ASI10 | LLM06 | — | Art. 14 |
| Flood auto-deny (R7) | ASI10 | LLM06 | AML.T0049 | MANAGE-2.2 |
| Redaction-before-persist (E6) | — | LLM02 | AML.T0057 | MANAGE-2.1 |
| Hash-chained evidence (R5) | — | — | — | Art. 12, MEASURE |
| Fail-closed degradation (E9) | ASI10 | LLM06 | — | — |
| No-ML-decision-path (N-1) | ASI09 | LLM01 | — | — |
