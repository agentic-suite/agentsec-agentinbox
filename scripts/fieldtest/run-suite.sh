#!/usr/bin/env bash
# Run one field-test suite: every case whose registry `suite` matches.
# Usage:
#   run-suite.sh SUITE              # e.g. s8-readiness
#   run-suite.sh SUITE FT-SC-68     # only these cases within the suite
#
# Results land under field-test/<FT_VERSION>/results/<SUITE>/.
# There is no skip: a case that cannot run is a failure (or BLOCKED for a
# P/F|B case whose environment is genuinely unavailable).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="${1:-}"
shift || true
if [[ -z "$SUITE" ]]; then
  {
    echo "usage: run-suite.sh SUITE [CASE...]"
    echo "suites: s0-core s1-cross-channel s2-escalation s3-flood s4-ci"
    echo "        s5-evidence s6-attacks s7-governance s8-readiness"
    echo "        s9-constrained s10-operations s11-outcomes s12-grants"
    echo "        s13-insights s14-study s15-harness s16-live"
  } >&2
  exit 2
fi

export FT_VERSION="${FT_VERSION:-v0.1.0}"
export FT_RUN_ID="$SUITE"
export FT_SHARED_STACK=1
# shellcheck source=lib.sh
source "$HERE/lib.sh"

ids=("$@")
if [[ ${#ids[@]} -eq 0 ]]; then
  while IFS= read -r id; do
    [[ -n "$id" ]] && ids+=("$id")
  done < <("$FT_PY" - "$HERE/cases/registry.json" "$SUITE" <<'PY'
import json, sys
try:
    registry = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    registry = []
for case in registry:
    if case.get("suite") == sys.argv[2]:
        print(case["id"])
PY
)
fi

if [[ ${#ids[@]} -eq 0 ]]; then
  echo "run-suite: no cases found for suite '$SUITE'" >&2
  exit 2
fi

# Bring the SUT up once for this suite. Cases with no Docker environment
# requirement (study/harness) are skipped at this step and BLOCKED instead.
echo "==> suite $SUITE: ${#ids[@]} case(s) -> $FT_RUN_DIR"
if ft_require_docker && stack_up && ft_wait_ready; then
  export FT_STACK_READY=1
  echo "==> SUT READY (built once per run; suites after the first boot with --no-build)"
else
  echo "!! SUT failed to start" >&2
fi
# One teardown per suite run, honoring STACK_KEEP (lib.sh defers it).
trap 'stack_teardown' EXIT

rc=0
for id in "${ids[@]}"; do
  echo
  echo "################ $id ################"
  if ! bash "$HERE/run-case.sh" "$id"; then
    rc=1
  fi
done

echo
echo "==> Aggregating results into $FT_RUN_DIR"
"$FT_PY" "$HERE/collect-results.py" "$FT_RUN_DIR" --expect "${ids[@]}" --allow-blocked || true

echo
echo "==> deep verification (grounding re-derivation + leak scan)"
if ! "$FT_PY" "$HERE/check_grounding.py" "$RESULTS_ROOT" > "$FT_RUN_DIR/.grounding.log" 2>&1; then
  tail -6 "$FT_RUN_DIR/.grounding.log"
  echo "!! deep-verification FAILED (a PASS is not grounded)" >&2
  rc=1
else
  tail -2 "$FT_RUN_DIR/.grounding.log"
fi
if ! "$FT_PY" "$HERE/scan_results.py" "$RESULTS_ROOT" --quiet; then
  echo "!! leak scan FAILED (unmasked secret in results)" >&2
  rc=1
else
  echo "leak scan: clean"
fi
exit "$rc"
