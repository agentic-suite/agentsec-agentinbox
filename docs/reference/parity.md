# Channel parity reference (v0.1.0 · M14)

**BLUF:** one ask, one decision, one record shape. Surfaces differ only in `channel` and `principal`.

- Design of record: [`docs/design/v0.1.0/parity.md`](../design/v0.1.0/parity.md)

## The decision record

| Field | Meaning |
|---|---|
| `ask_id` | the ask |
| `action_identity` | the canonical action hash |
| `status` | `approved` / `denied` |
| `decided_at` | when the winning answer landed |
| `decision` | `approve` / `deny` |
| `reason` | the deny reason, if any |
| `channel` | the winning surface |
| `principal` | the authenticated approver |

`comparable_decision()` removes `channel`/`principal`; the remainder is canonical bytes and must be identical for
the same logical ask answered on any surface.

## Rules

| Rule | Behaviour |
|---|---|
| one writer | only `AnswerVerifier` + the store CAS can decide |
| first wins | a race produces exactly one `answer` transition |
| late no-op | `already resolved by <principal> at <iso>`; state untouched; `late-answer` event |
| no re-ask | a downed surface reads the outcome on its next poll |
| display-only | desktop/webhook/ci `authenticate()` returns `None`; no answer path |
| conformance | every surface runs the same suite; a deciding channel fails it |

## Fixture matrix

| Surface | Answers? | Parities |
|---|---|---|
| terminal | yes | decision record, rendering, race, late |
| desktop | no | rendering, outcome refresh, notification counts |
| webhook | no | rendering, signed display-only payload |
| CI-wait (`ci`) | no | rendering for the gate, outcome refresh |

`tests/parity/` is the executable matrix.
