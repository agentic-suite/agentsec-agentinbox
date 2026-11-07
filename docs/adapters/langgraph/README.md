# LangGraph `human_gate` example (v0.1.0 · M19)

A minimal graph that pauses for a human decision and resumes with it. The LangGraph-specific code is only the
node + `interrupt`; the adapter (`agentinbox.adapters.langgraph`) is framework-neutral.

## Layout

```text
docs/adapters/langgraph/
  README.md
  graph.py          # the example graph
```

## Flow

```text
build ask → interrupt(payload) → agentinbox ask (durable) → human answers
          → Command(resume=decision) → graph continues
```

- `HumanGate.interrupt(ask)` creates the ask and returns the **ask id**.
- The graph checkpoints that id in its own state.
- The host resumes with the inbox decision (`approve` only for `status=allow`).
- `ExecutionJournal` makes the irreversible tool run at most once, even across a crash.

## Run

```sh
agentinbox init
agentinbox serve            # daemon: channels + scheduler + events
python docs/adapters/langgraph/graph.py
```

Answer in another terminal: `agentinbox inbox`, then `agentinbox answer <ask-id>`.

Requires `langgraph` in the *host* environment; agentinbox itself has no framework dependency.
