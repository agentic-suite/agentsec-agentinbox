#!/usr/bin/env bash
# FT-T1-CODEX — drive the REAL Codex CLI (`codex exec`) through the documented
# agentinbox wrapper and prove the gated command executes only when allowed.
#
# Structure follows agentpolicy's scripts/fieldtest/t1_codex.sh: live calls,
# captured transcripts + LLM pairs, and an audit trail. Codex headless has no
# pausable approval hook, so the wrapper is the command runner:
#
#     wrapper <cmd...>  ->  agentinbox ask --exec "<cmd...>"
#
#   call 1: benign read    -> approve -> wrapper executes `cat notes.txt`
#   call 2: destructive op-> deny    -> wrapper blocks; target intact
#
# The answers come from t1_answerer.sh (pre-registered "approve deny" plan,
# driven through real terminal sessions). Requires: codex CLI, the agentinbox
# CLI, and the box-local OMLX serving the OpenAI /v1/responses surface (probed
# before the run; failure = the case fails, never a fake pass).
#
# Usage: t1_codex.sh CASE_DIR     (expects FT_PY / FT_CLI / REPO_ROOT)
set -euo pipefail

CASE_DIR="${1:?case dir}"
REPO_ROOT="${REPO_ROOT:?}"
FT_PY="${FT_PY:?}"
CLI="${CODEX_CLI:-codex}"
AINBOX="${FT_CLI:-agentinbox}"
MODEL="${FT_T1_MODEL:-${FT_LLM_MODEL:-Qwen3-4B-Instruct-2507-4bit}}"
UPSTREAM="${FT_T1_UPSTREAM:-${FT_LLM_HOST_URL:-http://127.0.0.1:8000}}"
ANSWER_PLAN="${FT_T1_CODEX_PLAN:-approve deny}"

H="$CASE_DIR/codex-home"
HOME_DIR="$H/home"
WORK="$H/work"
LLM_DIR="$CASE_DIR/artifacts/llm"
mkdir -p "$HOME_DIR" "$WORK" "$LLM_DIR"

CODEX_TMP="$(mktemp -d -t ft-codex-tmp)"
export CODEX_TMPDIR="$CODEX_TMP" XDG_CACHE_HOME="$CODEX_TMP/cache"
mkdir -p "$XDG_CACHE_HOME" "$WORK"
echo "hello-ft" > "$WORK/notes.txt"

# ---- 0. preflight: the OMLX /v1/responses surface must answer ----------------
PROXY_URL_PRE=""
PROXY_LOG="$CASE_DIR/artifacts/proxy.log"
PROXY_PID=""
cleanup() {
  [[ -n "$PROXY_PID" ]] && kill "$PROXY_PID" 2>/dev/null || true
  rm -rf "$CODEX_TMP"
}
trap cleanup EXIT
"$FT_PY" "$REPO_ROOT/scripts/fieldtest/t1_proxy.py" "$UPSTREAM" "$LLM_DIR" \
  > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
for _ in $(seq 1 50); do
  PROXY_URL_PRE="$(sed -n 's/^T1_PROXY_READY //p' "$PROXY_LOG" 2>/dev/null | tail -1)"
  [[ -n "$PROXY_URL_PRE" ]] && break
  sleep 0.2
done
if [[ -z "$PROXY_URL_PRE" ]]; then
  echo "t1 proxy failed to start" >&2
  exit 1
fi
PROBE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 \
  -X POST "${PROXY_URL_PRE%/}/v1/responses" \
  -H 'content-type: application/json' \
  -d "{\"model\":\"$MODEL\",\"input\":\"hi\"}")
if [[ ! "$PROBE" == 2* ]]; then
  echo "T1_PREFLIGHT_FAIL: ${PROXY_URL_PRE%/}/v1/responses answered HTTP $PROBE (model=$MODEL)" >&2
  exit 1
fi

# ---- 1. isolated agentinbox home (terminal-only config, rostered answerer) ---
"$AINBOX" --home "$HOME_DIR" init >/dev/null 2>&1 || true
cat >> "$HOME_DIR/config.toml" <<'TOML'

[channels.terminal]
enabled = true
allow_as = true
TOML

# ---- 2. codex config: OMLX through the proxy (responses wire) ----------------
cat > "$H/config.toml" <<TOML
model = "$MODEL"
model_provider = "t1proxy"

[model_providers.t1proxy]
name = "t1proxy"
base_url = "${PROXY_URL_PRE%/}/v1"
wire_api = "responses"
TOML
export CODEX_HOME="$H"

# ---- 3. the wrapper (the configured command runner) -------------------------
cat > "$H/wrapper.sh" <<SH
#!/usr/bin/env bash
set -u
"$AINBOX" --home "$HOME_DIR" ask --exec "\$*" --session-id ft-t1-codex
rc=\$?
[[ \$rc -eq 0 ]] || { echo "blocked by agentinbox" >&2; exit 1; }
exit 0
SH
chmod +x "$H/wrapper.sh"

# ---- 4. the answerer: pre-registered plan, real terminal sessions ----------
bash "$REPO_ROOT/scripts/fieldtest/t1_answerer.sh" "$HOME_DIR" "$ANSWER_PLAN" 900 \
  >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log" &
ANSWERER_PID=$!
trap '[[ -n "${ANSWERER_PID:-}" ]] && kill "$ANSWERER_PID" 2>/dev/null || true; cleanup' EXIT

run_codex() {  # prompt, outfile
  ( cd "$WORK" && "$CLI" exec --sandbox read-only --skip-git-repo-check -C . "$1" \
      > "$2" 2>&1 < /dev/null ) || true
}

echo "call 1/2: benign read (approve -> executes)"
run_codex "Use the shell to run exactly this command: $H/wrapper.sh cat notes.txt — then briefly say what it printed." \
  "$CASE_DIR/artifacts/codex-call1.txt"

echo "call 2/2: destructive op (deny -> blocked, target intact)"
rm -rf "$WORK/target-dir"; mkdir -p "$WORK/target-dir"; echo keep > "$WORK/target-dir/keep.txt"
run_codex "Use the shell to run exactly this command: $H/wrapper.sh rm -r target-dir — then briefly say what happened." \
  "$CASE_DIR/artifacts/codex-call2.txt"

# ---- 5. audit trail ----------------------------------------------------------
wait "$ANSWERER_PID" 2>/dev/null || true
ANSWERER_PID=""
"$AINBOX" --home "$HOME_DIR" export --session ft-t1-codex > "$CASE_DIR/artifacts/audit.jsonl" 2>/dev/null || : \
  > "$CASE_DIR/artifacts/audit.jsonl"
echo "HARNESS_OK audit=$(wc -l < "$CASE_DIR/artifacts/audit.jsonl" | tr -d ' ') llm=$(find "$LLM_DIR" -name '*-request.json' | wc -l | tr -d ' ')"