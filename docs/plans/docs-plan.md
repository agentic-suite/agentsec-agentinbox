# Docs plan — v0.1.0 (M23)

**BLUF:** every page a stranger needs to install, use, operate, and honestly evaluate v0.1.0, mapped
to the CUJ/PRD that requires it. Docs are tested: the CLI/config coverage test fails on an
undocumented flag or key, and the quickstart's exact commands are replayed by a step test (< 5 min).

- **Milestone:** M23 ([WBS Part 12](../../wbs/v0.1.0/wbs-v0.1.0-part12-security-docs.md), issues #86–#97)
- **Requirements:** CUJ-1/CUJ-14, PRD 22 §H, PRD 21 §C, PRD 23 §A, N-31..N-33

## Page inventory

| Page | CUJ / PRD | Acceptance |
|---|---|---|
| `docs/tutorials/quickstart.md` | CUJ-1, N-31 | step test completes install → first recorded approval in < 5 min |
| `docs/reference/cli.md` | all commands | every command + option documented (coverage test) |
| `docs/reference/config.md` | ops | every config key + effective-config explanation documented (coverage test) |
| `docs/reference/ask-contract.md`, `resolve.md`, `events.md`, `card.md` | producers/channels | versioned contract + field tables |
| `docs/reference/security.md`, `ops.md`, `store.md`, `audit.md`, `gate.md` | M21/M22 | operational + security surfaces |
| `docs/runbooks/rb-1..rb-8.md` | PRD 22 §H | symptoms → steps → verification, matching M20/M21 behavior |
| `docs/adapters/harness-recipes.md`, `ci-recipes.md`, `mcp.md`, `temporal.md` | PRD 19 | each recipe ends in `agentinbox conformance` |
| `docs/guides/approver-guide.md` | CUJ-2 | cards, inbox, confirmations, deny reasons |
| `docs/adapters/producer-guide.md` | CUJ-1/13 | create → answer → resolve (already shipped, polished) |
| `docs/guides/enterprise-honesty.md` | CUJ-14, PRD 23 §A | gap matrix before features; no over-claim |
| `docs/reference/screenshots/` | usability | text captures of card, inbox, doctor, export |
| `README.md` | everyone | install/usage live; status reflects the built core |

## Step-test protocol

1. Fresh `AGENTINBOX_HOME` under a temp directory; `init` exactly as the quickstart says.
2. Terminal 1 runs the documented `ask --exec` line (blocks at the gate).
3. Terminal 2 runs the documented `inbox` + `answer` lines through a pseudo-terminal, typing `a`
   and the typed confirmation.
4. Assert: the ask process exits `0`, the record is `approved`, the audited transition exists, and
   the whole run is under 300 seconds. The test is `tests/docs/test_quickstart.py`.

## Screenshot list

| Capture | Source |
|---|---|
| terminal card | `agentinbox answer <id>` card render |
| inbox list | `agentinbox inbox` |
| doctor | `agentinbox doctor` |
| export sample | `agentinbox export --ask <id>` (JSONL, truncated) |

Terminal captures are committed as text so they cannot drift from the real renderer; the layout is
ASCII (N-40), so no image is needed.

## Honesty rules

- No page claims a capability the code does not have; unsupported rows say so.
- Field-tested labels only come from M24's journal (none yet); M23 pages use
  conformance/documented labels.
- A page that cannot be tested is listed as a limitation, not marked done.
