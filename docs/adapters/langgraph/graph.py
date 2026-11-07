"""Minimal LangGraph human_gate example (M19).

Run with LangGraph installed in the host environment:

    agentinbox init
    agentinbox serve
    python docs/adapters/langgraph/graph.py
"""

from __future__ import annotations

import os

from agentinbox.adapters.agentpolicy import AgentPolicyClient
from agentinbox.adapters.langgraph import ExecutionJournal, HumanGate
from agentinbox.contract import compute_action_identity

try:  # the host supplies LangGraph; agentinbox itself is framework-free
    from langgraph.graph import END, StateGraph
    from langgraph.types import Command, interrupt
except ImportError as exc:  # pragma: no cover - documentation example
    raise SystemExit("install langgraph to run this example") from exc


client = AgentPolicyClient(
    url=os.environ.get("AGENTINBOX_URL", "http://127.0.0.1:8377"),
    token=os.environ["AGENTINBOX_TOKEN"],
    adapter_key=os.environ["AGENTINBOX_ADAPTER_KEY"],
    principal=os.environ.get("USER"),
)
gate = HumanGate(client, journal=ExecutionJournal(".agentinbox-executions.json"))


def build_ask(state: dict[str, str]) -> dict[str, object]:
    arguments = {"command": state["command"]}
    return {
        "contract": "ask/1.0",
        "action_identity": compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        "tool": "shell",
        "action": "run_command",
        "arguments": arguments,
        "agent_id": "agent://langgraph-example",
        "session_id": "sess_langgraph_example",
        "environment": "local",
        "data_class": "unknown",
        "class": "irreversible",
        "reason_code": "human_gate_required",
        "policy_ref": {
            "rule_id": "langgraph-human-gate",
            "policy_version": "v0.1.0",
            "clause": "example",
        },
        "criticality": "normal",
        "requested_by": "langgraph-example",
        "expires_at": state["expires_at"],
        "context": {},
    }


def human_gate(state: dict[str, str]) -> Command:
    ask_id = gate.interrupt(build_ask(state))
    # LangGraph pauses here; the host resumes with Command(resume=decision).
    decision = interrupt({"ask_id": ask_id})
    if decision != "approve":
        return Command(goto=END)
    gate.run_once(ask_id, lambda: print("would execute:", state["command"]))
    return Command(goto=END)


def main() -> None:
    graph = StateGraph(dict)
    graph.add_node("human_gate", human_gate)
    graph.set_entry_point("human_gate")
    compiled = graph.compile()
    compiled.invoke({"command": "echo gated", "expires_at": "2030-01-01T00:00:00.000000Z"})


if __name__ == "__main__":  # pragma: no cover
    main()
