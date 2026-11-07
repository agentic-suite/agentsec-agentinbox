#!/usr/bin/env bash
# FT-T1 answerer: poll the inbox and answer each pending ask per a
# PRE-REGISTERED answer plan, in creation order. This is the "second terminal"
# the Tier-1 recipes document — automated, honestly recorded as automation.
#
# The product contract is untouched: each answer runs through a real terminal
# session (t1_answer.sh drives the CLI under a pty), so approvals still require
# the interactive path with typed confirmation. No non-interactive approve
# exists, by design.
#
# Usage: t1_answerer.sh HOME "PLAN" [TIMEOUT_SECONDS]
#   PLAN: space-separated actions in order, e.g. "approve deny deny"
#         each entry may be "approve:<confirm>" or "deny:<reason>"
#   The answerer exits when the plan is exhausted or the timeout passes.
set -euo pipefail

HOME_DIR="${1:?home}"
PLAN="${2:?answer plan}"
TIMEOUT="${3:-900}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"

read -r -a ACTIONS <<<"$PLAN"
idx=0
deadline=$((SECONDS + TIMEOUT))

while (( idx < ${#ACTIONS[@]} )) && (( SECONDS < deadline )); do
  # Pending asks in creation order (inbox --json lists pending).
  # bash 3.2 on macOS has no `mapfile`/`readarray` — read line by line.
  pending=()
  while IFS= read -r ask_id; do
    [[ -n "$ask_id" ]] && pending+=("$ask_id")
  done < <("$FT_PY" - "$FT_CLI" --home "$HOME_DIR" <<'PY'
import json, subprocess, sys
proc = subprocess.run(
    [sys.argv[1], "--home", sys.argv[2], "inbox", "--json"],
    capture_output=True, text=True,
)
try:
    rows = json.loads(proc.stdout)
except ValueError:
    rows = []
for row in rows:
    print(row["ask_id"])
PY
)
  if [[ "${#pending[@]}" -eq 0 ]]; then
    sleep 1
    continue
  fi
  entry="${ACTIONS[idx]}"
  action="${entry%%:*}"
  extra="${entry#*:}"
  [[ "$extra" == "$entry" ]] && extra=""
  confirm=""
  reason=""
  case "$action" in
    approve) confirm="$extra" ;;
    deny)    reason="$extra" ;;
  esac
  ask_id="${pending[0]}"
  echo "answerer: $action $ask_id" >&2
  if bash "$HERE/t1_answer.sh" "$HOME_DIR" "$ask_id" "$action" "$confirm" "$reason" \
      >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log"; then
    idx=$((idx + 1))
  else
    echo "answerer: answer $ask_id ($action) failed; retrying plan entry" >&2
    sleep 1
  fi
done

if (( idx < ${#ACTIONS[@]} )); then
  echo "answerer: plan unfinished (${idx}/${#ACTIONS[@]}) after ${TIMEOUT}s" >&2
  exit 1
fi
echo "answerer: plan complete (${idx}/${#ACTIONS[@]})"