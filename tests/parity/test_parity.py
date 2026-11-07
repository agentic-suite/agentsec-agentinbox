"""Decision parity: one record shape, only channel/principal vary (M14 item 14.1)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.config import ChannelConfig, ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.parity import comparable_decision, decision_record, surface_outcome
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload

ASK_ID = "ask_0123456789abcdef"


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",), "ci": ("bob",)}},
        channels={
            "terminal": ChannelConfig(enabled=True),
            "desktop": ChannelConfig(enabled=True),
            "webhook": ChannelConfig(enabled=True),
        },
    )


def make(store) -> object:  # type: ignore[no-untyped-def]
    return ingest(
        payload(ask_id=ASK_ID),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def answer(store, ask, *, principal: str, channel: str):  # type: ignore[no-untyped-def]
    minted = mint_claim(store, ask, channel=channel, tier=None, now=NOW)
    return AnswerVerifier(store, config(), now=lambda: NOW).submit(
        AnswerRequest(
            ask_id=ask.ask_id,
            claim_id=minted.claim.claim_id,
            secret=minted.secret,
            principal=principal,
            channel=channel,
            decision="approve",
            typed_confirmation="run_command",
        ),
        channel_authenticated=True,
    )


def test_the_decision_record_shape_is_channel_independent(store, store2) -> None:  # type: ignore[no-untyped-def]
    first = make(store)
    second = make(store2)
    assert first.ask_id == second.ask_id == ASK_ID

    answer(store, first, principal="alice", channel="terminal")
    answer(store2, second, principal="bob", channel="ci")

    left = decision_record(store, ASK_ID)
    right = decision_record(store2, ASK_ID)

    assert comparable_decision(left) == comparable_decision(right)
    assert left["channel"] == "terminal"
    assert right["channel"] == "ci"
    assert left["principal"] == "alice"
    assert right["principal"] == "bob"
    assert left["status"] == right["status"] == "approved"
    assert left["decision"] == right["decision"] == "approve"


def test_every_surface_renders_the_same_decision(store) -> None:  # type: ignore[no-untyped-def]
    ask = make(store)
    answer(store, ask, principal="alice", channel="terminal")

    rendered = {
        surface: surface_outcome(store, ASK_ID, surface=surface, now=NOW)
        for surface in ("text", "terminal", "desktop", "ci")
    }

    for surface, text in rendered.items():
        assert f"ASKS: {ASK_ID}" in text, surface
        assert "status=approved" in text, surface
        assert "fingerprint: sha256:" in text, surface

    # All surfaces share the same core body; footers differ by design.
    core = [
        line
        for line in rendered["text"].splitlines()
        if not line.startswith("Answer with:")
    ]
    assert core == [
        line
        for line in rendered["ci"].splitlines()
        if not line.startswith("::notice::")
    ]


def test_unknown_asks_raise(store) -> None:  # type: ignore[no-untyped-def]
    import pytest

    with pytest.raises(KeyError):
        decision_record(store, "ask_missing")
    with pytest.raises(KeyError):
        surface_outcome(store, "ask_missing", surface="text", now=NOW)


def test_a_pending_surface_updates_after_the_decision(store) -> None:  # type: ignore[no-untyped-def]
    ask = make(store)
    before = surface_outcome(store, ASK_ID, surface="desktop", now=NOW)
    assert "status=pending" in before

    answer(store, ask, principal="alice", channel="terminal")

    after = surface_outcome(store, ASK_ID, surface="desktop", now=NOW + timedelta(seconds=1))
    assert "status=approved" in after
