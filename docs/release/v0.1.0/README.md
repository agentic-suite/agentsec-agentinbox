# agentinbox v0.1.0 — Release Documentation

This is the entry point for the v0.1.0 release packet. It links the plan, the
honest compatibility matrix, the field evidence, and the operational runbooks.

> **Release status:** M33 is in progress. The `v0.1.0` tag is **not** cut until
> every release gate in the plan is green. The field-test record is complete
> with known issues; see the report.

## Release artifacts

| Artifact | Location | Status |
|---|---|---|
| Release plan (claims, gates, tag/rollback) | [RELEASE_PLAN.md](RELEASE_PLAN.md) | published |
| Compatibility matrix (generated, honest labels) | [COMPATIBILITY.md](COMPATIBILITY.md) | published |
| Field-test report (hand-maintained) | [FIELD_TEST_REPORT.md](../field-test/v0.1.0/FIELD_TEST_REPORT.md) | published |
| Field-test results (53 units) | [`field-test/v0.1.0/results/`](../../../field-test/v0.1.0/results/) | committed |
| Harness LLM captures (11 pairs) | [evidence/harness/](evidence/harness/README.md) | committed; not field-tested |
| Expansion runbooks | [RUNBOOKS.md](RUNBOOKS.md) | published |
| Security audit + risk re-grade | [SECURITY_AUDIT.md](SECURITY_AUDIT.md) | published |
| Release notes + gap list | `RELEASE_NOTES.md` | pending M33 #114 |
| Wave-0 demo evidence | [demo/](demo/transcript.txt) | published |
| SBOM, signatures, provenance, Scorecard | release artifacts | pending M33 #395 |

## Start here

- **First approval:** [docs/tutorials/quickstart.md](../../tutorials/quickstart.md)
  — install → init → ask → answer → verify.
- **Everyday operations:** [runbooks](../../runbooks/) for channel outage,
  secret rotation, corruption, flood, config drift, clock incident, escalation
  misfire, and upgrade day.
- **Expansion surfaces:** [RUNBOOKS.md](RUNBOOKS.md) for readiness, constrained
  allows, bundles/handoff, outcomes, grants, and insights.
- **What is claimed:** [claims and limitations](../../compliance/claims-and-limitations.md)
  and the compatibility matrix. A row is only `field-tested` with a run journal.

## Release gates

The tag is blocked until:

1. claims lint and the release evidence scan are green;
2. the compatibility matrix is current and fully labelled;
3. docs/quickstart/runbooks are linked and linted;
4. the Wave-0 demo and security audit are published;
5. release notes + gap list are published;
6. SBOM, signatures, provenance, and Scorecard verify;
7. 33.T/C/L/CR/D gates are green on the release candidate;
8. a fresh `pip install` reproduces the quickstart after publish.

See [RELEASE_PLAN.md](RELEASE_PLAN.md) for the exact order, artifact set, and
rollback rules.
