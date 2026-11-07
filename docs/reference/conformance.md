# Conformance kit reference (v0.1.0 · M19)

**BLUF:** `agentinbox conformance` proves an integration honours the contract. It runs against a fresh
in-memory store, never the live inbox.

- Design of record: [`docs/design/v0.1.0/framework-adapters.md`](../design/v0.1.0/framework-adapters.md)

```sh
agentinbox conformance          # human-readable checks
agentinbox --json conformance   # machine-readable checks
```

Exit `0` when every check passes, `4` otherwise (fail closed).

## Checks

| Name | Proves |
|---|---|
| `config.class` | a class is configured |
| `contract.ask` | a contract-valid ask is ingested |
| `redaction` | secrets in arguments are redacted; benign text survives |
| `idempotent-ingest` | a retried ask coalesces to one id |
| `resolve.pending` | pending resolves `deny_ask_pending` |
| `exit-codes` | `0/1/2/3/4/5` are the frozen integers |
| `events` | event types and payloads match the shipped schema |
| `channels` | every channel delivers/authenticates and cannot decide |
| `producers` | producer keys are references |

## JSON

```json
[
  {"name": "contract.ask", "ok": true, "detail": "created ask_…"},
  {"name": "redaction", "ok": true, "detail": "secret redacted, command preserved"}
]
```

## For third-party adapters

Run the kit in your repository's CI. A green run is the evidence for a PRD 19 **conformance-tested** row; a red
run names the failed check. The kit uses the same config and classes as the installation, so it also catches a
broken local config before it reaches a human.
