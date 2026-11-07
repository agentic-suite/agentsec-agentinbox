# v0.1.0 expansion runbooks

Operational procedures for the M26–M31 expansion surfaces. The core runbooks
remain in [`docs/runbooks/`](../../runbooks/); these cover readiness, constrained
allows, operations bundles/handoff, outcomes, grants, and insights.

Every runbook follows the same shape: **symptom → inspect → act → verify**.
The inbox records and returns outcomes; the enforcer enforces them. None of
these procedures authorizes an action.

## 1. Readiness rejection

**Symptom:** an ask is denied with a readiness/repair finding, or the agent
retries without changing the action.

- Inspect the resolve payload: reason code, `readiness`, `repair` packet, and
  missing evidence. See [readiness](../../reference/readiness.md) and
  [resolve](../../reference/resolve.md).
- Do not retry unchanged. Apply the repair packet (missing scope, evidence,
  constraint, or alternative) and re-ask.
- Verify: the new ask has a different `action_identity`/fingerprint and the
  readiness dimensions no longer include the failed check.

## 2. Constrained allow

**Symptom:** the approver wants to allow only a narrower action.

- Pick a constraint that names an **enforcer** and a matching fingerprint; an
  unenforceable constraint is advice, not an allow.
- Confirm the returned decision carries `decision=allow` plus the selected
  constraints; the agent must enforce them before acting.
- Verify: the outcome/evidence shows the constraints and the enforced result.
  See [constrained allows](../../reference/constrained-allows.md).

## 3. Bundle / handoff / incident mode

**Symptom:** several related asks need one review, or a reviewer must hand off.

- Bundles are derived views over individual asks; there is **no bundle-level
  approval**. Answer each ask.
- Handoff carries the remaining TTL, questions, evidence, and both principals;
  the new reviewer must still authenticate.
- Incident mode is a config-declared owner/reason with a capped scale; denies
  still deny and every change is chained.
- Verify: [operations](../../reference/operations.md), the cards, and the audit
  chain show the handoff/incident events with the original ask intact.

## 4. Outcome closure and divergence

**Symptom:** an approved action has no recorded outcome, or the observed result
differs from the approved identity.

- Record a closure with a bounded receipt; the closure is an observation and
  never rewrites the decision.
- On divergence, acknowledge it explicitly. The card shows
  `UNACKNOWLEDGED`; there is no absorption or auto-approval path.
- Verify: `agentinbox report`, the outcome record, and the chained divergence
  event. See [outcomes](../../reference/outcomes.md).

## 5. Grants and compression

**Symptom:** a window/grant is over-used, expired, revoked, or two grants are
active.

- Check the burn-down and the window's `max_uses`/`max_per_minute`; the next ask
  reverts to pending when exhausted.
- Two active session grants are refused; end the old session or revoke the
  grant loudly.
- Verify: issued/used/expired/revoked events are chained; a spent grant stays
  visible on the card as `spent`. See [grants](../../reference/grants.md) and
  [compression](../../reference/operations.md).

## 6. Insights and calibration

**Symptom:** an insight suggests a tuning change, or a per-principal view is
requested.

- Treat insight output as advisory. Applying a recommendation is a reviewed
  config/PR change, not an automatic action.
- Per-principal calibration requires a governance principal and writes an
  access event; default output is aggregate.
- Verify: decisions are unchanged; the `insight-action` records reviewer and
  origin. See [insights](../../reference/insights.md).

## Release-day checks

- `make gate` must be green (claims lint, evidence scan, matrix, tests,
  coverage, ruff/mypy).
- The release docs index is [README.md](README.md); the plan is
  [RELEASE_PLAN.md](RELEASE_PLAN.md).
- A failed release is fixed forward or yanked; never rewrite a published tag.
