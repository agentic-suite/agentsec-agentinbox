"""Trusted/untrusted classification (M2 item 2.5, T13)."""

from __future__ import annotations

import pytest

from agentinbox.ingest import ingest
from agentinbox.store import canonical_json
from agentinbox.trust import TRUSTED_FIELDS, ProducerIdentity, classify_trust
from tests.ask.conftest import NOW, config, payload


def test_unauthenticated_producer_cannot_assert_trusted_fields() -> None:
    trust = classify_trust(ProducerIdentity.unauthenticated())

    assert trust.trusted == ()
    assert set(trust.unverified) == set(TRUSTED_FIELDS)
    assert trust.untrusted == ("arguments", "context")


def test_authenticated_agentpolicy_producer_is_trusted() -> None:
    trust = classify_trust(
        ProducerIdentity(adapter="agentpolicy", authenticated=True, principal="agentpolicy")
    )

    assert set(trust.trusted) == set(TRUSTED_FIELDS)
    assert trust.unverified == ()


def test_authenticated_flag_without_adapter_is_not_trusted() -> None:
    trust = classify_trust(ProducerIdentity(adapter=None, authenticated=True))

    assert trust.trusted == ()
    assert set(trust.unverified) == set(TRUSTED_FIELDS)


def test_stored_payload_marks_unverified_fields(store) -> None:  # type: ignore[no-untyped-def]
    result = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    trust = result.ask.payload["_trust"]
    assert trust["trusted"] == []
    assert "policy_ref" in trust["unverified"]
    assert "arguments" in trust["untrusted"]


def test_a_class_can_require_a_signed_producer(store) -> None:  # type: ignore[no-untyped-def]
    from agentinbox.config import ClassConfig, Config
    from agentinbox.contract import ContractError

    cfg = Config(
        classes={
            "irreversible": ClassConfig(
                ttl_seconds=300, require_signed_producer=True
            )
        }
    )

    with pytest.raises(ContractError, match="signed producer"):
        ingest(
            payload(),
            store=store,
            config=cfg,
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )

    result = ingest(
        payload(),
        store=store,
        config=cfg,
        producer=ProducerIdentity(adapter="agentpolicy", authenticated=True),
        now=NOW,
    )
    assert result.created is True


def test_stored_payload_marks_trusted_fields_when_authenticated(store) -> None:  # type: ignore[no-untyped-def]
    result = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity(adapter="agentpolicy", authenticated=True),
        now=NOW,
    )

    trust = result.ask.payload["_trust"]
    assert set(trust["trusted"]) == set(TRUSTED_FIELDS)
    assert trust["unverified"] == []


def test_producer_cannot_self_assert_metadata(store) -> None:  # type: ignore[no-untyped-def]
    body = payload()
    body["_trust"] = {"trusted": sorted(TRUSTED_FIELDS), "unverified": [], "untrusted": []}
    body["_redactions"] = []

    result = ingest(
        body,
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    )

    stored = result.ask.payload
    assert stored["_trust"]["trusted"] == []
    assert stored["_redactions"] == []
    assert canonical_json(stored).count('"_trust"') == 1
