#!/usr/bin/env bash
# Hand-written Tier-1 harness step (not generated): real Claude Code.
if command -v claude >/dev/null 2>&1 && command -v "$FT_CLI" >/dev/null 2>&1 && ft_llm_up; then
  ft_assert "t1-claude-triple" bash "$FT_DIR/t1_claude.sh" "$FT_CASE_DIR"
  ft_assert "t1-claude-allow-executed" bash -c 'test -s "$FT_CASE_DIR/artifacts/claude-call1.txt" && echo EXECUTED'
  ft_assert "t1-claude-deny-held" bash -c 'test ! -e "$FT_CASE_DIR/harness/work/ft-t1-side-effect.txt" && echo BLOCKED'
  ft_assert_llm_capture "t1-claude-captured"
  ft_assert "t1-claude-audit" bash -c 'test -s "$FT_CASE_DIR/artifacts/audit.jsonl" && echo AUDIT-OK'
else
  ft_block "Claude Code CLI, agentinbox CLI, or the local OMLX endpoint (${FT_LLM_HOST_URL}, ${FT_LLM_MODEL}) is absent; the recipe runs on the field box" "PRD 21 Method D / M32 32.8 (#402)"
fi
ft_finalize
