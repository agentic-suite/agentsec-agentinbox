"""LangGraph-pattern reference adapter (M19, CUJ-13).

Design: ``docs/design/v0.1.0/framework-adapters.md``. The adapter is framework-neutral: a graph
node calls :meth:`HumanGate.interrupt` (LangGraph's ``interrupt(payload)``) and later
:meth:`HumanGate.decision` (the value fed to ``Command(resume=…)``). The ask and the decision
live in the durable store, so a process death between the two loses nothing and re-running does
not re-execute an irreversible tool.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from agentinbox.store import canonical_json


class AskClient(Protocol):
    def create(self, ask: Mapping[str, Any]) -> dict[str, Any]: ...

    def resolve(
        self,
        ask_id: str,
        *,
        wait: float = 30,
        action_identity: str | None = None,
    ) -> dict[str, Any]: ...


class ExecutionJournal:
    """Durable at-most-once execution marker keyed by ask id."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save(self, state: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        staging = self.path.with_name(self.path.name + ".tmp")
        staging.write_text(canonical_json(state) + "\n", encoding="utf-8")
        os.chmod(staging, 0o600)
        os.replace(staging, self.path)

    def state(self, ask_id: str) -> str | None:
        return self._load().get(ask_id)

    def claim(self, ask_id: str) -> bool:
        state = self._load()
        if ask_id in state:
            return False
        state[ask_id] = "executing"
        self._save(state)
        return True

    def complete(self, ask_id: str) -> None:
        state = self._load()
        state[ask_id] = "done"
        self._save(state)


class HumanGate:
    """The interrupt/resume pair a framework node uses."""

    def __init__(
        self,
        client: AskClient,
        *,
        journal: ExecutionJournal | None = None,
    ) -> None:
        self.client = client
        self.journal = journal
        self._executed: set[str] = set()

    def interrupt(self, ask: Mapping[str, Any]) -> str:
        """Create the ask and return the durable resume token (the ask id)."""
        created = self.client.create(ask)
        return str(created["ask_id"])

    def resume(self, ask_id: str, *, wait: float = 30) -> dict[str, Any]:
        """Read the recorded outcome by id; idempotent across restarts."""
        return self.client.resolve(ask_id, wait=wait)

    def decision(self, ask_id: str, *, wait: float = 30) -> str:
        outcome = self.resume(ask_id, wait=wait)
        return "approve" if outcome.get("status") == "allow" else "deny"

    def run_once(self, ask_id: str, action: Callable[[], Any]) -> bool:
        """Execute ``action`` at most once per ask, even across crashes."""
        if not self._claim(ask_id):
            return False
        action()
        if self.journal is not None:
            self.journal.complete(ask_id)
        return True

    def _claim(self, ask_id: str) -> bool:
        if self.journal is not None:
            return self.journal.claim(ask_id)
        if ask_id in self._executed:
            return False
        self._executed.add(ask_id)
        return True


__all__ = ["AskClient", "ExecutionJournal", "HumanGate"]
