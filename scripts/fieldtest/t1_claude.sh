#!/usr/bin/env bash
# FT-T1-CLAUDE — drive the REAL Claude Code loop through its PreToolUse hook and
# prove agentinbox gates the actual tool call.
#
# Structure follows agentpolicy's scripts/fieldtest/t1_claude.sh: a live 3-call
# agent triple, a hook-generated settings file, captured transcripts, and an
# audit trail. The difference is the decision surface: agentinbox is
# **exit-code gated** (`ask --file` blocks until answered), not
# `evaluate`-gated.
#
#   call 1: benign staging read        -> approve -> command EXECUTES
#   call 2: production write           -> deny    -> tool BLOCKED, no side effect
#   call 3: destructive production op -> deny    -> tool BLOCKED, agent replans
#
# The answers come from t1_answerer.sh: a pre-registered answer plan
# ("approve deny deny") driven through REAL terminal sessions (pty) — the
# "second terminal" the recipe documents, automated and recorded as automation.
# The product contract is untouched: no non-interactive approve exists.
#
# Requires: claude CLI, the agentinbox CLI, and the box-local OMLX serving the
# Anthropic /v1/messages surface (probed before the run; failure = the case
# fails, never a fake pass).
#
# Usage: t1_claude.sh CASE_DIR     (expects FT_PY / FT_CLI / REPO_ROOT)
set -euo pipefail

CASE_DIR="${1:?case dir}"
REPO_ROOT="${REPO_ROOT:?}"
FT_PY="${FT_PY:?}"
CLI="${CLAUDE_CLI:-claude}"
AINBOX="${FT_CLI:-agentinbox}"
MODEL="${FT_T1_MODEL:-${FT_LLM_MODEL:-Qwen3-4B-Instruct-2507-4bit}}"
UPSTREAM="${FT_T1_UPSTREAM:-${FT_LLM_HOST_URL:-http://127.0.0.1:8000}}"
ANSWER_PLAN="${FT_T1_CLAUDE_PLAN:-approve deny deny}"

H="$CASE_DIR/harness"
HOME_DIR="$H/home"
WORK="$H/work"
LLM_DIR="$CASE_DIR/artifacts/llm"
mkdir -p "$H/.claude" "$WORK" "$LLM_DIR"

# ---- 0. preflight: the OMLX /v1/messages surface must answer (no fake pass) --
PROBE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 \
  -X POST "$UPSTREAM/v1/messages" \
  -H 'content-type: application/json' \
  -d "{\"model\":\"$MODEL\",\"max_tokens\":1,\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}")
if [[ ! "$PROBE" == 2* ]]; then
  echo "T1_PREFLIGHT_FAIL: $UPSTREAM/v1/messages answered HTTP $PROBE (model=$MODEL)" >&2
  exit 1
fi

# ---- 1. isolated agentinbox home (terminal-only config, rostered answerer) ---
"$AINBOX" --home "$HOME_DIR" init >/dev/null 2>&1 || true
# The answerer acts as a rostered principal via --as (recorded as assumed).
CONFIG="$HOME_DIR/config.toml"
cat >> "$CONFIG" <<'TOML'

[channels.terminal]
enabled = true
allow_as = true
TOML

# ---- 2. PreToolUse hook: ask -> gate -> exit 0 only on approve ---------------
cat > "$H/hook.sh" <<SH
#!/usr/bin/env bash
set -u
INPUT="\$(cat)"
CMD="\$(printf '%s' "\$INPUT" | "$FT_PY" -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')"
[[ -z "\$CMD" ]] && exit 0
case "\$CMD" in
  *"rm -rf"*|*"rm -r"*) ENV=production ;;
  *"cat "*|*"grep "*|*"ls "*) ENV=staging ;;
  *) ENV=production ;;
esac
BODY="\$(mktemp)"
"$FT_PY" - "\$CMD" "\$ENV" > "\$BODY" <<'PY'
import json, sys
from datetime import timedelta
from agentinbox.contract import compute_action_identity
from agentinbox.store import to_iso, utcnow
cmd, env = sys.argv[1], sys.argv[2]
arguments = {"command": cmd}
now = utcnow()
print(json.dumps({
    "contract": "ask/1.0",
    "action_identity": compute_action_identity(tool="shell", action="run_command", arguments=arguments),
    "tool": "shell", "action": "run_command", "arguments": arguments,
    "agent_id": "agent://claude-code-t1", "session_id": "ft-t1-claude",
    "environment": env, "data_class": "internal", "class": "irreversible",
    "reason_code": "human_gate_required",
    "policy_ref": {"rule_id": "cli-exec", "policy_version": "v0.1.0", "clause": "T1 recipe"},
    "criticality": "normal", "requested_by": "agent://claude-code-t1",
    "expires_at": to_iso(now + timedelta(seconds=300)),
    "context": {},
}))
PY
"$AINBOX" --home "$HOME_DIR" ask --file "\$BODY" --timeout 600 >/dev/null 2>&1
rc=\$?
rm -f "\$BODY"
if [[ \$rc -eq 0 ]]; then exit 0; fi
echo "blocked by agentinbox (ask exit \$rc)" >&2
exit 2
SH
chmod +x "$H/hook.sh"

cat > "$H/.claude/settings.json" <<JSON
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "$H/hook.sh"}]}
    ]
  }
}
JSON

# ---- 3. capture LLM traffic: Claude Code -> logging proxy -> OMLX -------------
PROXY_LOG="$CASE_DIR/artifacts/proxy.log"
"$FT_PY" "$REPO_ROOT/scripts/fieldtest/t1_proxy.py" "$UPSTREAM" "$LLM_DIR" \
  > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
PROXY_URL=""
for _ in $(seq 1 50); do
  PROXY_URL="$(sed -n 's/^T1_PROXY_READY //p' "$PROXY_LOG" 2>/dev/null | tail -1)"
  [[ -n "$PROXY_URL" ]] && break
  sleep 0.2
done
if [[ -z "$PROXY_URL" ]]; then
  kill "$PROXY_PID" 2>/dev/null || true
  echo "t1 proxy failed to start" >&2
  exit 1
fi
export ANTHROPIC_BASE_URL="$PROXY_URL"
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_SMALL_FAST_MODEL="$MODEL"
export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-local}"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_TELEMETRY=1

# ---- 4. the answerer: pre-registered plan, real terminal sessions ----------
ANSWERER_PID=""
cleanup() {
  [[ -n "$ANSWERER_PID" ]] && kill "$ANSWERER_PID" 2>/dev/null || true
  [[ -n "$PROXY_PID" ]] && kill "$PROXY_PID" 2>/dev/null || true
}
trap cleanup EXIT
bash "$REPO_ROOT/scripts/fieldtest/t1_answerer.sh" "$HOME_DIR" "$ANSWER_PLAN" 900 \
  >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log" &
ANSWERER_PID=$!

# ---- 5. the live triple ------------------------------------------------------
run_claude() {
  ( cd "$WORK" && "$CLI" -p "$1" --model "$MODEL" \
      --settings "$H/.claude/settings.json" \
      2> "$CASE_DIR/artifacts/claude-$2.stderr" )
}

echo "hello-ft" > "$WORK/notes.txt"
echo "triple call 1/3: staging read (approve -> executes)"
run_claude "Use the Bash tool to run exactly this command: cat notes.txt — then briefly say what happened." c1 \
  > "$CASE_DIR/artifacts/claude-call1.txt" || true

echo "triple call 2/3: production write (deny -> blocked, no side effect)"
rm -f "$WORK/ft-t1-side-effect.txt"
run_claude "Use the Bash tool to run exactly this command: echo done >> ft-t1-side-effect.txt — then briefly say what happened." c2 \
  > "$CASE_DIR/artifacts/claude-call2.txt" || true

echo "triple call 3/3: destructive production op (deny -> structured rejection)"
rm -rf "$WORK/ft-t1-target"
run_claude "Use the Bash tool to run exactly this command: rm -rf ft-t1-target — then briefly say what happened." c3 \
  > "$CASE_DIR/artifacts/claude-call3.txt" || true

# ---- 6. audit trail: export the harness home's evidence ---------------------
wait "$ANSWERER_PID" 2>/dev/null || true
ANSWERER_PID=""
"$AINBOX" --home "$HOME_DIR" export --session ft-t1-claude > "$CASE_DIR/artifacts/audit.jsonl" 2>/dev/null || : \
  > "$CASE_DIR/artifacts/audit.jsonl"
echo "HARNESS_OK audit=$(wc -l < "$CASE_DIR/artifacts/audit.jsonl" | tr -d ' ') llm=$(find "$LLM_DIR" -name '*-request.json' | wc -l | tr -d ' ')"