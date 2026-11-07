# Terminal channel reference (v0.1.0 · M7)

**BLUF:** `agentinbox answer <id>` blocks on the card and records an authenticated answer; when stdin is not
a TTY it prints one JSON result and exits `5` — it never approves.

- Design: [`docs/design/v0.1.0/terminal.md`](../design/v0.1.0/terminal.md)
- Requirements: R2, E4

## Commands

```sh
agentinbox inbox                 # list pending asks (exit 5 if any, 0 if none)
agentinbox answer <id>           # interactive: a / d / ? / q
agentinbox answer <id> --approve # still requires a TTY; scripts get exit 5
agentinbox answer <id> --deny --reason "missing rollback plan"
agentinbox answer <id> --approve --as alice   # only if allow_as is configured
```

## Keys

| Key | Effect |
|---|---|
| `a` | approve (irreversible requires typing the action name) |
| `d` | deny (a reason is required when the class demands one) |
| `?` | re-print the card |
| `q` | leave pending (exit `5`, no claim consumed) |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | approved |
| `2` | denied |
| `3` | expired / timeout (deny class) |
| `4` | unavailable / rejected answer (no decision recorded) |
| `5` | left pending (also the non-interactive result) |

## Principal

Default: OS user. `--as NAME` is refused unless `[channels.terminal] allow_as = true`; an assumed principal is
recorded in the answer transition (`assumed_principal: true`) and shown in the CLI output.

## Non-interactive mode

```sh
echo "" | agentinbox answer <id> --approve
# {"contract": "resolve/1.0", "status": "pending", ...}   exit 5
```

No prompt, no claim consumption, no approval. This is the D-5 guarantee: scripts cannot approve.

## Config

```toml
[channels.terminal]
enabled = true
allow_as = false   # true only where assumed principals are an explicit, reviewed choice
```
