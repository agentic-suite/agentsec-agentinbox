#!/usr/bin/env bash
# Run one field-test case. Usage:
#   run-case.sh CASE-ID [--keep]
#
# Sources cases/steps/<CASE-ID>.sh, which runs its assertions and calls ft_finalize.
# There is no skip: a case that does not pass is a failure (or BLOCKED for a
# P/F|B case whose environment genuinely cannot be provided).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ID="${1:-}"
KEEP="${2:-}"
if [[ -z "$ID" ]]; then
  echo "usage: run-case.sh CASE-ID [--keep]" >&2
  exit 2
fi

REGISTRY="$HERE/cases/registry.json"
if [[ -x "$HERE/../../.venv/bin/python" ]]; then
  REG_PY="$HERE/../../.venv/bin/python"
else
  REG_PY="python3"
fi
_reg() {
  "$REG_PY" - "$REGISTRY" "$ID" "$1" <<'REG'
import json, sys
try:
    registry = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    registry = []
match = next((c for c in registry if c.get("id") == sys.argv[2]), {})
print(match.get(sys.argv[3], ""))
REG
}

if [[ -z "${FT_RUN_ID:-}" ]]; then
  export FT_RUN_ID="$(_reg suite)"
  [[ -n "$FT_RUN_ID" ]] || export FT_RUN_ID="standalone"
fi

# shellcheck source=lib.sh
source "$HERE/lib.sh"
if [[ "$KEEP" == "--keep" ]]; then export STACK_KEEP=1; fi

STEP="$HERE/cases/steps/$ID.sh"
if [[ ! -f "$STEP" ]]; then
  echo "unknown case $ID (no steps at $STEP)" >&2
  exit 2
fi

REQUIRES="$(_reg requires)"
CLASS="$(_reg class)"
export FT_CASE_CLASS="${CLASS:-P/F}"
export FT_CASE_ID="$ID"
export FT_CASE_REQUIRES="$REQUIRES"

trap ft_teardown_on_exit EXIT
ft_case_begin "$ID"

if [[ "$REQUIRES" == "study" || "$REQUIRES" == "host-harness" ]]; then
  # No Docker needed: the environment is the missing thing.
  set +e
  # shellcheck source=/dev/null
  source "$STEP"
  step_rc=$?
  set -e
  [[ "$step_rc" -ne 0 ]] && FT_ASSERT_FAILED=1
  ft_finalize
  ft_case_end "$ID" "$FT_CASE_STATUS"
  [[ "$FT_CASE_STATUS" == "pass" || "$FT_CASE_STATUS" == "blocked" ]] || exit 1
  exit 0
fi

if [[ "${FT_STACK_READY:-0}" != "1" ]]; then
  if ! ft_up_sut; then
    ft_finalize
    ft_case_end "$ID" "fail"
    exit 1
  fi
fi

set +e
# shellcheck source=/dev/null
source "$STEP"
step_rc=$?
set -e
if [[ "$step_rc" -ne 0 ]]; then FT_ASSERT_FAILED=1; fi
ft_finalize
ft_case_end "$ID" "$FT_CASE_STATUS"

[[ "$FT_CASE_STATUS" == "pass" || "$FT_CASE_STATUS" == "blocked" ]] || exit 1
