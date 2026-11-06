# Store reference (v0.1.0 · M1)

**BLUF:** `AskStore` is the only path the core uses to read or write state. There are two drivers in
v0.1.0 — `sqlite` (reference, on-disk) and `memory` (tests/embedded) — and both must pass the in-repo
conformance suite. A third-party driver is admitted only if it declares the current conformance version
**and** passes that suite; otherwise it is refused at load.

- Design of record: [`docs/design/v0.1.0/store.md`](../design/v0.1.0/store.md)
- WBS: [Part 1](../wbs/v0.1.0/wbs-v0.1.0-part1-foundation-store.md) · Requirements: E11, E2, E10

## Using the interface

```python
from agentinbox.store import AskRecord, AskStatus, TransitionRecord
from agentinbox.store.loader import load_store

store = load_store("sqlite", home=Path("~/.agentinbox").expanduser())
result = store.create_or_get_by_identity(ask)          # idempotent by identity + session
store.cas_status(ask.ask_id, expected=AskStatus.PENDING,
                 new=AskStatus.APPROVED, transition=transition)  # exactly one winner
store.consume_claim(claim_id, ask_id=ask.ask_id, at=now)          # atomic, single-use
store.append_event(transition)                          # per-ask seq + chained audit entry
```

| Method | Guarantee |
|---|---|
| `create_or_get_by_identity` | dedupe inside the window → same ask + `deduplicated` transition |
| `get` | `None` for unknown; never guesses |
| `cas_status` | status change + transition + audit entry in one atomic write |
| `issue_claim` / `consume_claim` | hash only; consumption is atomic and single-use |
| `list_pending` | all pending asks ordered by `expires_at` (overdue included) |
| `append_event` | per-ask seq and global gapless audit seq, hash-chained |
| `export_session` | read-only snapshot of asks, transitions, claims |

Capabilities are declared, not assumed:

```python
from agentinbox.store import require_capability

require_capability(store, "multi_writer")   # raises CapabilityError for sqlite/memory
```

| Driver | single_writer | multi_writer | cluster_safe |
|---|---|---|---|
| `sqlite` | ✅ | ❌ | ❌ |
| `memory` | ✅ | ❌ | ❌ |

## On-disk contract

- Home directory `0700`; database `0600` (tightened on open).
- SQLite WAL, `synchronous=FULL`, `busy_timeout` for concurrent processes.
- Schema version 2: `asks`, `transitions`, `claims`, `deliveries`, `floods`, `audit`, `schema_version`.
- Forward migrations run on open; a store **newer** than the build raises `SchemaVersionError` — downgrade is
  refused loudly, never guessed.
- `entry_hash = sha256(prev_hash | seq | kind | ref_id | at | payload_digest)`; genesis `prev_hash` is 64 zeros.
  `verify_chain()` / `verify_audit_chain()` recompute it.

## Writing a third-party driver

1. Implement the `AskStore` protocol (all nine methods, including `close`).
2. Put the seven semantics under test with the in-repo suite — copy `tests/store/conformance.py` into your CI
   and run every check against your driver.
3. Export a `DriverSpec` as your entry point target:

   ```python
   # my_driver/__init__.py
   from agentinbox.store import CONFORMANCE_VERSION, DriverSpec, StoreCapabilities

   DRIVER = DriverSpec(
       name="mydriver",
       conformance_version=CONFORMANCE_VERSION,   # only the version you actually passed
       capabilities=StoreCapabilities(single_writer=False, multi_writer=True),
       factory=open_my_driver,                    # (home: Path) -> AskStore
   )
   ```

   ```toml
   [project.entry-points."agentinbox.store"]
   mydriver = "my_driver:DRIVER"
   ```

4. `load_store("mydriver", required_capabilities=("multi_writer",))` checks the declared capabilities
   **before** constructing anything. A stale `conformance_version`, a missing spec, or an unknown name is
   refused with `DriverNotAdmittedError`.

Honesty rule: do not claim a capability you cannot prove. The core refuses unsupported configurations at
load instead of discovering them mid-decision.
