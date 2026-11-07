# What v0.1.0 is not (honest enterprise page)

A security reviewer should find the gaps stated here, not discover them. This page mirrors
[PRD 23 §A](../prd/23-enterprise-adoption-and-governance-hardening.md).

| Question | v0.1.0 answer |
|---|---|
| Where does data live? | The approver's machine. Redacted metadata only; no secrets; no telemetry out. |
| Who can approve? | Config rosters per channel (OS users by default). |
| Is there SSO/SAML/OIDC? | **No.** Server mode (v0.2.0). A fake RBAC would be worse than none. |
| Is the audit court-proof / WORM? | It is **tamper-evident and locally verifiable** (hash chain); not externally notarized. |
| Multi-tenant? | No — single principal by design. |
| Quorum / dual control? | **No** in v0.1.0 (forward slate). One authenticated approval decides. |
| Standing approvals / delegation? | **No** in v0.1.0 (forward slate). |
| Mobile push / chat platform? | Optional webhook/desktop/terminal/CI; no chat platform required, none bundled. |
| Support/SLA? | Community support first; enterprise tiers with server mode. |
| Pen-test summary? | v0.2.0 (the server surface is the right target). |
| SBOM / provenance / Scorecard? | SBOM + Scorecard workflows ship; signing and publication are release steps (M25). |

**What is real today:** timeout = deny, single-use identity-bound claims, one truth across channels,
flood protection as decisions, hash-chained local evidence, offline-complete operation, and an evidence
scanner + attack packs in CI.

**Claims we refuse until audited:** "injection-proof", "enterprise-ready", "court-proof audit",
"zero-trust", "SSO", "multi-tenant", "N-of-M quorum".
