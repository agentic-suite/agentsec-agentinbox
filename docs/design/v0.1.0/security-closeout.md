# Security close-out design — v0.1.0 (M22)

**BLUF:** the five PRD 06 invariants each get a test that **fails when violated**; the evidence scanner
proves zero secrets across every artifact class; the spoof/replay/forge, injection, and flood packs run
as release-blocking CI jobs; and the remaining hardening is comparison, uniform errors, log hygiene, and
permissions. No new network path, no telemetry, no ML in a decision path.

- **Milestone:** M22 ([WBS Part 12](../../wbs/v0.1.0/wbs-v0.1.0-part12-security-docs.md), issues #74–#85)
- **Requirements:** PRD 06 (all), PRD 18 (all), E3/E4/E5/E6, N-22..N-26, PRD 21 EV-9

---

## 1. Invariant → test map

| Invariant | Enforcement | Test that fails on violation |
|---|---|---|
| **I-1** No answer without a claim **and** an authenticated principal | `AnswerVerifier.submit` rejects unauthenticated channels and unknown claims; the commit records `claim_id` + `principal` | `tests/security/test_invariants.py::test_i1_*`; a store with an answer transition missing either field is detected by `agentinbox.invariants` |
| **I-2** Identity binding (ask, channel, tier, action identity) | claim comparison in `answers.py`; schema v5 `action_identity` | `test_i2_*`: substituting another ask/action is `identity_mismatch`, state unchanged |
| **I-3** Timeout never allows | scheduler expiry → `EXPIRED`; `allows_on_expiry` counter | `test_i3_*`: 100 expiries, counter `0`; a mutated resolver that allowed would fail the assertion |
| **I-4** Untrusted text is inert | card escape/label rules; webhook display-only payload | `test_i4_*`: poisoned corpus renders as text, never as an instruction; zero approvals caused by embedded text |
| **I-5** No secret persisted | redaction before ingest; scanner over the store/renders/exports/backups | `test_i5_*`: seeded secret is redacted, scanner finds zero; a raw secret written directly is detected |

`agentinbox/invariants.py` exposes the store-level checks (`answers_without_claim`,
`answers_without_principal`, `answers_without_binding`) so a broken fixture and the release pack share
one definition.

## 2. Evidence scanner (`agentinbox/scanner.py`)

- **Rules:** the same pattern set as redaction (`agentinbox.redaction.SENSITIVE_PATTERNS`) plus the
  private-key block rule — one source of truth for "secret-shaped".
- **Artifact classes:** store dump (ask payloads, transition details/reasons, deliveries, audit bodies,
  flood windows), rendered channel payloads (terminal/desktop/CI text + webhook JSON), audit exports
  (JSONL/CSV), and backup archives (every member).
- **Output:** rule + artifact + line, never the matched value. `ScanReport.ok` is the gate.
- **Self-test:** `python -m agentinbox.scanner --self-test` scans a clean corpus (must be zero) and a
  seeded corpus (must be detected). CI runs it; a seeded leak fails the build.
- **Live scan:** `python -m agentinbox.scanner --home <home> [--archive <tar>]` scans read-only; exit `1`
  on any finding.
- **Honesty:** a scanner pattern set is not a proof. It is a tripwire for the classes the product itself
  redacts, documented as such.

## 3. Attack packs (`agentinbox/packs.py`)

| Pack | What it attempts | Green means |
|---|---|---|
| `spoof-replay-forge` | forged/unknown claim, bad secret, replayed used claim, off-roster principal, identity substitution, self-review | every attempt rejected, evidence recorded, zero state change |
| `injection` | embedded instructions, fake urgency, CISO impersonation, poisoned context | rendered as untrusted text, zero approvals caused by the text |
| `flood` | 200 asks from one bucket | allowed = burst, remainder denied, one `ask-flood` event, one digest |

`python -m agentinbox.packs` exits `0` only when all three are green. CI runs it as a separate job; the
invariant checks are also applied to the pack's store (a broken gate fixture fails). Standalone so M24
can re-run the same packs as drills.

## 4. Timing, comparison, uniform errors

- All secret/token comparisons are `hmac.compare_digest` (claim hash, API bearer token, adapter HMAC).
- `AnswerRejected.public_cause` collapses credential failures into `bad_claim`; the API returns the same
  `403 {"error": {"field": "authorization", ...}}` body for every credential/authorization failure. The
  distinct internal cause is recorded in `answer-rejected` evidence, readable only from the store.
- The claim-attempt counter (`max_attempts=5`) turns guessing into a `guessing` rejection; a test proves
  the public body stays uniform.
- Timing envelopes are tested by equivalence of public responses, not by wall-clock assertions (which
  are flaky); the code paths share one reject helper so no branch returns early with a different shape.

## 5. Input, log, permission sweep

- `agentinbox.logsafe.sanitize_log_line` strips control characters, ANSI escapes, and newlines, and caps
  length. The CLI parser error path and untrusted error detail go through it.
- Field/total caps are re-audited (256 KiB total, per-field caps in the contract); oversized asks still
  reject with a diagnostic and never truncate.
- Creation paths (home, config, store, backup, restore, units) force `0700`/`0600` even with a permissive
  umask; tests set `umask 000` and assert the result.
- The CLI surface has no `--yes` or approval shortcut; only `init --force` and `doctor --restore --force`
  accept a destructive flag, and a surface test pins that list.

## 6. Own posture

- `agentinbox/posture.py`: `dependency_manifest()` proves the runtime dependency set is empty and names
  no model/ML package; `generate_sbom()` emits CycloneDX JSON; `check_security_txt()` validates the
  committed `docs/security.txt` (contact, policy, expiry).
- `SECURITY.md` states the disclosure SLA (acknowledge 48 h, critical fix target 7 days, coordinated
  disclosure 90 days). Publishing `security.txt` on the project domain is a release step (M25), not a code
  claim.
- SBOM generation is a dry run in M22 (artifact attached at M25); the generator and its test ship here.

## 7. CI gates

A `security` job runs:

```sh
python -m agentinbox.packs
python -m agentinbox.scanner --self-test
python -m pytest tests/security -q
```

A red pack, a scanner finding, or a red invariant test blocks the build. The local Makefile exposes
`make packs`, `make scan`, and `make sbom` for the same checks.

## 8. Non-goals

- No claim that pattern scanning finds every possible secret; no external scanning service.
- No timing-attack proof by measurement; uniform behavior and constant-time primitives are the claim.
- No SBOM signing or publication here (M25), no domain deployment of `security.txt` (M25).
