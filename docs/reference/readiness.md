# Ask readiness reference (v0.1.0 · M26)

**BLUF:** every ask is scored before delivery across six deterministic dimensions. A low-score or
contradicting ask is rejected to the producer with a machine-usable repair contract, or delivered with a
visible banner. The score is advisory to **delivery**; it never approves anything.

- Design: [`docs/design/v0.1.0/readiness.md`](../design/v0.1.0/readiness.md)
- Module: `agentinbox/readiness.py` · **Tests:** `tests/readiness/`

## Dimensions and score

| Dimension | Measures | Fix text |
|---|---|---|
| `completeness` | arguments, policy rule/clause, requester, environment, data class, context | `fill <field>` |
| `target_specificity` | a named resource (not `unknown` / "the database") | `name the exact resource` |
| `reversibility_clarity` | `reversible` / `partially_reversible` / `irreversible` | `state reversibility` |
| `evidence_presence` | the class's `required_evidence` | `attach: <missing>` |
| `trust_provenance` | signed producer (1.0) vs unsigned (0.5) | `sign the ask with a producer key` |
| `contradiction` | 1.0 clean, 0.0 any contradiction | `remove: <ids>` |

Score = mean of the six. Bands: **green ≥ 0.80**, **yellow ≥ 0.50**, **red < 0.50**. The score is
derived; a producer-supplied `_readiness` is stripped as reserved metadata.

## Contradictions

`staging_vs_prod` · `readonly_vs_destructive` · `low_criticality_vs_irreversible` ·
`unverified_trust_claim`. Default: deliver **with the flag** (the banner and `_readiness` carry it).
With `on_contradiction = "reject"`, ingest rejects the ask.

## Rejection and the repair contract

Enabled with `readiness_enforce = true` and `readiness_min_score`. Ingest rejects **before any store
write**:

```json
{
  "error": {
    "field": "readiness",
    "message": "ask is not decisionable",
    "reason_code": "ask_not_decisionable",
    "dimensions": [{"name": "target_specificity", "fix": "name the exact resource", "score": 0.0}],
    "contradictions": [],
    "retry": "after-repair",
    "readiness": {"score": 0.5, "band": "yellow", "dimensions": {}, "evidence": "absent", "freshness": "unknown freshness"}
  }
}
```

Zero pending rows, zero deliveries. `agentinbox ask --file` prints the same JSON on stderr; the HTTP API
returns it with `400`.

## Evidence and freshness

`required_evidence` is per class. The same ask scores differently for a class that demands `["diff",
"logs"]` and one that demands nothing (`strong` vs `absent`/`weak`). Labels name the missing dimension.

Freshness uses only producer-pinned `at`/`fetched_at`: older than `evidence_max_age_seconds` → `stale`;
no basis → `unknown freshness`; a mix → `mixed`. Freshness is never inferred.

## Card banner and precedent

A non-green card renders one line above ACTION:

```text
READINESS: yellow · missing target_specificity · contradictions: none · evidence: partial
```

Up to three prior same-class+same-tool asks render under SESSION SO FAR as
`precedent only: <ask_id> <outcome> (env=…, criticality=…)`. Precedent is never a recommendation.

## Config

```toml
[classes.irreversible]
ttl_seconds = 300
readiness_enforce = true
readiness_min_score = 0.6
required_evidence = ["diff", "logs"]
evidence_max_age_seconds = 86400
on_contradiction = "reject"   # default "deliver"
```

`readiness_enforce = true` without `readiness_min_score` is a load error naming the class.
`doctor --explain` prints the effective readiness settings per class. Classes without the block keep
legacy behavior (score computed and stored, no rejection).
