# Decision-card reference (v0.1.0 · M5)

**BLUF:** `build_card(ask, now=…)` produces a structured card; `card.render(surface)` renders it for `text`,
`terminal`, `desktop`, or `ci`. The four blocks are fixed, missing data is `unknown`, and untrusted text is
inert plain text with a source label and caps.

- Design: [`docs/design/v0.1.0/card.md`](../design/v0.1.0/card.md)
- Requirements: R1, E5

## Example

```text
ASKS: ask_9f2b7c31a4d0e5f6   status=pending   ttl=4m00s
fingerprint: sha256:5c1f4a2b9d01…

ACTION
  tool: [untrusted: tool output] shell
  action: [untrusted: tool output] run_command
  arguments: [untrusted: tool output] command=psql prod -c 'DROP TABLE customers'; timeout_s=30
  fingerprint: sha256:5c1f4a2b9d01…
  class: irreversible
  criticality: critical
  requested by: maya@team

POLICY
  reason code: human_gate_required
  rule: irreversible-ask-gate
  policy version: v0.4.2
  clause: [untrusted: tool output] permit advice { human_gate = "required" }

BLAST RADIUS
  resource: [untrusted: tool output] db:prod/customers
  reversibility: irreversible
  affected estimate: [untrusted: tool output] unknown
  environment: production
  data class: customer-pii

SESSION SO FAR
  session: sess_20261106T030412Z
  agent: agent://ops-agent/7f31
  session tail: [untrusted: tool output] read_file.read
  flags: code_freeze_window
  alternatives: staging database
  transitions: 2

REDACTIONS
  arguments.command: [SECRET x1]

Answer with: agentinbox answer <id> --approve|--deny  (q leaves it pending)
```

## Rules

| Rule | Behavior |
|---|---|
| missing field | literal `unknown` (no blank line) |
| unknown reversibility on irreversible class | `unknown (irreversible class)` |
| untrusted text | `[untrusted: tool output]` prefix, plain text, no markup/links/buttons |
| control / zero-width / bidi chars | stripped |
| field / card size | 512 chars / 4000 chars, visible `+N chars omitted` |
| redactions | `field: [CLASS xN]` — never the value |
| surfaces | same core blocks; footer differs (`terminal`, `desktop`, `ci`) |
| colour | never the sole signal; `NO_COLOR` safe |

## Corpora

`tests/fixtures/card_corpus/corpus.json` (checksum in `corpus.sha256`): 12 clean, 12 degraded, 10 poisoned.
The poisoned set is the release-gating injection posture (SC-23 groundwork); M24 owns the study answers.
