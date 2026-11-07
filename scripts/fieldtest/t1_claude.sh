#!/usr/bin/env bash
# FT-T1-CLAUDE — drive the REAL Claude Code loop through its PreToolUse hook and
# prove agentinbox gates the actual tool call.
#
# Structure follows agentpolicy's scripts/fieldtest/t1_claude.sh: a live 3-call
# agent triple, a hook-generated settings file, captured transcripts, and an
# audit trail. The difference is the decision surface: agentinbox is **exit-code
# gated** (`ask --file` blocks until answered), not `evaluate`-gated.
#
#   call 1: benign staging read      -> answer approve -> command EXECUTES
#   call 2: production write         -> answer deny    -> tool BLOCKED, no side effect
#   call 3: destructive production op-> answer deny    -> tool BLOCKED, agent replans
#
# A human answers from a second terminal:
#     agentinbox --home <case>/harness/home inbox
#     agentinbox --home <case>/harness/home answer <ask_id> --approve|--deny
#
# Requires: claude CLI, agentinbox CLI, a model configured for Claude Code.
# No hosted-model assumption is made by agentinbox itself; the harness's model is
# whatever the operator's Claude Code is configured with.
#
# Usage: t1_claude.sh CASE_DIR     (expects FT_PY / FT_CLI / REPO_ROOT)
set -euo pipefail

CASE_DIR="${1:?case dir}"
REPO_ROOT="${REPO_ROOT:?}"
FT_PY="${FT_PY:?}"
CLI="${CLAUDE_CLI:-claude}"
AINBOX="${FT_CLI:-agentinbox}"

H="$CASE_DIR/harness"
HOME_DIR="$H/home"
WORK="$H/work"
LLM_DIR="$CASE_DIR/artifacts/llm"
mkdir -p "$H/.claude" "$WORK" "$LLM_DIR"

# ---- 0. capture LLM traffic: Claude Code -> logging proxy -> upstream ------
# The proxy logs every request/response pair; deep validation fails the case if
# there is no balanced, 2xx, secret-free pair. No fake captures are possible.
UPSTREAM="${FT_T1_UPSTREAM:-${ANTHROPIC_BASE_URL:-http://127.0.0.1:8000}}"
PROXY_PID=""
PROXY_LOG="$CASE_DIR/artifacts/proxy.log"
"$FT_PY" "$REPO_ROOT/scripts/fieldtest/t1_proxy.py" "$UPSTREAM" "$LLM_DIR" \
  > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
trap 'kill "$PROXY_PID" 2>/dev/null || true' EXIT
PROXY_URL=""
for _ in $(seq 1 50); do
  PROXY_URL="$(sed -n 's/^T1_PROXY_READY //p' "$PROXY_LOG" 2>/dev/null | tail -1)"
  [[ -n "$PROXY_URL" ]] && break
  sleep 0.2
done
if [[ -z "$PROXY_URL" ]]; then
  echo "t1 proxy failed to start" >&2
  exit 1
fi
export ANTHROPIC_BASE_URL="$PROXY_URL"

# ---- 1. isolated agentinbox home (terminal-only default config) ------------
"$AINBOX" --home "$HOME_DIR" init >/dev/null 2>&1 || true

# ---- 2. PreToolUse hook: ask -> gate -> exit 0 only on approve -------------
# The ask body is a normal ask/1.0 contract payload. `ask --file` blocks until a
# human answers, so the hook is synchronous and Claude cannot proceed early.
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

# ---- 3. live triple --------------------------------------------------------
echo "hello-ft" > "$WORK/notes.txt"
run_claude() {
  ( cd "$WORK" && "$CLI" -p "$1" --settings "$H/.claude/settings.json" \
      2> "$CASE_DIR/artifacts/claude-$2.stderr" )
}

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

# ---- 4. audit trail: export the harness home's evidence --------------------
"$AINBOX" --home "$HOME_DIR" export --session ft-t1-claude > "$CASE_DIR/artifacts/audit.jsonl" 2>/dev/null || : \
  > "$CASE_DIR/artifacts/audit.jsonl"
echo "HARNESS_OK audit=$(wc -l < "$CASE_DIR/artifacts/audit.jsonl" | tr -d ' ') llm=$(find "$LLM_DIR" -name '*-request.json' | wc -l | tr -d ' ')"
