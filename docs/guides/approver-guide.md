# Approver guide (v0.1.0)

You are the human half of the gate. The card gives you enough to decide in seconds; the record proves
who said yes.

## The card

- **ACTION** — tool, action, arguments (labelled `[untrusted: tool output]`), fingerprint, class,
  criticality, requested by. `[unverified]` means the producer did not sign the field; treat it as a
  claim, not a fact.
- **POLICY** — reason code, rule, policy version, clause. The inbox does not invent policy.
- **BLAST RADIUS** — resource, reversibility, affected estimate, environment, data class, credential
  class. `unknown` is honest, never a guess.
- **SESSION SO FAR** — tier, escalations, prior asks, session tail, flags, alternatives, transitions.

## Answering

| Terminal choice | Meaning |
|---|---|
| `a` | approve (typed confirmation for irreversible classes) |
| `d` | deny — a reason is required where configured |
| `?` | details/help |
| `q` | leave pending (the TTL still denies later) |

Scripts and non-interactive shells **cannot** approve; they receive `pending`. Only an authenticated
channel with a single-use claim records a decision.

## Rules of thumb

- Deny when a field you need is `unknown`; a missing-context ask is not a safe ask.
- Never approve your own request (self-review is denied by default).
- Late answers are visible no-ops; the winner and time are recorded.
- Offline day: terminal, inbox, audit, export, and report all work with no network.

## After the decision

`agentinbox export --ask <id> --out /secure/export.jsonl` gives the evidence (mode `0600`).
`agentinbox verify-log` proves the chain. `agentinbox report --json` is local-only.
