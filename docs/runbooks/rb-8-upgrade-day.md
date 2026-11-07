# RB-8 — Upgrade day

**Symptoms:** a new release is ready; the daemon must pick up an old store without losing pending asks.

**Steps**
1. Pre-upgrade backup: `agentinbox doctor --backup /secure/pre-upgrade.tar` (chain-verified).
2. Stop the daemon (SIGTERM: accepts no work, flushes, closes).
3. Install the new release. Open the store with `agentinbox doctor`; the schema migrates forward in one
   transaction.
4. Run `agentinbox verify-log` and `agentinbox doctor`; both must be green.
5. Start the daemon; it adopts pending asks and fires overdue timers exactly once.
6. Re-run `agentinbox conformance` and `python -m agentinbox.packs`.

**Downgrade is refused loudly** (`schema` red, `SchemaVersionError`). Restore the pre-upgrade backup
into a fresh home rather than forcing a downgrade.

**Verify:** `doctor`, `verify-log`, conformance, packs green; a new ask reaches a decision; the
compatibility checks in `tests/ops/test_compat.py` match the release.
