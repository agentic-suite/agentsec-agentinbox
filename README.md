# agentinbox

> **Block / limit** — The approval control plane for consequential agent actions: every agent `ask` becomes a
> decision a human can make in seconds — from the terminal, a desktop notification, a CI checkpoint, or a
> signed webhook. No chat platform required.

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/agentic-suite/agentsec-agentinbox/badge)](https://scorecard.dev/viewer/?uri=github.com/agentic-suite/agentsec-agentinbox)

Part of the [agentic-suite](https://github.com/agentic-suite) — open-source,
harness-agnostic security for AI agents. agentinbox is the human half of the
ask-gate: **agentpolicy asks, agentinbox answers**.

## Contents

- [Status](#status)
- [What it does](#what-it-does)
- [What it is not](#what-it-is-not)
- [Compatibility](#compatibility)
- [Install](#install)
- [Quickstart (first approval in under 5 minutes)](#quickstart-first-approval-in-under-5-minutes)
- [Documentation](#documentation)
  - [Start here](#start-here)
  - [Reference](#reference)
  - [Guides](#guides)
  - [Runbooks](#runbooks)
  - [Adapters and recipes](#adapters-and-recipes)
  - [Release packet (v0.1.0)](#release-packet-v010)
  - [Field test](#field-test)
  - [Compliance and claims](#compliance-and-claims)
  - [Plan of record (PRDs)](#plan-of-record-prds)
  - [Work breakdown (WBS)](#work-breakdown-wbs)
  - [Design docs](#design-docs)
  - [Project](#project)
- [License](#license)

## Status

**v0.1.0 is released.** The core engine (M0–M23), the expansion surfaces
(M26–M31), the field test (M32), and release readiness (M33) are complete. The
package is published as `agentsec-agentinbox==0.1.0` and the `v0.1.0` tag is
cut.

The field test closed **with known issues**, stated plainly: **47 PASS / 6
FAIL** over 53 registry units — 4 KNOWN container test-setup/env failures and 2
study cases failed by design (no human cohort). One product defect was found,
fixed, regression-locked, and field-verified. See the
[field-test report](./docs/field-test/v0.1.0/FIELD_TEST_REPORT.md) and
[claims and limitations](./docs/compliance/claims-and-limitations.md).

## What it does

AI agents are increasingly trusted with actions that cannot be undone — dropping
a production table, force-pushing `main`, sending the customer list to an
external endpoint, rotating a live credential. The policy layer
([agentpolicy](https://github.com/agentic-suite/agentsec-agentpolicy)) can
already say **"a human must decide"** — but until now that sentence ended in a
harness prompt only one person, in one session, on one machine ever saw.
Headless and CI agents got nothing at all.

agentinbox is the missing destination:

- **Decision-ready cards** — what the agent wants to do, which policy clause
  fired, the blast radius, the session so far. An approver with zero context
  makes the correct call in **under 15 seconds** (that's an acceptance test,
  not a slogan).
- **Answer from where you are** — terminal/TUI, desktop notification, CI
  checkpoint, signed webhooks (ntfy/Pushover/Discord recipes). Matrix is next;
  Slack/Teams are *optional* adapters. The product is complete with **no chat
  platform at all** and works air-gapped.
- **Timeout = deny** — the safe default, configurable per action class, with a
  pre-expiry warning and a rescope hint the agent can act on. No answer in
  time means the action **does not happen**.
- **Escalation ladders** — unanswered asks route up (buddy → on-call → channel)
  within the configured window; escalation changes routing, never the deadline.
- **Flood protection** — a misbehaving agent cannot spam the inbox: throttling,
  auto-deny on flood, **one event, one digest** — the inbox gets quieter under
  attack, not louder.
- **Evidence-grade audit** — every ask/answer/timeout/escalation recorded in an
  append-only, hash-chained local log and emitted in the
  [agentwatch](https://github.com/agentic-suite/agentsec-agentwatch)
  security-event schema. Full gate history reconstructs per session.
- **Unforgeable answers** — an answer is a single-use claim token bound to the
  exact action identity **plus** an authenticated principal. Forwarded
  messages, replayed callbacks, late taps, and "similar" actions change
  nothing. A model never answers a gate — that's the anti-requirement.

## What it is not

No ML in any decision path. No chat-bot decision surface. No harness-side UI
replacement. No SaaS. Full list of boundaries in
[docs/prd/14-non-goals.md](./docs/prd/14-non-goals.md).

## Compatibility

Harness-agnostic by construction: it consumes the agentpolicy ask contract
(`ask/1.0` — a small JSON document reachable via HTTP, CLI, or file) and the
agentwatch event schema, so **any agentic system that can pause for a human can
emit an ask**. Named adapters make the top surfaces convenient — Claude Code
`PreToolUse` hooks, Codex CLI wrappers, a LangGraph `interrupt()` reference
adapter, CI recipes (GitHub Actions, GitLab, Jenkins, Argo), MCP tool-gating
recipes.

The honest, per-release compatibility table (field-tested /
conformance-tested / documented / not-supported) is generated and published at
[docs/release/v0.1.0/COMPATIBILITY.md](./docs/release/v0.1.0/COMPATIBILITY.md);
the design rationale is
[docs/prd/19-harness-compatibility.md](./docs/prd/19-harness-compatibility.md).

## Install

The package is **standalone**: no runtime dependencies beyond the Python
standard library, no network calls, no external services. Python 3.11–3.13 on
POSIX (Windows is not supported in v0.1.0).

```sh
pip install agentsec-agentinbox==0.1.0

agentinbox --version       # or: python -m agentinbox --version
agentinbox init            # writes ~/.agentinbox + a commented config.toml
agentinbox doctor          # exit 0 on a healthy install, 4 (fail-closed) otherwise
```

From source:

```sh
git clone https://github.com/agentic-suite/agentsec-agentinbox
cd agentsec-agentinbox
make setup                 # creates .venv and installs the package + dev tools
```

`AGENTINBOX_HOME` (or `--home`) relocates the home directory.

## Quickstart (first approval in under 5 minutes)

The step-tested walkthrough is [docs/tutorials/quickstart.md](./docs/tutorials/quickstart.md).
In short: put your OS user on the roster, then in two terminals:

```sh
# terminal 1 (blocks at the gate)
agentinbox ask --exec "echo hello" --timeout 300

# terminal 2
agentinbox inbox
agentinbox answer <ask_id>      # card → a → type run_command
agentinbox report --json        # local-only metrics
agentinbox verify-log           # hash chain
```

## Documentation

### Start here

- [Quickstart](./docs/tutorials/quickstart.md) — install → first recorded
  approval, step-tested in under five minutes.
- [Approver guide](./docs/guides/approver-guide.md) — how to read a card and
  answer safely.
- [Honest enterprise page](./docs/guides/enterprise-honesty.md) — what v0.1.0
  does and does not provide.
- [Claims and limitations](./docs/compliance/claims-and-limitations.md) — the
  verified / not-verified split.

### Reference

- [CLI](./docs/reference/cli.md)
- [Config](./docs/reference/config.md)
- [Ask contract](./docs/reference/ask-contract.md)
- [Resolve contract](./docs/reference/resolve.md)
- [Card](./docs/reference/card.md)
- [Lifecycle](./docs/reference/lifecycle.md)
- [Scheduler](./docs/reference/scheduler.md)
- [Store](./docs/reference/store.md)
- [Bus](./docs/reference/bus.md)
- [Events](./docs/reference/events.md)
- [Audit](./docs/reference/audit.md)
- [Security](./docs/reference/security.md)
- [Fail-closed behavior](./docs/reference/fail-closed.md)
- [Flood control](./docs/reference/flood.md)
- [Escalation](./docs/reference/escalation.md)
- [Parity](./docs/reference/parity.md)
- [Conformance](./docs/reference/conformance.md)
- [Operations](./docs/reference/ops.md)
- [Readiness](./docs/reference/readiness.md)
- [Constrained allows](./docs/reference/constrained-allows.md)
- [Operations bundles](./docs/reference/operations.md)
- [Outcomes](./docs/reference/outcomes.md)
- [Grants](./docs/reference/grants.md)
- [Insights](./docs/reference/insights.md)
- [Terminal channel](./docs/reference/terminal.md)
- [Desktop channel](./docs/reference/desktop.md)
- [Webhook channel](./docs/reference/webhook.md)
- [Gate](./docs/reference/gate.md)

### Guides

- [Approver guide](./docs/guides/approver-guide.md)
- [Honest enterprise page](./docs/guides/enterprise-honesty.md)
- [Producer guide](./docs/adapters/producer-guide.md)

### Runbooks

- [Runbook index](./docs/runbooks/ops.md)
- [Channel outage](./docs/runbooks/rb-1-channel-outage.md)
- [Secret rotation](./docs/runbooks/rb-2-secret-rotation.md)
- [Store corruption](./docs/runbooks/rb-3-store-corruption.md)
- [Live flood](./docs/runbooks/rb-4-live-flood.md)
- [Config drift](./docs/runbooks/rb-5-config-drift.md)
- [Clock incident](./docs/runbooks/rb-6-clock-incident.md)
- [Escalation misfire](./docs/runbooks/rb-7-escalation-misfire.md)
- [Upgrade day](./docs/runbooks/rb-8-upgrade-day.md)
- [Expansion runbooks](./docs/release/v0.1.0/RUNBOOKS.md) — readiness,
  constrained allows, bundles/handoff, outcomes, grants, insights.

### Adapters and recipes

- [Harness recipes](./docs/adapters/harness-recipes.md) — Claude Code, Codex CLI
- [CI recipes](./docs/adapters/ci-recipes.md) — GitHub Actions, GitLab, Jenkins, Argo
- [MCP ask-gating](./docs/adapters/mcp.md)
- [Temporal signal recipe](./docs/adapters/temporal.md)
- [LangGraph reference adapter](./docs/adapters/langgraph/README.md)
- [Producer guide](./docs/adapters/producer-guide.md)

### Release packet (v0.1.0)

- [Release index](./docs/release/v0.1.0/README.md)
- [Release plan](./docs/release/v0.1.0/RELEASE_PLAN.md)
- [Release notes + gap list](./docs/release/v0.1.0/RELEASE_NOTES.md)
- [Compatibility matrix](./docs/release/v0.1.0/COMPATIBILITY.md)
- [Security audit + risk re-grade](./docs/release/v0.1.0/SECURITY_AUDIT.md)
- [Wave-0 demo evidence](./docs/release/v0.1.0/demo/transcript.txt)
- [Harness LLM captures](./docs/release/v0.1.0/evidence/harness/README.md)
- [Benchmarks](./docs/release/v0.1.0/bench.json)
- [Artifacts + checksums](./docs/release/v0.1.0/artifacts/SHA256SUMS)

### Field test

- [Field-test report](./docs/field-test/v0.1.0/FIELD_TEST_REPORT.md) — 47 PASS / 6 FAIL
- [Field-test plan](./docs/field-test/v0.1.0/FIELD_TEST_PLAN.md)
- [Field-test results](./field-test/v0.1.0/results/)

### Compliance and claims

- [Claims and limitations](./docs/compliance/claims-and-limitations.md)
- [Claims design](./docs/design/v0.1.0/claims.md)
- [Security baseline (PRD 06)](./docs/prd/06-security-baseline.md)
- [Standards and claims (PRD 20)](./docs/prd/20-standards-and-claims.md)
- [Evidence register (PRD 21)](./docs/prd/21-evidence-register-and-method.md)

### Plan of record (PRDs)

- [PRD index](./docs/prd/README.md)
- [Press release](./docs/prd/00-press-release.md)
- [Why](./docs/prd/01-why.md)
- [Features](./docs/prd/05-features.md)
- [Scenario catalog](./docs/prd/17-scenarios.md)
- [Traceability](./docs/prd/12-traceability.md)
- [Non-goals](./docs/prd/14-non-goals.md)
- [Harness compatibility](./docs/prd/19-harness-compatibility.md)
- [Enterprise adoption](./docs/prd/23-enterprise-adoption-and-governance-hardening.md)

### Work breakdown (WBS)

- [WBS index](./docs/wbs/v0.1.0/wbs-v0.1.0-index.md) — 34 milestones (M0–M33)
  across 17 detail files
- [Field tests + release (M32–M33)](./docs/wbs/v0.1.0/wbs-v0.1.0-part17-expansion-fieldtest-release.md)
- [Code review log](./docs/wbs/v0.1.0/codereview-log.md)

### Design docs

- [Foundation](./docs/design/v0.1.0/foundation.md) — CLI surface, exit-code
  contract, config model, store layout
- [Design index](./docs/design/v0.1.0/)

### Project

- [Contributing](./CONTRIBUTING.md) and the
  [org guide](https://github.com/agentic-suite/.github/blob/main/CONTRIBUTING.md)
- [Security policy](./SECURITY.md)
- [Roadmap](https://github.com/agentic-suite)
- [agentpolicy](https://github.com/agentic-suite/agentsec-agentpolicy) ·
  [agentwatch](https://github.com/agentic-suite/agentsec-agentwatch)

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
