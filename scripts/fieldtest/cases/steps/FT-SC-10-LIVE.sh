#!/usr/bin/env bash
# Hand-written field step (not generated): SC-10 LIVE — expiry survives a real
# daemon kill -9 and restart, firing `ask-expired` exactly once (recovered).
# The pytest suites mock the crash; this case does it for real on the host.
LIVE="$FT_CASE_DIR/live"
HOME_DIR="$LIVE/home"
mkdir -p "$LIVE"
FT_LIVE_HOME="$HOME_DIR" "$FT_CLI" --home "$HOME_DIR" init >/dev/null 2>&1 || true
cat >> "$HOME_DIR/config.toml" <<'TOML'

[classes.irreversible]
ttl_seconds = 8
warn_seconds = 3

[channels.terminal]
enabled = true
allow_as = true
TOML

# The ask: short TTL, so the daemon has something to expire mid-crash.
"$FT_PY" - > "$LIVE/body.json" <<'PY'
import json
from datetime import timedelta
from agentinbox.contract import compute_action_identity
from agentinbox.store import to_iso, utcnow
arguments = {"command": "echo t1-live"}
now = utcnow()
print(json.dumps({
    "contract": "ask/1.0",
    "action_identity": compute_action_identity(tool="shell", action="run_command", arguments=arguments),
    "tool": "shell", "action": "run_command", "arguments": arguments,
    "agent_id": "agent://t1-live", "session_id": "ft-sc-10-live",
    "environment": "production", "data_class": "internal", "class": "irreversible",
    "reason_code": "human_gate_required",
    "policy_ref": {"rule_id": "cli-exec", "policy_version": "v0.1.0", "clause": "live"},
    "criticality": "normal", "requested_by": "agent://t1-live",
    "expires_at": to_iso(now + timedelta(seconds=8)),
    "context": {},
}))
PY

DAEMON_LOG="$LIVE/daemon.log"
"$FT_CLI" --home "$HOME_DIR" serve > "$DAEMON_LOG" 2>&1 &
DAEMON_PID=$!
sleep 1

# Create the ask (blocks briefly; nobody answers), then kill -9 mid-TTL.
"$FT_CLI" --home "$HOME_DIR" ask --file "$LIVE/body.json" --timeout 4 \
  > "$LIVE/ask.out" 2> "$LIVE/ask.err" || true
kill -9 "$DAEMON_PID" 2>/dev/null || true
wait "$DAEMON_PID" 2>/dev/null || true

# Restart AFTER the TTL: recovery must fire `ask-expired` exactly once.
sleep 8
"$FT_CLI" --home "$HOME_DIR" serve --once > "$LIVE/recover.log" 2>&1 || true

"$FT_CLI" --home "$HOME_DIR" export --session ft-sc-10-live > "$LIVE/export.jsonl" 2>/dev/null || true
ft_capture "$LIVE" "sc10-live"

ft_assert "sc10-expired-exactly-once" bash -c '
  test "$('"$FT_PY"' <<EOF
import json, pathlib
rows = [json.loads(l) for l in pathlib.Path("'"$LIVE"'/export.jsonl").read_text().splitlines() if l.strip()]
expired = [r for r in rows if r.get("kind") == "expired"]
assert len(expired) == 1, expired
print("EXPIRED-ONCE")
EOF
)" = "EXPIRED-ONCE"'

ft_assert "sc10-resolve-deny-timeout" bash -c '
  ASK_ID="$(grep -o "ask_[a-f0-9]*" "'"$LIVE"'/export.jsonl" | head -1)"
  OUT=$("'"$FT_CLI"' --home "'"$HOME_DIR"'" gate --ask "$ASK_ID" --timeout 2 2>/dev/null || true)"
  echo "$OUT" | grep -q "human_gate_timeout" && echo DENY-TIMEOUT'

ft_finalize