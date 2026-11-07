"""Fixtures for the claim/answer pipeline (M6)."""

from __future__ import annotations

from datetime import timedelta

from agentinbox.claims import mint_claim
from agentinbox.config import ClassConfig, Config
from agentinbox.ingest import ingest
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, payload


def answer_config(*, roster=("alice",), requested_by="maya") -> Config:
    del requested_by
    return Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300,
                warn_seconds=60,
                self_review="deny",
                require_reason_on_deny=True,
                ladder=("tier-1",),
            )
        },
        roster={"tier-1": {"terminal": list(roster)}},
    )


def make_ask(store, *, config=None, requested_by="maya", arguments=None):  # type: ignore[no-untyped-def]
    cfg = config or answer_config(roster=("alice", "maya"))
    body = payload(arguments=arguments) if arguments else payload()
    body["requested_by"] = requested_by
    return ingest(
        body,
        store=store,
        config=cfg,
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask, cfg


def mint(store, ask, *, channel="terminal", tier="tier-1"):  # type: ignore[no-untyped-def]
    return mint_claim(store, ask, channel=channel, tier=tier, now=NOW)


def expires_soon(ask):  # type: ignore[no-untyped-def]
    return ask.expires_at - timedelta(seconds=1)
