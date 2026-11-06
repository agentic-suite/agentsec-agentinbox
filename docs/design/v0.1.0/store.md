# AskStore design — v0.1.0 (M1)

**BLUF:** The AskStore is the **only** way the core touches state. It is a typed contract with seven
non-negotiable semantics, implemented by a SQLite reference driver (WAL, fsync'd, `0600`) and an in-memory
driver that passes the same conformance suite. Drivers must **declare** their capabilities, and the core
refuses a configuration a driver cannot guarantee. Third-party drivers are admitted only by passing the
in-repo conformance suite.

- **Milestone:** M1 ([WBS Part 1](../../wbs/v0.1.0/wbs-v0.1.0-part1-foundation-store.md), issues #17–#28)
- **Requirements:** E11, E2, E10 · PRD 15 §entities/§storage · PRD 16 §D · PRD 13 N-8..N-12
- **Out of scope:** scheduler math (M4), full entity surface (M3), audit export/verify UX (M15). M1 fixes the
  contract, the schema, and the truth-layer semantics those milestones build on.

---

## 1. Interface (frozen in M1)

```python
class AskStore(Protocol):
    capabilities: StoreCapabilities

    def create_or_get_by_identity(self, ask: AskRecord, *, dedupe_window_s: int = 900) -> CreateResult: ...
    def get(self, ask_id: str) -> AskRecord | None: ...
    def cas_status(self, ask_id: str, *, expected: AskStatus, new: AskStatus,
                   transition: TransitionRecord) -> bool: ...
    def issue_claim(self, claim: ClaimRecord) -> None: ...
    def consume_claim(self, claim_id: str, *, ask_id: str, at: datetime) -> bool: ...
    def list_pending(self, *, now: datetime, limit: int = 100) -> list[AskRecord]: ...
    def append_event(self, transition: TransitionRecord) -> AuditEntry: ...
    def export_session(self, session_id: str) -> SessionExport: ...
    def close(self) -> None: ...
```

| Method | Contract |
|---|---|
| `create_or_get_by_identity` | Dedupe key = `action_identity` + `session_id` **within the window**. First call inserts (appends a `created` transition); a duplicate inside the window returns the **existing** ask (`created=False`) and appends a `deduplicated` transition. Outside the window a new ask is minted. |
| `get` | `None` for unknown; never guesses. Status is stored, not inferred (expiry derivation is M3/M4). |
| `cas_status` | Compare-and-set **and** transition+audit append are one atomic write. Exactly one concurrent caller sees `True`; losers get `False` and write nothing. |
| `issue_claim` | Inserts a claim record (hash only — the secret never reaches the store). Duplicate `claim_id` is an error. |
| `consume_claim` | Atomic single-use: `True` exactly once for `(claim_id, ask_id)`; expired/revoked/already-used → `False`; never raises for a lost race. |
| `list_pending` | All asks in `pending` ordered by `expires_at`, **including overdue ones** — the scheduler derives due work from persisted instants, and a restart sees exactly the same set. |
| `append_event` | Appends a transition (per-ask seq) and an audit entry (global gapless seq, hash-chained) atomically. |
| `export_session` | Read-only snapshot of the session's asks, transitions, and claims. |

`TransitionRecord` fields: `ask_id`, `seq` (assigned by the store; caller passes 0), `at`, `kind`,
`from_status`, `to_status`, `detail`, `principal`, `channel`, `claim_id`, `reason`.

## 2. The seven semantics and how they are proven

| # | Semantics | Mechanism | Conformance test |
|---|---|---|---|
| 1 | Idempotent create | dedupe key + window check in one transaction | 3× create → one ask, `created` once, `deduplicated` twice |
| 2 | CAS, first-answer-wins | `UPDATE ... WHERE status = expected` inside a write transaction | N threads race `pending→approved`; exactly one wins |
| 3 | Single-use claims | conditional `UPDATE ... WHERE consumed_at IS NULL` | consume twice → second returns `False` |
| 4 | Gapless audit seq | audit insert inside the same serialized write; `prev_hash` chains from the last entry | N concurrent appends → seqs `1..N`, no gaps, each `prev_hash` matches |
| 5 | Exactly-once recovery | absolute instants persisted; `list_pending` deterministic | reopen the same store → identical pending set; seq continues |
| 6 | Durable commit before ack | SQLite `synchronous=FULL`, WAL, commit before return | child process `os._exit(0)` after create → parent sees the ask |
| 7 | Capability flags | `StoreCapabilities(single_writer, multi_writer, cluster_safe)` + `require_capability` | `sqlite`/`memory` refuse `multi_writer`/`cluster_safe`; a config asking for them fails closed |

A deliberately broken driver (e.g. a claim consumer that never checks `consumed_at`) **must fail** the same
suite — the suite is the admission gate, not a rubber stamp.

## 3. Capabilities

| Driver | `single_writer` | `multi_writer` | `cluster_safe` |
|---|---|---|---|
| `sqlite` | ✅ | ❌ | ❌ |
| `memory` | ✅ | ❌ | ❌ |

`require_capability(store, "multi_writer")` raises `CapabilityError`; the loader/core calls it **before**
serving a single request (fail-closed driver selection, never a runtime surprise).

## 4. Schema (SQLite reference, version 2)

```sql
schema_version(version INTEGER NOT NULL)

asks(
  ask_id TEXT PRIMARY KEY,
  action_identity TEXT NOT NULL,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,          -- UTC ISO-8601, always suffixed Z
  expires_at TEXT NOT NULL,
  payload TEXT NOT NULL,             -- canonical JSON; already redacted (M2)
  dedupe_key TEXT NOT NULL,          -- action_identity + '\n' + session_id
  decided_at TEXT
)
INDEX pending-by-expiry (status, expires_at)
INDEX asks-by-session (session_id)
INDEX asks-by-agent (agent_id)

transitions(
  ask_id TEXT NOT NULL, seq INTEGER NOT NULL, at TEXT NOT NULL,
  kind TEXT NOT NULL, from_status TEXT, to_status TEXT,
  principal TEXT, channel TEXT, claim_id TEXT, reason TEXT,
  detail TEXT NOT NULL,              -- canonical JSON, redacted
  PRIMARY KEY (ask_id, seq)
)
INDEX transitions-by-ask-seq

claims(
  claim_id TEXT PRIMARY KEY, ask_id TEXT NOT NULL, channel TEXT NOT NULL, tier TEXT,
  token_hash TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL,
  consumed_at TEXT, revoked_at TEXT
)
INDEX claims-by-ask

deliveries(
  delivery_id TEXT PRIMARY KEY, ask_id TEXT NOT NULL, channel TEXT NOT NULL,
  target TEXT, attempt INTEGER NOT NULL, status TEXT NOT NULL, at TEXT NOT NULL,
  error TEXT
)

floods(
  flood_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, session_id TEXT,
  window_start TEXT NOT NULL, window_end TEXT NOT NULL,
  denied_count INTEGER NOT NULL, first_ask_id TEXT, at TEXT NOT NULL
)

audit(
  seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL,
  kind TEXT NOT NULL, ref_id TEXT NOT NULL, at TEXT NOT NULL, payload_digest TEXT NOT NULL
)
```

`entry_hash = sha256(prev_hash | seq | kind | ref_id | at | payload_digest)` — content-addressed, so the chain
verifies on any driver. The genesis `prev_hash` is 64 zeros.

**File rules:** home `0700`, database `0600` (created with `os.open(..., 0o600)` semantics, re-tightened on
open), WAL + `synchronous=FULL`, `foreign_keys=ON`.

## 5. Migrations & versioning

- `SCHEMA_VERSION = 2` in code. Opening a store **forward-migrates** one version at a time inside a
  transaction.
- The version table is written only after all statements of a step succeed.
- A store whose version is **greater** than the code's raises `SchemaVersionError` ("downgrade is refused
  loudly") — it never guesses and never truncates.
- v1 → v2 adds `asks.decided_at`; the fixture proves an old row survives the upgrade.

## 6. Driver admission (entry points)

```toml
[project.entry-points."agentinbox.store"]
sqlite = "agentinbox.store.sqlite:SqliteStore"
memory = "agentinbox.store.memory:MemoryStore"
```

`load_store(name, entry_points=..., required_capabilities=...)`:

1. resolve the entry point in group `agentinbox.store`; unknown name → `DriverNotAdmittedError`;
2. the entry point must load a `DriverSpec` (`name`, `conformance_version`, `capabilities`, `factory`);
   require `conformance_version == agentinbox.store.CONFORMANCE_VERSION` — a driver that has not passed
   **this** suite version is refused (honesty rule, PRD 19);
3. capability requirements are checked against the **spec** before construction, so an unsupported
   configuration fails closed at load and no partial store is created;
4. construct the driver via `spec.factory(home)`; construction errors are surfaced, never retried into a
   memory fallback.

## 7. Tests (in-repo truth)

| File | Covers |
|---|---|
| `tests/store/conformance.py` | the reusable semantic suite (7 sections) |
| `tests/store/test_sqlite.py` | SQLite-specific: file modes, WAL, crash-durability subprocess |
| `tests/store/test_memory.py` | memory parity via the same suite |
| `tests/store/test_broken_driver.py` | a broken driver fails the suite |
| `tests/store/test_migrations.py` | v1 fixture migrates; downgrade refuses loudly |
| `tests/store/test_loader.py` | entry-point admission, unknown/unconformant driver refusal, capability refusal |

Coverage is enforced ≥95% on `agentinbox/store/**` at the M1 gate only.
