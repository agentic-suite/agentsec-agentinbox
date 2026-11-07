# agentinbox v0.1.0 — Release Notes

**Package:** `agentsec-agentinbox` · **Version:** `0.1.0` · **Tag:** `v0.1.0`

agentinbox is a **local-first human decision gate** for consequential agent
actions: it records an ask, renders one decision card, accepts one authenticated
answer bound to the exact action identity, and expires or denies by default.
The decision path is deterministic; there is no ML decision and no hosted
dependency.

> **Release status:** these notes are the v0.1.0 release candidate notes. The
> tag is cut only after every gate in [RELEASE_PLAN.md](RELEASE_PLAN.md) is
> green. The field-test record is complete **with known issues**; see §5.

## 1. What shipped

| Requirement | Delivered |
|---|---|
| **R1** Decision card | Four context blocks, unknown-labelling, untrusted rendering, inert agent text |
| **R2** Any-channel answer, one record | Terminal, desktop wake-up, webhook display, CI gate; one parity record |
| **R3** Timeout = deny | Per-class TTL, warning, rescope, expiry never allows |
| **R4** Escalation ladder | Routing tiers; escalation never extends the TTL |
| **R5** Audit trail | Hash-chained store, agentwatch events, export, offline `verify-log` |
| **R6** CI checkpoints | Reserved exit codes `0/1/2/3/4/5`; retry/offline behavior |
| **R7** Flood throttling | Burst allowance, auto-deny remainder, one event + one digest |
| **E1** Ask contract | `ask/1.0`, idempotent ingest, loopback API and CLI |
| **E2** Durable store | SQLite/memory drivers, crash-safe scheduler, migrations |
| **E3** Unforgeable claims | Single-use 128-bit claim tokens, hashed at rest |
| **E4** Answer authN/authZ | Claim + principal + roster + signed producer support |
| **E5** Injection-inert rendering | Poisoned corpus, untrusted labels, bounded markup stripping |
| **E6** Redaction before persistence | Secret/PII redaction + receipts + evidence scanner |
| **E7** Delivery accounting | Delivery attempts/events; movement is not truth |
| **E8** Time correctness | UTC + monotonic-ish ordering; clock-jump and restart tests |
| **E9** Fail-closed degradation | Bad config/store/sink/channel deny or exit 4, never allow |
| **E10** Versioning + compatibility | Frozen contract/exit/event surface; forward migrations |
| **E11** Pluggable store | Driver conformance gate (race/claim/chain/crash) |
| **E12** Pluggable bus | Filesystem spool + in-proc bus; atomic, idempotent consumers |

Also shipped: constrained allows, readiness/repair packets, operation bundles,
handoff/incident mode, outcome closure/divergence, grants/compression, and
advisory insights. These are **bounded** features: the inbox records and returns
outcomes; the enforcer enforces them.

## 2. Install and first approval

```sh
pip install agentsec-agentinbox==0.1.0
agentinbox init
agentinbox doctor
```

Then follow [docs/tutorials/quickstart.md](../../tutorials/quickstart.md):
`ask` → terminal `inbox`/`answer` → `report`/`verify-log`. The release smoke
also runs `export --session` + `verify-log` on a fresh box.

## 3. Compatibility

The generated matrix is [COMPATIBILITY.md](COMPATIBILITY.md). Only the four
labels are used: **field-tested**, **conformance-tested**, **documented**,
**not-supported**.

- **agentpolicy reference path:** field-tested by the Wave-0 demo.
- **LangGraph / generic CLI/HTTP / core channels:** conformance-tested.
- **Claude Code / Codex CLI:** **documented / capture-verified, not
  field-tested**. The end-to-end s15 suite was removed; 11/11 LLM pairs are
  retained under [evidence/harness/](evidence/harness/README.md).
- **Cursor / Gemini CLI / chat platforms / server-mode surfaces:** not
  supported at v0.1.0, with reasons in the matrix.

## 4. Benchmarks

Measured on the local release box (macOS arm64, Python 3.12.14, 2026-11-07) with
`agentinbox.bench.run_benchmarks(count=50, load_total=10000)`. Raw output:
[bench.json](bench.json).

| NFR | Measurement | Floor | Result |
|---|---|---|---|
| N-1 ingest | p50 0.23 ms / p99 0.43 ms | p50 < 50 ms, p99 < 250 ms | PASS |
| N-2 render | 1.58 ms | < 100 ms | PASS |
| N-4 resolve | p99 0.05 ms | < 100 ms | PASS |
| N-3b external delivery (mocked webhook) | p50 0.01 ms | < 2 s | PASS |
| N-3c spool pickup | 0.55 ms | < 1 s | PASS |
| N-5 scheduler tick | 0.53 ms | < 1 s | PASS |
| N-6 10k resolved load | p50 0.54 ms / p99 1.00 ms | p50 < 50 ms, p99 < 250 ms | PASS |
| N-7 startup | 3.80 ms | < 2 s | PASS |

These are local single-box numbers, not a fleet benchmark. N-3b is a mocked
webhook path, as labelled in the bench.

## 5. Field-test verdict (honest summary)

The M32 sweep is [FIELD_TEST_REPORT.md](../../field-test/v0.1.0/FIELD_TEST_REPORT.md).

- **53 registry units: 47 PASS / 6 FAIL.**
- **4 FAIL are KNOWN container test-setup/env:** `FT-SC-20`, `FT-SC-21`,
  `FT-SC-24`, `FT-SC-26`. Product assertions pass; the tests' own sqlite
  connections are promoted to unraisable warnings by pytest 9.2/Py3.13.
- **2 FAIL are by design:** `FT-SC-03`, `FT-SC-04` — no human cohort will run;
  the study/15-second claim is **not made**.
- **One product defect found and fixed:** Defect #5, the locked-store
  self-heal. It is regression-locked and field-verified (`FT-SC-24-LIVE`).
- **Harness:** the s15 suite was removed; Claude Code/Codex CLI are **not
  field-tested**. The 11 captured LLM pairs are evidence of connectivity, not a
  field verdict.

## 6. Gaps at v0.1.0 (stated before features)

- **No SSO/SCIM/RBAC**, no multi-tenancy, no server mode/HA.
- **No quorum or dual-control approvals** (single approver path).
- **No standing approvals** / long-lived grants; only time-boxed windows.
- **No mobile push and no chat adapters** (Matrix/Slack/Teams are v0.1.x).
- **No external audit notarization/WORM**; the hash chain is local and
  tamper-evident.
- **No third-party security audit, SOC 2, ISO 27001, or ISO 42001**.
- **No human study**: approval-fatigue/15-second claims are unproven.
- **No harness field-test** for Claude Code/Codex CLI.
- **No new absolute performance claims** beyond the local bench above.
- **Known test debt:** four container-only reds and the fixture sqlite cleanup.

## 7. Evidence packet

- [Release plan](RELEASE_PLAN.md) — claims, gates, tag, rollback.
- [Compatibility matrix](COMPATIBILITY.md) — generated, labelled, cited.
- [Security audit](SECURITY_AUDIT.md) — PRD 06 invariants + PRD 08 risks.
- [Wave-0 demo](demo/transcript.txt) — agentpolicy → ask → deny → events →
  export/verify.
- [Harness captures](evidence/harness/README.md) — 11 pairs; not field-tested.
- [Field-test report](../../field-test/v0.1.0/FIELD_TEST_REPORT.md) — 47/6.
- [Claims and limitations](../../compliance/claims-and-limitations.md).

## 8. Verification

```sh
make claims    # PRD 20 §G vocabulary
make evidence  # release/field evidence scan, 0 secrets
make compat    # matrix is generated/current
make gate      # lint + types + tests + coverage + claims/evidence/matrix
```

For a published artifact, verify `SHA256SUMS`, the SLSA provenance, and the
Sigstore signature before install. A failed release is fixed forward or yanked;
a published tag is never rewritten.
