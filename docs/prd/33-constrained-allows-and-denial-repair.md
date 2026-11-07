# PRD 33 — Constrained Allows & Denial Repair

**BLUF:** the gate grows from *approve/deny* to **shape the action**: the inbox suggests **safe narrower
variants** (staging-only, dry-run, caps, timeboxes), lets the human pick or edit one, and returns the producer
a **machine-readable denial repair packet** — what was missing, what was too broad, what would have passed.
Deny becomes a lesson, not a dead end; the safest reasonable allow becomes the easiest path.

**Status:** Draft — v0.1.0 (2026-11-06) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209

## Why this is compelling

Every real reviewer says a fourth thing — **"yes, but smaller"** — and no existing surface lets them say it.
This PRD extends [PRD 24](24-constrained-approvals-and-effects.md) (R14/R15 effect envelopes, constraints,
edits) with the two halves that make it a *product*: **producer-advertised alternatives rendered as one-click
choices**, and **denials that teach**. It inherits PRD 24's enforcement honesty clause verbatim: the inbox
records and returns; the enforcer enforces; a constraint no enforcer can honor is not offered.

## CUJs

| CUJ | Story | Priority |
|---|---|---|
| **CUJ-15** | "Approve safely in 5 s because the system already narrowed the blast radius" — the card proposes staging/read-only/subset variants, the human picks one | P0 |
| **CUJ-16** | "I denied it once; the agent resubmits correctly without making me teach it again" | P0 |
| **CUJ-29** | "Approve the safe subset in one move" — one click on a constrained allow, not a hand-written instruction | P0 |
| **CUJ-30** | "Deny once, teach permanently" — the repair packet is durable guidance, not a one-off string | P1 |
| **CUJ-31** | "Tell the agent the shape of a fix, not just 'no'" — constraint schemas, missing evidence, scope edits | P0 |
| **CUJ-32** | "Make narrow approvals safer than broad approvals are easy" — UX nudge: the constrained choice is the *first* choice | P0 |

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R87** | **Producer-advertised alternatives.** Producers may attach `alternatives[]` to an ask: named, scoped, constraint-carrying variants of the same intent (`staging`, `dry_run`, `max_rows=100`, `ttl=1h`), each with its own canonical fingerprint. The card renders them as selectable choices **above** the raw approve. | v0.1.0 | An ask with 2 alternatives renders both; choosing one yields `allow_with_constraints` bound to that alternative's fingerprint |
| **R88** | **Constraint suggestion heuristics.** When a producer advertises no alternatives, the card may suggest class-generic narrowings (environment demotion, dry-run, subset) **labelled as suggestions** — never executed, never recorded as the approver's intent unless picked. | v0.1.0 | Suggested-but-unpicked variants leave no constraint in the resolve |
| **R89** | **Denial repair packet.** Every deny may carry structured repair guidance: `violated_invariant`, `missing_evidence[]`, `suggested_scope`, `safe_alternative`, `retry_worthiness` (`pointless / conditional / likely`), `required_tier`. It rides the resolve, the audit detail, and (redacted) the agentwatch event. | v0.1.0 | A denied producer receives the packet without any human parsing; `retry_worthiness=pointless` suppresses blind retries in the demo agent |
| **R90** | **Human-applied edits.** For classes declaring an edit schema (PRD 24 R15), the approver's edits are re-canonicalized and re-fingerprinted; the **edited action is the approved action**; both original and edited forms are recorded. | v0.1.0 | Edited approval executes the edited form (SC-30); out-of-schema edits are rejected with the field named |
| **R91** | **Constraint provenance.** Every applied constraint/edit records who applied it (principal + channel), why (chosen alternative vs authored edit), and its narrowing diff vs the original ask. | v0.1.0 | A review of any constrained approval reconstructs exactly what was narrowed, by whom |
| **R92** | **Repair packet recall.** When a producer resubmits a previously denied intent, the card surfaces the prior denial reason and the packet's suggested scope — so the *second* reviewer sees the history, and the *agent* sees whether it addressed it. | v0.1.0 | Resubmission fixture renders prior-reason context; unresolved prior objections are labelled |
| **R93** | **No-constraint-without-enforcer.** A constraint alternative is offered only when the producer declares its enforcer binding (PRD 24 clause); undeclarable constraints render as plain text suggestions, never as choices. | v0.1.0 | An unbindable "max_rows" renders as advice; picking it is impossible |

## Resolve vocabulary (extends `resolve/1.0`)

`allow_with_constraints` and `allow_with_edits` (PRD 24 R20) carry: `constraints[]` (id, params, enforcer_ref),
`edits[]` (field, from, to), the chosen alternative's fingerprint, and `repair` on denials. Old clients that
only read `status` see `deny`/`allow` respectively — **additive, never breaking**.

## Non-goals

- No hidden standing approvals (PRD 27 owns those, with governance).
- No silent rewriting of producer asks; edits are explicit, diffed, recorded.
- No constraints persisting beyond the ask unless PRD 27's grant machinery adopts them.

## Scenario catalog additions

| Scenario | What it proves |
|---|---|
| **SC-71** | One-click constrained allow produces the constraint set; exceeding it denies at the enforcer with the constraint id named |
| **SC-72** | A denial repair packet drives a demo agent from deny → corrected resubmission → allow with no human in the loop |
| **SC-73** | A human edit re-fingerprints; the enforcer executes the edited form, not the original |
| **SC-74** | An unbindable constraint renders as advice and cannot be picked |

## Traceability

| Requirement | Test |
|---|---|
| R87–R89, R92–R93 | `tests/constraints/` (alternatives, repair packet, recall, enforcer binding) |
| R90–R91 | `tests/constraints/test_edits.py` (re-fingerprint, provenance) |
| SC-71..74 | executed at the next field-test release (extends M24) |
