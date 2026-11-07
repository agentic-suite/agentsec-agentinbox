# Runbook — operations (v0.1.0 · M21)

Covers install-as-service, backup/restore, upgrade day, reporting, and the offline day. Everything
here runs as the operator's own user; no step requires root.

## 0. Baseline health

```sh
agentinbox doctor                     # exit 0 = green; 4 = red
agentinbox --home "$HOME/.agentinbox" doctor --explain
agentinbox verify-log
agentinbox report --json
```

`doctor` is the single red/green surface: `platform`, `home`, `config`, `desktop`, `offline`,
`store-path`, `schema`, `chain`, `spool`, `keys`, `clock`, `clock-skew`. Any `fail` exits `4`.

## 1. Install / start / stop the daemon

```sh
agentinbox serve --install
# macOS
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.agentsec.agentinbox.plist
launchctl kickstart -k gui/$(id -u)/com.agentsec.agentinbox
# Linux
systemctl --user daemon-reload
systemctl --user enable --now agentinbox
```

Stop with `SIGTERM` (`launchctl kill TERM gui/$(id -u)/com.agentsec.agentinbox`,
`systemctl --user stop agentinbox`). The API closes first, the event sink flushes, and the store
closes cleanly. A waiting `gate` that started while the daemon was alive exits `4`.

Restart adopts pending asks: persisted deadlines are recomputed and overdue asks expire once. No
pending ask is lost.

## 2. Back up (safe while running)

```sh
agentinbox doctor --backup /secure/agentinbox-$(date +%F).tar
```

Keep the archive `0600`. It contains no resolved secrets, no `api-token`, and no spool — restore
re-resolves `env:`/`file:` references from the target machine. The backup refuses a corrupt chain.

## 3. Restore (fresh home)

```sh
export AGENTINBOX_HOME=/fresh/agentinbox
agentinbox init
agentinbox doctor --restore /secure/agentinbox-2026-11-07.tar
agentinbox verify-log
agentinbox doctor
```

The restore stages, verifies the manifest and chain, then installs. **A chain mismatch aborts and
the destination is untouched.** Overdue pending asks expire once; approved/denied decisions are
preserved. Rotate/confirm key references on the new host (`doctor` keys check).

## 4. Upgrade day

1. `agentinbox doctor --backup /secure/pre-upgrade.tar`
2. Stop the daemon.
3. Install the new release, then `agentinbox doctor` — the store migrates forward on open.
4. `agentinbox verify-log` and `agentinbox doctor` must be green.
5. Start the daemon; it adopts pending asks.

**Downgrade is refused loudly** (`doctor` schema red, `SchemaVersionError`). Restore the pre-upgrade
backup into a fresh home instead of forcing a downgrade.

## 5. Metrics review

```sh
agentinbox report --json > /secure/report-$(date +%F).json
```

Read `response_time_s.p50/p99`, `expiries`, `escalation_firings`, `flood_events`,
`answer_rejected_causes`, and `deny_rate_by_class`. The artifact is local-only; share it by choice.
A deny rate near 0% on irreversible asks is a rubber-stamp signal, not a success.

## 6. Offline day (CUJ-12 / SC-26)

1. Disable external channels: `[channels.webhook] enabled = false` (the scaffold default).
2. Drop the network.
3. Run: `init` → `ask`/`ingest` → terminal answer → `gate` → `export` → `verify-log` → `report` →
   `doctor`.

`doctor` shows `offline: ok offline-complete`. Local paths are complete; the only network code is
the explicitly enabled webhook adapter and the producer-side agentpolicy client.

## 7. Common failures

| Symptom | Check | Action |
|---|---|---|
| `doctor` chain red | `verify-log` | quarantine a copy; restore the last verified backup (RB-3) |
| `doctor` schema red | version skew | install the matching release or restore a backup; never force a downgrade |
| `gate` exits 4 | `serve.lock` / daemon state | restart the daemon; a stale lock means the daemon died |
| restore aborts | chain mismatch | the archive is corrupt or tampered; use another backup |
| offline warning | `doctor` `offline` | disable the named external channel for the offline window |
