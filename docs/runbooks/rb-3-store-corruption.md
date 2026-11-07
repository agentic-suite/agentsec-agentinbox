# RB-3 — Store corruption

**Symptoms:** `doctor` `schema`/`chain` red or `verify-log` names a bad seq; the daemon refuses to start.

**Steps**
1. Stop the daemon so nothing writes.
2. Quarantine a copy: `cp -p ~/.agentinbox/inbox.db /secure/quarantine-$(date +%s).db`.
3. `agentinbox verify-log` — note the first bad seq. Do **not** edit the chain.
4. Restore the last verified backup into a fresh home: `doctor --restore <tar>` (aborts on a bad chain).
5. Start the daemon; overdue pending asks expire once. Unresolved asks must be re-asked by producers.

**What is never lost:** delivered decisions (export them before quarantine if possible).
**What can be lost:** pending asks and detail pruned by retention; the chain marker records pruning.

**Verify:** `verify-log` over the restored chain; `doctor` green; `report --json` reads the restored data.
