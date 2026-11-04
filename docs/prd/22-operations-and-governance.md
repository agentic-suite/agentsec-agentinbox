# PRD 22 — Operations, Deployment & Governance

**BLUF:** agentinbox runs in **four deployment modes** — inline CLI (no daemon), local daemon, CI sidecar,
and (v0.2.0) a hosted server mode of the same core — and every operational surface is governed: config is
code (git-reviewed, digest-audited, doctor-explained), data lifecycle is explicit (retention, pruning with
chain markers, GDPR-aware), backups and upgrades are tested, and the runbooks a real operator needs (channel
outage, secret rotation, store corruption, live flood, config drift) ship in `docs/runbooks/`. If it can
break at 3 a.m., it has a runbook.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## A. Deployment modes (one core, four shapes)

| Mode | What runs | Use | Notes |
|---|---|---|---|
| **Inline** | `agentinbox ask` as a blocking process | Interactive single-shot gates; no daemon needed | Writes to the same store; a daemon started later **adopts** pending asks (E2 recovery) |
| **Local daemon** | `agentinbox serve` | Multi-session dev box; channels (desktop/webhook, Matrix/chat when configured); producers POST and long-poll | Loopback-only bind + socket token; adopted-pending on start |
| **CI sidecar** | daemon + `agentinbox gate` steps | Self-hosted runners (or a shared build box) | Same store; gates long-poll; cancellation maps to `cancelled` |
| **Server mode** (v0.2.0) | same core, deployed | Teams/enterprise: SSO rosters, SCIM, multi-tenant, WORM audit, HA | **Not a fork** — the local binary and the server share the store schema, claim model, and events (D-8) |

**Mode rules:** (1) semantics are identical across modes — TTL, claims, audit, flood; a mode only changes
*where the process runs and who may connect*. (2) Any mode can run offline (CUJ-12). (3) Upgrading a mode must
never orphan pending asks (N-8/N-10).

## B. Process lifecycle & supervision

| Concern | v0.1.0 answer |
|---|---|
| Start on login | `agentinbox serve --install` emits **launchd** (macOS) / **systemd** (Linux) units, user-scoped, no root; socket-activation optional |
| Restart semantics | Boot pass recomputes timers; overdue transitions fire **exactly once** with `scheduler-recovered` (E2); late warnings/escalations fire once |
| Shutdown | SIGTERM → stop accepting asks, flush events + sink buffers, close store cleanly; in-flight `gate` clients get exit `4` (fail-closed), not a hang |
| Supervision | No internal auto-restart magic (launchd/systemd own that); crash loops surface via `doctor --last-exit` |
| Logs | Local files under `~/.agentinbox/logs/` with rotation by size (10 MB × 5); log lines never contain secrets or unredacted context (N-25) |
| Resources | Single process; idle memory floor in [PRD 13 §N-14](13-non-functional-requirements.md); no resident framework runtime |

## C. Configuration governance (config is code)

- **Location:** `~/.agentinbox/config.toml` by default; `AGENTINBOX_HOME` overrides the root (for servers,
  test matrices, multi-instance side-by-side).
- **Review model:** the file belongs in git (dotfiles or a platform repo); **TTLs, rosters, ladder tiers, and
  flood thresholds are security-relevant settings** — a change is a PR, reviewed like policy. `agentinbox
  doctor --explain` prints the **effective class resolution** (class → TTL/roster/ladder/thresholds) so a
  reviewer reads what will actually happen, not what the TOML seems to say.
- **Config-change audit:** the daemon emits an **`inbox-config-changed`** event (digest + changed keys, no
  values) on every applied reload — mirroring agentwatch's `recorder-config-changed` precedent. Reload is
  SIGHUP or `agentinbox reload`; invalid config **refuses to apply** and keeps the last-good (fail-closed to
  the known state, never to the broken one).
- **Secrets in config:** only references (`env:SLACK_SIGNING_SECRET`, `file:…`), never literal values — a
  literal secret in config is a **lint error**, not a warning.
- **Validation:** `init` scaffolds a commented file; `doctor` validates it end-to-end (class resolution,
  non-empty rosters, sane delays, reachable channels) with exit codes for CI.

## D. Data lifecycle, retention & privacy

| Concern | Rule |
|---|---|
| **Retention** | Resolved asks + transitions + audit chain retained by policy: `never` (default), `90d`, `1y`, or custom. Pruning is **scheduled, logged, and produces a chain marker** so `verify-log` still passes over the pruned chain ([PRD 15 §retention](15-data-model.md)) |
| **GDPR / erasure vs. chain** | The chain is append-only, so erasure is by **redaction-in-place of payload fields** (identifiers, reasons) while preserving hashes — the marker records the erasure event; documented honestly as "tamper-evident, not forgettable-by-rewrite" |
| **Export** | `export --session/--ask/--format jsonl|csv` (CSV for auditors, JSONL is canonical, both carry the chain); exports are **written on request to `exports/`**, never auto-emitted; export itself is an audit event |
| **What is never stored** | Secrets (E6), unredacted arguments (E6), full transcripts (only producer-provided tails), biometric-like data (nothing of the sort) |
| **Multi-principal caution** | v0.1.0 is single-principal by design (D-8): shared machines share the store, and the docs say so loudly; per-user `AGENTINBOX_HOME` is the supported pattern until server mode exists |

## E. Backup, restore, migration

| Operation | Answer |
|---|---|
| **Backup** | `agentinbox doctor --backup out.tar` — uses SQLite's online-backup path (WAL-safe), plus config (secrets redacted to refs) and key-slot metadata; **no raw signing secrets in backups** (re-referenced from env/secret store at restore) |
| **Restore** | Extract into a fresh `AGENTINBOX_HOME`, run `doctor`; the chain verifies or the restore aborts loudly |
| **Restore mid-flight** | Pending asks adopt on start (E2); anything past `expires_at` expires once — a restored box **never resurrects** an expired approval |
| **Upgrades** | Store schema is versioned + forward-migrating on open; migrations tested old→new for every released version; **downgrade refuses loudly** (N-10), never guesses |
| **Contract compatibility** | `ask/1.0`, exit codes, and event set are additive-only within v0.x (E10); a release notes any new optional fields |

## F. Monitoring & alerting (local, by the owner, about the box — not about people)

- **`agentinbox report --json`** — [PRD 07](07-success-metrics.md) metrics computed locally: response-time
  percentiles, expiry counts, escalation firings, flood events, answer-rejected causes, deny-rate by class.
- **`agentinbox doctor`** — store + chain, schema versions, clock skew, key presence, channel reachability,
  config validity; exit-coded; scheduled in cron/CI it becomes the health check.
- **Signals that page the owner** (via an `on-event` hook config — local command, not telemetry): a flood
  event, a chain verification failure, a config reload failure, any configured external channel unreachable > N minutes with pending
  irreversible asks, clock skew beyond the signature window.
- **No telemetry out, ever** (N-26): the product phones nobody; if a team wants fleet metrics, they export
  the agentwatch events they already own.

## G. Coordination with the ecosystem's operational tooling

| Tool | Relationship |
|---|---|
| **agentpolicy** | The reference producer: its `AskBroker` persists its own record; agentinbox's `ask_id` is returned in the resolve so the two stores join; policy version + clause ride the contract (context the approver reads) |
| **agentwatch** | Event sink; if the sink is down, events buffer locally with a gap marker (E9) — the local chain remains authoritative |
| **agentdrill** | Runs the flood/attack packs against a deployed box as a release gate; the same packs double as an operator's **live-fire drill** runbook |
| **agenthalt / agentkeys** | The kill-switch and credential broker consume the *outcome* (a denied ask is a denied action; an approved one releases the capability at the enforcer) — no shared state, just the contract |

## H. Runbooks (shipped under `docs/runbooks/`, v0.1.0)

| Runbook | Covers |
|---|---|
| **RB-1 External-channel outage** (webhook/Matrix/chat adapter) | Symptoms (`ask-delivery-failed` streak), terminal/CI continuity, adopt-after-recovery, when to consider a temporary channel-off config (and why TTL still denies) |
| **RB-2 Signing-secret rotation** | Chat-adapter signing secrets / webhook HMAC key rotation without losing pending asks (claims are local — unaffected); the overlap window; verifying with `doctor` |
| **RB-3 Store corruption** | `verify-log` triage, quarantine copy, last backup restore, what is lost (unresolved asks re-ask by producers), what is never lost (delivered decisions) |
| **RB-4 Live flood** | Reading the `ask-flood` event, identifying the offending agent/session, pausing that agent (agenthalt), throttle tuning, post-incident policy feedback |
| **RB-5 Config drift / bad reload** | last-good config rollback, effective-config diff (`doctor --explain`), the `inbox-config-changed` trail |
| **RB-6 Clock incident** | NTP fix, `doctor` skew check, why TTLs did not extend, replayed signature failures explained to approvers |
| **RB-7 Escalation ladder misfire** | Config error triage (empty tier, zero-delay), the drill to re-run (SC-11), amending the ladder under review |
| **RB-8 Upgrade day** | Pre-upgrade backup, migration check, conformance fixtures, post-upgrade `verify-log` + `doctor` |

## I. Governance of the gate itself (who may change the rules)

| Change | Who | Control |
|---|---|---|
| TTLs, warn windows | platform owner | git-reviewed config; `inbox-config-changed` event; class-table diff in the PR |
| Rosters (who may approve) | team lead | git review; roster changes are high-visibility (an approval's principal is compared against the **roster at answer time**, recorded in the transition) |
| Ladder tiers | on-call owner | git review + the SC-11 drill after material changes |
| Flood thresholds | platform owner | git review; changes noted in the next `report` so a threshold "fix" can't silently suppress events |
| Class definitions (what is `irreversible`) | **agentpolicy owns it** | The inbox never redefines classes; it consumes them (N-8) |

**The governance invariant:** the inbox is the *record of who said yes*. Everything that changes how "yes"
happens — TTLs, rosters, tiers, thresholds — is itself recorded. A gate whose rules change invisibly is not a
gate.
