# Harness LLM captures — v0.1.0

This directory preserves the **11 LLM request/response pairs** captured during the
M32 Tier-1 harness attempt (Claude Code 6, Codex CLI 5). They are evidence that
the harnesses reached the box-local OMLX model and returned 2xx, secret-free
responses.

**They are not a field-test verdict.** The end-to-end s15-harness cases failed on
a pty answerer defect and the suite was removed from the M32 registry with the
rationale in `docs/field-test/v0.1.0/FIELD_TEST_PLAN.md` §6 ("Suite removals").
Consequently the v0.1.0 compatibility matrix labels Claude Code and Codex CLI
**documented / capture-verified**, not `field-tested`.

## Provenance and redaction

- Source commit: `6dab44d^` (the commit before the s15 results tree was removed).
- Only the `artifacts/llm/` files were restored; the rest of the s15 tree stays
  out of the registry.
- The captures are byte-identical except one vendor no-reply email address,
  which was replaced with `[REDACTED:EMAIL]` so the release evidence scanner
  reports zero findings. No secret was present.
- Re-scan with: `python -m agentinbox.scanner --path docs/release/v0.1.0/evidence/harness`
