#!/usr/bin/env bash
# Hand-written field step (not generated): SC-10 LIVE — expiry survives a real
# daemon kill -9 and restart, firing `ask-expired` exactly once (recovered).
# The pytest suites mock the crash; this case does it for real on the host.
LIVE="$FT_CASE_DIR/live"
HOME_DIR="$LIVE/home"
mkdir -p "$LIVE"
"$FT_CLI" --home "$HOME_DIR" init >/dev/null 2>&1 || true

# Replace the scaffold with a dedicated live config. Do NOT append tables that
# already exist ([classes.irreversible], [channels.terminal]) — duplicate TOML
# tables made the daemon fail to start (batch-1 defect).
cat > "$HOME_DIR/config.toml" <<'TOML'
[classes.irreversible]
ttl_seconds = 8
warn_seconds = 3
self_review = "deny"
require_reason_on_deny = true
ladder = []

[roster.tier-1]
terminal = ["alice"]

[throttle]
per_agent_burst = 20
per_agent_rate_per_min = 10
flood_window_seconds = 30

[channels.terminal]
enabled = true

[channels.desktop]
enabled = false

[channels.webhook]
enabled = false

[bus]
driver = "filesystem"

[store]
driver = "sqlite"
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
"$FT_CLI" --home "$HOME_DIR" serve --no-api > "$DAEMON_LOG" 2>&1 &
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

ft_assert "sc10-expired-exactly-once" "$FT_PY" - "$LIVE/export.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
expired = [row for row in rows if row.get("kind") == "expired"]
assert len(expired) == 1, f"expired rows: {expired}"
print("EXPIRED-ONCE")
PY

ft_assert "sc10-resolve-deny-timeout" "$FT_PY" - "$HOME_DIR" "$LIVE/export.jsonl" <<'PY'
import json, sys
from pathlib import Path
from agentinbox.config import load_config, resolve_config_path
from agentinbox.resolve import resolve
from agentinbox.store import utcnow
from agentinbox.store.sqlite import SqliteStore

home = Path(sys.argv[1])
rows = [json.loads(line) for line in open(sys.argv[2], encoding="utf-8") if line.strip()]
ask_id = next(row["ask_id"] for row in rows if row.get("type") == "ask")
config = load_config(resolve_config_path(home))
store = SqliteStore(home / "inbox.db")
try:
    outcome = resolve(store, ask_id, now=utcnow(), config=config)
finally:
    store.close()
assert outcome.status == "deny", outcome.status
assert outcome.reason_code == "human_gate_timeout", outcome.reason_code
print("DENY-TIMEOUT")
PY

ft_finalize