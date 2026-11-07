"""Raw-API answer forgery is refused (M6 item 6.6, T14)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest

from agentinbox.api import IngestAPI, start_api
from agentinbox.store import AskStatus
from tests.answers.conftest import NOW, answer_config, make_ask, mint

TOKEN = "answer-guard-token"


@pytest.fixture
def api(store) -> Iterator[IngestAPI]:  # type: ignore[no-untyped-def]
    handle = start_api(
        store=store,
        config=answer_config(roster=("alice", "maya")),
        token=TOKEN,
        now=lambda: NOW,
    )
    try:
        yield handle
    finally:
        handle.stop()


def call(api: IngestAPI, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{api.url}{path}", data=json.dumps(body).encode(), method="POST"
    )
    request.add_header("Authorization", f"Bearer {TOKEN}")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_raw_api_answer_is_forbidden_and_changes_nothing(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    ask, _cfg = make_ask(store, config=answer_config(roster=("alice", "maya")))
    minted = mint(store, ask)

    status, body = call(
        api,
        f"/v1/asks/{ask.ask_id}/answer",
        {
            "claim_id": minted.claim.claim_id,
            "secret": minted.secret,
            "principal": "alice",
            "channel": "terminal",
            "decision": "approve",
            "typed_confirmation": "run_command",
        },
    )

    assert status == 403
    assert body["error"]["field"] == "authorization"
    stored = store.get(ask.ask_id)
    assert stored is not None
    assert stored.status is AskStatus.PENDING
    assert store.transitions_for(ask.ask_id)[-1].detail["cause"] == "bad_signature"


def test_invalid_decision_is_400(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    ask, _cfg = make_ask(store, config=answer_config(roster=("alice",)))

    status, body = call(api, f"/v1/asks/{ask.ask_id}/answer", {"decision": "maybe"})

    assert status == 400
    assert body["error"]["field"] == "decision"


def test_unknown_ask_is_404(api: IngestAPI) -> None:
    status, body = call(
        api,
        "/v1/asks/ask_0000000000000000/answer",
        {"decision": "approve", "claim_id": "x", "secret": "y", "principal": "alice"},
    )

    assert status == 404
    assert body["error"]["field"] == "ask_id"
