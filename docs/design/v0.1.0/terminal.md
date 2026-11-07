# Terminal channel design — v0.1.0 (M7)

**BLUF:** The terminal is the primary human surface: the M5 card, `a`/`d` answers with typed confirmation
and required deny reasons, the **OS session as principal**, and a strict non-interactive mode that prints a
structured result and **can never approve**. Channels deliver and authenticate; only the M6 verifier decides.

- **Milestone:** M7 ([WBS Part 4](../../wbs/v0.1.0/wbs-v0.1.0-part4-claims-terminal.md), issues #181–#191)
- **Requirements:** R2, E4, N-2/N-40..42 · CUJ-1 (surface), CUJ-9

---

## 1. Principal

| Case | Principal |
|---|---|
| default | OS user (`getpass.getuser()`) — the TTY owner |
| `--as NAME` | accepted **only** when `[channels.terminal] allow_as = true`; recorded as an **assumed** principal in the answer transition (`detail.assumed_principal = true`) |

An assumed principal is visible in the audit; it is not a hidden impersonation. Without config, `--as` is
refused loudly (exit `4`).

## 2. Interactive loop

```
card (M5, full four blocks)
[a]pprove / [d]eny / [?]details / [q]leave pending
```

- approve on an `irreversible` class requires typing the action name (typed confirmation);
- deny on a class with `require_reason_on_deny` requires a non-empty reason;
- `q` leaves the ask pending and exits `5` — no claim is consumed;
- a rejected answer prints the **public** cause and exits `4` (no decision was recorded);
- success exits `0` (approved) or `2` (denied).

The channel mints its own claim (terminal, ask tier) and submits through `AnswerVerifier` with
`channel_authenticated=True`. It never writes status directly.

## 3. Non-interactive contract (D-5)

When stdin is not a TTY:

- **no prompt is ever shown**;
- stdout is one JSON `resolve/1.0` object;
- exit code is the decision: `5` pending (never `0`), `2` deny, `3` expired, `4` unavailable.

A script cannot approve: the only path to `0` requires an interactive answer with a principal.

## 4. Accessibility

- ASCII-safe layout; no colour is required to read any signal (colour is never the sole signal).
- `NO_COLOR` is honoured (the renderer already emits no colour).
- Full keyboard operability: `a`, `d`, `?`, `q`; no mouse, no timing pressure.
- Screen-reader-linear: block titles, then one field per line.

## 5. Channel contract

`InboxChannel`: `name`, `deliver(ask, card)`, `authenticate(as_name=None) -> principal`. The conformance test
asserts a channel exposes **no** `decide`/`submit` method — channels cannot answer for a human.

## 6. Tests

| File | Covers |
|---|---|
| `tests/channels/test_terminal.py` | interactive approve/deny, reason/confirm, `q`, non-interactive, `--as`, rendering |
| `tests/channels/test_cli_answer.py` | script cannot approve (exit 5), inbox listing, unknown ask |
| `tests/channels/test_conformance.py` | the shared channel contract |
