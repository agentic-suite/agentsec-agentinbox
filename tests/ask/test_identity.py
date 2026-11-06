"""Canonical identity + idempotent ingest (M2 item 2.3, SC-06)."""

from __future__ import annotations

from agentinbox.ingest import ingest
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload


def test_retries_coalesce_to_one_ask(store) -> None:  # type: ignore[no-untyped-def]
    producer = ProducerIdentity.unauthenticated()

    results = [
        ingest(payload(), store=store, config=config(), producer=producer, now=NOW)
        for _ in range(3)
    ]

    assert [result.created for result in results] == [True, False, False]
    assert len({result.ask.ask_id for result in results}) == 1

    export = store.export_session(results[0].ask.session_id)
    assert len(export.asks) == 1
    assert [item.kind for item in export.transitions] == [
        "created",
        "deduplicated",
        "deduplicated",
    ]


def test_different_arguments_are_a_different_ask(store) -> None:  # type: ignore[no-untyped-def]
    producer = ProducerIdentity.unauthenticated()
    first = ingest(payload(), store=store, config=config(), producer=producer, now=NOW)
    second = ingest(
        payload(arguments={"command": "rm -rf /tmp/x"}),
        store=store,
        config=config(),
        producer=producer,
        now=NOW,
    )

    assert first.ask.ask_id != second.ask.ask_id


def test_different_sessions_are_different_asks(store) -> None:  # type: ignore[no-untyped-def]
    producer = ProducerIdentity.unauthenticated()
    first = ingest(payload(), store=store, config=config(), producer=producer, now=NOW)
    second = ingest(
        payload(session_id="sess_other"),
        store=store,
        config=config(),
        producer=producer,
        now=NOW,
    )

    assert first.ask.ask_id != second.ask.ask_id


def test_producer_ask_id_is_kept_when_fresh(store) -> None:  # type: ignore[no-untyped-def]
    body = payload()
    body["ask_id"] = "ask_" + "b" * 16

    result = ingest(
        body,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    assert result.ask.ask_id == "ask_" + "b" * 16


def test_server_mints_ask_id_when_absent(store) -> None:  # type: ignore[no-untyped-def]
    result = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    assert result.ask.ask_id.startswith("ask_")
    assert len(result.ask.ask_id) == len("ask_") + 16
