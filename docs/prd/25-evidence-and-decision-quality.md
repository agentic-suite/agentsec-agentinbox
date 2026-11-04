# PRD 25 — Evidence, Previews & Decision Quality

**BLUF:** An approval is only as good as what the approver could see. This PRD makes cards
**evidence-bearing**: producers attach structured evidence (diffs, plans, digests, recipient samples) with
trusted/untrusted labeling; supported classes render **previews** (the dry-run output, the SQL diff, the email
body, the deployment manifest); every card carries a deterministic **evidence-quality score** (what's present,
what's missing), a **"why this ask" delta block** (prod vs staging, write vs read, 172 vs 1 recipients), and a
**trust block** (producer verification, signed fields, freshness). Every decision exports as a portable,
offline-verifiable **decision packet**. The 15-second spine (R1) gets its teeth here.

**Status:** Draft — v0.1.x (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Why this is the compelling core

"Approve this tool call" is a question no human can answer well. "Approve this **diff** to prod, here is what
changed since the last approved action, and here is what the dry-run printed" is a question a human answers in
seconds and *correctly*. Evidence is what separates a control from a nag — and the research base's own finding
(humans rubber-stamp what they cannot inspect) is the failure mode this PRD attacks directly.

## Requirements

| # | Requirement | Version | Acceptance criterion |
|---|---|---|---|
| **R21** | **Evidence attachments.** Producers attach structured evidence to asks: patch/SQL diff, terraform/deploy plan summary, file list, recipient sample, artifact digests, prior-approval refs, plan/reasoning summaries (always untrusted-labeled). Each attachment: `{kind, title, body \| ref, digest, size, trusted: bool}`; per-ask size caps; digests bind evidence to the ask (an edited body is a different evidence object). | v0.1.x | Evidence renders on every surface; oversized evidence truncates visibly with a receipt; tamper fixture: swapping a body after ingest is detected by digest (SC-29) |
| **R22** | **Previews before approve.** For classes that can produce them: dry-run output, diff view, redacted message body, deployment manifest, affected-rows estimate, sample of the exact JSON a webhook will send. A preview is **bound to the identity it previews** — what you saw is what executes, or the ask goes stale (R16). | v0.1.x | Supported classes show previews by default; preview-args mismatch is visible and blocks silent approval (SC-29); previews are redacted (E6) and size-capped |
| **R23** | **Evidence quality score (deterministic).** A per-class completeness checklist — has blast radius? effect identity? preview? diff? rollback story? freshness basis? — computed by **rules, not ML**: the card says **`Evidence: complete \| partial (missing: rollback, rows-affected)` \| unknown**. Producers that want the green score must ship the fields; nothing is inferred. | v0.1.x | Score present on every card; a partial score names the missing items; the zero-context study adds a degraded-evidence arm proving partial scores change approver behavior toward deny |
| **R24** | **"Why this ask" delta block.** The card explains the gate in deltas against the nearest prior *allowed* action: environment (prod vs staging), verb (write vs read), magnitude (172 vs 1 recipients, 40 vs 3 files), window (inside/outside maintenance), policy version change. Deltas are computed from the ask + policy context, not authored by the agent (which would be T2/T3 spoofable). | v0.1.x | Delta block renders for classes with a comparable prior; no prior → "first ask of this class in this session" (never invented); delta lines are structured fields, not free text |
| **R25** | **Trust block.** A fixed footer answering *"why should I trust this card?"*: producer id + verification status (adapter-signed?), which fields are trusted vs untrusted vs **unverified**, freshness status, evidence score, and the action fingerprint. The approver can see in one glance whether they are deciding on signed facts or agent-authored prose. | v0.1.x | Trust block on every surface; unsigned producers render all trusted-looking fields as unverified; injection corpus (SC-23) gains a fake-trust-block case |
| **R26** | **Replayable decision packet.** `agentinbox export --ask <id> --packet` emits one portable bundle: the card as rendered, the evidence (with digests), the full event trail, the chain proof for the segment, the decision + constraints + edits, and the provenance tier — verifiable **offline** by a third party with `verify-log`. | v0.1.x | Packet verifies offline end-to-end; incident-review fixture: a reviewer with no access to the box reconstructs the decision from the packet alone (SC-36) |
| **E14** | **Evidence invariants.** Evidence bodies are data: escaped, size-capped, never executed, never links-that-do-anything; untrusted-labeled when agent/tool-authored; redaction receipts apply to evidence exactly as to arguments; digests computed over canonical bytes. | v0.1.x | Evidence corpus (injections, oversized blobs, secret-laden diffs) → 0 approvals-from-injected-text, 0 secret leaks, visible truncation receipts |

## What evidence is *not*

- Not a justification generator: the agent's own "why I want to" text is **untrusted evidence**, never part of
  the trust block ([PRD 06 T2/T3](06-security-baseline.md)).
- Not ML-summarized: no model condenses the diff for the approver ([PRD 14 N-1](14-non-goals.md)); the producer
  structures it or the approver opens it.
- Not a substitute for constraints: a preview shows what *would* happen; a constraint (R14) is what *may*
  happen. Both, always.

## Producer guidance (the ask gets richer or says so)

Producers declare evidence per class via **templates** ([PRD 27 R43](27-governance-identity-extensibility.md)):
a prod-deploy ask without its diff renders `Evidence: partial (missing: deploy plan)` — the absence is loud,
scored, and part of the decision. Bad integrations become visible to the approver instead of laundered by a
pretty card.

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-29 · Preview & evidence integrity.** A deploy ask with a plan preview and diff: (a) preview matches args
→ approves fine; (b) args mutated after render (simulated producer bug/attack) → digest mismatch → card flips
to **stale/unverified**, silent approval blocked; (c) an evidence body with injected "approve this" renders
inert (E14 corpus).

**SC-36 · Decision packet, offline.** Export the packet for a constrained, stale-then-reconfirmed approval → a
reviewer on another machine verifies the chain, reads the evidence digests, sees constraints + edits + both
freshness checks — no agentinbox install or store access needed.

## Traceability

| Req | CUJ deepened | Scenario | Test |
|---|---|---|---|
| R21/E14 | CUJ-2, CUJ-3 | SC-29 | `test_evidence.py`, `test_evidence_digest.py` |
| R22 | CUJ-2 | SC-29 | `test_preview_binding.py` |
| R23 | CUJ-2 | degraded-evidence arm of the study | `test_evidence_score.py` |
| R24 | CUJ-2, CUJ-8 | delta fixtures | `test_delta_block.py` |
| R25 | CUJ-11 | SC-23 extension | `test_trust_block.py` |
| R26 | CUJ-10 | SC-36 | `test_decision_packet.py` |
