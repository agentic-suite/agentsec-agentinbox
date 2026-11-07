# Framework adapter + conformance-kit design — v0.1.0 (M19)

**BLUF:** a framework adapter is thin: a **pause** that creates an ask and a **resume** that reads the recorded
outcome by id. The ask and decision live in the durable store, so a crash between them loses nothing and a replay
does not execute an irreversible tool twice. The **conformance kit** is the admission gate: any integration runs
`agentinbox conformance` against the contract, and a deliberately broken adapter fails it.

- **Milestone:** M19 ([WBS Part 10](../../wbs/v0.1.0/wbs-v0.1.0-part10-adapters-conformance.md), issues #40–#50)
- **Requirements:** E1, E2, E10, D-5 · PRD 16 §E.3, PRD 19, PRD 30 E18 · CUJ-13 · SC-25

---

## 1. Interrupt / resume mapping

| Framework idea | Inbox mechanism |
|---|---|
| `interrupt(payload)` | `HumanGate.interrupt(ask)` → `POST /v1/asks` → durable `ask_id` is the resume token |
| graph state checkpoint | the ask is durable; the host persists the `ask_id` in its checkpoint |
| `Command(resume=decision)` | `HumanGate.resume(ask_id)` → `GET /v1/asks/{id}?wait=` → `resolve/1.0` |
| graph re-entry | `HumanGate.decision(ask_id)` returns `approve` only for `status=allow` |

`decision()` maps pending/deny/expiry/flood to `deny`; only an explicit allow resumes as approval. The adapter
never answers, never mints a claim, and never decides.

## 2. Crash-resume durability (SC-25)

1. The graph pauses; the ask is in the store.
2. The process dies (`kill -9`). The graph checkpoint (host) and the ask (inbox) both survive.
3. On restart the graph reads its checkpoint, calls `resume(ask_id)`, and gets the recorded outcome (or pending).
4. The tool executes at most once:
   - `ExecutionJournal.claim(ask_id)` records `executing` **before** the action and `complete` after;
   - a replay after a crash sees `executing`/`done` and refuses to run again;
   - a second resume returns the same outcome (idempotent read).

At-most-once is deliberate for irreversible actions: a crash mid-action is surfaced as uncertain, never blindly
repeated.

## 3. Conformance kit

`agentinbox conformance` (or `run_conformance(config, store_factory=…)`) runs against a **fresh in-memory store**,
so it never touches the live inbox:

| Check | What it proves |
|---|---|
| `config.class` | a class exists to exercise |
| `contract.ask` | a contract-valid ask is ingested |
| `redaction` | a secret in arguments is redacted; the benign command survives |
| `idempotent-ingest` | a duplicate retry coalesces to one ask/id |
| `resolve.pending` | the pending outcome is `deny_ask_pending` |
| `exit-codes` | `0/1/2/3/4/5` are the frozen integers |
| `events` | the event types/payloads match the shipped schema fixture |
| `channels` | terminal/desktop/webhook/ci deliver + authenticate and never decide |
| `producers` | every producer key is a reference, not a literal |

A broken store/adapter makes the report red and the command exits `4`. `--json` emits the same checks for CI.
Third-party adapters add a PRD 19 matrix row by making the kit green in their PR.

## 4. Reference graph

`docs/adapters/langgraph/` ships a minimal graph: a `human_gate` node calls `interrupt`, the adapter creates the
ask, a human answers in any surface, and `Command(resume=decision)` continues. The adapter itself is
framework-neutral (`agentinbox.adapters.langgraph`), so the example is the only LangGraph-specific code.

## 5. Harness recipes

Claude Code `PreToolUse` and Codex CLI wrapper recipes are documented (not bespoke adapters): the hook/wrapper
calls `agentinbox ask --exec`, and the tool is blocked unless the exit is `0`. Honest labels for the M24/M25
matrix: **documented** until field-tested.

## 6. Tests

`tests/adapters/test_langgraph.py` covers interrupt → answer → resume, at-most-once execution, crash-journal
recovery, and restart-by-id. `tests/conformance/` covers a green reference, a broken store, the shipped fixture,
and the CLI.
