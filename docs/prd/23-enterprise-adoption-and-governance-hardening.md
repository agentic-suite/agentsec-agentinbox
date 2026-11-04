# PRD 23 — Enterprise Adoption & Governance Hardening

**BLUF:** v0.1.0 is honestly **not** an enterprise product (local-first, single-principal, config-file
identity) — and it is built so the enterprise version is the **same core**, hardened: v0.2.0's **server mode**
adds SSO (OIDC/SAML) + SCIM rosters + RBAC roles, multi-tenancy, HA, and WORM/externally-notarized audit;
v0.1.x–v0.2.0 add the controls enterprises already expect from CI/ITSM/PAM — quorum/dual-control, delegation,
recertification, business-hours SLAs, step-up. This PRD is the staged hardening plan plus the **buyer
packet**: what a security reviewer gets, what we can sign, and exactly which claims we refuse until audited.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## A. The honest starting point (what a reviewer is told on day one)

| Question | v0.1.0 answer (stated in the docs, not discovered in review) |
|---|---|
| Where does data live? | The approver's machine. Redacted metadata only; no secrets (E6); no telemetry out (N-26) |
| Who can approve? | Config rosters per channel (OS users by default; platform user ids where a chat adapter is configured); assurance level per channel is documented ([PRD 18](18-approval-integrity.md)) |
| Is there SSO? | **No.** v0.2.0 server mode. A fake RBAC would be worse than none ([PRD 14 N-12](14-non-goals.md)) |
| Is the audit court-proof? | It is **tamper-evident and locally verifiable** (hash chain), not externally notarized or WORM; v0.2.0 adds external attestation |
| Multi-tenant? | No — single principal by design; server mode (v0.2.0) introduces tenancy |
| Support/SLA? | Community support first; enterprise support tiers ship with server mode |

## B. Staged hardening plan (what lands when, with the requirement it closes)

### Stage 1 — v0.1.x: assurance depth on the local core

| Hardening | Closes (gap source) | Requirement |
|---|---|---|
| **Step-up re-auth** for `irreversible`/`critical` (platform-verified user + second factor) | PAM precedent (Azure PIM MFA-on-activate) | [PRD 18 §step-up](18-approval-integrity.md); own attack pack |
| **Business-hours SLA calendars** for TTLs | ITSM SLA clocks (PRD 03 §B) | calendar-aware `expires_at`; holiday/timezone config |
| **On-call schedule sync** (PagerDuty/Opsgenie lookup tiers) | Incident-tool ladders (PRD 03 §C) | tier = "whoever is on call now" with schedule evidence in the event |
| **Delegation windows** (out-of-office) | IGA/PIM (PRD 03 §D) | time-boxed, expiring delegate grants, recorded per-approval |
| **Ticket/incident linkage** + resolve webhooks | ITSM/SOAR (PRD 03 §B/F) | `correlation_id`, ServiceNow/Jira issue refs on the card |
| **Standing approvals with expiry + recertification** | PIM time-bound grants | R10; recert campaigns; auto re-gate on expiry |
| **Chat-platform adapters** (Slack/Teams) — optional, behind the Matrix-identical InboxChannel contract | chat reach | [PRD 16 §B](16-channel-and-harness-adapters.md) |

### Stage 2 — v0.2.0: server mode (the enterprise deployment of the same core)

| Hardening | Design commitment |
|---|---|
| **Identity:** OIDC/SAML SSO for approvers; **SCIM** sync of rosters from the IdP; per-tenant approver directories | Principals become IdP identities; the channel adapters verify **through** the IdP, so the Slack-account risk ([PRD 18](18-approval-integrity.md)) is mitigated by enterprise identity on top |
| **RBAC roles:** `approver` (answer), `auditor` (read/export only), `admin` (config), `owner` (class policy — points at agentpolicy) | Least-privilege read paths: auditors see records, cannot answer; admins cannot approve unless also rostered |
| **Multi-tenancy:** per-team spaces with isolated stores; shared policy references | Same schema, namespaced; no cross-tenant joins |
| **HA:** leader-elected scheduling (timers are the only mutable hot state), store replication, no split-brain allows (an ask answers once — cluster-level first-wins) | The single-machine claim model (single-use, bound) is what makes HA safe to add |
| **WORM + external attestation:** nightly chain notarization (RFC 3161 TSA), object-lock storage of exports | Upgrades "tamper-evident" to "externally timestamped" |
| **Data residency / air-gap:** deployable in a closed network; the offline guarantee (CUJ-12) becomes a topology, not a limitation | No SaaS dependency anywhere in the core (N-19) |
| **Quorum / dual-control** (N-of-M distinct approvers for the irreversible class) | agentpolicy R41 decision semantics; the inbox renders progress ("1 of 2 approvals") and does not release until quorum — single approval never releases ([PRD 03 §D](03-landscape.md)) |
| **Shared inbox (R12)** + **approver analytics (R11)** | Round-robin distribution; the "what you approve most" report feeding policy refinement |

### Stage 3 — v1.x: certifications and fleet

SOC 2 Type I → Type II pipeline (evidence starts accumulating the day server mode ships); ISO 27001/42001
programs; fleet/central policy sync (org-wide class tables distributed with drift detection — the agentpolicy
R31 pattern applied to gate config); CIS-hardened deployment manifests; optional hosted control plane **as a
deployment choice**, never a requirement (the local core stays complete — D-8).

## C. The buyer packet (what a security reviewer receives)

| Artifact | Content | Exists |
|---|---|---|
| **Datasheet (1 page)** | What it does, what it does not, the assurance table per channel, deployment modes | ✅ v0.1.0 |
| **Threat model** | [PRD 06](06-security-baseline.md) STRIDE table + [PRD 18](18-approval-integrity.md) pipeline, as a standalone PDF-style doc | ✅ v0.1.0 |
| **Evidence pack** | [PRD 21](21-evidence-register-and-method.md) register: fixtures, attack-pack outputs, field-test report, study protocol | ✅ v0.1.0 |
| **SBOM + provenance** | CycloneDX SBOM, SLSa provenance, Sigstore signatures per release | ✅ v0.1.0 |
| **Compliance mappings** | OWASP ASI/LLM, ATLAS, NIST AI RMF, ISO 42001 control appendix, EU AI Act Art. 12/14 alignment (labeled alignment, **not** conformance) | ✅ v0.1.0 |
| **Pen-test summary** | Third-party test of the answer-verification surface; summary + remediation timeline published | v0.2.0 (server mode surface is the right target) |
| **CVE/disclosure history** | `security.txt` + SLAs + published history | ✅ v0.1.0 |
| **SOC 2 / ISO letters** | audit letters | Stage 3 |

## D. Enterprise deployment topologies (v0.2.0 target shapes)

| Topology | Shape | Why |
|---|---|---|
| **Per-team server** | One server per team; IdP-federated; channels connected (Matrix/chat/webhook as configured) | The 90% case; blast-radius contained to a team |
| **Regional server (residency)** | EU/US regional instances; no cross-region event flow | Data-residency answers |
| **Air-gapped cluster** | Server in a closed network; terminal/CI only; exports to WORM share | Regulated environments (CUJ-12 generalized) |
| **Federated (no central store)** | Keep v0.1.0 local cores; central **policy** (agentpolicy) + central **events** (agentwatch aggregation), approvals stay local | The topology that preserves local-first for orgs that don't want a crown-jewel approval server |

## E. The hardening principles (why the core survives enterprise use)

1. **The security model is already multi-channel hostile.** Claims are channel-bound and single-use, rosters
   are per-class, and nothing trusts a channel's word alone — so bolting an IdP on top *raises* assurance
   without redesigning verification ([PRD 18](18-approval-integrity.md)).
2. **HA is safe to add because answers are rare and unique.** First-wins is a local rule at v0.1.0; at
   cluster scale it becomes exactly-once decisioning on a rare write — the easy case for distributed correctness.
3. **Identity is an adapter concern, deliberately.** The core records "principal, verified via channel X";
   which directory backs channel X is swappable — that is what keeps the local core cloud-free.
4. **Compliance is an export problem, not a storage problem.** Chain-verified exports + schema'd events mean
   evidence tooling reads what we already write; no parallel "compliance store" to drift
   ([PRD 15](15-data-model.md)).
5. **Nothing enterprise ships by complicating local.** Every Stage-2 item is a mode, a config, or an adapter —
   the single-machine install path is regression-tested against becoming second-class (CUJ-1/SC-01 run on
   every release).
