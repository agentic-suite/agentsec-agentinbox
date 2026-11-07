"""agentpolicy reference adapter: signed trusted fields + resolve round-trip (M18 item 18.1)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from agentinbox.adapters import AdapterError, AgentPolicyClient
from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.api import IngestAPI, start_api
from agentinbox.claims import mint_claim
from agentinbox.config import ChannelConfig, ClassConfig, Config, ProducerConfig
from tests.ask.conftest import NOW, payload


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
        channels={"terminal": ChannelConfig(enabled=True)},
        producers={"agentpolicy": ProducerConfig(key_ref="env:ADAPTER_KEY")},
    )


@pytest.fixture
def api(store) -> Iterator[IngestAPI]:  # type: ignore[no-untyped-def]
    server = start_api(
        store=store,
        config=config(),
        token="tok",
        now=lambda: NOW,
        environ={"ADAPTER_KEY": "shared-key"},
    )
    try:
        yield server
    finally:
        server.stop()


def client(
    api: IngestAPI, *, key: str = "shared-key", adapter: str = "agentpolicy"
) -> AgentPolicyClient:
    return AgentPolicyClient(
        url=api.url,
        token=api.token,
        adapter_key=key,
        principal="maya@team",
        adapter=adapter,
    )


def test_signed_create_marks_trusted_fields(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    created = client(api).create(payload())

    assert created["status"] == "pending"
    ask = store.get(created["ask_id"])
    assert ask is not None
    assert ask.payload["_producer"]["adapter"] == "agentpolicy"
    assert ask.payload["_producer"]["authenticated"] is True
    assert ask.payload["_producer"]["principal"] == "maya@team"
    assert ask.payload["_trust"]["trusted"]


def test_a_bad_signature_is_refused(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(AdapterError, match="401"):
        client(api, key="wrong").create(payload())

    assert store.list_pending(now=NOW) == []


def test_an_unknown_adapter_is_refused(api: IngestAPI) -> None:
    with pytest.raises(AdapterError, match="401"):
        client(api, adapter="not-configured").create(payload())


class BadResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> BadResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def test_ask_combines_create_and_resolve(api: IngestAPI) -> None:
    outcome = client(api).ask(payload(), wait=0)
    assert outcome["contract"] == "resolve/1.0"
    assert outcome["reason_code"] == "deny_ask_pending"


def test_a_non_object_response_is_refused(api: IngestAPI) -> None:
    broken = AgentPolicyClient(
        url=api.url,
        token=api.token,
        adapter_key="shared-key",
        opener=lambda *args, **kwargs: BadResponse(b"[]"),
    )
    with pytest.raises(AdapterError, match="non-object"):
        broken.create(payload())


def test_an_unreachable_inbox_is_refused(api: IngestAPI) -> None:
    def refuse(*args: object, **kwargs: object) -> object:
        raise OSError("connection refused")

    broken = AgentPolicyClient(
        url=api.url, token=api.token, adapter_key="shared-key", opener=refuse
    )
    with pytest.raises(AdapterError, match="unreachable"):
        broken.create(payload())


def test_the_resolve_round_trip_feeds_agentpolicy(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    adapter = client(api)
    created = adapter.create(payload())
    ask_id = created["ask_id"]

    pending = adapter.resolve(ask_id, wait=0)
    assert pending["contract"] == "resolve/1.0"
    assert pending["reason_code"] == "deny_ask_pending"

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

    resolved = adapter.resolve(ask_id, wait=0)
    assert resolved["status"] == "allow"
    assert resolved["reason_code"] == "allow_ask_approved"
    assert resolved["answered_by"] == "alice"
