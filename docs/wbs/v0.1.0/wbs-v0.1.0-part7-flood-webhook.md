# WBS v0.1.0 — Part 7: Flood Guard & Webhook Channel (M12–M13)

**BLUF:** **M12 is rate protection as a security property**: per-agent/session/environment token buckets,
duplicate-identity coalescing, and **flood auto-deny** — an attack produces N denies, **one** `ask-flood`
event, **one** digest notification, and the inbox gets quieter under attack while pre-flood pendings stay
answerable and a legitimate 20-ask migration burst survives (R7, D-12; SC-13/14). **M13 is reach without a
platform**: the signed-webhook channel — display-only outbound POSTs (HMAC-signed so receivers can verify
provenance) with recipes for ntfy/Pushover/Discord/email bridges — plus the delivery accounting that makes
every attempt an event, with bounded retries, failover, and the unroutable-class rule (E7).

> **Standard exit criteria + closure** — see the [index](wbs-v0.1.0-index.md).

---

## Milestone M12 — Flood guard (R7)

**Goal:** a looping or malicious agent cannot spam the approver into rubber-stamping (or muting): token-bucket
throttles keyed per agent/session/environment (+ producer uid where available), duplicate-identity coalescing
first, then auto-deny with `ask_flood_throttled` — and the discriminators that keep a legitimate burst
answerable. Flood denial is a decision the producer learns, not a suppression (D-12).

**CUJ:** CUJ-6 · **Requirements:** R7, D-12, [PRD 05 E12 interplay](../../prd/05-features.md) (1 digest job on
the bus), [PRD 06](../../prd/06-security-baseline.md) (T5), [PRD 30 R70-posture](../../prd/30-correctness-conflict-abuse-hardening.md)
(thresholds are security-relevant config).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 12.D0 | **Design docs first** | Flood design: bucket keys/dimensions, thresholds per class/agent, coalescing rules, the digest job, producer-facing deny semantics, config governance + doctor explanation | docs | reviewed before code | #238 | — | — |
| 12.1 | Duplicate coalescing | Identity+session dedupe window first (E1) — the *first* defense; near-identical repeat POSTs coalesce to one ask, one delivery | coalescing | SC-06 + burst fixtures: 3 retries → 1 ask; the bus publishes one delivery | #239 | — | R7, E1 |
| 12.2 | Token buckets | Per-agent/session/environment counters (burst + rate/window, default 20/10-per-min), thresholds config-per-class; recorded keys include producer uid where available | throttle | bucket trip at threshold; config visible in `doctor --explain` | #240 | — | R7 |
| 12.3 | **Flood auto-deny** | Trip → new asks resolve `flood_denied` + `ask_flood_throttled`; producer gets retryable-after-window semantics; the runtime records a zero-resurrection counter | auto-deny | agentdrill flood pack (200/30s): burst capacity allowed + the remainder denied (20/180 with defaults), distinct reason, agent learns and stops | #241 | CUJ-6 | R7, D-12 |
| 12.4 | **One event, one digest** | One `ask-flood` event (window, counts, first ask id, offending agent/session) + one digest notification job on the bus (M9 rule); pre-flood pendings remain answerable and un-spammed | aggregation | SC-13: exactly 1 event, 1 digest job, 1 notification; pendings answerable | #242 | CUJ-6 | R7, E12 |
| 12.5 | Legitimate-burst headroom | A 20-action migration (distinct identities, <2 s apart) stays fully answerable — dedupe + burst ceiling keep it under the threshold; per-class tuning documented | headroom | SC-14 green **together with** SC-13 (the discriminator is behavior, not volume) | #243 | — | R7 |
| 12.T | Tests | Buckets, coalescing, auto-deny, aggregation, burst fixtures | tests | coverage ≥ 95% | #244 | — | — |
| 12.C | Coverage gate | ≥95% | report | ≥95% | #245 | — | — |
| 12.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #246 | — | — |
| 12.CR | Code review | Findings resolved | log | no open findings | #247 | — | — |
| 12.D | Docs | Flood reference (keys, thresholds, digest, tuning, config governance) | docs | updated + linked | #248 | — | — |
| 12.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 12.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Flood pack: N denies, 1 event, 1 digest; pre-flood asks answerable; legitimate burst survives
- [ ] Thresholds validated at load and explained by `doctor`; flood denial teaches the producer (retryable-after)

---

## Milestone M13 — Webhook channel (display-only) + delivery accounting (E7)

**Goal:** reach into whatever the team already runs — ntfy.sh, Pushover, Discord, Teams, email bridges — over
one honest primitive: an HMAC-signed outbound POST carrying the rendered card summary. **Display-only at
v0.1.0**: the webhook says "answer in your terminal"; the answer path is the verified pipeline (chat adapters
with per-platform signatures are the forward slate). Plus the delivery ledger: every attempt a Delivery
record + event, bounded retry with backoff, channel failover, and the unroutable-class rule (a class with no
enabled channel is a load-time config error, not a quiet timeout).

**CUJ:** CUJ-3 (surface), CUJ-9 (surface) · **Requirements:** E7, [PRD 16 §B.4](../../prd/16-channel-and-harness-adapters.md),
[PRD 18 §assurance](../../prd/18-approval-integrity.md) (webhook row), [PRD 13](../../prd/13-non-functional-requirements.md) (N-3b).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 13.D0 | **Design docs first** | Webhook design: payload shape, HMAC header + key refs (env/file), display-only enforcement, recipe catalog, retry/failover policy, unroutable-class rule | docs | reviewed before code | #249 | — | — |
| 13.1 | Signed outbound POST | Canonical payload + `X-AgentInbox-Signature` (HMAC over canonical bytes); receivers verify provenance; keys via refs only | sender | signature verifies at a mock receiver; secret never in config/logs | #250 | — | E7 |
| 13.2 | **Display-only enforcement** | The adapter implements `deliver()`; no answer parsing exists on this channel; payload text points to the terminal answer command | adapter | channel conformance: webhook has deliver, no answer; a crafted "response" POST does nothing | #251 | — | E4, D-5 |
| 13.3 | Recipes | Documented recipes for ntfy.sh (self-hosted push), Pushover, Discord webhook, Teams connector, email bridges — each with a setup snippet + the display-only caveat | recipes | each recipe rendered in fixtures; no recipe implies an answer path | #252 | CUJ-3 | R2 |
| 13.4 | Delivery ledger + retries + failover | Every attempt → Delivery record + `ask-delivered`/`ask-delivery-failed`; bounded retries with backoff; failover to the next configured channel; **ingest never blocks on delivery** | accounting | SC-18: external channel 500s ×10 min → logged streak, terminal answers, no duplicate notification, latency unaffected | #253 | CUJ-9 | E7 |
| 13.5 | **Unroutable-class rule** | A class resolving to zero enabled channels = config error at load (producer told loudly; `doctor` flags); a configured-but-down channel is different (pending + delivery-failed) | validation | unroutable fixture: load refuses with a class-named error | #254 | — | E7, E9 |
| 13.T | Tests | Signing, display-only, recipes' payload contracts, retries/failover, unroutable rule | tests | coverage ≥ 95% | #255 | — | — |
| 13.C | Coverage gate | ≥95% | report | ≥95% | #256 | — | — |
| 13.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #257 | — | — |
| 13.CR | Code review | Findings resolved | log | no open findings | #258 | — | — |
| 13.D | Docs | Webhook reference (payload, signature, recipes, display-only honesty) + delivery-accounting reference | docs | updated + linked | #259 | — | — |
| 13.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 13.W | Update WBS | Checkpoint | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Webhooks are signed, provenance-verifiable, and structurally incapable of answering
- [ ] Every delivery attempt is an event; failover works; unroutable classes refuse at load

---

Part 7 green ⇒ the inbox survives attack (M12) and reaches anywhere (M13); proceed to
[Part 8 (M14–M15)](wbs-v0.1.0-part8-parity-audit.md).
