# PRD 18 — Approval Integrity (anti-spoofing, the security core)

**BLUF:** An agentinbox approval is a **cryptographic object**: a single-use **claim** (hashed secret, bound to
the ask's action identity, the channel, the escalation tier, and the deadline) presented by an **authenticated
principal** who is on the **roster** for that action class and is not the requester (where configured). Every
other path — forwarded links, replayed callbacks, late taps, forged principals, model-written "approvals" — is
a logged rejection. This document resolves the consolidated PRD's open question: *"anti-spoofing for approval
channels (especially Slack) — approval links must be unforgeable."*

**Status:** Draft — v0.1.0 (2026-11-04) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #220

## The answer-acceptance pipeline (in order, all must pass)

| Step | Check | Failure event (`answer-rejected` cause) |
|---|---|---|
| 1 | **Channel authenticity** — e.g., Slack: raw-body HMAC-SHA256 (`v0=`) with the app signing secret + `X-Slack-Request-Timestamp` within ±5 min, verified before any parsing | `bad_signature` |
| 2 | **Claim validity** — token exists, hash matches (constant-time compare), not expired, not revoked, not used | `unknown_claim` / `expired_claim` / `revoked_claim` / `used_claim` |
| 3 | **Binding** — claim's `ask_id` + `action_identity` + `channel` + `tier` match the ask being answered | `binding_mismatch` |
| 4 | **Ask state** — ask is `pending` and not past `expires_at` | `late` (state unchanged; approver told "already resolved" / "expired") |
| 5 | **Principal authorization** — the authenticated principal is on the class roster; `self_review` policy checked against `requested_by` | `off_roster` / `self_review` |
| 6 | **Commit** — first winner records the decision; all later attempts become observations | `late` (no state change) |

Steps 1–5 are **verifications**, step 6 is the only write. Any failure at any step: logged, approver informed,
state untouched, **deny-safe by default** (the ask keeps running its clock).

## Claim token design (v0.1.0)

```
claim_id:  cl_<12 hex>                       # public handle (safe in logs/cards)
secret:    128-bit random                    # the actual bearer proof
stored:    H(secret)                         # never the raw secret
binding:   ask_id ‖ action_identity ‖ channel ‖ tier ‖ expires_at
encoding:  <claim_id>.<secret_b64>           # carried in the button action value / terminal session
```

Properties (each testable, each mapped to a SC-22 attack):

- **Single-use** — first presentation marks `used`; second → `used_claim` (replay).
- **Deadline-bound** — expires with the ask, independent of claim issue time.
- **Tier-invalidated** — escalation revokes all prior-tier claims; a tier-1 tap after tier-2 fired →
  `revoked_claim` (prevents "sleeper approvals" answering after the ladder moved).
- **Channel-scoped** — a terminal-issued claim cannot answer via the raw HTTP API; a chat-surface claim cannot
  answer on terminal; a webhook cannot answer at all (display-only at v0.1.0).
- **Non-guessable, non-enumerable** — 128-bit random; constant-time compares; uniform error timing on bad
  `claim_id`.
- **Never in a URL that does anything** — links are informational (open the terminal UI / Slack message);
  answers are POSTs with the claim in the body; **GET can never answer an ask** (N-3).

## Per-channel authentication assurance (honest table)

| Channel | Principal proof | Assurance | Residual risk (documented, not hidden) |
|---|---|---|---|
| Terminal | OS session uid + TTY ownership (+ optional `--as` with config) | The human at the machine | A shared login weakens attribution; `--as` is audited |
| Desktop notification | None to deliver; the answer happens in the terminal under the OS session (uid + TTY) | The human at the machine | The notification itself is a wake-up, never a decision surface — a spoofed notification cannot forge the terminal principal |
| Webhook | None at v0.1.0 (**display-only**); answers arrive via the terminal/CLI paths | The remote rendering is honest (HMAC-signed outbound) | A compromised receiver can render, never answer; interactive webhook adapters must pass the chat-adapter conformance + their platform's signature model first |
| Matrix (v0.1.x) | Platform-verified user id via signed event/interaction, roster check | The Matrix account, on the roster | Same residual shape as any chat account: a compromised **account** can approve — mitigated by step-up; a compromised **adapter secret** can forge callbacks — mitigated by rotation guidance + `doctor` |
| Slack / Teams (optional community adapters) | Same contract as Matrix: platform-verified user id via signed callback, roster check | The platform account, on the roster | Identical residual risks as Matrix; identical mitigations; **never load-bearing** — disable the adapter and the product is unchanged |
| CI | None (CI never approves — waiter only) | — | — |

**Step-up (v0.1.x design now):** for `irreversible`/`critical` classes, an approve action triggers a second
factor (platform-verified user via a chat adapter, or the terminal OS session, + a challenge shown on the
terminal / an authenticator app code). The design is
frozen so the lifecycle has a slot; it ships only with its own attack pack. It is *not* in v0.1.0 — the roster
+ signature model is the v0.1.0 assurance level, stated plainly on the card footer for critical asks.

## The confused-deputy & identity-binding defenses

- **Action fingerprint on the card:** the last 8 hex of `action_identity` shown next to the decision buttons —
  an approver comparing two surfaces (or two similar asks) catches substitution.
- **Typed confirmation on irreversible terminal approvals:** approve requires typing the action's short name
  (e.g., `DROP TABLE customers`), so a rushed `a` cannot release it and a swapped card cannot be confirmed by
  muscle memory.
- **Deny-reason required** on irreversible classes: raises the rubber-stamp cost and feeds policy tuning
  (R-R1 mitigation).
- **`requested_by` recorded at ingest** and rendered on the card next to "requested by" — the approver sees who
  benefits (self-review is visible, not just blocked).

## Anti-injection rendering rules (E5, executed at the renderer)

1. Untrusted fields (arguments, tool output, agent intent, deny reasons typed by humans are **trusted-ish**
   but still escaped) render as **plain text**; no markdown, no HTML, no link auto-detection, no emoji
   shortcodes expanded into clickable entities.
2. Length caps per field + per card, with a visible "+N chars omitted" marker.
3. Trusted chrome (title, four block headers, buttons, fingerprints) is generated from structured fields only
   and is visually distinct.
4. Untrusted content is prefixed with a source label (`[tool output — untrusted]`) wherever it appears.
5. No images, no message-link unfurls inside untrusted fields.
6. The corpus gate: SC-23 must produce **0 approvals and 0 navigation events** from injected content —
   release-blocking.

## Online-guessing resistance (the claim-brute-force math)

- A claim secret is **128 bits** drawn from the OS CSPRNG; the store holds `H(secret)`, so there is **no
  offline dictionary** (nothing to hash guesses against except the stored hash — and the search space is
  2^128).
- Online guessing is doubly bounded: the deadline (claims expire with the ask) and **verification rate
  limits** — per-claim attempt counters with lockout and per-endpoint token buckets; a burst of bad claims is
  itself an `answer-rejected` (cause `guessing`) *event*, so brute force is noisy, slow, and recorded.
- Timing side channels are closed: constant-time comparisons, uniform error responses (same body shape and
  latency envelope for `unknown_claim` vs `bad_signature` vs `off_roster`), and no existence leaks via
  distinct error codes on the public path (distinct causes are written to the **audit**, shown only to
  already-authenticated approvers).

## What we do about the chat-platform risk

Our guarantees are **ours**, not the platform's: signature verification is local (secret in config), claim
tokens are local, the roster is local, and the audit is local. If a chat platform introduces a regression (new
interaction type, changed signing), the adapter fails closed (`bad_signature`), the field fails, and terminal
+ CI remain fully functional. The R-R9 mitigation is structural: **no single channel is load-bearing for
correctness.**

## Open items (owner: this PRD, tracked to closure)

| Item | Status at v0.1.0 | Closes |
|---|---|---|
| Step-up re-auth for critical classes | Designed ([PRD 09](09-roadmap.md) v0.1.x), not shipped | with its attack pack |
| Producer-adapter signing key management (trusted-field HMAC) | agentpolicy shared-key in v0.1.0; per-producer keys in server mode | v0.2.0 |
| Claims on channel-tiers with **channel-wide** rosters (e.g., `#agent-oncall` anyone-taps) | Supported but **config-explicit**; card footer states "anyone in #agent-oncall can answer" | documented behavior |
| WORM/external notarization of the audit chain | Local chain only | v0.2.0 server mode |
