# PRD 13 — Non-Functional Requirements

**BLUF:** agentinbox must be **fast enough to not be the reason an approver waits** (sub-100 ms local
operations, sub-second desktop alerts, sub-2 s webhook delivery), **small enough to trust** (one install,
one process, no daemon zoo),
**durable** (no lost decisions across crashes), **honest offline** (zero-cloud mode is complete), **portable**
(macOS/Linux first-class, loopback-only), and **observable to its owner without surveilling anyone else**
(local metrics only, no telemetry out).

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## Performance

| NFR | Target | Measured by |
|---|---|---|
| **N-1** Ingest latency (`POST /v1/asks` → recorded) | **p50 < 50 ms, p99 < 250 ms** local | bench fixture in CI |
| **N-2** Render+deliver: terminal | **< 100 ms** from ingest to card on screen | bench fixture |
| **N-3a** Render+deliver: desktop notification | **< 1 s p99** local (no network involved) | adapter bench |
| **N-3b** Render+deliver: external channels (webhook; Matrix/chat when configured) | **< 2 s p50, < 5 s p99** (network-dependent, retried within bounds) | adapter bench with a mock API |
| **N-3c** Filesystem-bus pickup latency (inotify/FSEvents, bounded-poll fallback) | **≤ 1 s** from job publish to consumer start | spool bench |
| **N-4** Resolve latency (answer → producer-visible outcome) | **p99 < 100 ms** local; long-poll wakes immediately | bench fixture |
| **N-5** Scheduler jitter on warn/escalate/expire | **≤ 1 s** at the configured instant | timer tests |
| **N-6** Pathological load | 10k resolved asks, 100 pending: all of the above hold; UI pages the inbox | load fixture |
| **N-7** Startup + `doctor` | **< 2 s** cold, on a real store | bench fixture |

**The budget that matters:** the *human* round-trip (p50 seconds) dwarfs machine time, so we spend engineering
on **card quality** (R1) rather than shaving milliseconds — but a sluggish local inbox makes approvers alt-tab
away, so the above are floors, not stretch goals.

## Reliability & durability

| NFR | Requirement |
|---|---|
| **N-8** | No ask is lost across crash/restart (WAL, atomic writes; E2 recovery exactly-once semantics) |
| **N-9** | No resolved decision is ever mutated (append-only transitions; corrections are new events) |
| **N-10** | Store survives version upgrades; migrations are tested **both directions** (open-old, refuse-loudly on downgrade) |
| **N-11** | Delivery failures never block ingest (bounded async queues; E7) |
| **N-12** | The process is single-user, single-machine; concurrent producers supported via the loopback API with write serialization |

## Size, packaging, dependencies

| NFR | Requirement |
|---|---|
| **N-13** | One install (`pip install agentsec-agentinbox`); zero required external services; optional external channels (webhook/Matrix/chat) only |
| **N-14** | Runtime memory **< 100 MB** idle with a real store; no resident framework runtime |
| **N-15** | Dependency surface minimal and pinned; no ML/scientific stack anywhere; stdlib-first (urllib vs requests is a decision kept in ADRs with vendoring considered) |
| **N-16** | Works with `python -m agentinbox` and the `agentinbox` console script both |

## Environment & portability

| NFR | Requirement |
|---|---|
| **N-17** | macOS + Linux first-class (the ecosystem's field-test box is macOS; CI runs both); Windows best-effort, no claims |
| **N-18** | Loopback-only bind by default (`127.0.0.1` + a local socket token); binding wider is a loud config with a `doctor` warning |
| **N-19** | **Offline-complete**: with no network, terminal + CI + audit + export all function; Slack disabled cleanly; no telemetry ever calls out (CUJ-12) |
| **N-20** | Python 3.11–3.13 supported (matches agentpolicy/agentwatch) |
| **N-21** | Timezone-agnostic correctness: all persisted UTC; rendering local; DST/jump safe (E8) |

## Security NFRs (summary — full treatment in [PRD 06](06-security-baseline.md))

| NFR | Requirement |
|---|---|
| **N-22** | Store/keys 0600 by default; directory 0700; `doctor` warns on loose perms |
| **N-23** | Constant-time comparisons for tokens; hashed storage of claim secrets |
| **N-24** | Input caps: per-field and total ask size (default 256 KiB) — oversized rejects with a diagnostic, never truncates silently |
| **N-25** | Log injection sanitized; no secrets in logs (evidence scanner in CI) |
| **N-26** | No telemetry/analytics out, ever; `report` is local-only output (privacy as a default, not a setting) |

## Observability (for the owner, not about the approver)

| NFR | Requirement |
|---|---|
| **N-27** | `agentinbox doctor` checks: store integrity + chain, schema versions, clock skew, key presence, channel reachability (any configured external channel), bus spool health (flock owner, leftover `.tmp`), config validity — exit-coded for CI |
| **N-28** | `agentinbox report --json` computes [PRD 07](07-success-metrics.md) metrics locally from the owner's own data |
| **N-29** | Every async failure (delivery, sink, escalation) is an event the owner can see; **no silent failures** |
| **N-30** | Log levels follow the ecosystem convention; `--verbose` adds per-event detail; never redaction-bypassing raw dumps |

## Usability

| NFR | Requirement |
|---|---|
| **N-31** | Install → first recorded approval **< 5 minutes** for the terminal-only path (CUJ-1; field-tested, docs promise) |
| **N-32** | Every error message names the next action ("Slack callback rejected: signature expired — check clock skew via `doctor`") |
| **N-33** | Config is one file, commented by `init`, validated with actionable errors; effective config printable (`doctor --explain`) |
| **N-34** | The card is readable at a glance on the away-from-desk surface — the desktop notification carries class + fingerprint + TTL, and the full card opens in one terminal command (phone via Matrix/webhook recipes when configured) — the 3 a.m. test (CUJ-5) |
| **N-35** | Keyboard-only terminal flow; no interactive-only dead ends in scripts (non-interactive mode returns structured JSON + exit codes) |

## Maintainability & compliance (own posture)

| NFR | Requirement |
|---|---|
| **N-36** | `ruff` + `mypy --strict` + targeted pytest per ticket; full gate once per milestone (org rule) |
| **N-37** | DCO'd commits, CODEOWNERS, pinned deps, Sigstore-signed releases, SLSA provenance — the org floor |
| **N-38** | Conformance fixtures (contract, exit codes, event schema) live in-repo so external adapters test against *this* repo's truth |
| **N-39** | Docs (this PRD set) version with the code; claims lint runs against docs in CI |

## Accessibility

| NFR | Requirement |
|---|---|
| **N-40** | Severity/criticality is **never encoded by color alone** — every card carries a text label (`[ASK] irreversible · production`), and terminal rendering is ASCII-safe with no color dependency (colors are additive, via NO_COLOR honored) |
| **N-41** | Cards are screen-reader navigable: chat-platform cards (Matrix/Slack, when configured) use text-first composition (headers, sections, buttons with `text` actions — no image-only state); the terminal card is a plain, linearly-readable document |
| **N-42** | Interactive terminal flows are fully keyboard-operable (N-35) with visible focus state and no time-boxed input that a screen reader cannot reach in time; the typed-confirmation for irreversible actions accepts the exact string and offers a paste-safe retry |
