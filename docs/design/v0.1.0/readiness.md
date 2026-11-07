# Ask readiness design — v0.1.0 (M26)

**BLUF:** every ask is scored before delivery across six deterministic dimensions; a below-threshold or
contradicting ask is either **rejected to the producer with a machine-usable repair contract** or
delivered with a visible quality banner. Scoring is advisory to delivery only — it never approves, and a
low score never silently allows.

- **Milestone:** M26 ([WBS Part 14](../../wbs/v0.1.0/wbs-v0.1.0-part14-quality-constraints.md), issues #306–#317)
- **Requirements:** PRD 32 R78–R86 · CUJ-25..28 · SC-68/69/70
- **Module:** `agentinbox/readiness.py` · **Config:** `[classes.<name>]` readiness keys

---

## 1. The six dimensions (R78)

| Dimension | Rule | Fix text on failure |
|---|---|---|
| **completeness** | arguments non-empty; `policy_ref.rule_id` and `clause` non-empty; `requested_by`, `environment`, `data_class` non-empty; context present | "fill <field>" |
| **target_specificity** | `context.blast_radius.resource` names a specific target (not empty, `unknown`, or generic: "the database", "prod", "it", "the service") | "name the exact resource" |
| **reversibility_clarity** | `blast_radius.reversibility` ∈ `reversible` / `partially_reversible` / `irreversible` | "state reversibility" |
| **evidence_presence** | against the class's `required_evidence`; `strong` (all) / `partial` (some) / `weak` (none but optional) / `absent` (none required-missing) | "attach: <missing>" |
| **trust_provenance** | `1.0` signed producer, `0.5` unsigned (fields render unverified) | "sign the ask with a producer key" |
| **contradiction** | `1.0` no contradiction, `0.0` any | the contradiction ids |

Score = mean of the six, rounded to 4 dp. Band: `green ≥ 0.80`, `yellow ≥ 0.50`, `red < 0.50`.
The score is **derived**: any producer-supplied `_readiness` is stripped as reserved metadata.

## 2. Contradictions (R80)

| Id | Rule |
|---|---|
| `staging_vs_prod` | environment ∈ {staging, dev, test} while the resource names prod/production |
| `readonly_vs_destructive` | context claims `read_only`/`mode=read-only` (or `arguments.dry_run`) while arguments contain destructive verbs (`drop`, `delete`, `truncate`, `rm -rf`, `force`, `overwrite`, `alter`) |
| `low_criticality_vs_irreversible` | criticality ∈ {low, info} while class is `irreversible` or reversibility is `irreversible` |
| `unverified_trust_claim` | unsigned producer while `context.trust` claims `verified`/`authenticated` |

A contradicting ask is **delivered with the flag** by default; with `on_contradiction = "reject"` the
class rejects it at ingest. There is no silent unflagged delivery.

## 3. Rejection + repair contract (R79/R84, SC-68)

With `readiness_enforce = true` on the class and `score < readiness_min_score` (or
`on_contradiction = "reject"`), ingest raises `ReadinessRejection` **before any store write**:

```json
{
  "error": {
    "field": "readiness",
    "message": "ask is not decisionable",
    "reason_code": "ask_not_decisionable",
    "dimensions": [
      {"name": "target_specificity", "fix": "name the exact resource", "score": 0.0}
    ],
    "contradictions": ["staging_vs_prod"],
    "retry": "after-repair",
    "readiness": {"score": 0.42, "band": "red", "dimensions": {"...": "..."}}
  }
}
```

Zero pending rows, zero deliveries, one structured response. The API includes the same body; the CLI
prints the repair JSON on `ask --file`.

## 4. Evidence sufficiency + freshness (R81/R82, SC-70)

`required_evidence` is per class (e.g. `["diff", "logs"]`); the same weak ask scores differently for a
read-only class (no requirements → strong) and an irreversible class (missing diff → weak/absent). The
label **names the missing dimension**, never a bare "insufficient".

Freshness is computed only from producer-pinned data: each evidence artifact may carry `at`/`fetched_at`
and `digest`. Age > `evidence_max_age_seconds` → `stale`; missing basis → `unknown freshness`; mixed →
`mixed`. Inferred freshness is forbidden.

## 5. Quality banner (R83) and similar cases (R85)

The card renders one line above ACTION, only when not fully green:

```text
READINESS: yellow · missing target_specificity · contradictions: none · evidence: partial (no diff)
```

Up to three prior asks with the same class+tool are rendered under SESSION SO FAR as `precedent`
(ask id, outcome, differing fields, reason); the line never says "approve". Similar cases are read from
the audit chain (no new store query).

## 6. Config (R86)

```toml
[classes.irreversible]
readiness_enforce = true
readiness_min_score = 0.6
required_evidence = ["diff", "logs"]
evidence_max_age_seconds = 86400
on_contradiction = "reject"   # default "deliver"
```

`readiness_enforce = true` without `readiness_min_score` is a load error naming the class. The whole
block is opt-in: existing configs without it keep legacy behavior (score computed, no rejection). A
`doctor --explain` line prints the effective readiness settings per class.

## 7. Tests

`tests/readiness/`: scorer dimensions, 12-case contradiction corpus, rejection stores nothing +
structured contract, per-class evidence difference, freshness, banner ordering, similar cases, config
load errors, and a demo repair loop (reject → fix → pass).
