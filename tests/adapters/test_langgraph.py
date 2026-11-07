"""LangGraph-pattern gate: interrupt/resume, crash resume, at-most-once execution (M19)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from agentinbox.adapters.langgraph import ExecutionJournal, HumanGate
from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.resolve import resolve
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
    )


class LocalClient:
    """The adapter's client over the local store (the reference transport in tests)."""

    def __init__(self, store) -> None:  # type: ignore[no-untyped-def]
        self.store = store

    def create(self, ask) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        result = ingest(
            dict(ask),
            store=self.store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )
        return {"ask_id": result.ask.ask_id, "status": result.ask.status.value}

    def resolve(
        self,
        ask_id: str,
        *,
        wait: float = 30,
        action_identity: str | None = None,
    ) -> dict[str, Any]:
        del wait
        return resolve(
            self.store,
            ask_id,
            now=NOW,
            config=config(),
            action_identity=action_identity,
        ).to_dict()


def approve(store, ask_id: str) -> None:
    ask = store.get(ask_id)
    assert ask is not None
    minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)
    AnswerVerifier(store, config(), now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=ask_id,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal="alice",
            channel="terminal",
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )


def test_interrupt_answer_resume(store) -> None:  # type: ignore[no-untyped-def]
    gate = HumanGate(LocalClient(store))

    ask_id = gate.interrupt(payload())
    assert gate.decision(ask_id, wait=0) == "deny"  # pending reads as deny, never allow

    approve(store, ask_id)
    assert gate.resume(ask_id, wait=0)["reason_code"] == "allow_ask_approved"
    assert gate.decision(ask_id, wait=0) == "approve"


def test_execution_is_at_most_once(store, tmp_path) -> None:  # type: ignore[no-untyped-def]
    journal = ExecutionJournal(tmp_path / "executions.json")
    gate = HumanGate(LocalClient(store), journal=journal)
    ask_id = gate.interrupt(payload())
    approve(store, ask_id)
    runs = []

    assert gate.run_once(ask_id, lambda: runs.append(1)) is True
    assert gate.run_once(ask_id, lambda: runs.append(1)) is False
    assert runs == [1]
    assert journal.state(ask_id) == "done"


def test_a_crash_during_execution_is_not_replayed(store, tmp_path) -> None:  # type: ignore[no-untyped-def]
    journal = ExecutionJournal(tmp_path / "executions.json")
    gate = HumanGate(LocalClient(store), journal=journal)
    ask_id = gate.interrupt(payload())
    assert journal.claim(ask_id) is True  # the process died while "executing"
    approve(store, ask_id)

    restarted = HumanGate(
        LocalClient(store), journal=ExecutionJournal(tmp_path / "executions.json")
    )
    assert restarted.run_once(ask_id, lambda: None) is False


def test_the_journal_tolerates_a_missing_or_corrupt_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    missing = ExecutionJournal(tmp_path / "missing.json")
    assert missing.state("ask_x") is None

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("[]", encoding="utf-8")
    assert ExecutionJournal(corrupt).state("ask_x") is None


def test_an_in_memory_gate_still_runs_once(store) -> None:  # type: ignore[no-untyped-def]
    gate = HumanGate(LocalClient(store))
    ask_id = gate.interrupt(payload())
    runs = []

    assert gate.run_once(ask_id, lambda: runs.append(1)) is True
    assert gate.run_once(ask_id, lambda: runs.append(1)) is False
    assert runs == [1]


def test_resume_survives_a_restart_by_id(store, tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = HumanGate(LocalClient(store))
    ask_id = first.interrupt(payload())

    # Process dies. The durable ask is the checkpoint; a new gate resumes by id.
    second = HumanGate(LocalClient(store), journal=ExecutionJournal(tmp_path / "x.json"))
    assert second.resume(ask_id, wait=0)["reason_code"] == "deny_ask_pending"
    approve(store, ask_id)
    outcome = second.resume(ask_id, wait=0)
    assert outcome["status"] == "allow"
    assert outcome["answered_by"] == "alice"
    assert store.get(ask_id).expires_at == NOW + timedelta(seconds=300)  # type: ignore[union-attr]
