#!/usr/bin/env bash
set -u
INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | "/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')"
[[ -z "$CMD" ]] && exit 0
case "$CMD" in
  *"rm -rf"*|*"rm -r"*) ENV=production ;;
  *"cat "*|*"grep "*|*"ls "*) ENV=staging ;;
  *) ENV=production ;;
esac
BODY="$(mktemp)"
"/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/.venv/bin/python" - "$CMD" "$ENV" > "$BODY" <<'PY'
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
"/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/.venv/bin/agentinbox" --home "/Users/deghosal/Desktop/code/github/agentic-suite/agentinbox/field-test/v0.1.0/results/s15-harness/cases/FT-T1-CLAUDE/harness/home" ask --file "$BODY" --timeout 600 >/dev/null 2>&1
rc=$?
rm -f "$BODY"
if [[ $rc -eq 0 ]]; then exit 0; fi
echo "blocked by agentinbox (ask exit $rc)" >&2
exit 2
