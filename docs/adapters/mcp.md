# MCP ask-gating recipe (v0.1.0)

Gate an MCP tool call through agentinbox: create an ask, wait for the resolve, and return the decision
to the MCP server. The inbox records/returns; the MCP server enforces.

```python
import json, subprocess, time

def gate_mcp_tool(tool: str, arguments: dict) -> dict:
    ask = {
        "contract": "ask/1.0",
        "tool": tool,
        "action": "invoke",
        "arguments": arguments,
        "agent_id": "agent://mcp-server",
        "session_id": "mcp-session-1",
        "environment": "local",
        "class": "irreversible",
        "reason_code": "human_gate_required",
        "criticality": "normal",
        "requested_by": "agent://mcp-server",
        "context": {},
        # expires_at must be in the future; compute it in real code
        "action_identity": "sha256:...",  # compute_action_identity(...)
        "expires_at": "2026-11-07T12:05:00.000000Z",
    }
    created = subprocess.run(
        ["agentinbox", "ask", "--file", "-"], input=json.dumps(ask),
        capture_output=True, text=True,
    )
    # `ask --file` waits for the decision; exit 0 = allow, 2/3/4 = deny/expired/unavailable.
    return {"allowed": created.returncode == 0, "output": created.stdout}
```

Rules:
- `exit 0` is the **only** allow; treat `2/3/4` as deny at the MCP tool boundary.
- Never let the model answer; the claim + principal come from the human channel.
- Use a bounded wait (`--timeout`) shorter than the tool budget.

**Verify:** `agentinbox conformance` must be green against the same home, then run
`python -m agentinbox.packs` (the spoof/injection/flood packs).
