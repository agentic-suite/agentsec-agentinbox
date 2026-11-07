# AGENTS.md — agentinbox

These rules apply to every agent/assistant session in this repository.
They are gates, not preferences.

## Field-test reports are hand-maintained — automation must never write them

- `docs/field-test/<version>/FIELD_TEST_REPORT.md` is a **hand-maintained journal**.
  Edit it by hand only.
- **No script, generator, CLI, agent, task, or automation may write, rewrite,
  regenerate, move, truncate, or delete the canonical report.** There is no
  "force" exception. This rule exists because a lossy automated rewrite has
  destroyed hand-written field notes before.
- Automated drafts, if ever added, must write a **separate**
  `FIELD_TEST_REPORT.generated.md` sibling and must refuse to overwrite any file
  carrying the `HAND-MAINTAINED` marker.
- Verdicts are entered **by hand** from the committed evidence under
  `field-test/<version>/results/`. Never infer, auto-fill, or "clean up" a
  verdict, a miss, a limitation, or a note.
- A report-guard test must assert the marker and the refusal behavior. If a
  report writer is added, the guard ships in the same change.
- Field-test **results** live under `field-test/<version>/results/`, not under
  `docs/`. `docs/field-test/<version>/` holds only the plan and the
  hand-maintained report.
- Breaching this rule is a release-blocking violation. Fix forward by hand;
  never regenerate the report from results.

Precedent: `agentpolicy` guards this with a `HAND-MAINTAINED` marker,
`build_report.py` refusing the canonical file, and
`tests/test_field_report_guard.py` locking the behavior in. Mirror that posture.

## Working rules

- Read the owning PRD/WBS and design doc before implementing a ticket.
- Route state through the `AskStore` contract; every externally visible change
  is an append-only transition plus its event. Never write the store directly
  from a channel, adapter, or producer.
- Keep the decision rule intact: the inbox records and returns outcomes; the
  enforcer enforces them. Readiness scores, suggestions, grants, and insights
  are advisory or bounded — they never authorize an action.
- Additive contracts only: extend `ask/1.0` and `resolve/1.0`; never renumber.
- Tests first (RED → GREEN), then the milestone gate once at the end.
- Do not close an issue when the intent is to move/re-point it.
- Blocked work is marked BLOCKED with the reason; never reported as done.
