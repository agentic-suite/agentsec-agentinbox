"""Loopback ingest API + bounded long-poll (M2 item 2.6)."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest

from agentinbox.api import IngestAPI, start_api
from agentinbox.ingest import ingest
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload

TOKEN = "test-socket-token-0123456789"


@pytest.fixture
def api(store) -> Iterator[IngestAPI]:  # type: ignore[no-untyped-def]
    handle = start_api(store=store, config=config(), token=TOKEN, now=lambda: NOW)
    try:
        yield handle
    finally:
        handle.stop()


def call(
    api: IngestAPI,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = TOKEN,
    raw: bytes | None = None,
) -> tuple[int, dict[str, Any]]:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(f"{api.url}{path}", data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_bind_is_loopback(api: IngestAPI) -> None:
    assert api.url.startswith("http://127.0.0.1:")


def test_missing_token_is_rejected(api: IngestAPI) -> None:
    status, body = call(api, "POST", "/v1/asks", body=payload(), token=None)

    assert status == 401
    assert body["error"]["field"] == "authorization"


def test_wrong_token_is_rejected(api: IngestAPI) -> None:
    status, _ = call(api, "POST", "/v1/asks", body=payload(), token="wrong")

    assert status == 401


def test_alternate_token_header_is_accepted(api: IngestAPI) -> None:
    request = urllib.request.Request(
        f"{api.url}/v1/asks",
        data=json.dumps(payload()).encode(),
        method="POST",
    )
    request.add_header("X-AgentInbox-Token", TOKEN)
    request.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 201


def test_post_creates_ask_and_get_reads_it(api: IngestAPI) -> None:
    status, created = call(api, "POST", "/v1/asks", body=payload())
    assert status == 201
    assert created["created"] is True
    ask_id = created["ask_id"]

    status, fetched = call(api, "GET", f"/v1/asks/{ask_id}")
    assert status == 200
    assert fetched["ask_id"] == ask_id
    assert fetched["status"] == "pending"


def test_duplicate_post_returns_200_and_the_same_id(api: IngestAPI) -> None:
    _, first = call(api, "POST", "/v1/asks", body=payload())
    status, second = call(api, "POST", "/v1/asks", body=payload())

    assert status == 200
    assert second["created"] is False
    assert second["ask_id"] == first["ask_id"]


def test_invalid_payload_is_400_with_the_field(api: IngestAPI) -> None:
    status, body = call(api, "POST", "/v1/asks", body=payload(**{"class": "nope"}))

    assert status == 400
    assert body["error"]["field"] == "class"


def test_malformed_json_is_400(api: IngestAPI) -> None:
    status, body = call(api, "POST", "/v1/asks", raw=b"{not json")

    assert status == 400
    assert body["error"]["field"] == "body"


def test_oversize_payload_is_413(api: IngestAPI) -> None:
    status, body = call(api, "POST", "/v1/asks", body=payload(blob="x" * 300_000))

    assert status == 413
    assert body["error"]["field"] == "body"


def test_unknown_ask_is_404(api: IngestAPI) -> None:
    status, body = call(api, "GET", "/v1/asks/ask_0000000000000000")

    assert status == 404
    assert body["contract"] == "resolve/1.0"
    assert body["reason_code"] == "deny_ask_unknown"


def test_a_reloaded_config_is_applied_to_the_running_api(api: IngestAPI) -> None:
    from agentinbox.config import ClassConfig, Config

    api.update_config(
        Config(classes={"irreversible": ClassConfig(ttl_seconds=600)})
    )
    body = payload(
        expires_at=(NOW + timedelta(seconds=500))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )

    status, _ = call(api, "POST", "/v1/asks", body=body)

    assert status == 201


def test_update_config_can_replace_the_flood_guard(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.flood import FloodGuard

    api.update_config(config(), flood_guard=FloodGuard(store, config(), now=lambda: NOW))

    status, _ = call(api, "GET", "/v1/asks/ask_0000000000000000")
    assert status == 404


def test_resolve_rejects_a_different_action_identity(api: IngestAPI) -> None:
    _, created = call(api, "POST", "/v1/asks", body=payload())

    status, body = call(
        api,
        "GET",
        f"/v1/asks/{created['ask_id']}?action_identity=sha256:{'b' * 64}",
    )

    assert status == 200
    assert body["contract"] == "resolve/1.0"
    assert body["reason_code"] == "deny_action_identity_mismatch"


def test_resolve_is_idempotent(api: IngestAPI) -> None:
    _, created = call(api, "POST", "/v1/asks", body=payload())

    first = call(api, "GET", f"/v1/asks/{created['ask_id']}")
    second = call(api, "GET", f"/v1/asks/{created['ask_id']}")

    assert first == second


def test_store_failure_is_503(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    store.close()

    status, body = call(api, "POST", "/v1/asks", body=payload())

    assert status == 503
    assert body["error"]["field"] == "store"


def test_resolved_ask_returns_immediately(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    _, created = call(api, "POST", "/v1/asks", body=payload())
    ask_id = created["ask_id"]
    ask = store.get(ask_id)
    assert ask is not None
    from agentinbox.store import AskStatus, TransitionRecord

    store.cas_status(
        ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.APPROVED,
        transition=TransitionRecord(
            ask_id=ask_id, at=NOW, kind="answer", to_status=AskStatus.APPROVED
        ),
    )

    started = time.monotonic()
    status, body = call(api, "GET", f"/v1/asks/{ask_id}?wait=5s")

    assert status == 200
    assert body["contract"] == "resolve/1.0"
    assert body["status"] == "allow"
    assert time.monotonic() - started < 1.0


def test_long_poll_wakes_on_notify(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    _, created = call(api, "POST", "/v1/asks", body=payload())
    ask_id = created["ask_id"]
    result: dict[str, Any] = {}

    def wait() -> None:
        result["response"] = call(api, "GET", f"/v1/asks/{ask_id}?wait=5s")

    thread = threading.Thread(target=wait)
    thread.start()
    time.sleep(0.1)
    from agentinbox.store import AskStatus, TransitionRecord

    store.cas_status(
        ask_id,
        expected=AskStatus.PENDING,
        new=AskStatus.DENIED,
        transition=TransitionRecord(
            ask_id=ask_id, at=NOW, kind="answer", to_status=AskStatus.DENIED
        ),
    )
    api.notify(ask_id)
    thread.join(timeout=3)

    assert not thread.is_alive()
    status, body = result["response"]
    assert status == 200
    assert body["status"] == "deny"


def test_long_poll_times_out_with_pending(api: IngestAPI) -> None:
    _, created = call(api, "POST", "/v1/asks", body=payload())

    started = time.monotonic()
    status, body = call(api, "GET", f"/v1/asks/{created['ask_id']}?wait=0.2s")

    assert status == 200
    assert body["status"] == "pending"
    assert time.monotonic() - started >= 0.15


def test_ingest_records_producer_remote_address(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    _, created = call(api, "POST", "/v1/asks", body=payload())

    ask = store.get(created["ask_id"])
    assert ask is not None
    assert ask.payload["_producer"]["remote_addr"] == "127.0.0.1"
    assert ask.payload["_producer"]["authenticated"] is False


def test_direct_ingest_and_api_share_the_same_store(api: IngestAPI, store) -> None:  # type: ignore[no-untyped-def]
    direct = ingest(
        payload(arguments={"command": "direct"}),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    status, body = call(api, "GET", f"/v1/asks/{direct.ask.ask_id}")

    assert status == 200
    assert body["ask_id"] == direct.ask.ask_id
