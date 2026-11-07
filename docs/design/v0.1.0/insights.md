# Policy learning & governance insights design — v0.1.0 (M31)

**BLUF:** insights turn stored decisions into **reviewed proposals**, never automatic policy. Every
payload is aggregated and redacted: shapes, counts, time ranges, and a representative ask id — never raw
arguments. Queries are read-only except an explicit calibration access log and an explicit action record.

- **Milestone:** M31 (WBS Part 16, issues #365–#378) · **Requirements:** PRD 37 R115–R122, SC-87..90
- **Module:** `agentinbox/insights.py` · **Tests:** `tests/insights/`

## 1. Repetitive approvals (R115)

Groups asks by `class|tool|action|argument-shape` (key names + value types only). At or above
`[insights].approval_threshold` (default 20) with low variance (few denials/divergences) it emits one
insight proposing a bounded grant, standing rule, or producer self-certification. `counts`, `time_range`,
and one representative ask id are included; the raw corpus never is.

## 2. Deny clusters (R116)

Clusters human denies by `reason_code` + shape at `deny_threshold` (default 10) and recommends a TTL
change, class split, or evidence relaxation. It reports noise; it changes nothing.

## 3. Escalation hotspots (R117)

Groups `escalated`/`expired` transitions by class × tier × UTC hour at `hotspot_threshold` (default 3)
and recommends an on-call roster (night) or a daytime rota/TTL change.

## 4. Calibration (R118)

Aggregate view of approve/deny counts, approve rate, deny reasons, and median time-to-answer by shape.
Per-principal rows require the requester in `[insights].governance_principals`; every access appends a
chained `insight-calibration-access` event. No rankings or individual scoring.

## 5. Evidence gaps and outcome tuning (R119/R120)

- Denied asks expose `_readiness.missing` dimensions per class → “consider requiring `<dimension>`”.
- Closures with `exceeded`/`divergent` for a class (≥2) propose typed confirmation, a tier bump, or a
  shorter TTL. Both are proposals only.

## 6. Insight to action (R121)

`to_action(..., kind="config_diff"|"runbook"|"grant", reviewer=...)` returns a reviewable body and
appends a chained `insight-action` event with the insight id, kind, reviewer, and origin. Applying the
diff remains a git-reviewed config PR; there is no inbox apply button.

## 7. Hygiene (R122)

Computation reads stored redacted payloads and never copies argument values. `export_insights` runs the
shared evidence scanner over the canonical export and refuses on findings. Insights expire
`stale_after_seconds` after their last observation.

## 8. Tests

`tests/insights/test_insights.py`: 20-approval redacted insight, 10-deny cluster, hotspot, evidence gap,
divergence hardening proposal, aggregate vs gated calibration (+ access log), action export/origin,
stale expiry, and scanner-clean export.
