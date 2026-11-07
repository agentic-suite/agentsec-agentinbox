# Quickstart — first recorded approval in under 5 minutes (v0.1.0)

**BLUF:** install from source, scaffold a private home, put your OS user on the roster, raise an ask
in one terminal and answer it in another. No chat platform, no network, no account.

- Time: **< 5 minutes** (step-tested; the test replays these exact commands)
- Prerequisite: Python 3.11–3.13 on macOS or Linux, and `git`

## 1. Install (about 60 s)

```sh
git clone https://github.com/agentic-suite/agentsec-agentinbox
cd agentsec-agentinbox
make setup
agentinbox --version
```

`make setup` creates `.venv` and installs the package plus dev tools. The runtime itself has **zero
dependencies** beyond the Python standard library.

## 2. Create the home (about 5 s)

```sh
agentinbox init
```

This writes `~/.agentinbox/` (mode `0700`) and a working `~/.agentinbox/config.toml` (mode `0600`).
Set `AGENTINBOX_HOME=/some/absolute/path` (or pass `--home`) to use a different location.

## 3. Put yourself on the roster (about 15 s)

Open `~/.agentinbox/config.toml` and replace `alice` with your OS username (`whoami`):

```toml
[roster.tier-1]
terminal = ["your-username"]
```

Then check the install:

```sh
agentinbox doctor
```

A healthy box prints `ok` lines and exits `0`. Any `fail` exits `4` (fail-closed) and names the fix.

## 4. Raise an ask (terminal 1)

```sh
agentinbox ask --exec "echo hello" --timeout 300
```

The command blocks at the gate. Nothing runs yet. Copy the printed `ask_…` id, or see it from the
other terminal with `agentinbox inbox`.

## 5. Answer it (terminal 2)

```sh
agentinbox inbox
agentinbox answer <ask_id>
```

You get the decision card. Type `a` to approve, then type the action name (`run_command`) when asked
for confirmation. The answer is recorded with your user as the principal and a single-use claim.

Terminal 1 now prints `approved` and runs `echo hello`. A deny (`d`, with a reason) or the TTL
lapsing both leave the action **not executed** — timeout is deny.

## 6. Verify the record

```sh
agentinbox report --json
agentinbox verify-log
```

`report` shows one ask, one answered sample, and the deny rate; `verify-log` proves the hash chain.
`agentinbox export --ask <ask_id> --out "$PWD/export.jsonl"` writes the evidence (mode `0600`).

## What just happened

- `ask` ingested an `ask/1.0` document and waited at the CI-style gate.
- `answer` minted a single-use claim bound to the action, authenticated the OS user, enforced the
  roster, and recorded the approval in the append-only chain.
- `report` is **local only**; nothing left the machine.

## Next

- [Producer guide](../adapters/producer-guide.md): HTTP/CLI/`--exec`, signed adapters, resolve.
- [CLI reference](../reference/cli.md) · [config reference](../reference/config.md).
- [Install as a service / backup / restore](../runbooks/ops.md).
- [Runbooks RB-1..RB-8](../runbooks/).
