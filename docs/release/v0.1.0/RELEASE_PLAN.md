# agentinbox v0.1.0 — Release Plan

> **M33 33.D0 — reviewed before release work.** This is the design for *how*
> v0.1.0 is shipped: the claims we are allowed to make, the compatibility
> labels, the artifact set, the evidence, the gates, and the exact tag/release
> steps. Later M33 items implement this plan; nothing ships that is not named
> here.
>
> Owning milestone: **M33 Release readiness** · WBS
> `docs/wbs/v0.1.0/wbs-v0.1.0-part17-expansion-fieldtest-release.md` `33.D0`
> (issue #391). Package: **`agentsec-agentinbox`** · Version: **`0.1.0`** ·
> Tag: **`v0.1.0`**.

---

## 1. Release scope and starting point

v0.1.0 is a **local-first, single-principal human decision gate** for
consequential agent actions. It ingests an ask, renders one decision card,
accepts one authenticated answer bound to the exact action identity, and
expires or denies by default. The decision path is deterministic; there is no
ML decision and no hosted dependency.

The release starts from the closed **M32 field-test** record, not from a clean
assumption:

- The M32 report is `docs/field-test/v0.1.0/FIELD_TEST_REPORT.md`.
- Verdicts on disk are **47 PASS / 6 FAIL** over the 53-unit registry:
  **4 KNOWN container test-setup/env failures** and **2 study cases failed by
  design**.
- One product defect was found by the field test — the locked-store
  self-heal (Defect #5) — and is **fixed, regression-locked, and field-verified**.
- The **study was not run** (no human cohort; the 15-second claim is not
  proven).
- The **harness suite was removed from the sweep**; Claude Code and Codex CLI
  were **not field-tested**. Their 11/11 captured LLM request/response pairs
  (2xx, secret-free) are retained as evidence, but they do not satisfy the
  field-test journal bar.
- The four container-only failures are accepted as **KNOWN test-setup/env
  issues**, not product failures; the product assertions in those cases passed,
  and the same surface is green locally and in the LIVE cases.

This plan records those caveats as release facts. It does not turn them into
PASS claims.

## 2. Versioning policy

- **Scheme:** semantic versioning (`MAJOR.MINOR.PATCH`). The package is
  `agentsec-agentinbox==0.1.0`; the git tag is `v0.1.0` (annotated, with a
  release message).
- **Normative source:** `agentinbox/__init__.py` `__version__` is the single
  version source; `pyproject.toml` reads it through Hatch. The release commit
  bumps `0.1.0.dev0` to `0.1.0`; the tag MUST equal `v<version>`, and release
  tooling fails if they disagree.
- **Pre-1.0 stability:** while `MAJOR == 0`, a `MINOR` bump MAY carry breaking
  changes; a `PATCH` bump MUST be backward-compatible. Every breaking change is
  named in the release notes.
- **Compatibility matrix:** the shipped surface matrix is published with the
  notes and generated from evidence (PRD 19 / PRD 21 Method D). A row is only
  `field-tested` when a run journal cites the harness version, date, and
  transcript. v0.1.0 lists exactly what M32 proved and names what it did not.
- **Deprecation:** a deprecated surface is announced one `MINOR` before removal
  and recorded in the release notes; nothing is removed silently in a `PATCH`.

## 3. Claim set and compatibility labels

The release uses only the four PRD 19 labels:

| Label | Required evidence |
|---|---|
| **field-tested** | A run journal with harness/tool version, date, OS/user, transcript, gate outcome, and a verdict in the field-test report |
| **conformance-tested** | A green CI fixture/conformance suite naming the tested surface |
| **documented** | A recipe or reference exists, but no live field run |
| **not-supported** | A stated reason, never an implied absence |

The PRD 20 §G vocabulary is enforced by the claims lint. In particular:

- “Prevents prompt injection”, “enterprise-ready”, and unproven performance
  numbers are **forbidden**.
- “Unforgeable approvals” is **restricted** to the tested spoof/replay/forward
  claim (SC-22), never platform-unbreakability.
- “Works with Claude Code / Codex” is allowed only with its true label; at
  v0.1.0 the label is **documented / capture-verified**, **not** `field-tested`.
- The study bar is **not claimed**; the report states the miss.

The matrix rows are written to pass the claims lint and are reviewed with the
security audit before the notes are published. No row may carry ✅ without a
citation.

## 4. Artifact set

Every release produces, from the release commit, an immutable, verifiable set:

| Artifact | Produced by | What it proves |
|---|---|---|
| **wheel** (`*.whl`) + **sdist** (`*.tar.gz`) | `python -m build` / release dry run | the installable distribution |
| **CycloneDX SBOM** (`sbom.cdx.json`) | release tooling (`agentinbox.posture sbom`) | the dependency inventory (runtime deps must stay empty) |
| **`SHA256SUMS`** | release tooling | a checksum for every shipped artifact |
| **SLSA provenance** (`provenance.intoto.jsonl`) | CI/release workflow | how/where the artifact was built |
| **Sigstore signatures** | `cosign`/Sigstore | artifact authenticity |
| **OpenSSF Scorecard result** | `.github/workflows/scorecard.yml` + recorded grade | supply-chain posture |
| **Release notes + gap list** (`RELEASE_NOTES.md`) | M33 #114 | what shipped, what did not, benches, verdict summary |
| **Compatibility matrix** (`COMPATIBILITY.md`) | M33 #392 | honest labels and citations |
| **Security audit** (`SECURITY_AUDIT.md`) | M33 #117 | PRD 06 invariants + PRD 08 risk re-grade |
| **Demo evidence** (`demo/`) | M33 #116 | agentpolicy → ask → deny → events → export/verify |

No artifact is hand-edited after it is hashed. A failed artifact build or a
hash mismatch blocks the tag.

## 5. Evidence

The release cites, and does not restate, the evidence produced by prior
milestones:

- **Field-test report** — `docs/field-test/v0.1.0/FIELD_TEST_REPORT.md`
  (47/6; the four env reds and two by-design study reds are explicit).
- **Field-test results** — `field-test/v0.1.0/results/` (53 units; per-case
  verdicts/artifacts).
- **M32 code-review close-out** — `docs/wbs/v0.1.0/codereview-log.md`
  (Defect #5 fix and the gate fail-closed close fix).
- **Contract conformance** — `tests/fixtures/conformance/` + `agentinbox conformance`.
- **Attack/flood packs** — `tests/security/test_packs.py`, `make packs`.
- **Evidence scanner** — `agentinbox.scanner`, `make scan`, plus the M33
  evidence-scanner gate (#393).
- **Benchmarks** — M21 bench outputs cited in the release notes.
- **Gates on the release commit** — 33.T tests · 33.C coverage ≥ 95% · 33.L
  `ruff` zero + `mypy --strict` clean · 33.CR review log clean · 33.D docs.

**EV register:** the release notes map each claimed capability to its PRD 21
evidence ID (EV-1..EV-14). An unmapped claim is a release defect. EV-10
(study) and EV-11 (live harness) are explicitly **not met**; they are recorded
as gaps, not silently dropped.

## 6. Security and privacy

- **Zero unresolved findings** is a release condition. A finding is either
  fixed or explicitly waived with a written reason in the security audit; it
  is never silently dropped.
- **No secrets** in any artifact, log, SBOM, evidence packet, or transcript.
  The evidence scanner must report zero; a seeded leak must fail the gate.
- **Signed/verifiable artifacts:** every artifact has a `SHA256SUMS` entry,
  SLSA provenance, and a Sigstore signature; consumers verify before install.
- **Local-first:** no telemetry, no hosted service, and no network dependency
  in the approval path. The demo may use only local adapters.
- **Audit honesty:** the hash chain is tamper-evident and locally verifiable;
  it is not externally notarized or WORM. The audit states this limitation.
- **No release artifact rewrites:** a bad release is superseded forward, never
  silently replaced under the same version.

## 7. Release gates and sequence

The work is ordered by dependency; the WBS numbers are labels, not a mandate
to write docs before their enforcement exists.

1. **Release plan (#391).** This document, reviewed before release work.
2. **Claims lint + evidence scanner (#393).** Build the enforcement first:
   PRD 20 §G vocabulary, evidence references, and a seeded over-claim/leak
   fixture must fail. Green before public docs are finalized.
3. **Compatibility matrix (#392).** Write the matrix to pass the lint; every
   row labelled and cited; harness rows downgraded honestly.
4. **Docs, quickstart, runbooks (#394).** Public docs and runbooks for the
   expansion surfaces, linked from README/WBS; claims lint green.
5. **Wave-0 demo (#116).** Local agentpolicy rule → ask → terminal/desktop
   alert → deny(reason) → agentwatch events → `export --session` + `verify-log`.
   Evidence recorded under `docs/release/v0.1.0/demo/`.
6. **Security audit + risk re-grade (#117).** PRD 06 invariants against the
   M22 fixtures and M32 evidence; PRD 08 risks re-graded with observed
   tripwires; every M32 finding dispositioned.
7. **Release notes + gap list (#114).** R1–R7/E1–E12, benches, PRD 23 gaps,
   the 47/6 verdict summary, and links to the matrix/demo/audit.
8. **SBOM, signing, Scorecard (#395, artifacts phase).** Build and verify the
   SBOM, signatures, provenance, and Scorecard result; no tag yet.
9. **Milestone gates (#396–#400).** Tests, coverage, lint/type, code review,
   and docs on the release candidate. Green, once, at milestone end.
10. **Tag, GitHub release, PyPI (#395, release phase).** Only after every gate
    above is green and the release notes/matrix/audit are published.
11. **Published-artifact smoke (#396, post-release).** Fresh box:
    `pip install agentsec-agentinbox` → quickstart → demo → export/verify.
    A failure yanks the release and starts a patch; it does not rewrite the tag.

**Tag precondition:** claims lint green, evidence scanner zero, matrix fully
labelled, demo green, security audit published, all gates green, and a clean
`git status` on the release commit.

## 8. Tag and release steps

Run from the release commit on the release branch, after every gate is green:

1. **Freeze** — bump `agentinbox/__init__.py` to `0.1.0`; confirm the
   field-test report, compatibility matrix, security audit, demo evidence, and
   release notes are current and committed.
2. **Dry run** — build wheel + sdist, CycloneDX **SBOM**, **`SHA256SUMS`**,
   **SLSA** provenance, and **Sigstore** signatures; verify independently.
3. **Tag** — annotated tag **`v0.1.0`** on the release commit; the message
   summarizes the release and links the notes.
4. **GitHub Release** — attach wheel, sdist, SBOM, `SHA256SUMS`, provenance,
   signatures, and the Scorecard result; body links the release notes.
5. **Publish** — upload to PyPI as **`agentsec-agentinbox==0.1.0`**; install in
   a clean venv and run a first approval.
6. **Verify** — downloaded artifact hashes MUST match `SHA256SUMS`; the PyPI
   install MUST reproduce the quickstart on a fresh box.
7. **Record** — update the WBS index/checkpoint and close the M33 tracking
   issues with links to the evidence.

## 9. Rollback

- **Before the tag:** fix forward and re-run the affected gate; no tag exists,
  so there is nothing to withdraw.
- **After the tag, bad artifact:** do **not** force-push or move the tag. Yank
  the PyPI release, mark the GitHub release withdrawn with a reason, publish a
  patch version, and keep the original evidence for the audit trail.
- **After publish, product defect:** follow the security/disclosure process;
  publish a patch and a CVE/security note if the defect is security-relevant.
  Never delete release artifacts or rewrite history to hide a failure.

## 10. Out of scope

- New product features or changes to the decision engine (M0–M31 are frozen for
  this release).
- Re-running the field test or adding new scenarios; M32 is closed, and its
  report is the evidence.
- A human study (no cohort; recorded as a gap).
- Server mode, SSO, multi-tenancy, quorum, mobile push, chat adapters, and
  other PRD 23 Stage 2/3 items.
- Third-party audit, SOC 2/ISO certification, or external notarization.
- Deleting or rewriting predecessor history.

## 11. Known issues and release decisions

| Issue | Disposition | Release statement |
|---|---|---|
| 4 container-only toolchain reds (FT-SC-20, 21, 24, 26) | **Accepted as KNOWN test-setup/env** | Product assertions passed; same surface green locally and in LIVE cases; not a product-failure claim |
| 2 study cases (FT-SC-03, 04) | **FAIL by design** | No human cohort; the 15-second/study bar is **not claimed** |
| Harness suite removed (s15-harness) | **Removed with rationale** | Claude Code/Codex are **not field-tested**; 11/11 LLM pairs retained; matrix label is documented/capture-verified |
| Defect #5 locked-store self-heal | **Fixed + regression + field-verified** | Included in the release; evidence in the M32 report and code-review log |
| M32 report 47 PASS / 6 FAIL | **Published honestly** | M33 consumes it; no silent reclassification |

These decisions are part of the release record. If any reviewer cannot accept
one, the release is blocked until it is resolved or explicitly waived here.

## 12. Definition of done

This plan is reviewed before release code. The implementation items then
produce exactly the evidence above:

- claims lint + evidence scanner green and seeded failures caught (#393);
- compatibility matrix fully labelled/cited (#392);
- docs/quickstart/runbooks linked and linted (#394);
- Wave-0 demo green with recorded evidence (#116);
- security audit + risk re-grade published (#117);
- release notes + gap list published (#114);
- SBOM, signatures, provenance, and Scorecard verified (#395);
- 33.T/C/L/CR/D gates green (#396–#400);
- `v0.1.0` tagged and PyPI install verified only after all of the above.

The plan is linked from the WBS and the release-notes index. A change to the
claimed scope or the tag conditions requires a reviewed edit to this document
before the release proceeds.
