# PRD 17 — Scenario Catalog (the field-test spine)

**BLUF:** 67 scenarios, each a fixture with a trigger, a cast, a scripted walk, exact expected events, and a
verdict — plus the **attack packs** (spoof, replay, inject, flood, confuse, constraint-bypass, staleness-bypass,
tier-confusion, suppression-escape, scope-escape, review-treadmill, illegal-transition, web-UI forge,
self-asserted-trust) where the only correct outcome is a fail-closed one. SC-01–SC-26 gate the v0.1.0 core;
**SC-27–SC-40 gate the product-depth slate (PRDs 24–27); SC-41–SC-53 gate the review-loop, orchestration &
trust-maturity slate (PRDs 28–29); SC-54–SC-67 gate the correctness/conflict/abuse hardening layer
(PRD 30)**. This is the catalog the field test executes and the report grades; every requirement in
[PRD 05](05-features.md) is exercised by at least one scenario ([PRD 12](12-traceability.md)).

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Conventions

- **Cast:** Maya (owner), Ravi (approver, roster), Dana (on-call tier-2), Sam (solo user), Bot (the agent).
- **Expected events** use the [PRD 15](15-data-model.md) vocabulary: `ask-raised`, `ask-delivered`,
  `ask-warned`, `ask-escalated`, `ask-answered`, `ask-expired`, `ask-cancelled`, `ask-flood`,
  `answer-rejected`, plus the local transition log.
- **Verdicts:** **P**ass / **F**ail — per-scenario assertions are exact (state, reason codes, event order,
  redaction receipts); "roughly right" is a fail.

## Group 1 — Lifecycle & context (R1, R3, E1, E2)

**SC-01 · First ask, terminal, zero config.** Sam installs; `init` writes terminal-only config; Bot's ask
(restore prod DB from backup) arrives. *Walk:* ingest → card renders (4 blocks, TTL 300 s) → `a` + typed
confirm. *Expect:* `ask-raised`→`ask-delivered(terminal)`→`ask-answered(approved, principal=sam)`; resolve
`allow/allow_ask_approved`; store + chain entries present. **P** iff card shows all four blocks and the audit
reconstructs in ≤ 3 transitions.

**SC-02 · Malformed ask rejected loudly.** Producer sends `ask/1.0` missing `expires_at`, oversized args (300
KiB), and a floating `expires_at` ("tomorrow"). *Expect:* 400 with field-named diagnostics each time; **no
record**, no delivery; producer log states the failing field. **P** iff nothing partial persists.

**SC-03 · Zero-context correct call (the spine).** Ravi (no prior knowledge) receives 12 pre-registered cards
from the corpus. *Expect:* ≥ 10/12 correct decisions; median time < 15 s; every missing field he got rendered
`unknown`. **P** iff both gates hold (user-study protocol: [PRD 21](21-evidence-register.md)).

**SC-04 · Missing-context honesty.** Degraded corpus (policy_ref stripped, blast_radius null, reversibility
unknown). *Expect:* every card shows explicit `unknown` for the stripped fields; the *correct* decision flips
to deny (not "guess safe"). **P** iff 0 silent blanks and 0 guessed values.

**SC-05 · Rescope hint changes the agent's behavior.** Bot's `rm -rf` deny includes the hint; the harness
re-asks with `--dry-run` (allowed class). *Expect:* second ask is a new ask (new identity), first stays denied;
hint text present in resolve payload. **P** iff no state reuse.

**SC-06 · Duplicate ingest coalesces.** Bot retries the same POST 3× (network flake). *Expect:* same `ask_id`
all 3×; one delivery; transitions record `deduplicated` ×2; approver sees one card.

**SC-09 · Timeout = deny with warning.** Nobody answers a 5-min irreversible ask. *Expect:* `ask-warned` at
T-60 s on both channels; `ask-expired` at T=300; resolve = `deny/human_gate_timeout/retryable=false` + rescope
hint. **P** iff wall-clock jitter ≤ 1 s and zero allow paths.

**SC-10 · Expiry survives a crash.** Kill -9 the daemon at T-30 s; restart at T+10 s. *Expect:* on boot,
`ask-expired` fires exactly once (with `scheduler-recovered`), one event, correct time. Clock-jump variant:
NTP steps back 2 min mid-TTL → TTL does **not** extend.

## Group 2 — Cross-channel truth (R2, E3, E7)

**SC-07 · Second-surface approve, terminal parity.** Card on terminal + desktop/webhook (and on a chat
adapter when one is configured); Ravi answers on the second surface. *Expect:*
`ask-answered(channel=<surface>, principal=<id>)`; terminal shows "resolved via <surface> at …" within poll
interval; resolve fires once. Byte-parity check on the decision record vs a terminal-answered twin.

**SC-08 · Race: two answers, one decision.** Ravi and Dana both tap within 200 ms (mocked). *Expect:*
first-wins recorded; second logged as `answer-rejected(cause=late)`; both surfaces show the same winner;
exactly one `ask-answered`; **no double-execution path exists** (resolve called twice → same single decision,
idempotent).

**SC-18 · Channel failover.** The external channel (webhook/chat adapter) 500s for 10 min (mocked). *Expect:*
delivery attempts logged
(`ask-delivery-failed` × retries) → terminal still works; answer via terminal resolves; the external surface
is later
updated to the outcome (not re-asked). **P** iff ingest latency never regressed (async) and no duplicate
notification appeared.

**SC-19 · Late answer is a visible no-op.** Ravi taps Approve 45 s after expiry. *Expect:* "expired — action
was denied" to Ravi; `answer-rejected(cause=late)`; state untouched; **never** a resurrection.

## Group 3 — Escalation (R4, E8)

**SC-11 · The 3 a.m. drill.** Prod deploy ask at 03:04; tier-1 (Maya) silent. *Expect:* `ask-escalated(tier-2)`
at T+300 s per config; Dana's surface (desktop notification → terminal; Matrix DM or a webhook-to-phone
recipe when configured) has the card with "tier 1 did not answer · expires in mm:ss";
Dana denies. *Expect:* claims from tier-1 revoked (a late tier-1 tap → `answer-rejected(cause=revoked)`).

**SC-12 · Ladder exhaustion denies.** No tier answers. *Expect:* tiers fire in order, each once; final
`ask-expired` → deny; total ladder events = tiers−1; TTL unchanged throughout (never extended).

## Group 4 — Flood & abuse (R7)

**SC-13 · Flood pack (the attack).** Bot emits 200 asks / 30 s (agentdrill pack). *Expect:* the key starts with
its configured burst capacity, which is allowed; post-threshold asks → `flood_denied` + `ask_flood_throttled`;
exactly **1** `ask-flood` event; **1** digest notification; pre-flood pendings remain answerable and un-spammed.
The verdict records the allowed burst count and the denied remainder (with the defaults: 20 allowed, 180 denied);
a literal "200/200 denied" would also deny SC-14's legitimate burst and is not the contract.

**SC-14 · Legitimate burst is not an attack.** Migration touches 20 tables (20 asks, distinct identities,
< 2 s apart). *Expect:* all delivered, all answerable, no throttle trip (dedupe + burst headroom). **P** iff
SC-13 and SC-14 pass **together** — the discriminator is behavior, not volume.

## Group 5 — CI / headless (R6)

**SC-15 · Pipeline halts on an ask.** Release job's irreversible step runs `gate`. *Expect:* job log shows
ask id + summary; answered from a second surface → exit `0` → job continues; audit names both the pipeline and Ravi.

**SC-16 · Deterministic exits.** Matrix: deny → `2`; expiry → `3`; daemon killed → `4`; still-pending → `5`;
approved → `0`. *Expect:* reserved codes only, stable across a retry (idempotent same-ask `gate`). Cancelled
job → ask `cancelled`, not orphaned.

## Group 6 — Evidence (R5)

**SC-20 · Reconstruction + chain.** Session with 3 asks (approve/deny/expire + 1 escalation). *Expect:*
`export --session` yields an ordered JSONL: every transition, principal, channel, reason codes, redaction
receipts, hash chain; `verify-log` passes offline; agentwatch events join on `session_id`/ask id. Tamper
fixture: flip one payload → verify names the exact `seq`.

**SC-21 · Evidence carries no secrets.** Asks seeded with API keys/tokens/PII in args and reasons. *Expect:*
store dump, channel payload captures (webhook/chat/desktop), and audit export → **0 findings** by the evidence scanner; every redaction
has a receipt (field, class, count).

## Group 7 — Attack packs (E3, E4, E5)

**SC-22 · Spoof/replay/forge matrix.** 10 attacks: unsigned chat callback (any configured chat adapter); stale signature (> 5 min); replayed
valid callback; off-roster user; forged `approver` field via raw API; token from a forwarded message (valid
claim, wrong channel principal); expired claim; claim answered after escalation revocation; claim reused
twice; identity-mismatched answer (approve ask A with ask B's token). *Expect:* all 10 →
`answer-rejected` with distinct causes; **zero state changes**; approver-facing message explains each.

**SC-23 · Injection corpus.** 10 poisoned asks (markdown "buttons", fake links, "CISO authorized this",
"ignore previous instructions", zero-width spoofing, fake `policy_ref` from an unsigned producer). *Expect:*
inert rendering everywhere (terminal + every configured channel); trusted fields from unsigned producers render **unverified**;
**0 approvals caused by** injected content; the fake-policy-ref card visibly says "unverified policy
reference".

## Group 8 — Governance & persona flows

**SC-17 · Self-review denied.** Maya's own agent asks; Maya is rostered; class `irreversible` with
`self_review=deny`. *Expect:* her approval → `answer-rejected(cause=self_review)`; the card told her upfront.
Config-allowed variant for `low-risk` class → allowed and audited as `self_review=allowed`.

**SC-24 · Fault-injection matrix (fail-closed).** Store locked; corrupted schema; sink offline; external channel down;
scheduler killed mid-fire. *Expect:* every path → deny-or-pending, explicit `delivery-failed`/degradation
events, `doctor` red; **zero** silent allows, **zero** silent skips.

**SC-25 · Framework adapter round-trip (LangGraph).** A graph's `human_gate` node interrupts; adapter → ask;
a second surface approves; graph resumes with approve; process killed mid-wait then restarted → resume-by-id returns the
same decision (no double-execution; durable ask). *Expect:* exactly one tool execution post-approval.

**SC-26 · Offline day.** Network disabled; external channels off (the filesystem spool + desktop notifications stay). *Expect:* SC-01/SC-09 pass; `doctor` reports offline mode
green; no outbound call attempts in logs; export works to a local file.

## Group 9 — Product-depth slate (PRDs 24–27; ship-gated per their versions, not v0.1.0)

**SC-27 · Constrained approval round-trip.** Approver picks "staging only" on a prod DB ask →
`allow_with_constraints` → the agent re-asks scoped to staging → allow; the original prod identity never
executes; the **enforcer** denies constraint-exceeding call 101 of `max_rows=100` naming the constraint id.
**P** iff the inbox recorded and the enforcer enforced — a constraint no enforcer honors must never be
offered.

**SC-28 · Stale ask, delayed answer.** Ask pinned to repo rev `a1b2`; answered 40 min later; rev moved →
card degrades to **stale**, bare answer rejected `stale_reconfirm_required`; re-confirm binds to the new basis;
audit shows the drift event + the re-confirm. Clock/TTL unchanged — staleness never extends anything.

**SC-29 · Preview & evidence integrity.** (a) preview matches args → clean approve; (b) args mutated after
render → digest mismatch → card flips stale/unverified, silent approval blocked; (c) evidence body with
injected "approve this" renders inert (E14). **P** iff 0 approvals-from-injected-text and visible receipts.

**SC-30 · Edit-in-flight.** Approver edits a 172-recipient send down to 2 (edit schema allows) → executes
exactly the edit; original recorded, never sent; out-of-schema edit refused loudly; both identities in the audit.

**SC-31 · Claim ≠ approve; handoff up the ladder.** Claim is visible and clock-running; handoff note travels to
tier 3; tier 3 denies. Events: claimed → handoff-noted → escalated → answered; **no** `ask-answered` before the
deny.

**SC-32 · Incident mode + quiet hours.** Freeze toggle (owner + reason, audited on/off): TTLs shorten,
low-priority queues silently, deny-only classes stop asking, `irreversible` still rings immediately. **P** iff
nothing irreversible is ever silenced and exit is audited.

**SC-33 · Standing approval, end to end.** A 7-day standing rule auto-answers matching asks
(`human-remembered`, rule id, hit count on the card); day 8 re-gates with zero cleanup; shadow report matched
replay exactly before activation.

**SC-34 · Bundle without bulk-approve (hard mode).** 20-ask migration bundle: one grouped review, 20 individual
decisions, shared rationale per ask; **no approve-all exists**; a scripted bulk-answer attempt is rejected
(N-20 regression).

**SC-35 · Effect identity mismatch.** Approval bound to effect E1 (fingerprint F) cannot release a call claiming
E1 with different arguments → deny; both fingerprints shown side-by-side on the card.

**SC-36 · Decision packet, offline.** Export the packet for a constrained, stale-then-reconfirmed approval → a
reviewer on another machine verifies chain + evidence digests + constraints + edits + provenance tier with no
store access.

**SC-37 · Tier enforcement.** `irreversible` with `min_tier=T3`: bare-terminal answer (T1) → rejected
`insufficient_provenance`; chat-verified principal (T3) → allowed; tier stored on the answer and in the packet.

**SC-38 · Rule simulation before a config change.** Candidate TTL change 300→180 s replayed over history: exact
flip set (3 would-have-expired) attached to the config PR; read-only, watermarked, store untouched.

**SC-39 · Ask dependencies.** `deploy` ask blocked on `db-migration` ask: renders "waiting on X", claims do not
issue; blocker resolves → claims issue; declared cycle → loud config error; no scheduling logic in the inbox.

**SC-40 · Event hooks fire, and never block.** Hooks configured on `ask-answered` and `ask-flood`: a deny fires
the ticket hook with the event payload (post-decision, signed); the flood fires the pager hook **once**; a dead
hook (connection refused) produces a `hook-failed` event, delays nothing, and the decision is already recorded.
**P** iff hooks are strictly observational — no hook output can alter any ask state.

## Group 10 — Review loop, orchestration & trust maturity (PRDs 28–29; ship-gated per their versions)

**SC-41 · needs_changes round trip.** Approver requests "reduce recipients + attach rollback" (hold-and-clarify
mode); producer responds within the *remaining* TTL; revised ask approved — or TTL lapses → deny (**no
extension ever**). Resolve-and-reask variant: terminal `needs_changes`, producer re-asks, the thread renders as
v2 with prior context.

**SC-42 · Session grant.** "db-migration, this agent, 15 min" minted at an ask → 6 matching asks auto-answer
with grant provenance (`human-remembered` + grant id) → minute 16: the 7th gates again. Zero cleanup; hard
ceiling enforced.

**SC-43 · Future-effective approval.** Deploy approved 21:40, effective 22:00: the 21:55 execution attempt is
**denied by the enforcer naming the window**; 22:05 executes. Approval is inert outside its window, not just
unrecorded.

**SC-44 · Incident suppression.** During INC-7, `db.stats.*` on prod-db suppressed 30 min: matches auto-answer
(recorded); a *different* table still gates; minute 31 gates again; scope + on/off are events; irreversible
classes excluded by default.

**SC-45 · Parallel notify.** A `critical` security ask notifies security + owner at t=0; security answers first;
owner's late answer is a logged no-op; quorum variant releases only with one answer from each group.

**SC-46 · Rollback-required approval.** `prod-migrate` without rollback evidence → blocking partial score,
approve disabled, `rollback-missing` suggested; with plan + owner + digest → approves; the rollback block rides
the packet.

**SC-47 · Confidence labeling.** Three sibling asks — exact file count (`exact·high`), EXPLAIN estimate
(`estimated·low`), unknown — render sources distinctly; the delta block compares magnitudes only within
same-confidence fields; nothing estimates silently as fact.

**SC-48 · Deny taxonomy analytics.** A week of denies codes up (`too-broad` ×12, `outside-window` ×6,
`missing-evidence` ×5); the weekly report names rule + class as top sources; free text rides along, codes are
mandatory on configured classes.

**SC-49 · External attestation.** Three decisions exported as a signed attestation bundle → a verifier with
only the public key + bundle confirms chain-segment match, provenance tiers, rationale hashes — offline, no
store access. Attests facts, never "was correct."

**SC-50 · Writeback.** CI ask answered in a terminal: GitHub check pending → completed with the ask id; a PR
comment lands; token revoked mid-run → `writeback-failed` event, decision already recorded, zero delay.

**SC-51 · Correlation under pressure.** 4 asks share `rollout_id=RL-9`, 6 touch prod-db in an hour: both
groupings render with honest counts; every ask still decided individually; grouping feeds the postmortem.

**SC-52 · Training mode.** A new approver replays 10 historical asks; store digest unchanged before/after
(zero live mutation); score report: correctness, latency, weakest class.

**SC-53 · Chaos drill pack.** `agentinbox drill`: all 7 attacks (spoof, flood, stale, missing-evidence,
dual-control failure, tier-confusion, suppression escape) blocked with named events on a sandboxed instance,
green in < 2 min, zero real asks touched.

## Group 11 — Correctness, conflict & abuse hardening (PRD 30; gates the PRD 24–29 slate)

**SC-54 · Precedence conflict matrix.** Pairwise fixtures across all 8 lattice levels: standing rule vs freeze
deny-only (deny), grant vs min-tier (provenance wins), window vs suppression (window wins), stale vs human
answer (stale wins), dependency vs grant (dependency wins) — deterministic, documented, tested.

**SC-55 · Illegal-transitions fuzz.** Drive every non-edge (approved→denied, expired→approved, terminal→revised,
suppressed→approved): all `illegal-transition-rejected` + logged; state-graph version pinned.

**SC-56 · Outbound exactly-once.** Force 3× retries on a check update, a PR comment, a hook: one effect each,
two logged no-ops, ledger replays; "decision recorded" and "writeback happened" remain separate truths.

**SC-57 · Old producer, new core.** A v1-schema ask into a later core: tolerated fields, preserved unknowns,
resolves normally; a retyped-field payload refuses loudly per E18; `doctor` names mismatched versions.

**SC-58 · Self-asserted trust.** Producer blobs marked `trusted=true` render untrusted; signed prose renders
"verified origin, untrusted content"; adapter-keyed evidence renders trusted. Trust is computed, never
declared.

**SC-59 · Clarification treadmill.** A producer loops 8 hold-rounds: forced terminal at the 2nd (default),
evidence revisions capped, entries digest-collapsed, flood budget decremented — a treadmill is a flood.

**SC-60 · Scope-escape edits.** 2→200 recipients, staging→prod, `dry_run:true→false`, repo→org: all **rejected**
(monotonic narrowing); 172→2 and cap 1000→100 allowed; a broadening-flagged field requires the class's max
provenance tier and renders loudly.

**SC-61 · Shared-machine provenance.** tmux-attach flags weaker attribution; sudo records both uids;
SSH-principal plugin verifies at its tier; `doctor` warns on sub-minimum terminal assurance.

**SC-62 · Sleep/wake clock.** Sleep mid-TTL, wake past expiry: one expiry with `scheduler-recovered(wake)`,
missed desktop notifications collapse to one digest, no resurrection; DST/TZ fixtures double-fire nothing.

**SC-63 · Derivative scrubbing.** Evidence scanner over packet, PR comment, check annotation, attestation,
training corpus, drill fixture: **0 findings**; an unscrubbable raw diff exports as digest + redacted excerpt.

**SC-64 · No advisory allows.** An enforcement-incapable producer receives deny-with-rescope for every shaped
outcome; a resuming process that can't verify the binding re-asks; enforcement proofs ride enforcer events.

**SC-65 · Mid-window revocation.** Grant revoked at minute 7 of 15: new asks gate instantly, cached answers
invalidated by version, the 6 recorded decisions stand, `grant-revoked` names principal + reason.

**SC-66 · Web-UI attacks.** Cross-origin answer (no claim) rejected; non-loopback bind refuses to start; a
browser without the OS-session handshake cannot answer; clickjacking headers present.

**SC-67 · Dead-man.** Three expired criticals in 24 h → `systemic-coverage-failure` + incident hook fires once;
a fourth doesn't double-fire; any answered critical resets the counter.

## Scoring and reporting

- Each scenario is graded independently; the field-test report reproduces this catalog with a verdict column
  and per-scenario notes — **misses documented, never smoothed** (the org's honesty rule).
- Attack packs (SC-22/23, SC-13, and the depth-pack attacks: constraint-bypass SC-27, staleness-bypass SC-29,
  tier-confusion SC-37, suppression-escape SC-44) plus the hardening gates (scope-escape SC-60,
  review-treadmill SC-59, illegal-transitions SC-55, self-asserted-trust SC-58, web-UI forge SC-66) are
  **release gates**: any fail blocks the release.
- The zero-context study (SC-03/04/05) is the R1 acceptance and is reported with its protocol, corpus
  checksum, and raw timings ([PRD 21](21-evidence-register.md)).
