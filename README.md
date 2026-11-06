# agentinbox

> **Block / limit** — The approval control plane for consequential agent actions: every agent `ask` becomes a
> decision a human can make in seconds — from the terminal, a desktop notification, a CI checkpoint, or a
> signed webhook. No chat platform required.

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/agentic-suite/agentsec-agentinbox/badge)](https://scorecard.dev/viewer/?uri=github.com/agentic-suite/agentsec-agentinbox)

Part of the [agentic-suite](https://github.com/agentic-suite) — open-source,
harness-agnostic security for AI agents. agentinbox is the human half of the
ask-gate: **agentpolicy asks, agentinbox answers**.

## Status

**in development — v0.1.0, milestone M0 (foundation).** The installable
skeleton exists today: the package, the frozen CLI surface and exit-code
contract, the fail-closed config model, `init`, and `doctor`. Nothing asks or
answers yet, and every unimplemented command says so instead of pretending.
The full requirement set is published early on purpose, so we can be held to
it: the v0.1.0 core (requirements R1–R7, engineering requirements E1–E12), the
forward product-depth slate (PRDs 24–30), and the hardening layer that gates it
all (PRD 30). See [docs/prd/](./docs/prd/README.md) for the plan of record and
[the WBS](./docs/wbs/v0.1.0/wbs-v0.1.0-index.md) for the build order.

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
recipes. The honest, per-release compatibility table (field-tested /
conformance-tested / documented / not-supported) lives in
[docs/prd/19-harness-compatibility.md](./docs/prd/19-harness-compatibility.md).

## Install (from source, M0)

The package is **standalone**: no runtime dependencies beyond the Python
standard library, no network calls, no external services. Python 3.11–3.13 on
POSIX (Windows is not supported in v0.1.0).

```sh
git clone https://github.com/agentic-suite/agentsec-agentinbox
cd agentsec-agentinbox
make setup                 # creates .venv and installs the package + dev tools
agentinbox --version       # or: python -m agentinbox --version

agentinbox init            # writes ~/.agentinbox + a commented config.toml
agentinbox doctor          # exit 0 on a healthy install, 4 (fail-closed) otherwise
```

`AGENTINBOX_HOME` (or `--home`) relocates the home directory. A PyPI release
(`pip install agentsec-agentinbox`) lands with v0.1.0.

## Documentation

- **The PRD set (00–30) is the plan of record:** [docs/prd/](./docs/prd/README.md) —
  start with the [press release](./docs/prd/00-press-release.md) and
  [why](./docs/prd/01-why.md); the [features](./docs/prd/05-features.md),
  [scenario catalog](./docs/prd/17-scenarios.md), and
  [traceability](./docs/prd/12-traceability.md) define what "done" means.
- **The v0.1.0 WBS is written:** [docs/wbs/v0.1.0/](./docs/wbs/v0.1.0/wbs-v0.1.0-index.md) —
  **26 milestones (M0–M25)** across **13 detail files** (2 milestones per file): the core
  engine (M0–M9), reach (M10–M14), evidence + producers (M15–M19), hardening +
  ops + docs (M20–M23), field tests + release (M24–M25, which tags `v0.1.0`).
- **Design docs are authored before code**, milestone by milestone — start with
  [the foundation design](./docs/design/v0.1.0/foundation.md) (CLI surface,
  exit-code contract, config model, store layout).
- Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md) (workflow, DCO, tests) and
  the [org guide](https://github.com/agentic-suite/.github/blob/main/CONTRIBUTING.md)
- Security: [SECURITY.md](./SECURITY.md)
- Roadmap: [agentic-suite](https://github.com/agentic-suite)

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
