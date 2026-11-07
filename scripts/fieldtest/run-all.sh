#!/usr/bin/env bash
# Run every field-test suite and collect results.
# Results land under field-test/<FT_VERSION>/results/<suite>/.
#
#   run-all.sh              # all suites
#   run-all.sh s8-readiness # just these suites
#
# FT_STRICT_BLOCKED=1 (default) makes a BLOCKED case fail the run: a release
# cannot be tagged while a required field case is blocked.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export FT_VERSION="${FT_VERSION:-v0.1.0}"
export FT_RUN_ID="${FT_RUN_ID:-all}"
export FT_SHARED_STACK=1
# shellcheck source=lib.sh
source "$HERE/lib.sh"

ALL=(s0-core s1-cross-channel s2-escalation s3-flood s4-ci s5-evidence
     s6-attacks s7-governance s8-readiness s9-constrained s10-operations
     s11-outcomes s12-grants s13-insights s14-study s16-live)

suites=("$@")
if [[ ${#suites[@]} -eq 0 ]]; then
  suites=("${ALL[@]}")
fi

echo "==> field-test run: ${#suites[@]} suite(s); STACK_KEEP=${STACK_KEEP:-0}"

# Verify the verifier FIRST: if the grounding gate cannot catch a shallow pass,
# the whole run's green is worthless.
if ! "$FT_PY" "$HERE/verify_harness.py"; then
  echo "!! verify-harness FAILED — the grounding gate is too weak; aborting." >&2
  exit 1
fi

rc=0
for s in "${suites[@]}"; do
  echo
  echo "############## suite $s ##############"
  # Each suite is its own run dir (verdict isolation), but the IMAGE build is
  # shared: run-suite boots with --no-build when FT_STACK_BUILT=1 is exported.
  if ! bash "$HERE/run-suite.sh" "$s"; then
    echo "!! suite $s had failures" >&2
    rc=1
  fi
  # run-suite tears its stack down; keep the built image for the next suite.
  export FT_STACK_BUILT=1
done

echo
echo "==> end-of-run deep verification"
if ! "$FT_PY" "$HERE/check_grounding.py" "$RESULTS_ROOT" --strict > "$RESULTS_ROOT/.grounding.log" 2>&1; then
  tail -8 "$RESULTS_ROOT/.grounding.log"
  echo "!! end-of-run deep-verification FAILED" >&2
  rc=1
else
  tail -2 "$RESULTS_ROOT/.grounding.log"
fi
if ! "$FT_PY" "$HERE/scan_results.py" "$RESULTS_ROOT" --quiet; then
  echo "!! leak scan FAILED" >&2
  rc=1
else
  echo "leak scan: clean"
fi

blocked=$("$FT_PY" - "$RESULTS_ROOT" <<'PY'
import json, sys
from pathlib import Path
count = 0
for path in Path(sys.argv[1]).glob("*/cases/*/verdict.json"):
    try:
        verdict = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    if verdict.get("status") == "blocked":
        count += 1
print(count)
PY
)
if [[ "${blocked:-0}" -gt 0 && "${FT_STRICT_BLOCKED:-1}" == "1" ]]; then
  echo "!! $blocked BLOCKED case(s); release is blocked until they run (FT_STRICT_BLOCKED=0 to allow locally)" >&2
  rc=1
fi

echo
echo "==> run complete (rc=$rc). Results under field-test/$FT_VERSION/results/"
exit "$rc"
