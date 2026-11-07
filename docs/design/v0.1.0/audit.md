# Audit chain design — v0.1.0 (M15)

**BLUF:** the record an auditor trusts is append-only and hash-chained. Every transition, delivery, flood window,
and export appends an `AuditEntry` (`seq`, `prev_hash`, `entry_hash` over canonical material). `verify-log`
recomputes the chain and names the first bad seq; a corrupted row is **detected, not skipped**. `export` emits
ordered evidence (JSONL/CSV) with the chain included, verifiable offline. Retention prunes detail rows and appends
a chain marker, so verification still passes.

- **Milestone:** M15 ([WBS Part 8](../../wbs/v0.1.0/wbs-v0.1.0-part8-parity-audit.md), issues #271–#281)
- **Requirements:** R5, E11, E12, D-10 · PRD 15 §integrity, PRD 22 §D · CUJ-10 · SC-20

---

## 1. Chain construction

```text
entry_hash = sha256(prev_hash | seq | kind | ref_id | at | payload_digest)
payload_digest = sha256(canonical_json(payload))
```

`seq` is gapless from `1`; `prev_hash` is the previous `entry_hash` (`GENESIS_HASH = "0"*64` for the first).
The store assigns `seq` inside the same transaction as the row it records, so concurrent appends cannot gap.

| kind | ref_id | payload |
|---|---|---|
| `transition` | ask id | the transition detail |
| `delivery` | ask id | delivery id/channel/attempt/status/target/error |
| `flood` | flood id | agent/session/window/count/first ask |
| `export` | session/ask id | format, scope, record count |
| `retention-pruned` | `retention` | cutoff, deleted transition/delivery counts |

## 2. Verification

`agentinbox verify-log` recomputes every hash in order and checks seq continuity and `prev_hash` linkage. The
first mismatch raises `ChainHashMismatch("audit seq N: …")`, and the command exits `4`. A tampered payload,
deleted row (seq gap), or broken link is detected by its exact seq. Verification needs no network and no daemon.

## 3. Export

`agentinbox export --session ID|--ask ID [--format jsonl|csv] [--out PATH]`:

- **meta** first: `contract: export/1.0`, generated time, scope, counts, `authority: "none"`;
- **asks** (payload includes `_redactions` receipts), then **transitions** (principals, channels, reason codes,
  details), then **deliveries**, then the **audit** entries whose `ref_id` is in scope, in seq order;
- exports are written on request only; `--out` must be absolute and the file is `0600`;
- the export itself appends an `export` audit entry.

The chain rows carry `seq`, `prev_hash`, `entry_hash`, `payload_digest`, so an offline verifier can recompute the
chain from the JSONL alone (using the documented hash construction). CSV carries the same chain columns.

## 4. Retention

`[audit] retention = "never" | "1y" | "<n>d"` (default `never`). `serve` applies the policy: detail rows
(transitions/deliveries) older than the cutoff are deleted and a `retention-pruned` marker is appended to the
chain, recording the cutoff and counts. The chain itself remains intact and verifiable. **Honest limit:** pruned
detail cannot be reconstructed locally; the audit entries remain, and exports taken before pruning are the
archive. A marker whose payload records the cutoff is the boundary evidence.

## 5. Read-only posture (D-10)

Evidence leaves; it never re-enters as authority. There is no `import` command, no `import_*` API, and the
export meta says `authority: "none"`. A negative test pins both. Re-importing an export would have to be a new
producer submit subject to ingest, not a restore of trust.

## 6. Tests

`tests/audit/` covers delivery/flood/export chain entries, tamper detection by seq, JSONL/CSV shapes, the export
audit entry, retention markers/verification, and the no-import posture. `tests/cli/test_audit_cli.py` pins the
CLI and tamper exit codes.
