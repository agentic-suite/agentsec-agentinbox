# Adapter template (v0.1.0 · M19)

**BLUF:** an adapter is a thin translation between a framework's pause/resume and the inbox contract. Keep it
boring: create an ask, carry the id, read the outcome. The conformance kit is the acceptance gate.

- Pattern design: [`docs/design/v0.1.0/framework-adapters.md`](../design/v0.1.0/framework-adapters.md)
- Kit: [`docs/reference/conformance.md`](../reference/conformance.md)

## Must

- Create a contract-valid `ask/1.0` (or use `agentinbox ask --file` / the HTTP API).
- Persist the `ask_id` in the framework's own checkpoint/state.
- Resume by id: read `resolve/1.0`; treat only `status=allow` as approval.
- Make irreversible actions at-most-once (`ExecutionJournal` or the framework's idempotency).
- Handle `deny_ask_pending` (poll), `human_gate_timeout` (rescope), `ask_flood_throttled` (wait
  `retry_after`), `deny_action_identity_mismatch` (do not retry the same id).
- Run `agentinbox conformance` in CI and publish the result.

## Must never

- Answer an ask, mint a claim, or call the verifier — adapters produce asks; humans answer.
- Treat a pending/deny/expiry as approval, or retry a denied action automatically.
- Parse or execute `rescope_hint` (advisory text, not policy).
- Claim a PRD 19 row without a green kit.

## Suggested structure

```text
my-harness-agentinbox/
  pyproject.toml
  my_adapter/
    __init__.py        # pause(payload) -> ask_id ; resume(ask_id) -> decision
    mapping.py         # framework payload <-> ask/1.0
  tests/
    test_roundtrip.py  # pause -> answer (fixture) -> resume -> exactly-once
    test_conformance.py# run the kit against the reference config
  docs/
    README.md          # setup, honest limits, kit result
```

The kit itself lives in agentinbox; an adapter repo only needs to call it and assert a green report.

## Review checklist

- [ ] kit green (`agentinbox conformance`)
- [ ] no answer/claim code in the adapter
- [ ] ask id persisted; resume by id works after a restart
- [ ] exactly-once execution evidenced by a test
- [ ] honest labels (documented vs conformance-tested) for the matrix
