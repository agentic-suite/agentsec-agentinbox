# Approver guide (v0.1.0)

You are the human half of the gate. The card gives you enough to decide in seconds; the record proves
who said yes.

**Contents**

- [The card](#the-card)
- [Answering](#answering)
- [Rules of thumb](#rules-of-thumb)
- [After the decision](#after-the-decision)
- [Where to go next](#where-to-go-next)

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
- A constrained allow is narrower than a plain approve — pick it when the full action is too broad.
- A readiness/repair packet means the ask is missing evidence; deny and let the agent repair it.

## After the decision

`agentinbox export --ask <id> --out /secure/export.jsonl` gives the evidence (mode `0600`).
`agentinbox verify-log` proves the chain. `agentinbox report --json` is local-only.

## Where to go next

- [Quickstart](../tutorials/quickstart.md) — install → first approval.
- [Card reference](../reference/card.md) — every field explained.
- [Constrained allows](../reference/constrained-allows.md) — narrower approvals.
- [Readiness](../reference/readiness.md) — why an ask was rejected.
- [Outcomes](../reference/outcomes.md) — recording what actually happened.
- [Grants](../reference/grants.md) — time-boxed windows and burn-down.
- [Expansion runbooks](../release/v0.1.0/RUNBOOKS.md) — operational procedures.
- [Claims and limitations](../compliance/claims-and-limitations.md) — what v0.1.0 does not claim.
