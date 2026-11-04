---
name: Feature request
about: Propose a capability, channel, adapter, or contract change for agentinbox
title: ""
labels: ["enhancement"]
assignees: []
---

<!--
agentinbox is scope-guarded on purpose (docs/prd/14-non-goals.md). Read that first.
Ideas that belong to the forward slate (PRDs 24–30: constrained approvals, evidence, operator experience,
governance, review loops, trust maturity, hardening) are welcome — but say which PRD/requirement they extend.
-->

## Problem

<!-- What can a human or an agent not do today? Whose job is it blocking? Be concrete. -->

## Proposed capability

<!-- What should exist. One paragraph, then the acceptance test you would write. -->

## Which requirement does this map to?

- [ ] An existing PRD requirement: <!-- e.g. R3, E4, R21, R48 — cite the PRD section -->
- [ ] A new requirement (needs a PRD change first) — which PRD, and why
- [ ] Out of scope for agentinbox (enforcement, policy authoring, chat-bot decisions, ML answering gates) — see PRD 14

## Why this belongs in agentinbox (not elsewhere)

<!--
- Policy decisions belong to agentpolicy.
- Enforcement belongs to the enforcer (harness hook, agentgate, agentkeys, agentseatbelt).
- Recording belongs to agentwatch.
agentinbox is the approval control plane: it records, routes, and returns the human decision.
-->

## Interface impact

| Surface | Change (none / additive / breaking — breaking needs a major bump per PRD 30 E18) |
|---|---|
| `ask/1.0` contract | |
| `resolve/1.0` | |
| Reserved exit codes | |
| Event set (agentwatch schema) | |
| Store schema / bus jobs | |
| Config keys (`[channels.*]`, `[classes.*]`, `[bus]`, `[store]`) | |

## Security & privacy

<!--
Does it create a new way to answer? Who authenticates the principal? What is the claim binding?
Does it persist anything new (redaction implications)? Does it weaken fail-closed or timeout=deny?
A feature that lets a model answer a gate will be rejected — that is the anti-requirement.
-->

## Alternatives considered

<!-- Including "do nothing" and the harness-native equivalent. -->

## Definition of done

- [ ] PRD updated (requirement + acceptance criteria + traceability row)
- [ ] WBS work item(s) added under the owning milestone
- [ ] Tests first, then implementation; milestone gate green
- [ ] Docs + reference updated
