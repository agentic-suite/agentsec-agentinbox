# Wave-0 release demo — evidence

This directory is the committed output of the M33 33.5 release smoke test
(issue #116). It demonstrates the ecosystem path end-to-end on the release
candidate:

1. **agentpolicy** evaluates the Replit destructive rule (`drop_database` in
   production): **deny** (`deny_critical_op`).
2. A production write (`deploy_service`) **escalates** (`escalate_prod_write`)
   and is turned into an `ask/1.0` by the M18 agentpolicy reference adapter.
3. agentinbox raises the ask, delivers the terminal card and a desktop
   notification, and the release owner **denies with a reason** in the terminal.
4. `resolve/1.0` returns **deny**, the agentwatch events carry the join keys,
   `export --session` produces the evidence export, and `verify-log` verifies
   the audit chain offline.

## Files

| File | Content |
|---|---|
| `transcript.txt` | human-readable run: decisions, card, delivery, deny, resolve, events, verify |
| `events.jsonl` | agentwatch event projection (`ask-raised`, two `ask-delivered`, `ask-answered`) |
| `export.jsonl` | session export, including the audit chain |
| `environment.json` | agentinbox/agentpolicy versions, Python, platform, user, session |
| `checksums.txt` | SHA-256 for every committed file above |

## Reproduce

The demo needs the local agentpolicy checkout and its virtualenv (the policy
engine has dependencies agentinbox does not ship):

```sh
PYTHONPATH="$PWD" ../agentpolicy/.venv/bin/python scripts/release/wave0_demo.py
```

Set `AGENTPOLICY_SRC` if the checkout is not at `../agentpolicy/src`. The script
uses only loopback/local paths, sends one real desktop notification via the
platform notifier, and writes the files above. It does not write the
hand-maintained field-test report.

## Honest scope

This is a **release smoke test**, not a new field test. The M32 report remains
the field-test evidence. The harness rows for Claude Code/Codex CLI remain
`documented / capture-verified`; only the agentpolicy reference path is promoted
to `field-tested` by this demo. The demo's environment/transcript are the
citation for that label.
