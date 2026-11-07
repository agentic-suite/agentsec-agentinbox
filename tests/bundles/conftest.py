"""Helpers for the M28 operations suite."""

from __future__ import annotations

from typing import Any

from agentinbox.ingest import ingest
from agentinbox.store import AskRecord, AskStore
from agentinbox.trust import ProducerIdentity
from tests.readiness.conftest import NOW, config, good_body


def signed() -> ProducerIdentity:
    return ProducerIdentity(adapter="agentpolicy", authenticated=True, principal="maya@team")


def ingest_ask(
    store: AskStore,
    *,
    session: str = "sess_ops",
    operation: str | None = "op_deploy_7",
    phase: str | None = "review",
    environment: str = "production",
    command: str | None = None,
    **overrides: Any,
) -> AskRecord:
    body = good_body(
        session_id=session,
        environment=environment,
        arguments={"command": command or f"psql prod -c 'select {session}'"},
        **overrides,
    )
    context = dict(body["context"])
    if operation is not None:
        context["operation_id"] = operation
    if phase is not None:
        context["phase"] = phase
    body["context"] = context
    return ingest(body, store=store, config=config(), producer=signed(), now=NOW).ask
