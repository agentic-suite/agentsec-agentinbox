# Claims and limitations — v0.1.0

**BLUF:** code conformance is not a field-test claim. This document separates what the repository proves with
tests from what the field test proved, and what remains unproven. The v0.1.0 field test is complete **with
known issues**; the release notes and the field-test report carry the honest verdict.

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
| Zero-context study (≥9/10, <15 s), injection corpus approval rate | needs human participants | **Not run** — no cohort; the study claim is not made (M32) |
| SC-01–SC-26 (and SC-68–SC-90) executed end-to-end | needs the field-test box | M32 field test: 47 PASS / 6 FAIL (4 KNOWN env + 2 study by design) |
| Real agentwatch/agentpolicy joins | only contract fixtures here | M32 Wave-0 demo (agentpolicy → ask → deny → events → export/verify) |
| Claude Code / Codex recipes | documented, not field-tested | **Not field-tested** — s15 suite removed; 11 LLM pairs retained |
| `serve --install` units, backup/restore, `report`, offline day, benches | M21 built | M21 + M32; benches published in the release notes |
| Signed releases, SBOM, SLSA/Sigstore, OpenSSF Scorecard, claims lint | release pipeline | M33: claims lint + evidence scanner + generated matrix are live; SBOM/checksums published |
| Chat adapters (Matrix/Slack/Teams), web UI, server mode | not shipped in v0.1.0 | v0.1.x / v0.2.0 |

## Honest labels for the compatibility matrix

Use only: **field-tested** (executed on the field-test box with recorded verdicts), **conformance-tested**
(green `agentinbox conformance` + the relevant fixtures), **documented** (recipe exists, not field-tested),
**not-supported**. The v0.1.0 matrix is generated and published at
[`docs/release/v0.1.0/COMPATIBILITY.md`](../release/v0.1.0/COMPATIBILITY.md); the agentpolicy reference path
is field-tested by the Wave-0 demo, and the Claude Code / Codex CLI rows are **documented /
capture-verified, not field-tested**.

## Standing limitations

- Unsigned producers can misreport `requested_by`; set `require_signed_producer = true` on a class to make the
  self-review anchor enforceable (a signed adapter's principal outranks the field).
- The flood guard's first `burst` asks are allowed by design; SC-13 verdicts record the allowed burst and the
  denied remainder, not a literal 200/200.
- The filesystem spool is one box; movement is at-least-once and never truth.
- The audit chain proves internal consistency; it is not externally notarized (WORM/attestation is M33+).
