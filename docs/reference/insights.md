# Insights reference (v0.1.0 · M31)

**BLUF:** aggregated, redacted governance insights with a reviewed action path — no auto-tuning.

- Design: [`docs/design/v0.1.0/insights.md`](../design/v0.1.0/insights.md)
- Module: `agentinbox/insights.py` · **Tests:** `tests/insights/`

```toml
[insights]
governance_principals = ["auditor"]
approval_threshold = 20
deny_threshold = 10
hotspot_threshold = 3
stale_after_seconds = 86400
```

## Compute

```python
from agentinbox.insights import compute_insights, export_insights

insights = compute_insights(store, config)     # repetitive-approval, deny-cluster,
                                               # escalation-hotspot, evidence-gap, outcome-tuning
export_insights(insights)                      # insights/1.0, scanner-checked
```

Each insight carries `counts`, `time_range`, one `representative_ask`, a recommendation, and a proposed
diff. Argument values are never included; expired insights are not returned.

## Calibration

```python
calibration(store, config)                                  # aggregate only
calibration(store, config, principal="auditor")             # gated + access-logged
```

Per-principal rows require `governance_principals`; access writes a chained
`insight-calibration-access`. There are no rankings.

## Action

```python
to_action(store, insight, kind="config_diff", reviewer="alice")
```

Kinds: `config_diff` (reviewable TOML comment block), `runbook` (task), `grant` (proposal). The action,
reviewer, and originating insight are recorded as `insight-action`; applying is a git-reviewed PR.
