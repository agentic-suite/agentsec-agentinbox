# agentinbox docs

Documentation for **agentinbox** — the ask-gate consumer: routes agent approval requests (`ask` decisions)
to the human with full decision context, and records the answer, timeout, or escalation. Answerable from
the terminal, desktop notification, Slack, CI checkpoint, or mobile. Part of the
[agentic-suite](https://github.com/agentic-suite).

> **Status: planned — PRD set 00–30 complete (plan of record).** The full requirement set is written and
> published early on purpose so we can be held to it: [PRD 00–30 + Appendix A](prd/README.md) (why, landscape,
> CUJs, features, security baseline, integrity, compatibility, scenarios, evidence, ops, enterprise — plus the
> forward product-depth slate: constrained approvals & effects, evidence & decision quality, approver
> experience & operations, governance & extensibility, review loops & orchestration, trust maturity &
> writeback — and the correctness/conflict/abuse hardening layer that gates them all).
> Design docs, ADRs, the WBS, and the field-test plan follow as they are authored with the build; the PRD set is
> the plan of record today.

## Sections

| Directory / file | Purpose |
|---|---|
| [prd/](prd/) | Product requirements — 00–23 + Appendix A: why, landscape, CUJs, features R1–R10/E1–E10, security, integrity, compatibility, scenarios, evidence, ops, enterprise |
| [design/](design/) | Subsystem designs + decisions + threat model (ask lifecycle, channels, escalation, flood throttling) |
| [reference/](reference/) | CLI, config, ask/answer API, channel adapters, errors, limitations |
| [adr/](adr/) | Architecture Decision Records |
| [architecture/](architecture/) | Spec + component architecture (v0.1.0) |
| [wbs/](wbs/) | Work breakdown, by version (index + parts) |
| [plans/](plans/) | Execution plans + testing strategy |
| [field-test/](field-test/) | Field-test plan + report, by version |
| [release/](release/) | Release notes, security audit, claims ledger, verifier |
| [runbooks/](runbooks/) | Operational runbooks |
| [tutorials/](tutorials/) | Hands-on guides |
| [guides/](guides/) | User guide |
| [compliance/](compliance/) | OWASP/ATLAS/NIST/EU/OpenSSF mappings |
| [adapters/](adapters/) | Channel adapters (terminal, Slack, desktop, CI checkpoint, mobile) and harness adapters (Claude Code, Cursor, Copilot, Codex CLI, Gemini CLI) |
| [examples/](examples/) · [articles/](articles/) · [skills/](skills/) | Samples, posts, operator skills |
| [testing/](testing/) | Test plans (unit, conformance, field-test agents, docker) |

## Start here

- [PRD index](prd/README.md) · [Press release](prd/00-press-release.md) · [Why](prd/01-why.md) · [Features](prd/05-features.md)
- [Harness compatibility](prd/19-harness-compatibility.md) · [Approval integrity](prd/18-approval-integrity.md) · [Scenario catalog](prd/17-scenarios.md)
- Design docs, architecture, ADRs, WBS, runbooks, and tutorials are authored with the build; the PRD set is the
  plan of record today.

## Conventions

- **BLUF** — Bottom Line Up Front in major documents.
- **Honesty** — misses and limitations are documented, not hidden.
- **Versioned directories** — each documentation type is organized by version.
