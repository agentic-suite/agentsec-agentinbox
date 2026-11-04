---
name: Bug report
about: Something in agentinbox is broken, unsafe, or contradicts the PRD
title: ""
labels: ["bug"]
assignees: []
---

<!--
Security first: if this is a vulnerability (a way to approve without a valid claim + principal, a replay that
works, a secret in a store/channel/export, or a fail-open path), do NOT open a public issue.
See SECURITY.md and report privately.
-->

## What happened

<!-- One paragraph. What did you do, what did you expect, what happened instead? -->

## Reproduction

```sh
# exact commands, from a clean AGENTINBOX_HOME if possible
export AGENTINBOX_HOME=$(mktemp -d)
agentinbox --version
agentinbox doctor
```

1.
2.
3.

## Expected vs actual

| | |
|---|---|
| Expected | |
| Actual | |

## Environment

| | |
|---|---|
| agentinbox version / commit | |
| OS + version | |
| Python version | |
| Channel(s) in use (terminal / desktop / CI / webhook / chat adapter) | |
| Store driver / bus driver | |
| Offline? | yes / no |

## Evidence

<!--
Redact before pasting: arguments, reasons and evidence are already redacted by the agentinbox redactor, but
double-check. Paste `agentinbox doctor` output, the relevant `agentinbox export --ask <id>` lines (not the whole
packet), and any `answer-rejected` cause. Never paste claim tokens or signing secrets.
-->

```
```

## Safety check

- [ ] This bug does **not** turn an expiry, a rejection, or a failure into an allow (fail-closed is intact), or it is reported privately as a security issue.
- [ ] I have removed secrets, claim tokens and signing keys from this report.

## Which PRD section does this contradict?

<!-- If behavior contradicts the documented contract, name it: PRD 02 (lifecycle), 05 (features), 15 (data model), 16 (adapters), 18 (integrity), 20 (events/claims). -->
