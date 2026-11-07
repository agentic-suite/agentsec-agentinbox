# Security Policy

Please report vulnerabilities privately — see the
[organization security policy](https://github.com/agentic-suite/.github/blob/main/SECURITY.md).

Do not open public issues for security problems.

## Disclosure SLA (v0.1.0)

| Stage | Target |
|---|---|
| Acknowledge a report | within **48 hours** |
| Triage + severity (CVSS-style, impact-first) | within **5 business days** |
| Critical/high fix | target **7 days** after triage |
| Coordinated disclosure | default **90 days**, sooner by agreement |
| Credit | offered unless the reporter prefers anonymity |

## Machine-readable metadata

The source `security.txt` (RFC 9116) is committed at
[`docs/security.txt`](docs/security.txt) and is validated in CI by
`python -m agentinbox.posture security-txt`. Publishing it at
`https://agentic-suite.dev/.well-known/security.txt` is a release step (M25).

## Scope

The local daemon, CLI, store, audit chain, claim/answer pipeline, and the shipped channel adapters.
Out of scope: third-party harnesses, chat platforms, and deployments that bind the API beyond
loopback against the documented configuration.

## Honest limits

The evidence scanner is a pattern tripwire, not a proof that no secret can ever be stored. The
security claims and their evidence live in
[`docs/compliance/claims-and-limitations.md`](docs/compliance/claims-and-limitations.md).
