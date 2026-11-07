# RB-5 — Config drift / bad reload

**Symptoms:** an operator changed `config.toml`; behavior did not change and the log says the reload was
refused; or a change applied but you need to see exactly what is effective.

**Steps**
1. `agentinbox doctor --explain` — effective class → TTL/roster/ladder/thresholds, with secret
   **references** only.
2. Fix the file; `doctor` names the exact key on error.
3. Reload with `kill -HUP <serve pid>` (or restart). A bad file keeps the last-good config and emits
   `inbox-config-changed(failed)`.
4. Check the config-change trail: digest + changed keys (no values); revert in git if needed.

**Verify:** `doctor` green; `inbox-config-changed` shows the applied digest; no in-flight ask changed.
