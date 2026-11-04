# PRD 16 — Adapters: Channels, Bus, Store & Producers (the plugin surfaces)

**BLUF:** agentinbox plugs into the world through **four adapter families**: *inbox channels* (how a human
sees and answers a card — terminal/TUI, desktop notifications, CI checkpoint; Matrix next; chat platforms
optional), the *bus* (how delivery/escalation jobs move — in-proc default, **filesystem spool at v0.1.0**,
Redis/NATS later), the *store* (where truth lives — **SQLite at v0.1.0**, Postgres/embedded later, behind one
contract), and *producers* (how an agentic system emits an ask — agentpolicy, harness hooks, framework
interrupts, MCP bridges). All the hard invariants (claims, identity binding, TTL, audit) live in the core so
**no adapter can weaken them** — a driver that cannot guarantee the semantics is refused by conformance, not
by hope.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## A. The adapter contract (why thin is a security property)

| Adapter family | Receives from core | Must do | Must **never** do |
|---|---|---|---|
| **InboxChannel** | A rendered card (structured, already redacted) + a claim token + channel config | Deliver; authenticate the human on answer (platform signature, OS session, process ownership); return `(claim, principal)` to the core | Make decisions; interpret free text as approval; keep approval state of its own; render untrusted fields as markup |
| **AskBus** | Delivery/escalation/digest jobs (typed, dedupable) | Move jobs at-least-once with idempotent consumers; honor `not_before` | Store authoritative state; answer asks; lose a job silently (every loss is an event) |
| **AskStore** | Typed calls: `create_or_get_by_identity`, `get`, `cas_status`, `issue_claim`, `consume_claim`, `list_pending`, `append_event`, `export_session` | Provide the storage semantics in §D exactly | Buffer writes it has acked; relax single-use claims; reorder the audit seq |
| **Producer adapter** | The `ask/1.0` contract + `resolve/1.0` (long-poll or callback) | Validate; serialize/deserialize; map framework-native types; re-deliver resolve idempotently | Send unredacted secrets (E6 rejects at ingest anyway); invent trusted fields; poll in a hot loop (use `?wait=`); answer asks |

**The rule that keeps the matrix honest:** an adapter passes conformance fixtures in *this* repo
(`tests/fixtures/conformance/`) before it is listed as supported in [PRD 19](19-harness-compatibility.md).

## A.2 The v0.1.0 surface set — the OSS-first choice, and why

**The chosen shape (the "Option B" architecture):**

> **SQLite for truth · filesystem spool for movement · terminal/TUI + desktop notifications for the human ·
> CI checkpoint for headless · webhook recipes for reach · Matrix next · chat platforms (Slack/Teams) as
> optional community adapters.**

**Rationale — why this set, stated as decisions with reasons:**

| # | Choice | Why (the honest reasons) |
|---|---|---|
| 1 | **Local-first defaults with zero external services** | The install promise is `pip install` → working gate in 5 minutes (CUJ-1). Every required service beyond the process breaks that promise for the exact users OSS must win first: solo devs, air-gapped shops, and this project's own design partner (**who does not run Slack at all**). A tool whose *default* path needs a workspace, a broker, or a cloud account has already lost the OSS story. |
| 2 | **Queue for movement, store for truth** (D-13) | The bus carries *jobs* (deliver, re-notify, escalate, digest) that may be redelivered; the store carries the ask record, claims, and the audit chain, which must never be redelivered or reordered. Conflating them is how systems get "the message said approved but the record says pending." Movement without truth = no evidence; truth without movement = no humans. |
| 3 | **Filesystem bus before Redis/NATS** | A directory of JSONL jobs is the only queue that is simultaneously (a) dependency-free, (b) inspectable with `cat`/`grep`/`tail -f`, (c) durable by default, and (d) a *conformance-tested driver of the same interface* the broker drivers implement later. OSS users trust what they can read; SREs trust what they can tail. |
| 4 | **Terminal/TUI as the primary human surface, desktop notifications as the wake-up** | The gate competes with muscle memory, not with features. A blocking card in the terminal is the only surface with zero context-switch cost for a developer already in the loop; a desktop notification is the only "remote" channel that needs **no account, no workspace, no network, and no third-party trust** — it is the 3 a.m. path for the no-Slack, no-Matrix user. |
| 5 | **Matrix as the second interactive surface (v0.1.x), chat platforms as optional adapters** | For remote/phone approval we pick the **open** federation protocol, not the proprietary one. Slack/Teams adapters keep the exact same `InboxChannel` contract for those who want them — but the product must be **complete without any chat platform** ([PRD 14](14-non-goals.md)); that is a market reality (most OSS teams run no Slack) *and* a security stance (fewer third-party trust boundaries, [PRD 06](06-security-baseline.md)). |
| 6 | **One store contract, SQLite first, Postgres later (server mode)** | The storage semantics (CAS on status, single-use claims, append-only seq) are the actual hard part; the backend is replaceable. Writing them once against SQLite (single-writer, WAL) proves the contract; the server-mode Postgres driver (E11) then inherits conformance instead of re-deriving semantics. |
| 7 | **Generic webhook channel (display-only) + recipes** | Without chat platforms, reach comes from *recipes* over one honest primitive: a signed outbound POST. ntfy/Pushover/Discord/Teams/email-bridges all consume it; none of them can forge an approval at v0.1.0 because the webhook channel is **display-only** — answers still arrive via terminal/CLI with the full claim+principal pipeline. |
| 8 | **In-proc bus as the default implementation** | The common case (one producer, one human, one box) needs no bus at all — jobs are function calls. The bus interface exists so the *same core* runs single-process, filesystem-queued, or broker-backed without branching logic. |

**The gotchas this design owns (filesystem-bus hard parts, each with its rule):**

| Gotcha | The rule |
|---|---|
| Atomicity | **Write tmp → atomic rename.** Never append job files in place; leftover `.tmp` files are swept on boot. |
| Single-use claims are CAS | Solved at the *store*, not the bus: `consume_claim` is compare-and-set; a bus job can be redelivered freely because consuming a used claim fails benignly (idempotent consumer). |
| Notification latency | inotify/FSEvents/kqueue where available; bounded poll (default 1 s) as the universal fallback — invisible next to a 15-second human decision (N-5). |
| Durability | fsync file before rename; fsync directory after (POSIX). Boring, crash-safe. |
| Single writer | One inbox owner per spool dir — `flock`; a second daemon **refuses loudly** (D-8 stays true). |
| Portability | macOS + Linux first-class (rename atomicity, flock); **no Windows claim at v0.1.0**. |
| Multi-machine | **Not supported, not pretended** — the filesystem bus is one box. Cross-machine is exactly what the Redis/NATS drivers are for (v0.2.0 server mode). |
| Flood spam on the bus | The flood guard throttles **before jobs are published** — a flood never becomes 200 delivery jobs; it becomes 1 digest job (R7). |

## B. Inbox channels

### B.1 Terminal / TUI (P0 — the primary surface)

- **When:** interactive local sessions (the CUJ-1 path), CI operators on the box, and offline mode.
- **Render:** TTY card with the four blocks; countdown refreshed on warning.
- **Answer:** `a` = approve (typed confirmation for `irreversible`/`critical`), `d` = deny (reason required for
  those classes), `?` = detail view, `q` = quit (leaves the ask pending).
- **Principal:** OS user + TTY ownership; `--as` only when explicitly configured in `[channels.terminal]`
  (recorded as an assumed principal — audited loudly).
- **Non-interactive:** no TTY → no prompt, structured JSON to stdout, exit `5`; **a script can never approve.**
- **Queue view (v0.1.x):** `agentinbox inbox` — a live list of pending asks (age, class, remaining TTL) with
  per-ask answer; grouped display is allowed, **"approve all" is not** ([PRD 14 N-20](14-non-goals.md)); every
  row still resolves through the same claim + principal pipeline.
- **Conformance:** renders from the same card-renderer core as every other channel (parity fixture).

### B.2 Desktop notifications (P0 — the no-chat remote path)

- **When:** the approver is away from the terminal but at the machine — and the entire "remote" story for
  the no-Slack/no-Matrix install.
- **Mechanics:** macOS Notification Center (via `osascript`/UserNotifications) and Linux `notify-send`/`notify`
  (Freedesktop) — **no third-party account, no network, no external trust boundary**.
- **Content:** the alert carries the ask fingerprint, class, and remaining TTL; full context opens in the
  terminal (`agentinbox inbox` or the session's blocking card). The notification is a **wake-up, not a
  decision surface** — macOS/Linux notification *buttons* are platform-dependent and spoof-prone, so answers
  happen in the terminal/CLI where the OS session is the principal.
- **Hygiene:** escalated asks re-notify once per tier; floods notify once (the digest); quiet-hours config
  (v0.1.x).
- **Failure mode:** notifications unavailable (no notification daemon, SSH headless) → `doctor` reports it,
  the terminal path is unaffected.

### B.3 CI checkpoint (P0 — the headless surface)

- **When:** headless agents in CI/CD (CUJ-7) — any runner that can execute a CLI step.
- **Shape:** `agentinbox gate --ask <id> --wait --timeout <s>` as a blocking step; prints the ask id, card
  summary, and a deep link when an interactive channel is configured.
- **Exit codes (reserved, stable):** `0` approved · `2` denied · `3` expired · `4` inbox unreachable (fail
  closed) · `5` pending (runner retries) · `1` usage error.
- **Native-friendly:** GitHub Actions (environment-gate step + `GITHUB_STEP_SUMMARY` annotation), GitLab
  (protected-environment/manual-job semantics preserved — we are the *approval side* of them), Jenkins, Argo
  Workflows (a suspend template calling `gate`). Nothing vendor-specific in the core; recipes live in
  `docs/adapters/`.
- **Cancellation:** SIGTERM/cancellation maps to `cancelled` (a producer withdrawing), never a silent orphan.

### B.4 Generic webhook (P0 — reach without a chat platform)

- **When:** pushing cards/summaries into whatever the team already runs — ntfy.sh (self-hosted push),
  Pushover, Discord, Teams, email bridges, a ticketing system.
- **Shape:** signed outbound POST (HMAC header so receivers can verify provenance) with the rendered card;
  **display-only at v0.1.0** — an answer tap on the receiving surface is a v0.1.x per-platform interactive
  adapter (each carrying that platform's signature verification, per [PRD 18](18-approval-integrity.md)).
  Until then the webhook says *"answer in your terminal"* and the answer path is `agentinbox answer` with the
  full claim + principal pipeline.
- **Why display-only:** it keeps the v0.1.0 answer-verification surface at exactly two well-audited paths
  (terminal principal, CI exit) instead of N unaudited ones. The reach ships now; the tap-to-answer ships when
  each platform's anti-spoofing story does.

### B.5 Matrix (v0.1.x — the second interactive surface)

- **When:** genuine remote/phone approval over an **open federation protocol** — the honest OSS answer to the
  3 a.m. scenario (CUJ-5) for teams, without proprietary-platform trust.
- **Shape:** a small bot (or your existing homeserver) posts the card to a configured room/DM; Approve/Deny
  buttons use Element's validated interactive events; the adapter verifies the homeserver's event signature
  and the interacting user against the roster, then hands `(claim, principal)` to the core — identical to the
  chat-platform contract, so the same conformance fixtures apply.
- **Mobile:** Element on iOS/Android is the 3 a.m. phone path; native push (R8) remains v1.x on top.

### B.6 Chat platforms — Slack/Teams (optional community adapters, v0.1.x)

- **When:** an org already lives in Slack/Teams and wants approvals there. **Not required by any CUJ; not in
  the v0.1.0 set.**
- **Shape (Slack, as the reference community adapter):** Block Kit card, `POST
  /v1/channels/slack/interactions` verifying `X-Slack-Signature` (raw-body HMAC-SHA256, `v0=` scheme, ±5 min
  window) **before parsing**, then `(claim, user_id)` → core verify. Teams follows the same contract with its
  own callback verification.
- **The rule:** a chat platform is just another `InboxChannel` behind the same claim model — the product is
  complete without it (CUJ-12), and its spoofing surface ([PRD 18](18-approval-integrity.md)) is additive,
  never load-bearing.

## C. Bus drivers (AskBus — movement, not truth)

| Driver | Version | Notes |
|---|---|---|
| **in-proc** | ✅ v0.1.0 (default) | Jobs are function calls; zero moving parts; the common single-box case needs nothing else |
| **filesystem spool** | ✅ v0.1.0 | The OSS queue: atomic tmp→rename writes, fsync'd, `flock` single-owner, inotify/poll wakeups, JSONL inspectable with standard tools; **one box only** |
| **redis streams** | ◐ v0.2.0 (server mode) | Consumer groups for multi-notifier servers; at-least-once + idempotent consumers already guaranteed by the contract |
| **nats jetstream / rabbitmq** | ◐ v0.2.0+ | For teams with an existing broker; same interface, conformance-gated |
| **none** (bus-less) | ✅ v0.1.0 | Inline mode (`agentinbox ask` blocking, no daemon) — the bus is optional machinery, the store is not |

**Spool layout (contract, not implementation detail):**

```
~/.agentinbox/spool/
  jobs/<issued_at>-<job_id>.json        # tmp → rename; job = {type, ask_id, not_before, attempt, payload_digest}
  done/<job_id>.json                    # consumed jobs moved here (rename), pruned by retention
  locks/spool.lock                      # flock — one writer per spool
```

**Job types:** `deliver(card)`, `renotify(warn)`, `escalate(tier)`, `digest(flood)`, `expire(ask)`. All
consumers are **idempotent by ask state** — a redelivered job against a resolved ask is a logged no-op, never
a second notification or a state change.

## D. Store drivers (AskStore — truth, not movement)

| Driver | Version | Notes |
|---|---|---|
| **sqlite** (WAL) | ✅ v0.1.0 (reference) | Single-writer; fsync'd commits; handles the real load (TTL-bounded pending sets); the semantics below are proven here first |
| **memory** | ✅ v0.1.0 | Tests, fixtures, embedded ephemeral use — same semantics, no disk |
| **postgres** | ◐ v0.2.0 (server mode) | Multi-writer server mode; row-level CAS replaces SQLite's write serialization; conformance-inherits the semantics |
| **embedded-lib** | ◐ v0.2.0+ | Host app owns persistence via the interface (e.g., a LangGraph user storing asks in their own checkpointer) |
| **object/WORM export** | ◐ v0.2.0 | Not a state driver — evidence-grade export sink (object-lock storage), see [PRD 22 §D](22-operations-and-governance.md) |

**The storage semantics every driver MUST provide (the conformance bar, E11):**

1. **Idempotent create** keyed by `action_identity` + `session_id` within the dedupe window.
2. **CAS on ask status** — first-answer-wins under concurrency; a loser sees `already-resolved`, never a
   double-write (SC-08).
3. **Single-use claims** — `consume_claim` is atomic; exactly one consumer wins, all others fail benignly.
4. **Monotonic, gapless audit seq per inbox** — `append_event` serializes on seq; `prev_hash` chains (the
   chain verifies on any driver because it is content-addressed, not storage-addressed).
5. **Exactly-once timer recovery** — `list_pending(now)` must be derivable from persisted absolute instants
   (E2): a restarted driver recovers overdue transitions once.
6. **Durable-commit-before-ack** — nothing is "recorded" that a crash can lose.
7. **Capability flags** — a driver declares `single_writer`, `multi_writer`, `cluster_safe`; the core
   **refuses to enable** configurations the driver cannot guarantee (fail-closed driver selection, not
   runtime surprise).

**Third-party drivers:** Python entry points (`agentinbox.store`, `agentinbox.bus`) + the conformance suite
as the gate; an unlisted driver that has not passed conformance is unsupported, per the honesty rule
([PRD 19](19-harness-compatibility.md)).

## E. Producer adapters — "agentic-wise" (the harness/framework matrix)

The whole point: **every agentic system that can pause for a human can emit an ask.** Each adapter below maps
the system's native pause mechanism to `ask/1.0` and its resume mechanism to `resolve/1.0`.

### E.1 agentpolicy (reference producer — shipped v0.1.0)

The `AskBroker.create` → ask record hand-off: policy says `ask` → adapter POSTs `ask/1.0` (trusted fields signed
with the shared key) → answer/timeout returns through the existing
`approve/deny/resolve` path (`allow_ask_approved`, `human_gate_timeout`, …). This is the Wave-0 demo wiring:
"Replit rule fires → Maya's laptop pings → deny with a reason."

### E.2 Coding-agent harnesses (Tier 1)

| Harness | Native surface | Adapter shape | v0.1.0 |
|---|---|---|---|
| **Claude Code** | `PreToolUse` hook returning `ask`-equivalent permission decision | Hook script: on `ask` outcome → POST the ask → block until resolve → emit the permission decision the hook returns | ✅ example hook in `docs/adapters/claude-code/` (field-tested; the hook surface is the cleanest of all Tier-1) |
| **OpenAI Codex CLI** | config/sandbox approval surface | Wrapper command the agent runs for gated tools → `gate` semantics; sandbox covers the rest | ✅ documented (sandbox-first; `gate` as the explicit-step path) |
| **Cursor** | No headless hook surface on the field-test box | Not claimable — documented honestly; revisit if a headless surface ships | ✗ (honest matrix) |
| **GitHub Copilot agent mode** | Closed hook surface | Reached via the ecosystem's lower layers (agentgate MCP proxy / agentseatbelt confinement) — documented, not field-tested at v0.1.0 | ◐ documented coverage |
| **Gemini CLI** | Approval modes incl. an auto/YOLO tier | Adapter maps its approval prompts through the generic wrapper; field-tested only if the surface cooperates | ◐ v0.1.x target |

**Generic fallback that makes *any* harness work today:** the `agentinbox ask` CLI *is* the harness adapter —
any harness with a pre-execution hook (or a human who wraps the risky command) can `agentinbox ask --exec`
("gate this exact command"), making the gate harness-agnostic by construction even before a bespoke adapter
exists.

### E.3 Agent frameworks (Tier 2)

| Framework | Native HITL | Adapter shape (v0.1.0 ships the pattern + one reference; rest follow demand) |
|---|---|---|
| **LangGraph** | `interrupt()` + checkpointer; resume with `Command(resume=…)` | A `human_gate` tool node calls `interrupt(payload)`; the adapter converts the interrupt payload → `ask/1.0`, waits on `?wait=`, resumes with `Command(resume=decision)`. Durable ask + checkpoint = both survive restarts (SC-25). ✅ **reference adapter shipped v0.1.0** |
| **OpenAI Agents SDK** (py/js) | Tool `needs_approval` → interruptions → resumable `RunState` | Adapter catches the interruption, maps to ask, resumes the run on resolve. The SDK's docs literally leave "the approval surface" to the developer — this is it. ◐ v0.1.x |
| **CrewAI** | `human_input=True` on a Task (console-blocking) | Adapter replaces the console block: route the ask, return the decision to the task. ◐ v0.1.x |
| **AutoGen / AG2** | `human_input_mode` (ALWAYS/TERMINATE/NEVER) + UserProxy console | Same shape: UserProxy's register_reply hook → ask → response. ◐ v0.1.x |
| **PydanticAI** | Tool approval hooks / manual intervention points | Adapter at the tool boundary. ◐ v0.2.0 |
| **smolagents / LlamaIndex / Agno / Letta** | Framework-specific pause points | Same contract, thin mapping. ○ v0.3.0 by community pull |
| **kagent** | K8s-native pending tool calls | Their HITL returns a pending call to a person; adapter maps pending-call → ask, resume ← resolve. ○ watchlist — their model is convergent with ours, bridge when demand appears |
| **Temporal / durable-workflow users** | Signals + timers | The ask IS a signal-shaped wait; example: a workflow activity calls `gate`, a human answers from any interactive channel, the signal resumes it. ✅ recipe documented v0.1.0 (no SDK needed) |

### E.4 Protocol surfaces (Tier 3)

| Protocol | Relationship | v0.1.0 position |
|---|---|---|
| **MCP elicitation** (2025-06-18) | Presentation bridge: an MCP client may relay our card via `elicitation/create` (`accept`/`decline` map cleanly to approve/deny; `cancel` → keep pending) | Bridge design doc v0.1.0; implementation v0.2.0. **The authoritative decision + audit always live in agentinbox** — elicitation is a lens, not the record (the spec itself punts on identity/audit) |
| **MCP clients generally** (incl. Claude Desktop) | An MCP server tool can be "ask-first": tool call → emits ask via the local daemon → returns the resolved outcome | ✅ trivially supportable at v0.1.0 via the generic CLI-in-tool pattern; recipe documented |
| **A2A / CHAP-class research protocols** | Inter-agent task and human-coordination semantics emerging | Watchlist only; v0.3.0+ if stable. No dependency |
| **AuthZEN** | agentpolicy's interop shape for decisions | Our `resolve/1.0` stays mappable to it (decision + context/reasons) so an AuthZEN-shaped PEP can consume the outcome ([PRD 20 §B](20-standards-and-claims.md)) |

### E.5 Anything else (the escape hatches)

1. **CLI:** `agentinbox ask --file ask.json` — the universal adapter for glue code.
2. **HTTP:** `POST /v1/asks` on loopback — for anything with an HTTP client.
3. **File drops** (air-gapped): `agentinbox ask --watch dir/` — for environments where even loopback HTTP is
   disallowed; the watcher validates the same contract (v0.1.x, documented now) and pairs naturally with the
   filesystem spool.

## F. Channel-vs-producer compatibility notes

- **Terminal answers are always available** for local asks regardless of producer (a CI-originated ask on a
  shared box still shows in the operator's terminal if they are the roster).
- **Any interactive channel answers any ask** (terminal always; Matrix once configured; a chat adapter if
  installed); the producer is notified on its next long-poll/callback — the CI step unblocks either way.
- **Webhook is display-only** at v0.1.0: it renders, it never answers.
- **CI can answer nothing itself** (it is a waiter, not a decider) — this is a rule, not a limitation: a pipeline
  approving its own action is self-review by another name (E4's roster check enforces it).

## G. Adapter acceptance (all families)

1. Contract conformance fixtures pass (round-trip ask/resolve, redaction, idempotency; for bus/store drivers,
   the full semantic suite in §D incl. crash and race fixtures).
2. The lifecycle scenario for its surface passes ([PRD 17](17-scenarios.md)): for channels — parity + spoof
   fixtures; for producers — pause/answer/resume + crash-recovery fixtures.
3. The compatibility table in [PRD 19](19-harness-compatibility.md) gains its row with an honest
   "field-tested / conformance-tested / documented" label.
