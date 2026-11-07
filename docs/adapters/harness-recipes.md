# Harness recipes (v0.1.0 · M19)

**BLUF:** before a bespoke adapter exists, a pre-exec hook is enough. The hook calls
`agentinbox ask --exec "$COMMAND"` and blocks the tool unless the exit is `0`. Labels for the M25 matrix:
**documented** now; field-tested at M24.

- Producer guide: [producer-guide.md](producer-guide.md)
- Adapter template: [adapter-template.md](adapter-template.md)

## Claude Code `PreToolUse`

`harness_hook.py`:

```python
#!/usr/bin/env python3
import json
import subprocess
import sys

event = json.load(sys.stdin)
command = event.get("tool_input", {}).get("command", "")
if not command:
    sys.exit(0)

completed = subprocess.run(
    ["agentinbox", "ask", "--exec", command],
    check=False,
)
# Claude Code blocks the tool on exit 2.
sys.exit(0 if completed.returncode == 0 else 2)
```

`settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "python /absolute/path/harness_hook.py"}
        ]
      }
    ]
  }
}
```

Answer in the terminal (`agentinbox inbox` / `agentinbox answer <id>`). A deny/expiry exits non-zero → Claude Code
does not run the tool.

## Codex CLI wrapper

```sh
#!/usr/bin/env bash
set -u
COMMAND=("$@")
if ! agentinbox ask --exec "${COMMAND[*]}"; then
  echo "blocked by agentinbox" >&2
  exit 1
fi
exec "${COMMAND[@]}"
```

Use the wrapper as the configured command runner. Exit `0` means the human allowed it; the wrapper then executes
the command **once** (the `ask --exec` path already gated it; do not double-run — prefer passing the command to
`ask --exec` directly).

## Caveats

- Hooks are advisory to the harness; the authoritative gate is `agentinbox ask --exec` (or the API). A harness
  that ignores a non-zero hook exit is not gated.
- Prefer passing the exact command to `ask --exec` rather than re-implementing execution in the wrapper.
- Label these **documented** until a field test records them against the real harness (M24).
