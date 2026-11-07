#!/usr/bin/env bash
# Hand-written Tier-1 harness step (not generated): real Codex CLI.
if command -v codex >/dev/null 2>&1 && command -v "$FT_CLI" >/dev/null 2>&1; then
  ft_assert "t1-codex-triple" bash "$FT_DIR/t1_codex.sh" "$FT_CASE_DIR"
  ft_assert "t1-codex-allow-executed" bash -c 'grep -q "hello-ft" "$FT_CASE_DIR/artifacts/codex-call1.txt" && echo EXECUTED'
  ft_assert "t1-codex-deny-held" bash -c 'test -f "$FT_CASE_DIR/codex-home/work/target-dir/keep.txt" && echo HELD'
  ft_assert_llm_capture "t1-codex-captured"
  ft_assert "t1-codex-audit" bash -c 'test -s "$FT_CASE_DIR/artifacts/audit.jsonl" && echo AUDIT-OK'
else
  ft_block "Codex CLI or the agentinbox CLI is absent on this host; the recipe can only run on the field box" "PRD 21 Method D / M32 32.8 (#402)"
fi
ft_finalize
