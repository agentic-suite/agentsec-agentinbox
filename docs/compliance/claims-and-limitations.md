# Claims and limitations — v0.1.0 (M0–M20)

**BLUF:** code conformance is not a field-test claim. This document separates what the repository proves with
tests from what still requires the field-test box, real harnesses, and the release pipeline.

## Verified in this repository (tests + gates)

| Claim | Evidence |
|---|---|
| `ask/1.0` contract, idempotent ingest, redaction, caps | `tests/ask/`, conformance kit |
| Store contract, SQLite/memory drivers, CAS, gapless chain | conformance suite (v7), both drivers |
| Timeout = deny, crash-safe scheduler, warning delivery | `tests/scheduler/`, M4/M20 fixtures |
| Unforgeable single-use claims bound to ask/channel/tier/action identity | `tests/answers/`, SC-22-style fixtures |
| One decision across surfaces, races/late answers | `tests/parity/` |
| Flood guard, one event + one digest, legitimate burst | `tests/flood/` |
| Hash chain, payload re-hash, verify-log, export, retention, read-only posture | `tests/audit/`, `tests/cli/test_audit_cli.py` |
| agentwatch event set, schema fixtures, buffered sink, joins | `tests/events/` |
| Resolve bridge, reason codes, rescope hints, mismatch guard | `tests/lifecycle/test_resolve.py`, `tests/ask/test_api.py` |
| Channel conformance (terminal/desktop/webhook/CI) | `tests/channels/` |
| Fault matrix (store, schema, sink, channel, scheduler, reload, clock) | `tests/faults/`, `tests/cli/test_doctor_m20.py` |
| Conformance kit gates an integration; a broken adapter fails | `tests/conformance/` |

## Not verified here (blocked on other stages)

| Area | Why | Where it is verified |
|---|---|---|
| Zero-context study (≥9/10, <15 s), injection corpus approval rate | needs human participants | M24/M32 field study (PRD 21) |
| SC-01–SC-26 (and SC-68–SC-90) executed end-to-end | needs the field-test box | M24 (baseline) and M32 (final) |
| Real agentwatch/agentpolicy joins | only contract fixtures here | M16/M17 integration on the field-test box |
| Claude Code / Codex recipes | documented, not field-tested | M24 (labels updated at M25) |
| `serve --install` units, backup/restore, `report`, offline day, benches | M21 not built | M21, re-run at M24/M32 |
| Signed releases, SBOM, SLSA/Sigstore, OpenSSF Scorecard, claims lint | release pipeline | M33 (PRD 20/23) |
| Chat adapters (Matrix/Slack/Teams), web UI, server mode | not shipped in v0.1.0 | v0.1.x / v0.2.0 |

## Honest labels for the compatibility matrix

Use only: **field-tested** (executed on the field-test box with recorded verdicts), **conformance-tested**
(green `agentinbox conformance` + the relevant fixtures), **documented** (recipe exists, not field-tested),
**not-supported**. M25 publishes the matrix from these labels; until then, treat every recipe as documented.

## Standing limitations

- Unsigned producers can misreport `requested_by`; set `require_signed_producer = true` on a class to make the
  self-review anchor enforceable (a signed adapter's principal outranks the field).
- The flood guard's first `burst` asks are allowed by design; SC-13 verdicts record the allowed burst and the
  denied remainder, not a literal 200/200.
- The filesystem spool is one box; movement is at-least-once and never truth.
- The audit chain proves internal consistency; it is not externally notarized (WORM/attestation is M33+).
