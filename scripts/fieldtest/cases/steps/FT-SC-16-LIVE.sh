#!/usr/bin/env bash
# Hand-written field step (not generated): SC-16 LIVE — the real `gate` exit
# matrix on the host CLI: approved -> 0, denied -> 2, expired -> 3, pending -> 5.
# The contract tests pin the codes; this case exercises them end-to-end.
LIVE="$FT_CASE_DIR/live"
HOME_DIR="$LIVE/home"
mkdir -p "$LIVE"
"$FT_CLI" --home "$HOME_DIR" init >/dev/null 2>&1 || true
cat >> "$HOME_DIR/config.toml" <<'TOML'

[classes.irreversible]
ttl_seconds = 60
require_reason_on_deny = true

[classes.readonly]
ttl_seconds = 4

[roster.tier-1]
terminal = ["alice"]

[channels.terminal]
enabled = true
allow_as = true
TOML

make_ask() {  # CLASS SESSION TTL_SECONDS -> ask id (non-blocking create)
  "$FT_PY" - "$FT_CLI" "$HOME_DIR" "$1" "$2" "$3" <<'PY' | tail -1
import json, subprocess, sys
cli, home, class_name, session, ttl = sys.argv[1:6]
body = {
    "contract": "ask/1.0",
    "tool": "shell", "action": "run_command",
    "arguments": {"command": "echo matrix"},
    "agent_id": "agent://t1-live", "session_id": session,
    "environment": "production", "data_class": "internal", "class": class_name,
    "reason_code": "human_gate_required",
    "policy_ref": {"rule_id": "cli-exec", "policy_version": "v0.1.0", "clause": "live"},
    "criticality": "normal", "requested_by": "agent://t1-live",
    "expires_at": None, "context": {},
}
from datetime import timedelta
from agentinbox.contract import compute_action_identity
from agentinbox.store import to_iso, utcnow
body["action_identity"] = compute_action_identity(
    tool="shell", action="run_command", arguments=body["arguments"])
body["expires_at"] = to_iso(utcnow() + timedelta(seconds=int(ttl)))
proc = subprocess.run(
    [cli, "--json", "--home", home, "ask", "--file", "/dev/stdin", "--timeout", "0.5"],
    input=json.dumps(body), capture_output=True, text=True,
)
try:
    print(json.loads(proc.stdout).get("ask_id", ""))
except ValueError:
    print("")
PY
}

gate_rc() {  # ASK_ID EXTRA_TIMEOUT -> gate exit code
  local args=(--ask "$1")
  [[ -n "${2:-}" ]] && args+=(--timeout "$2")
  "$FT_CLI" --home "$HOME_DIR" gate "${args[@]}" >/dev/null 2>&1 || true
  echo $?
}

# approved -> exit 0
A1="$(make_ask irreversible ft-sc16-approved 60)"
bash "$FT_DIR/t1_answer.sh" "$HOME_DIR" "$A1" approve run_command \
  >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log" || true
rc="$(gate_rc "$A1")"
ft_assert "gate-approved-exit-0" test "$rc" -eq 0

# denied -> exit 2
A2="$(make_ask irreversible ft-sc16-denied 60)"
bash "$FT_DIR/t1_answer.sh" "$HOME_DIR" "$A2" deny "" "not in the window" \
  >> "$FT_CASE_DIR/stdout.log" 2>> "$FT_CASE_DIR/stderr.log" || true
rc="$(gate_rc "$A2")"
ft_assert "gate-denied-exit-2" test "$rc" -eq 2

# expired -> exit 3 (short-TTL readonly class, nobody answers)
A3="$(make_ask readonly ft-sc16-expired 2)"
sleep 3
rc="$(gate_rc "$A3")"
ft_assert "gate-expired-exit-3" test "$rc" -eq 3

# pending -> exit 5 (ask exists, unanswered, gate times out)
A4="$(make_ask readonly ft-sc16-pending 60)"
rc="$(gate_rc "$A4" 1)"
ft_assert "gate-pending-exit-5" test "$rc" -eq 5

ft_finalize