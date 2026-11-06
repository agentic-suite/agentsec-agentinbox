"""Validation, caps, and expiry ceilings (M2 item 2.2).

Every rejection names the failing field and nothing partial is stored (SC-02).
"""

from __future__ import annotations

import pytest

from agentinbox.contract import ContractError, parse_ask
from agentinbox.ingest import enforce_caps, ingest, validate_ask, verify_action_identity
from agentinbox.store import StoreError
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload


def test_valid_ask_passes_every_check() -> None:
    validate_ask(payload(), now=NOW, config=config())


def test_total_payload_cap_is_413() -> None:
    body = payload(extra_blob="x" * 300_000)

    with pytest.raises(ContractError) as excinfo:
        enforce_caps(body)

    assert excinfo.value.field == "body"
    assert excinfo.value.status_code == 413


def test_single_string_cap_names_the_nested_field() -> None:
    body = payload(arguments={"command": "x" * 5_000})

    with pytest.raises(ContractError) as excinfo:
        enforce_caps(body)

    assert excinfo.value.field == "arguments.command"


def test_arguments_object_cap() -> None:
    body = payload(arguments={"items": ["y" * 1_000 for _ in range(80)]})

    with pytest.raises(ContractError) as excinfo:
        enforce_caps(body)

    assert excinfo.value.field == "arguments"


def test_context_object_cap() -> None:
    body = payload(context={"items": ["z" * 1_000 for _ in range(80)]})

    with pytest.raises(ContractError) as excinfo:
        enforce_caps(body)

    assert excinfo.value.field == "context"


def test_policy_clause_cap() -> None:
    body = payload(
        policy_ref={"rule_id": "r", "policy_version": "v1", "clause": "c" * 9_000}
    )

    with pytest.raises(ContractError) as excinfo:
        enforce_caps(body)

    assert excinfo.value.field == "policy_ref.clause"


def test_expired_ask_is_rejected() -> None:
    body = payload(expires_at="2026-11-06T11:59:59.000000Z")

    with pytest.raises(ContractError) as excinfo:
        validate_ask(body, now=NOW, config=config())

    assert excinfo.value.field == "expires_at"


def test_expiry_beyond_class_ceiling_is_rejected() -> None:
    body = payload(expires_at="2026-11-06T12:30:00.000000Z")

    with pytest.raises(ContractError) as excinfo:
        validate_ask(body, now=NOW, config=config(ttl_seconds=300))

    assert excinfo.value.field == "expires_at"
    assert "ceiling" in excinfo.value.message


def test_unresolvable_class_is_rejected() -> None:
    body = payload(**{"class": "not-configured"})

    with pytest.raises(ContractError) as excinfo:
        validate_ask(body, now=NOW, config=config())

    assert excinfo.value.field == "class"


def test_producer_ask_id_shape_is_enforced() -> None:
    body = payload(ask_id="my-id")

    with pytest.raises(ContractError) as excinfo:
        validate_ask(body, now=NOW, config=config())

    assert excinfo.value.field == "ask_id"


def test_identity_mismatch_is_rejected() -> None:
    body = payload(action_identity="sha256:" + "0" * 64)
    ask = parse_ask(body)

    with pytest.raises(ContractError) as excinfo:
        verify_action_identity(ask)

    assert excinfo.value.field == "action_identity"


def test_malformed_ask_stores_nothing(store) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ContractError):
        ingest(
            payload(**{"class": "unknown"}),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )

    assert store.list_pending(now=NOW) == []
    assert store.audit_entries() == []


def test_duplicate_producer_ask_id_with_different_identity_is_rejected(store) -> None:  # type: ignore[no-untyped-def]
    first = dict(payload())
    first["ask_id"] = "ask_" + "a" * 16
    ingest(
        first,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    second = payload(arguments={"command": "something else"})
    second["ask_id"] = "ask_" + "a" * 16
    with pytest.raises(ContractError) as excinfo:
        ingest(
            second,
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )

    assert excinfo.value.field == "ask_id"


def test_store_failure_is_not_masked_as_a_contract_error(store) -> None:  # type: ignore[no-untyped-def]
    store.close()

    with pytest.raises(StoreError):
        ingest(
            payload(),
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )
