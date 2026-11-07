"""The CI-wait surface renders the ci card and never authenticates a principal (M14)."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from agentinbox.card import Block, Card, Field
from agentinbox.channels.ci import CiWaitChannel
from agentinbox.store import AskRecord

ASK = AskRecord(
    ask_id="ask_0123456789abcdef",
    action_identity="sha256:" + "a" * 64,
    session_id="sess",
    agent_id="agent",
    created_at=datetime(2026, 11, 8, tzinfo=UTC),
    expires_at=datetime(2026, 11, 8, 0, 5, tzinfo=UTC),
)


def test_ci_surface_renders_and_never_answers() -> None:
    out = io.StringIO()
    channel = CiWaitChannel(output=out)
    card = Card(
        ask_id=ASK.ask_id,
        status="pending",
        ttl_seconds=300,
        fingerprint="sha256:aaa…",
        blocks=(Block("ACTION", (Field("class", "irreversible"),)),),
        redactions=(),
    )

    channel.deliver(ASK, card)

    assert "ASKS: ask_0123456789abcdef" in out.getvalue()
    assert "::notice::agentinbox ask" in out.getvalue()
    assert channel.authenticate() is None
    assert channel.authenticate(as_name="alice") is None
