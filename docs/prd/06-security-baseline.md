# PRD 06 — Security Baseline & Threat Model

**BLUF:** agentinbox is a **security boundary**: an approval it records authorizes an irreversible action. The
baseline therefore treats (1) the ask text as attacker-controlled, (2) every channel callback as spoofable,
(3) the store as tamper-target evidence, and (4) time as an attack vector. The invariants: **no ML in the
decision path**, **no allow without an authenticated human + a valid single-use claim bound to the exact action**,
**timeout = deny**, **fail closed everywhere**, and **redaction before persistence**.

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## The five security invariants (test-enforced)

| # | Invariant | Enforcement |
|---|---|---|
| **I-1** | **No answer without an authenticated human + a valid claim** | Answer verifier requires both (E3, E4); a missing/failed principal or token rejects and logs `answer-rejected` |
| **I-2** | **An approval binds to exactly one action identity** | `action_identity` (tool+action+canonical args) checked at resolve; mismatch → deny (`deny_action_identity_mismatch`, reusing agentpolicy's code) |
| **I-3** | **Timeout = deny, always** | Expiry is a terminal state feeding `human_gate_timeout`; no config, channel, or retry path converts expiry to allow |
| **I-4** | **All agent-derived text is inert data** | Escaping, length caps, untrusted labeling; trusted fields only from authenticated producer adapters (E5) |
| **I-5** | **No secret ever persisted or rendered** | Redaction before store/channel/audit + receipts (E6); evidence scanner in CI |

## STRIDE-style threat model

| ID | Threat | Vector | Control | Test |
|---|---|---|---|---|
| **T1** | **Spoofed approver** — attacker answers an ask | Forged chat callback (where a chat adapter is configured); stolen token; off-roster user answers | Platform HMAC signature + timestamp window (chat adapters); claim single-use + hashed + bound; roster check; first-wins | SC-22 replay/forge matrix |
| **T2** | **Spoofed trusted context** — attacker writes the "policy clause"/"criticality" the approver reads | Malicious tool output or agent supplies fake trusted fields | Trusted fields accepted only from authenticated producer adapters; otherwise rendered **unverified** | SC-23 |
| **T3** | **Prompt injection via ask text** — embedded instructions ("CISO authorized this") drive approval | Agent/tool text lands on the card | Untrusted labeling + inert rendering + no links in untrusted fields; injection corpus must produce 0 approvals | SC-22 corpus |
| **T4** | **Replay / forwarding** — a valid approval reused | Forwarded chat message; duplicated HTTP callback; late answer | Single-use claims; ask binding; expiry window; `late-answer` logged no-op | SC-07, SC-08 |
| **T5** | **Ask flood / exhaustion** — spam until the approver approves anything (or mutes) | Looping or malicious agent | Token buckets, duplicate coalescing, digest-only notification, flood auto-deny event (R7) | SC-13, SC-14 |
| **T6** | **Denial of decision** — inbox unreachable at answer time | Store lock; network partition; daemon down | Local-first single process; `gate` exit 4 fail-closed; producers deny at enforcer on 503 | SC-24 fault matrix |
| **T7** | **Audit tampering** — evidence edited after the fact | Direct store edit; log truncation | Hash chain (`seq` + `prev_hash` + `entry_hash`), `verify-log`, export carries the chain | SC-20 |
| **T8** | **Secrets exfil via the ask itself** — arguments contain keys/PII rendered into any channel payload | Args copied into the card | Ingest-time redaction + receipts + evidence scanner on store/channel/audit dumps | SC-21 |
| **T9** | **Time manipulation** — TTL extended by clock jump or restart race | NTP jump; kill -9 during expiry window | Absolute UTC + monotonic deltas; boot-time exactly-once expiry; backwards jump cannot extend (E8) | SC-09, SC-10 |
| **T10** | **Self-approval** — requester approves their own irreversible ask | Agent owner both requests and approves | `requested_by` recorded; `self_review=deny` default for irreversible classes | SC-17 |
| **T11** | **Confused deputy** — approval answers a *different* ask than displayed | Card/link manipulation between display and tap | Token bound to `ask_id` + identity; typed confirm for irreversible terminal approvals | SC-08 |
| **T12** | **Supply chain / update attack** — malicious release ships a backdoor | PyPI/package compromise | Signed releases (Sigstore), pinned deps, SLSA provenance, DCO'd commits — org floor | release checklist |
| **T13** | **Local adversary — producer spoofing** — a process on the same machine emits asks (or rotates `agent_id`s to evade flood buckets, or forges trusted fields like `policy_ref`) | Any local process can reach loopback | Socket token on the loopback API; producer identity recorded (uid where the OS exposes it) and included in throttle keys; trusted fields accepted only from the **agentpolicy adapter's key** (v0.1.0) or per-producer signing keys (server mode); unverified trusted fields render as **unverified** | SC-22 extensions + `test_trusted_fields.py` |
| **T14** | **Local adversary — answer forgery via loopback** — a non-approver process on the box tries to answer asks directly | Direct `POST /v1/asks/{id}/answer` | Answers require the claim secret (never printed, never in env, held only by channel adapters) **and** a channel-authenticated principal; the API is not a bypass around channel verification — it *is* the verifier | SC-22 (raw-API forge rows) |

## Channel security specifics

| Channel | AuthN of the human | Anti-spoof |
|---|---|---|
| **Terminal** | OS session (uid + TTY ownership); `--as` only with explicit config | Token shown never; typed confirmation for irreversible; non-interactive mode cannot approve |
| **Desktop notification** | None required to *deliver*; answers happen in the terminal under the OS session (uid + TTY ownership) | The notification is a wake-up, **not a decision surface** — its buttons (platform-dependent, spoof-prone) never answer; a faked notification cannot forge the terminal principal |
| **Webhook** | None at v0.1.0 — **display-only**; the answer arrives via the terminal/CLI paths with full verification | Outbound posts are HMAC-signed so receivers can verify provenance; a compromised receiver can render but never answer |
| **Matrix / Slack / Teams** (optional adapters) | Platform user id of the interacting user, from a **signature-verified** callback (raw-body/platform HMAC + timestamp window), then roster check | Unsigned/expired/replayed callbacks rejected before parsing; forwarded buttons don't carry the roster user; structured actions only, never free text |
| **CI** | The blocking process exit; answers arrive via terminal/interactive-channel paths with full verification | Pipeline cancellation cancels the ask; job retries idempotent; unreachable → exit 4 |

## Data classification & privacy

- **Ask content**: tool, action, redacted args, reason codes, environment/data-class labels — stored locally.
- **Never stored**: secret values (redacted at ingest), full session transcripts (only the tail summary the
  producer includes), credentials.
- **Approver data**: channel principal ids (e.g., Slack user id), decision, timestamps, optional reason.
- **Transport**: Channel payloads (webhook/chat/desktop) carry redacted content only; the full unredacted context **never leaves the
  machine** — the store is the only place the (already redacted) record lives, by design, so there is nothing
  richer to leak.

## Security hardening (own posture)

Loopback-only HTTP by default (bind `127.0.0.1`; a socket token for local producers); file permissions 0600 on
the store and keys; constant-time token comparison; no `--force`/`--yes` flags anywhere near an answer; input
size caps at ingest (per-field and total) to prevent storage-based DoS; log injection sanitized (newline
control); a `doctor` that refuses to look healthy when the store is corrupt.

## OWASP/ATLAS/NIST alignment (summary)

| Control | Mapping |
|---|---|
| Identity-bound approvals, no chat-bot decisions | OWASP **ASI09** Human-Agent Trust Exploitation · EU AI Act **Art. 14** human oversight |
| Flood throttling, fail-closed | **ASI10** Rogue Agents · LLM06 excessive agency |
| Redaction at ingest, secrets never rendered | **LLM02** sensitive disclosure |
| Untrusted rendering, unverified trusted fields | **LLM01** prompt injection (mitigation by architecture) |
| Hash-chained evidence, export | **Art. 12** logging (EU AI Act) · NIST AI RMF **MEASURE** |
| Time-boxed asks, no standing grants at v0.1.0 | PAM-style least privilege (NIST SP 800-63B thinking applied to approvals) |

Full mapping lives in [PRD 20](20-standards-and-claims.md) and `docs/compliance/`.

## What we explicitly do **not** claim

- We do **not** "detect prompt injection" — we make injected text **inert** in the approval surface
  (architectural control, not detection).
- We do **not** claim unforgeability of any chat platform — we claim our callbacks are verified and our tokens
  are single-use, which holds regardless of platform weaknesses **and holds with no chat platform configured at
  all** (the default install's answer paths are the OS session and the CI process exit).
- We do **not** claim the audit log is cryptographically notarized (no external timestamp authority at
  v0.1.0) — the chain proves internal consistency; a determined local admin can rewrite it **with visible
  recompute work**. WORM/external attestation is roadmap ([PRD 22](22-operations-and-governance.md)).
