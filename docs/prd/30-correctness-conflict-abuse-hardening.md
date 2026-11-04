# PRD 30 — Correctness, Conflict & Abuse Hardening (the final layer)

**BLUF:** PRDs 24–29 made the inbox *powerful* — grants, suppressions, edits, constraints, review loops,
windows, writebacks. This PRD makes that power **safe**: one **precedence lattice** that answers "which rule
wins?" for every conflict; one **formal state machine** with explicit legal/illegal transitions; **idempotent,
never-authoritative** outbound side effects; a **frozen schema-evolution policy**; **producer-asserted trust
rejected** by construction; **hard limits on review-loop abuse**; **monotonic-narrowing edits** (scope escapes
impossible); a **shared-machine provenance model**; **sleep/wake/DST time semantics**; **redaction for every
derived artifact**; a **no-advisory-allows rule** when enforcement can't be proven; **revocation semantics**
for every expiring artifact; **governed training corpora**; a **localhost web-UI security model**; and
**dead-man detection** for systemic human-coverage failure. If the set ships without this PRD, the slate in
24–29 would be a bundle of sharp edges held together by hope.

**Status:** Draft — hardening for PRDs 24–29 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## 1. The precedence lattice (R68 — which rule wins?)

Every mechanism that can influence an ask composes into **one total order**, evaluated at resolve time. Higher
number = wins. When two entries at the same level conflict, the **more restrictive** outcome wins.

| L | Level | Examples | Beats |
|---|---|---|---|
| **1** | **Hard policy deny** (agentpolicy `deny`) | destructive-command forbid | everything |
| **2** | **Freeze / incident deny-only classes** (R32) | external-send during freeze | 3–8 |
| **3** | **Freshness failure** (R16: stale, unreconfirmed) | repo moved, unreconfirmed | 4–8 |
| **4** | **Provenance failure** (R39: below `min_tier`) | T1 answer on a T3 ask | 5–8 |
| **5** | **Time-window failure** (R52: outside effective window; expiry) | pre-22:00 execution; TTL elapsed | 6–8 |
| **6** | **Dependency block** (R19: blocker unresolved) | deploy before db-migration approved | 7–8 |
| **7** | **Explicit human answer** (approve/deny/needs_changes, identity-bound) | the decision itself | 8 |
| **8** | **Convenience rules** — session grant (R51), suppression (R53), standing rule (R37) | auto-answers | — |

**Composition rules:** constraints/edits ride the winning level and are always evaluated (a grant "answers" an
ask, but its constraints still bind); quorum (R38) is a *shape* of level 7, not a level; when levels tie
restrictively, the deny-shaped outcome wins. **Acceptance:** a conflict matrix fixture set — every pair of
mechanisms across levels resolves to the lattice's answer, deterministically (SC-54).

## 2. The formal state machine (R69 — legal transitions only)

The lifecycle becomes a **single versioned graph** with exactly these states and edges; anything else is an
`illegal-transition-rejected` event:

```
pending ──► claimed ──► pending            (claim/release; never a decision)
pending ──► needs_changes ──► revised ──► pending      (hold-and-clarify, ≤ max_rounds)
pending ──► needs_changes (terminal; thread re-ask = new ask, same review_thread_id)
pending ──► stale ──► pending              (re-confirm resets stale; clock unchanged)
pending ──► waiting_on_dependency ──► pending
pending ──► approved | approved_constrained | approved_edited | denied | expired
pending ──► auto_answered_by_rule (grant/suppression/standing; rule id recorded)
pending ──► flood_denied | cancelled | suppressed_expired(no-op observe)
ALL terminal ──► (late-answer observation only; never a state change)
```

**Rules:** states are **append-only forward** — no state is ever revisited except the explicit
`stale→pending(re-confirmed)` and review-loop returns, each bounded by R70; terminal is terminal
([PRD 15](15-data-model.md) holds); every transition carries the causative principal/rule. **Acceptance:** a
state-machine fuzz fixture drives every illegal edge (approved→denied, expired→approved, revised after terminal…)
and every one is rejected + logged (SC-55).

## 3. Outbound idempotency & exactly-once (E17)

Every external side effect — writeback (R64), hook (R44), check update, ticket transition, attestation export —
carries an **idempotency key** (`event_id + target`), retries are safe, duplicates are detected and logged as
no-ops, and **"decision recorded" and "side effect happened" are separate truths** (a dead GitHub token never
revises the decision; the writeback ledger is replayable). **Acceptance:** each outbound target demonstrates
at-least-once delivery + exactly-once effect under forced retries (SC-56).

## 4. Schema & version evolution policy (E18)

One frozen policy for **every** versioned surface — `ask/1.0`, `resolve/1.0`, evidence objects, grants, review
threads, attestations, the event vocabulary, config: **additive-only within v0.x**; unknown fields are
**tolerated-and-preserved** (never silently dropped); a producer speaking an older schema validates; a
*removed/retyped* field requires a major contract bump and a dual-write migration window; `doctor` names any
mismatched versions it can see. **Acceptance:** old-payload-under-new-binary and new-payload-under-old-binary
fixtures both behave per policy (tolerate or refuse loudly — never guess) (SC-57).

## 5. Producer cannot self-assert trust (E19)

**Trust class is computed by the core, never declared by the producer.** A producer may *sign* evidence
(provenance — "this blob came from tool X") and may *propose* a trust class, but the core re-classifies from
adapter identity + content scanning; **signed ≠ trusted** (a signed blob of agent prose is still untrusted
rendering). Adapter trust comes from the configured producer keys ([PRD 18](18-approval-integrity.md)), and
each adapter's default trust mapping ships in the conformance kit. **Acceptance:** a producer marking its blob
`trusted=true` renders untrusted; signed-untrusted renders as "verified origin, untrusted content" (SC-58).

## 6. Review-loop abuse limits (R70)

`needs_changes` is abusable into an infinite clarification treadmill. Hard limits, config-per-class with
defaults: **max hold rounds** (default 2) before forced terminal resolution or re-ask; **max evidence
revisions** per thread (default 4); **max thread entries** retained (older entries collapse to digests);
evidence revisions count against the producer's **flood budget** (R7) — a treadmill is a flood by another name.
**Acceptance:** a looping producer hits the ceiling and gets a terminal outcome; thread size stays bounded;
limits are visible in `doctor --explain` (SC-59).

## 7. Scope-escape protection for edits and constraints (R71)

**Edits are monotonic-narrowing by default.** An edit that broadens scope — more recipients, staging→prod,
one repo→org-wide, `dry_run: true→false`, higher caps — is **rejected** unless the class declares that field
explicitly broadening-allowed, in which case it requires **the highest provenance tier configured for the
class** and renders the widening loudly on the card + packet. Constraints may only tighten what the producer
offered. **Acceptance:** every widening-edit fixture is rejected (or tier-gated + loud); a narrowing-only
invariant test runs over the edit-schema corpus (SC-60). This is the security-critical sibling of
[PRD 24 R15](24-constrained-approvals-and-effects.md).

## 8. Shared-machine provenance (R72)

The OS-user principal is honest about its limits and says so: **shared sessions** (tmux/screen attach, shared
logins, sudo ambiguity) are detected where possible and **flagged on the card, the audit, and the packet**
("principal: alice (via shared session — weaker attribution)"); sudo-executed approvals record both the
effective and invoking uid; the **SSH-principal plugin** ([PRD 27 R40](27-governance-identity-extensibility.md))
ships in the first wave *because headless/remote answering is the OSS reality*, and `doctor` warns when the
terminal principal's assurance is weaker than the class's minimum. **Acceptance:** shared-session/sudo
fixtures render the warning and downgrade provenance; an SSH-principal approval verifies and lands at its tier
(SC-61).

## 9. Time semantics hardening (E20)

Explicit semantics for the messy real world: **sleep/wake** — timers are absolute-UTC so a wake re-evaluates
instantly: overdue transitions fire exactly once with a `scheduler-recovered(wake)` marker, desktop
notifications that missed their window collapse to one digest (never a notification flood on wake); **TZ
changes and DST** — persisted instants are UTC, rendering is local, no boundary double-fires;
**approval windows crossing sleep** — evaluated at execution attempt by the enforcer, not at notification
time. **Acceptance:** sleep-mid-TTL, wake-past-expiry, TZ-jump, and DST-boundary fixtures all behave
fail-closed and exactly-once (SC-62).

## 10. Derivative redaction (E21)

Redaction applies to **everything derived from the record, not just the record**: decision packets (R26),
writebacks and PR comments (R64), check annotations, attestation bundles (R63), training corpora (R66), replay
sets, drill fixtures. Same redactor, same receipts; if an artifact cannot be scrubbed (a raw diff that *is*
secrets), it exports as a **digest + redacted excerpt**, never the raw bytes. **Acceptance:** the evidence
scanner runs over every export path — **0 findings** anywhere (SC-63).

## 11. The no-advisory-allows rule (R73)

**If the producer/enforcer cannot prove it enforced the returned outcome, the safe fallback is deny or re-ask —
never an advisory allow.** Concretely: a producer that cannot enforce constraints receives a plain
**deny-with-rescope**, not `allow_with_constraints`; a resumed process that cannot verify the decision's
identity binding re-asks; an enforcer acknowledging an outcome includes the enforcement proof in its next
event. This generalizes [PRD 24's enforcement-honesty clause](24-constrained-approvals-and-effects.md) from
"don't offer unenforceable constraints" to **every shaped outcome**. **Acceptance:** an enforcement-incapable
producer fixture gets deny/re-ask across the whole outcome vocabulary (SC-64).

## 12. Revocation & undo semantics (R74)

Every expiring artifact — session grants, suppressions, approval windows, standing rules — is **revocable by
its minter, any admin-role approver, and (for rules) the owner**: revocation is immediate, evented
(`grant-revoked`), and takes effect at the **next resolve evaluation**; **already-recorded decisions stand**
(recorded history is immutable — revocation stops the future, never rewrites the past); in-flight calls that
already passed the enforcer are the enforcer's business (its kill-switch/halt story), and the inbox flags
`revoked_after_release` observations. **Acceptance:** mid-window revocation stops new auto-answers instantly;
cached answers in any queue are invalidated by version check; the audit shows revoke principal + reason (SC-65).

## 13. Training corpus governance (R75)

Training corpora (R66) are **governed exports**: creatable only by an admin-role approver; redacted snapshots
(E21) with the evidence scanner green before export; **regulated/attested asks excluded by default** (config
can include them only with retention sign-off); historical asks are **never reclassifiable** (the corpus
records what was decided under the policy of the time — rewriting history for training would poison both);
corpora carry checksums + creator + scope like every other artifact. **Acceptance:** a corpus export excludes
regulated asks by default; scanner green; checksum verified at load (SC-52 extension).

## 14. Localhost web-UI security model (R76)

The local web UI (R35) is an answer-capable channel, so it gets a real security model: **loopback-only bind
enforced in code** (a non-loopback bind refuses to start); **CSRF token** on every answer (the claim token
doubles as the per-ask CSRF secret — a cross-origin POST cannot know it); `Origin`/`Referer` checked against
the loopback origin; standard clickjacking headers; the **browser principal maps to the OS user** via a
localhost handshake (the server writes a nonce file readable only by the OS session, the page proves it) —
no cookie story, no remote anything; answers require the same claim + principal + roster pipeline as every
channel ([PRD 16 §A](16-channel-and-harness-adapters.md)). **Acceptance:** cross-origin forge, non-loopback
bind, and browser-without-handshake fixtures all fail closed (SC-66).

## 15. Dead-man / systemic-coverage detection (R77)

When nobody answers at all, deny is safe — but **silence itself is a signal**: N consecutive critical-tier
expiries within a window (config: default 3 in 24 h) emit a **`systemic-coverage-failure`** event and fire the
configured response — create an incident, page, or trigger **agenthalt** on the offending agents — because
"a gate nobody answers" is the failure mode this entire product exists to kill
([PRD 01](01-why.md)). Detection is a counter + threshold, deterministic, never ML. **Acceptance:** three
expired criticals in the window fire the event + hook exactly once; recovery resets the counter; the drill
shows the on-call path being paged about *the silence*, not just the asks (SC-67).

## Engineering summary

| ID | Clause | Gated by |
|---|---|---|
| **E17** | Idempotent, never-authoritative outbound side effects (idempotency keys, separate truths) | SC-56 |
| **E18** | Frozen schema/version evolution policy (additive-only, tolerate-and-preserve, major-bump rules) | SC-57 |
| **E19** | Trust class computed by core; producers sign provenance, never assert trust | SC-58 |
| **E20** | Sleep/wake/TZ/DST exactly-once semantics; wake digests, no notification floods | SC-62 |
| **E21** | Derivative redaction — every export path scanned, raw-that-can't-scrub exports as digest+excerpt | SC-63 |

## Scenarios ([PRD 17](17-scenarios.md) additions)

**SC-54 · Precedence conflict matrix.** Pairwise fixtures across all 8 lattice levels: standing-rule vs freeze
deny-only (deny), grant vs min-tier (provenance wins), window vs suppression (window wins), stale vs human
answer (stale wins), dependency vs grant (dependency wins) — deterministic, documented, tested.

**SC-55 · Illegal transitions fuzz.** Drive every non-edge (approved→denied, expired→approved, terminal→revised,
suppressed→approved) — all `illegal-transition-rejected` + logged; state graph version pinned.

**SC-56 · Outbound exactly-once.** Force 3× retries on a check update, a PR comment, and a hook: one effect
each, two logged no-ops, ledger replays.

**SC-57 · Old producer, new core.** A v1-schema ask posts into a later core: tolerated fields, preserved
unknowns, resolves normally; a retyped-field payload refuses loudly per E18.

**SC-58 · Self-asserted trust.** Producer blobs marked `trusted=true` render untrusted; signed prose renders
"verified origin, untrusted content"; adapter-keyed evidence renders trusted.

**SC-59 · Clarification treadmill.** A producer loops 8 hold-rounds: forced terminal at the 2nd (default),
evidence revisions capped, entries digest-collapsed, flood budget decremented.

**SC-60 · Scope-escape edits.** 2→200 recipients (rejected), staging→prod (rejected), `dry_run:true→false`
(rejected), repo→org (rejected), 172→2 recipients (allowed), cap 1000→100 (allowed); broadening-flagged field
with T-max tier gates + renders loudly.

**SC-61 · Shared-machine provenance.** tmux-attached approval flags weaker attribution; sudo records both uids;
SSH-principal plugin verifies at its tier; `doctor` warns on sub-minimum terminal assurance.

**SC-62 · Sleep/wake clock.** Laptop sleeps mid-TTL, wakes past expiry: one expiry event with
`scheduler-recovered(wake)`, one digest of missed notifications, no resurrection; DST/TZ fixtures double-fire
nothing.

**SC-63 · Derivative scrubbing.** Evidence scanner over packet, PR comment, check annotation, attestation,
training corpus, drill fixture: 0 findings; an unscrubbable raw diff exports as digest + redacted excerpt.

**SC-64 · No advisory allows.** An enforcement-incapable producer receives deny-with-rescope for every shaped
outcome; a resuming process that can't verify binding re-asks; enforcement proofs ride enforcer events.

**SC-65 · Mid-window revocation.** Grant revoked at minute 7 of 15: new matching asks gate instantly, cached
answers invalidated by version, the 6 already-recorded decisions stand, `grant-revoked` names principal+reason.

**SC-66 · Web-UI attacks.** Cross-origin answer POST (no claim) rejected; non-loopback bind refuses to start;
browser without the OS-session handshake cannot answer; clickjacking headers present.

**SC-67 · Dead-man.** Three expired criticals in 24 h → `systemic-coverage-failure` + incident hook fires once;
a fourth expiry doesn't double-fire; counter resets on any answered critical.

## Traceability

| Req/Clause | Deepens | Scenario | Test |
|---|---|---|---|
| R68 | PRDs 24–29 (all) | SC-54 | `test_precedence_lattice.py` |
| R69 | [PRD 15](15-data-model.md) | SC-55 | `test_state_machine_fuzz.py` |
| E17 | R44/R64 | SC-56 | `test_outbound_idempotency.py` |
| E18 | E10 | SC-57 | `test_schema_evolution.py` |
| E19 | R21/R25 | SC-58 | `test_trust_classification.py` |
| R70 | R48–R50 | SC-59 | `test_review_limits.py` |
| R71 | R14/R15 | SC-60 | `test_scope_escape.py` |
| R72 | [PRD 18](18-approval-integrity.md) | SC-61 | `test_shared_provenance.py` |
| E20 | E8 | SC-62 | `test_wake_clock.py` |
| E21 | E6 | SC-63 | `test_derivative_redaction.py` |
| R73 | R14/R15/R20 | SC-64 | `test_no_advisory_allows.py` |
| R74 | R51–R53, R37 | SC-65 | `test_revocation.py` |
| R75 | R66 | SC-52 ext | `test_corpus_governance.py` |
| R76 | R35 | SC-66 | `test_webui_security.py` |
| R77 | R3/R4 | SC-67 | `test_deadman.py` |

## Non-goals

- **No priority engine** — the lattice is a fixed total order shipped as a table + tests, not user-programmable
  weights (configurable precedence is how products acquire both bugs and marketing).
- **No rewriting of recorded history** — revocation stops the future; the past is evidence.
- **No ML anomaly detection on silence** — a counter with a threshold, stated in prose, testable in fixtures.
- **No remote web UI, ever, in the local product** — the loopback bind is code, not config.
