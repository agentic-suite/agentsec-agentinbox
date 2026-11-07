# Audit reference (v0.1.0 · M15)

**BLUF:** append-only hash chain + offline-verifiable export. `verify-log` names the first bad seq; there is no
import path.

- Design of record: [`docs/design/v0.1.0/audit.md`](../design/v0.1.0/audit.md)

## `verify-log`

```sh
agentinbox verify-log
# ok: 42 audit entries verify            (exit 0)
# agentinbox: chain verification failed: audit seq 7: entry_hash does not verify  (exit 4)
```

## `export`

```sh
agentinbox export --session sess_… --format jsonl
agentinbox export --ask ask_… --format csv --out /secure/evidence.csv
```

- exactly one of `--session` / `--ask`;
- `--format jsonl` (default) or `csv`;
- `--out` is optional and must be absolute; the file is written `0600`;
- every export appends an `export` audit entry.

### JSONL

| Line | Contains |
|---|---|
| `meta` | contract `export/1.0`, generated time, scope, counts, `authority: "none"` |
| `ask` | the ask fields + the redacted payload (with `_redactions`) |
| `transition` | seq, at, kind, from/to status, principal, channel, claim id, reason, detail |
| `delivery` | delivery id, channel, attempt, status, target, error |
| `audit` | seq, prev_hash, entry_hash, kind, ref_id, at, payload_digest |

### CSV

The same records flattened into `record_type, ask_id, seq, at, kind, from_status, to_status, principal, channel,
claim_id, reason, detail, status, prev_hash, entry_hash, payload_digest`.

## Offline verification recipe

```python
import hashlib, json

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

prev = "0" * 64
for entry in [json.loads(line) for line in open("evidence.jsonl")]:
    if entry["type"] != "audit":
        continue
    assert entry["prev_hash"] == prev
    material = f'{prev}|{entry["seq"]}|{entry["kind"]}|{entry["ref_id"]}|{entry["at"]}|{entry["payload_digest"]}'
    assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_hash"]
    prev = entry["entry_hash"]
```

The export carries everything the recipe needs; no inbox, network, or daemon is involved.

## Retention

```toml
[audit]
retention = "never"   # or "1y", "90d", "7d"
```

On daemon start, detail rows older than the cutoff are pruned and a `retention-pruned` marker records the cutoff
and counts. The chain remains verifiable. Pruned detail is not recoverable locally — keep exports as the archive.

## Read-only posture

`authority: "none"` is written into every export. There is no import command or API; evidence never re-enters as
authority.
