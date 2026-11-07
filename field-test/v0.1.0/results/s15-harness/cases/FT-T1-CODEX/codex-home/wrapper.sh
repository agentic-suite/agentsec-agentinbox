#!/usr/bin/env bash
set -u
"/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/.venv/bin/agentinbox" --home "/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/field-test/v0.1.0/results/s15-harness/cases/FT-T1-CODEX/codex-home/home" ask --exec "$*" --session-id ft-t1-codex
rc=$?
[[ $rc -eq 0 ]] || { echo "blocked by agentinbox" >&2; exit 1; }
exit 0
