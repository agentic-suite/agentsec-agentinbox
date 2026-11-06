# Contributing to agentinbox

Thanks for helping. This repo is built to the published plan of record, not to improvisation:
**[PRD 05 — features](../docs/prd/05-features.md)** defines the requirement set,
**[PRD 12 — traceability](../docs/prd/12-traceability.md)** maps each requirement to its test, and the
**[v0.1.0 WBS](../docs/wbs/v0.1.0/wbs-v0.1.0-index.md)** defines the milestone order and exit gates.

## Workflow (one ticket at a time)

1. Pick the next open work item from the WBS milestone (its GitHub issue).
2. **Test-first:** write the failing test for that item only, and watch it fail (RED).
3. Implement the smallest change that makes it pass (GREEN).
4. Run **only** that test. Do not run the full suite between tickets.
5. Commit and push on a feature branch. The full gate (suite, coverage ≥95%, `ruff`,
   `mypy --strict`) runs **once at milestone end**, not per ticket.

Design docs are written before code for every milestone; the current one is
[the foundation design](../docs/design/v0.1.0/foundation.md).

## Local commands

```sh
make setup      # .venv + editable install + dev tools
make lint       # ruff
make typecheck  # mypy --strict
make test       # pytest
make cov        # pytest with the >=95% coverage gate
make gate       # the milestone gate (run once, at milestone end)
```

The runtime is stdlib-only by design. Do not add a runtime dependency without an explicit
decision recorded in the design docs — "standalone" is a product property, not an accident.

## Commits

Every commit must be **DCO signed off**:

```sh
git commit -s -m "feat(area): what changed"
# adds: Signed-off-by: Your Name <you@example.com>
```

The DCO check rejects unsigned commits. Keep commits ticket-scoped and reference the issue
(`Fixes #NN`) in the commit body.

## Security

Report vulnerabilities privately per [SECURITY.md](../SECURITY.md) — never in a public issue.
Configuration is a security surface: invalid config must fail closed, secrets are references
only (`env:` / `file:`), and the bind stays loopback.

## Scope

v0.1.0 is PRD 05 §A/§B P0 only. The forward slate (PRDs 24–30) is explicitly out of scope
until v0.1.0 ships — see [PRD 14 — non-goals](../docs/prd/14-non-goals.md).
