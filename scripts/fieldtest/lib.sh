#!/usr/bin/env bash
# Field-test helpers for agentinbox — a thin, self-contained harness layer.
#
# Source from a runner:
#   source "$(dirname "$0")/lib.sh"
#   trap ft_teardown_on_exit EXIT
#   ft_case_begin "$ID"
#   ... steps + ft_assert / ft_sut_pytest ...
#   ft_finalize
#   ft_case_end "$ID" "$FT_CASE_STATUS"
#
# No skips: every case is pass/fail (or BLOCKED for a P/F|B case whose
# environment is genuinely unavailable — never a silent pass).
# Results are version-scoped: field-test/<FT_VERSION>/results/<run-id>/.
set -euo pipefail

FT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$FT_DIR/../.." && pwd)"
export REPO_ROOT

if [[ -f "$FT_DIR/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$FT_DIR/.env"
  set +a
fi

FT_VERSION="${FT_VERSION:-v0.1.0}"
for _frozen in ${FT_FROZEN_VERSIONS:-}; do
  if [[ "${FT_VERSION}" == "${_frozen}" && "${FT_ALLOW_FROZEN_WRITE:-0}" != "1" ]]; then
    echo "FATAL: refusing to write to docs/field-test/${_frozen} (frozen)." >&2
    echo "       Set FT_VERSION to a later version (override only with FT_ALLOW_FROZEN_WRITE=1)." >&2
    exit 3
  fi
done

RESULTS_ROOT="${FT_RESULTS_ROOT:-$REPO_ROOT/field-test/$FT_VERSION/results}"
if [[ -z "${FT_RUN_ID:-}" ]]; then
  echo "FATAL: FT_RUN_ID is not set — refusing to write to a default results dir." >&2
  echo "       Run via run-suite.sh / run-case.sh." >&2
  exit 3
fi
FT_RUN_DIR="$RESULTS_ROOT/$FT_RUN_ID"

if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  FT_PY="${AGENTINBOX_PYTHON:-$REPO_ROOT/.venv/bin/python}"
else
  FT_PY="${AGENTINBOX_PYTHON:-python3}"
fi
export FT_PY

# Host CLI for the Tier-1 harness cases (Claude Code / Codex CLI run on the host,
# not inside the Docker SUT). Resolve the venv console script, then PATH.
if [[ -x "$REPO_ROOT/.venv/bin/agentinbox" ]]; then
  FT_CLI="${AGENTINBOX_CLI:-$REPO_ROOT/.venv/bin/agentinbox}"
else
  FT_CLI="${AGENTINBOX_CLI:-agentinbox}"
fi
export FT_CLI

# The field-test compose overlay is standalone: the agentinbox CLI/SUT.
STACK_COMPOSE=(docker compose --project-directory "$REPO_ROOT" -f "$FT_DIR/docker-compose.fieldtest.yml")
FT_SUT_SERVICE="agentinbox"
FT_SERVICES=(agentinbox)
FT_CONTAINER_PY="${FT_CONTAINER_PY:-python}"

FT_CASE_DIR=""
FT_CASE_STATUS="fail"
FT_ASSERT_FAILED=0
FT_ASSERT_TOTAL=0
FT_ASSERT_GROUNDED=0
FT_CASE_CLASS="${FT_CASE_CLASS:-P/F}"
FT_CASE_BLOCKED=0
FT_BLOCK_REASON=""
FT_BLOCK_GATE=""

# --- run directory -----------------------------------------------------------
ft_run_init() {
  mkdir -p "$FT_RUN_DIR"
  if [[ ! -f "$FT_RUN_DIR/env.json" ]]; then
    {
      printf '{"run_id":"%s","version":"%s","docker":"%s","compose":"%s","os":"%s","arch":"%s","python":"%s","commit":"%s"}\n' \
        "$FT_RUN_ID" \
        "$FT_VERSION" \
        "$(docker --version 2>/dev/null || echo unknown)" \
        "$(docker compose version --short 2>/dev/null || echo unknown)" \
        "$(uname -s 2>/dev/null || echo unknown)" \
        "$(uname -m 2>/dev/null || echo unknown)" \
        "$("$FT_PY" --version 2>/dev/null | tr ' ' '-' || echo unknown)" \
        "$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    } > "$FT_RUN_DIR/env.json"
  fi
}

FT_SETUP_DIR="${FT_SETUP_DIR:-$RESULTS_ROOT/_setup}"
FT_SETUP_LOG="${FT_SETUP_LOG:-$FT_SETUP_DIR/${FT_RUN_ID}-stack-up.log}"

_ft_log() {
  mkdir -p "$(dirname "$FT_SETUP_LOG")"
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$FT_SETUP_LOG"
}

# --- case lifecycle ----------------------------------------------------------
ft_case_begin() {
  local id="$1"
  ft_run_init
  FT_CASE_DIR="$FT_RUN_DIR/cases/$id"
  export FT_CASE_DIR
  mkdir -p "$FT_CASE_DIR/artifacts"
  : > "$FT_CASE_DIR/commands.log"
  : > "$FT_CASE_DIR/stdout.log"
  : > "$FT_CASE_DIR/stderr.log"
  : > "$FT_CASE_DIR/assertions.ndjson"
  FT_CASE_STATUS="fail"
  FT_ASSERT_FAILED=0
  FT_ASSERT_TOTAL=0
  FT_ASSERT_GROUNDED=0
  FT_CASE_BLOCKED=0
  FT_BLOCK_REASON=""
  FT_BLOCK_GATE=""
  echo "== case $id =="
}

# BLOCKED is valid only for a P/F|B case and requires a named limitation + the
# downstream gate it blocks. A hard P/F case cannot be blocked.
ft_block() {
  local reason="$1" gate="${2:-}"
  if [[ "$FT_CASE_CLASS" != "P/F|B" ]]; then
    echo "  BLOCK-INVALID $reason (case class is $FT_CASE_CLASS, not P/F|B)" >&2
    FT_ASSERT_FAILED=1
    return 1
  fi
  FT_CASE_BLOCKED=1
  FT_BLOCK_REASON="$reason"
  FT_BLOCK_GATE="$gate"
  printf '{"name":"blocked","ok":true,"blocked":true,"reason":"%s","release_gate_item":"%s"}\n' \
    "$(_ft_json_escape "$reason")" "$(_ft_json_escape "$gate")" \
    >> "$FT_CASE_DIR/assertions.ndjson"
  echo "  BLOCKED $reason"
}

ft_record() {
  [[ -n "${FT_CASE_DIR:-}" ]] || return 0
  printf '+ %s\n' "$*" >> "$FT_CASE_DIR/commands.log"
}

_ft_json_escape() {
  local s="${1:-}"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  printf '%s' "$s"
}

# Weak-assertion catalogue — an assertion that proves only plumbing is not a
# grounded check and cannot, alone, justify a PASS.
_ft_weak_reasons() {
  local cmd="$1" reasons=""
  [[ -z "${cmd// }" ]] && reasons="$reasons empty-command"
  grep -qE "^(:|true)$" <<<"$cmd" && reasons="$reasons bare-true"
  grep -qE "python3? +-c +['\"]import " <<<"$cmd" && reasons="$reasons import-only"
  grep -qE "python3? +-m +[A-Za-z_.]+ *$" <<<"$cmd" && reasons="$reasons module-import-only"
  grep -qF "|| true" <<<"$cmd" && reasons="$reasons cannot-fail"
  grep -qF "json.tool" <<<"$cmd" && reasons="$reasons json.tool"
  if grep -qE "\btest +-[fsn]\b" <<<"$cmd" && [[ "$cmd" != *grep* && "$cmd" != *"&&"* ]]; then
    reasons="$reasons existence-only"
  fi
  if grep -qE "(^| )pytest " <<<"$cmd" && [[ "$cmd" != *run_pytest.py* ]]; then
    reasons="$reasons bare-pytest"
  fi
  printf '%s' "$reasons"
}

ft_assert() {
  local name="$1"; shift
  local cmd="$*"
  local weak; weak="$(_ft_weak_reasons "$cmd")"
  local grounded="true"; [[ -n "$weak" ]] && grounded="false"
  if "$@" >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log"; then
    if [[ "$grounded" == "true" ]]; then FT_ASSERT_GROUNDED=$((FT_ASSERT_GROUNDED + 1)); fi
    printf '{"name":"%s","ok":true,"grounded":%s,"cmd":"%s"}\n' \
      "$name" "$grounded" "$(_ft_json_escape "$cmd")" >> "$FT_CASE_DIR/assertions.ndjson"
    echo "  PASS $name${weak:+ (WEAK:${weak# })}"
    return 0
  fi
  FT_ASSERT_FAILED=1
  printf '{"name":"%s","ok":false,"grounded":%s,"cmd":"%s"}\n' \
    "$name" "$grounded" "$(_ft_json_escape "$cmd")" >> "$FT_CASE_DIR/assertions.ndjson"
  echo "  FAIL $name" >&2
  return 1
}

ft_fail() {
  local name="$1"
  FT_ASSERT_FAILED=1
  printf '{"name":"%s","ok":false}\n' "$name" >> "$FT_CASE_DIR/assertions.ndjson"
  echo "  FAIL $name" >&2
}

ft_pass() {
  local name="$1"
  printf '{"name":"%s","ok":true,"grounded":true}\n' "$name" >> "$FT_CASE_DIR/assertions.ndjson"
  FT_ASSERT_GROUNDED=$((FT_ASSERT_GROUNDED + 1))
  echo "  PASS $name"
}

# Container pytest: skip = failure, no-tests = failure.
ft_sut_pytest() {
  local name="$1"; shift
  ft_assert "$name" ft_sut "$FT_CONTAINER_PY" /ft/scripts/run_pytest.py "$@"
}

ft_capture() {
  local src="$1" dest="$2"
  mkdir -p "$FT_CASE_DIR/artifacts/$dest"
  cp -R "$src"/. "$FT_CASE_DIR/artifacts/$dest/" 2>/dev/null || true
}

ft_case_end() {
  local id="$1" status="${2:-$FT_CASE_STATUS}"
  FT_CASE_STATUS="$status"
  if grep -rqiIE 'sk-[A-Za-z0-9]{16,}|Bearer +[A-Za-z0-9._-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}' \
        "$FT_CASE_DIR/artifacts" 2>/dev/null; then
    FT_ASSERT_FAILED=1
    printf '{"name":"no-secret-leak","ok":false,"grounded":true,"cmd":"scan artifacts for secrets"}\n' \
      >> "$FT_CASE_DIR/assertions.ndjson"
    echo "  FAIL no-secret-leak (unmasked secret in case artifacts)" >&2
    FT_CASE_STATUS="fail"
  else
    printf '{"name":"no-secret-leak","ok":true,"grounded":true,"cmd":"scan artifacts for secrets"}\n' \
      >> "$FT_CASE_DIR/assertions.ndjson"
    echo "  PASS no-secret-leak"
  fi
  {
    printf '{\n'
    printf '  "id": "%s",\n' "$id"
    printf '  "status": "%s",\n' "$status"
    printf '  "class": "%s",\n' "$FT_CASE_CLASS"
    printf '  "blocked": %s,\n' "$([[ "$FT_CASE_BLOCKED" -eq 1 ]] && echo true || echo false)"
    printf '  "grounded": %s,\n' "$([[ "${FT_ASSERT_GROUNDED:-0}" -ge 1 ]] && echo true || echo false)"
    printf '  "assertions_total": %s,\n' "$FT_ASSERT_TOTAL"
    printf '  "assertions_grounded": %s,\n' "$FT_ASSERT_GROUNDED"
    if [[ "$FT_CASE_BLOCKED" -eq 1 ]]; then
      printf '  "limitation": "%s",\n' "$(_ft_json_escape "$FT_BLOCK_REASON")"
      printf '  "release_gate_item": "%s",\n' "$(_ft_json_escape "$FT_BLOCK_GATE")"
    fi
    printf '  "run_id": "%s",\n' "$FT_RUN_ID"
    printf '  "assertions": ['
    if [[ -s "$FT_CASE_DIR/assertions.ndjson" ]]; then
      paste -sd, "$FT_CASE_DIR/assertions.ndjson"
    fi
    printf ']\n}\n'
  } > "$FT_CASE_DIR/verdict.json"
  echo "== case $id: $status =="
}

ft_finalize() {
  local total=0
  if [[ -s "$FT_CASE_DIR/assertions.ndjson" ]]; then
    total=$(wc -l < "$FT_CASE_DIR/assertions.ndjson" | tr -d ' ')
  fi
  FT_ASSERT_TOTAL="$total"
  if [[ "$FT_ASSERT_FAILED" -ne 0 ]]; then
    FT_CASE_STATUS="fail"
  elif [[ "$FT_CASE_BLOCKED" -eq 1 ]]; then
    FT_CASE_STATUS="blocked"
  elif [[ "$total" -eq 0 ]]; then
    FT_CASE_STATUS="fail"
    echo "  FAIL no-assertions (a pass must be backed by >=1 assertion)" >&2
  elif [[ "${FT_STRICT_GROUNDING:-1}" == "1" && "$FT_ASSERT_GROUNDED" -eq 0 ]]; then
    FT_CASE_STATUS="fail"
    echo "  FAIL ungrounded (no grounded assertion; every assertion is plumbing)" >&2
  else
    FT_CASE_STATUS="pass"
  fi
}

ft_teardown_on_exit() {
  local code=$?
  if [[ "${FT_SHARED_STACK:-0}" == "1" ]]; then
    exit "$code"
  fi
  if [[ "${STACK_KEEP:-}" == "1" ]]; then
    echo "==> STACK_KEEP=1 set; leaving the stack running"
    exit "$code"
  fi
  stack_teardown
  exit "$code"
}

# --- docker SUT lifecycle -----------------------------------------------------
FT_SUT_HOME=/data/agentinbox

ft_require_docker() {
  if ! docker info >/dev/null 2>&1; then
    echo "FAIL: Docker is unavailable; the agentinbox field test runs in Docker." >&2
    return 3
  fi
}

stack_up() {
  ft_record "compose up (agentinbox)"
  if [[ -n "${FT_CASE_DIR:-}" ]]; then
    "${STACK_COMPOSE[@]}" up -d --build "$FT_SUT_SERVICE" \
      >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log" || return 1
  else
    mkdir -p "$(dirname "$FT_SETUP_LOG")"
    "${STACK_COMPOSE[@]}" up -d --build "$FT_SUT_SERVICE" \
      >> "$FT_SETUP_LOG" 2>&1 || return 1
  fi
}

stack_teardown() {
  if [[ "${STACK_KEEP:-}" == "1" ]]; then
    return 0
  fi
  "${STACK_COMPOSE[@]}" down -v >/dev/null 2>&1 || true
}

ft_wait_ready() {
  local timeout="${STACK_TIMEOUT:-180}"
  local deadline=$((SECONDS + timeout))
  _ft_log "waiting for stack readiness (timeout ${timeout}s)"
  while :; do
    local all_ok=1 svc cid status health
    for svc in "${FT_SERVICES[@]}"; do
      cid="$("${STACK_COMPOSE[@]}" ps -q "$svc" 2>/dev/null)"
      if [[ -z "$cid" ]]; then _ft_log "  $svc: no container yet"; all_ok=0; continue; fi
      status="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null)"
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null)"
      _ft_log "  $svc: status=$status health=$health"
      [[ "$status" == "running" ]] || all_ok=0
      [[ "$health" == "healthy" || "$health" == "none" ]] || all_ok=0
    done
    [[ "$all_ok" -eq 1 ]] && break
    if (( SECONDS >= deadline )); then
      _ft_log "FAIL: stack not running+healthy within ${timeout}s"
      "${STACK_COMPOSE[@]}" ps >>"$FT_SETUP_LOG" 2>&1 || true
      return 1
    fi
    sleep 2
  done
  while :; do
    if "${STACK_COMPOSE[@]}" exec -T "$FT_SUT_SERVICE" agentinbox --version >>"$FT_SETUP_LOG" 2>&1; then
      _ft_log "SUT answers: agentinbox --version OK"
      break
    fi
    if (( SECONDS >= deadline )); then
      _ft_log "FAIL: SUT did not answer within ${timeout}s"
      return 1
    fi
    sleep 2
  done
  _ft_log "stack READY"
  return 0
}

ft_up_sut() {
  ft_require_docker || return 3
  if ! stack_up; then ft_fail "stack-up"; return 1; fi
  ft_pass "stack-up"
  if ft_wait_ready; then ft_pass "stack-ready"; else ft_fail "stack-ready"; return 1; fi
}

ft_exec() {
  local service="$1"; shift
  ft_record "compose exec $service $*"
  local rc=0
  "${STACK_COMPOSE[@]}" exec -T "$service" "$@" \
    >> "${FT_CASE_DIR:-/dev/null}/stdout.log" 2>> "${FT_CASE_DIR:-/dev/null}/stderr.log" || rc=$?
  return "$rc"
}

ft_sut() { ft_exec "$FT_SUT_SERVICE" "$@"; }
