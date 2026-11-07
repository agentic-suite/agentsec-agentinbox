# Temporal signal recipe (v0.1.0)

Use a Temporal workflow activity to raise the ask and a signal/query to carry the human decision back.
The inbox is the record; Temporal is the orchestration.

```python
from temporalio import activity, workflow

@activity.defn
async def raise_gate(ask_body: dict) -> dict:
    # POST /v1/asks with the API token, then GET /v1/asks/<id>?wait=25s until resolved.
    ...

@workflow.defn
class GatedAction:
    def __init__(self) -> None:
        self.decision: str | None = None

    @workflow.signal
    def human_decision(self, decision: str) -> None:
        self.decision = decision

    @workflow.run
    async def run(self, ask_body: dict) -> str:
        ask = await workflow.execute_activity(
            raise_gate, ask_body, start_to_close_timeout=timedelta(seconds=30)
        )
        await workflow.wait_condition(lambda: self.decision is not None)
        return self.decision  # "approve" only; anything else denies at the activity boundary
```

Rules:
- The workflow must **not** treat a pending/expired read as approval; map `allow` only.
- Use resolve's `retry_after`/`rescope_hint` to route a denial back to the agent.
- A resumed workflow re-reads the ask by id; the decision is durable in the inbox.

**Verify:** `agentinbox conformance` and `python -m agentinbox.packs` green.
