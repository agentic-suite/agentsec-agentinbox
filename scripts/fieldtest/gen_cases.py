#!/usr/bin/env python3
"""Generate field-test case step scripts + the suite registry for agentinbox.

The registry (`cases/registry.json`) is the single source of truth: case id,
suite, class, environment requirement, and the pytest target(s) that back the
case's assertions. This generator writes one `cases/steps/<ID>.sh` per case.

Run after editing the registry:
    python3 scripts/fieldtest/gen_cases.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"
STEPS = CASES / "steps"

REGISTRY: list[dict[str, object]] = [
    # --- S0 core lifecycle (SC-01..06, 09, 10, 17, 19) ------------------------
    {"id": "FT-SC-01", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/cli/test_cuj1.py"],
     "note": "first ask, terminal, zero config"},
    {"id": "FT-SC-02", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/ask/test_validation.py", "tests/ask/test_contract.py"],
     "note": "malformed ask rejected loudly; nothing partial persists"},
    {"id": "FT-SC-05", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/config/test_hints.py", "tests/lifecycle/test_resolve.py"],
     "note": "rescope hint -> new identity, no state reuse"},
    {"id": "FT-SC-06", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/ask/test_api.py"],
     "note": "duplicate ingest coalesces"},
    {"id": "FT-SC-09", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/scheduler/test_expiry.py", "tests/lifecycle/test_resolve.py"],
     "note": "timeout = deny + warning"},
    {"id": "FT-SC-10", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/scheduler/test_recovery.py", "tests/scheduler/test_clock.py"],
     "note": "expiry survives crash; clock step-back does not extend TTL"},
    {"id": "FT-SC-17", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/answers/test_pipeline.py"],
     "note": "self-review denied (+ allowed variant)"},
    {"id": "FT-SC-19", "suite": "s0-core", "class": "P/F",
     "pytest": ["tests/answers/test_pipeline.py"],
     "note": "late answer is a visible no-op"},

    # --- S1 cross-channel -----------------------------------------------------
    {"id": "FT-SC-07", "suite": "s1-cross-channel", "class": "P/F",
     "pytest": ["tests/channels/test_conformance.py", "tests/parity/test_parity.py"],
     "note": "second-surface approve + terminal parity"},
    {"id": "FT-SC-08", "suite": "s1-cross-channel", "class": "P/F",
     "pytest": ["tests/parity/test_races.py"],
     "note": "race: one decision, second rejected late"},
    {"id": "FT-SC-18", "suite": "s1-cross-channel", "class": "P/F",
     "pytest": ["tests/parity/test_failover.py"],
     "note": "channel failover, no duplicate notify"},

    # --- S2 escalation --------------------------------------------------------
    {"id": "FT-SC-11", "suite": "s2-escalation", "class": "P/F",
     "pytest": ["tests/escalation/test_tiers.py", "tests/escalation/test_revocation.py"],
     "note": "3 a.m. drill, tier claims revoked"},
    {"id": "FT-SC-12", "suite": "s2-escalation", "class": "P/F",
     "pytest": ["tests/escalation/test_no_extension.py"],
     "note": "ladder exhaustion denies; TTL never extended"},

    # --- S3 flood -------------------------------------------------------------
    {"id": "FT-SC-13", "suite": "s3-flood", "class": "P/F",
     "pytest": ["tests/flood/test_buckets.py", "tests/flood/test_deny_digest.py"],
     "note": "attack pack: burst allowed / overflow denied (counts recorded)"},
    {"id": "FT-SC-14", "suite": "s3-flood", "class": "P/F",
     "pytest": ["tests/flood/test_headroom.py"],
     "note": "legitimate burst passes together with SC-13"},

    # --- S4 CI ----------------------------------------------------------------
    {"id": "FT-SC-15", "suite": "s4-ci", "class": "P/F",
     "pytest": ["tests/channels/test_ci.py", "tests/cli/test_gate_cli.py"],
     "note": "pipeline halts on gate, resumes on answer"},
    {"id": "FT-SC-16", "suite": "s4-ci", "class": "P/F",
     "pytest": ["tests/contract/test_exit_codes.py", "tests/cli/test_gate_cli.py"],
     "note": "deterministic exit matrix, idempotent retry"},

    # --- S5 evidence ----------------------------------------------------------
    {"id": "FT-SC-20", "suite": "s5-evidence", "class": "P/F",
     "pytest": ["tests/audit/test_chain.py", "tests/audit/test_export.py",
                "tests/cli/test_audit_cli.py"],
     "note": "reconstruction + chain; tamper names seq"},
    {"id": "FT-SC-21", "suite": "s5-evidence", "class": "P/F",
     "pytest": ["tests/security/test_scanner.py", "tests/security/test_hardening.py"],
     "note": "0 scanner findings; receipts complete"},

    # --- S6 attacks (release-gating) -----------------------------------------
    {"id": "FT-SC-22", "suite": "s6-attacks", "class": "P/F",
     "pytest": ["tests/security/test_packs.py"],
     "note": "RELEASE-GATING: 10 spoof/replay/forge attacks"},
    {"id": "FT-SC-23", "suite": "s6-attacks", "class": "P/F",
     "pytest": ["tests/security/test_packs.py", "tests/security/test_hardening.py"],
     "note": "RELEASE-GATING: 10 poisoned cards, 0 approvals"},
    {"id": "FT-SC-24", "suite": "s6-attacks", "class": "P/F",
     "pytest": ["tests/faults/test_matrix.py"],
     "note": "RELEASE-GATING: fail-closed matrix, 0 silent allows"},

    # --- S7 governance / adapters / offline ----------------------------------
    {"id": "FT-SC-25", "suite": "s7-governance", "class": "P/F",
     "pytest": ["tests/adapters/test_langgraph.py"],
     "note": "LangGraph round-trip + crash-resume, one execution"},
    {"id": "FT-SC-26", "suite": "s7-governance", "class": "P/F",
     "pytest": ["tests/ops/test_offline.py"],
     "note": "offline day, doctor green, no outbound attempts"},

    # --- S8 readiness ---------------------------------------------------------
    {"id": "FT-SC-68", "suite": "s8-readiness", "class": "P/F",
     "pytest": ["tests/readiness/test_rejection.py"],
     "note": "pre-write bounce, nothing stored, repair contract"},
    {"id": "FT-SC-69", "suite": "s8-readiness", "class": "P/F",
     "pytest": ["tests/readiness/test_contradictions.py"],
     "note": "contradiction visible / reject-on-ingest"},
    {"id": "FT-SC-70", "suite": "s8-readiness", "class": "P/F",
     "pytest": ["tests/readiness/test_scorer.py", "tests/readiness/test_class_config.py"],
     "note": "same weak ask, different class bands"},

    # --- S9 constrained allows ------------------------------------------------
    {"id": "FT-SC-71", "suite": "s9-constrained", "class": "P/F",
     "pytest": ["tests/constraints/test_alternatives.py"],
     "note": "one-click constrained allow + constraint set"},
    {"id": "FT-SC-72", "suite": "s9-constrained", "class": "P/F",
     "pytest": ["tests/constraints/test_repair.py", "tests/constraints/test_recall.py"],
     "note": "repair packet round trip, no human re-teach"},
    {"id": "FT-SC-73", "suite": "s9-constrained", "class": "P/F",
     "pytest": ["tests/constraints/test_edits.py"],
     "note": "edit re-fingerprints; enforcer runs the edited form"},
    {"id": "FT-SC-74", "suite": "s9-constrained", "class": "P/F",
     "pytest": ["tests/constraints/test_alternatives.py", "tests/constraints/test_edges.py"],
     "note": "unbindable = advice only, cannot be picked"},

    # --- S10 operations -------------------------------------------------------
    {"id": "FT-SC-75", "suite": "s10-operations", "class": "P/F",
     "pytest": ["tests/bundles/test_operations.py"],
     "note": "20-ask bundle: one screen, 20 answers, no approve-all"},
    {"id": "FT-SC-76", "suite": "s10-operations", "class": "P/F",
     "pytest": ["tests/bundles/test_operations.py"],
     "note": "shift handoff preserves TTL + notes"},
    {"id": "FT-SC-77", "suite": "s10-operations", "class": "P/F",
     "pytest": ["tests/bundles/test_operations.py"],
     "note": "incident mode, denies still deny"},
    {"id": "FT-SC-78", "suite": "s10-operations", "class": "P/F",
     "pytest": ["tests/bundles/test_operations.py"],
     "note": "narrative reproduces a 3 a.m. denial"},

    # --- S11 outcomes ---------------------------------------------------------
    {"id": "FT-SC-79", "suite": "s11-outcomes", "class": "P/F",
     "pytest": ["tests/outcomes/test_outcomes.py"],
     "note": "executed closure + offline-verifiable packet"},
    {"id": "FT-SC-80", "suite": "s11-outcomes", "class": "P/F",
     "pytest": ["tests/outcomes/test_outcomes.py"],
     "note": "exceeded manifest loud, never absorbed"},
    {"id": "FT-SC-81", "suite": "s11-outcomes", "class": "P/F",
     "pytest": ["tests/outcomes/test_outcomes.py"],
     "note": "rollback leaves the decision untouched"},
    {"id": "FT-SC-82", "suite": "s11-outcomes", "class": "P/F",
     "pytest": ["tests/outcomes/test_outcomes.py"],
     "note": "packet-only reviewer reconstructs end-to-end"},

    # --- S12 grants -----------------------------------------------------------
    {"id": "FT-SC-83", "suite": "s12-grants", "class": "P/F",
     "pytest": ["tests/grants/test_grants.py"],
     "note": "12-ask compressed view, 12 answers, export complete"},
    {"id": "FT-SC-84", "suite": "s12-grants", "class": "P/F",
     "pytest": ["tests/grants/test_grants.py"],
     "note": "window expires mid-burst -> per-ask, 0 silent allows"},
    {"id": "FT-SC-85", "suite": "s12-grants", "class": "P/F",
     "pytest": ["tests/grants/test_grants.py"],
     "note": "owner revocation immediate + loud"},
    {"id": "FT-SC-86", "suite": "s12-grants", "class": "P/F",
     "pytest": ["tests/grants/test_grants.py"],
     "note": "repeated denials -> insight, no auto-hardening"},

    # --- S13 insights ---------------------------------------------------------
    {"id": "FT-SC-87", "suite": "s13-insights", "class": "P/F",
     "pytest": ["tests/insights/test_insights.py"],
     "note": "20 approvals -> one redacted insight"},
    {"id": "FT-SC-88", "suite": "s13-insights", "class": "P/F",
     "pytest": ["tests/insights/test_insights.py"],
     "note": "noisy policy -> named tuning diff (PR to apply)"},
    {"id": "FT-SC-89", "suite": "s13-insights", "class": "P/F",
     "pytest": ["tests/insights/test_insights.py"],
     "note": "calibration aggregate; per-principal gated + logged"},
    {"id": "FT-SC-90", "suite": "s13-insights", "class": "P/F",
     "pytest": ["tests/insights/test_insights.py"],
     "note": "divergence -> proposal only, nothing applies itself"},

    # --- S14 study (human; BLOCKED until participants exist) -----------------
    {"id": "FT-SC-03", "suite": "s14-study", "class": "P/F|B",
     "requires": "study",
     "note": "the 15-second spine — 46-card study, plan §9.1"},
    {"id": "FT-SC-04", "suite": "s14-study", "class": "P/F|B",
     "requires": "study",
     "note": "degraded cards -> explicit unknown + deny"},

    # --- S15 harness (BLOCKED until the real CLI is on the box) --------------
    {"id": "FT-T1-CLAUDE", "suite": "s15-harness", "class": "P/F|B",
     "requires": "host-harness",
     "note": "Claude Code PreToolUse live — journal: version, transcript, gate outcome"},
    {"id": "FT-T1-CODEX", "suite": "s15-harness", "class": "P/F|B",
     "requires": "host-harness",
     "note": "Codex CLI wrapper live — deny + expiry behavior recorded"},
]

SUITES = [
    "s0-core",
    "s1-cross-channel",
    "s2-escalation",
    "s3-flood",
    "s4-ci",
    "s5-evidence",
    "s6-attacks",
    "s7-governance",
    "s8-readiness",
    "s9-constrained",
    "s10-operations",
    "s11-outcomes",
    "s12-grants",
    "s13-insights",
    "s14-study",
    "s15-harness",
]


def main() -> None:
    CASES.mkdir(parents=True, exist_ok=True)
    STEPS.mkdir(parents=True, exist_ok=True)
    (CASES / "registry.json").write_text(
        json.dumps(REGISTRY, indent=2) + "\n", encoding="utf-8"
    )
    for case in REGISTRY:
        case_id = str(case["id"])
        path = STEPS / f"{case_id}.sh"
        if path.exists() and not path.read_text(encoding="utf-8").startswith(
            "# generated by gen_cases.py"
        ):
            continue  # never clobber a hand-written step
        requires = str(case.get("requires", ""))
        if requires in {"study", "host-harness"}:
            if requires == "study":
                reason = (
                    "the 15-second study needs >=10 non-author participants; "
                    "none are provisioned on this Docker SUT"
                )
                gate = "PRD 21 Method B / M32 32.5 (#384)"
            else:
                reason = (
                    "the real Claude Code / Codex CLI harness is not installed in the "
                    "Docker SUT; the recipe runs on the field box"
                )
                gate = "PRD 21 Method D / M32 32.8 (#402)"
            body = (
                "# generated by gen_cases.py — BLOCKED environment class\n"
                f'ft_block "{reason}" "{gate}"\n'
            )
        else:
            targets = " ".join(str(item) for item in case.get("pytest", []))
            body = (
                "# generated by gen_cases.py — suite-backed field assertions\n"
                f'ft_sut_pytest "{case_id} assertions" {targets}\n'
            )
        path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
        path.chmod(0o755)


if __name__ == "__main__":
    main()
