"""Claim mint/bind/revoke properties (M6 item 6.1, E3)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agentinbox.claims import hash_secret, mint_claim, secret_matches
from agentinbox.ingest import ingest
from agentinbox.store import StoreError
from agentinbox.store.sqlite import SqliteStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload


def make_ask(store):  # type: ignore[no-untyped-def]
    return ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask


def test_secret_is_returned_once_and_only_the_hash_is_stored(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)

    minted = mint_claim(store, ask, channel="terminal", tier="tier-1", now=NOW)
    stored = store.get_claim(minted.claim.claim_id)

    assert stored is not None
    assert stored.secret_hash == hash_secret(minted.secret)
    assert minted.secret not in stored.secret_hash
    assert secret_matches(stored, minted.secret)
    assert not secret_matches(stored, "wrong-secret")


def test_claim_expires_with_the_ask(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)

    minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)

    assert minted.claim.expires_at == ask.expires_at
    assert (
        store.consume_claim(
            minted.claim.claim_id, ask_id=ask.ask_id, at=ask.expires_at
        )
        is False
    )


def test_claim_is_single_use_across_channels(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)

    assert store.consume_claim(minted.claim.claim_id, ask_id=ask.ask_id, at=NOW) is True
    assert store.consume_claim(minted.claim.claim_id, ask_id=ask.ask_id, at=NOW) is False
    assert store.get_claim(minted.claim.claim_id).consumed_at == NOW  # type: ignore[union-attr]


def test_revocation_by_tier(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    tier_one = mint_claim(store, ask, channel="terminal", tier="tier-1", now=NOW)
    on_call = mint_claim(store, ask, channel="terminal", tier="on-call", now=NOW)

    assert store.revoke_claims(ask.ask_id, at=NOW + timedelta(seconds=1), tier="tier-1") == 1

    assert store.consume_claim(tier_one.claim.claim_id, ask_id=ask.ask_id, at=NOW) is False
    assert store.consume_claim(on_call.claim.claim_id, ask_id=ask.ask_id, at=NOW) is True


def test_duplicate_claim_id_is_refused(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)
    minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW)

    import pytest

    with pytest.raises(StoreError):
        store.issue_claim(minted.claim)


def test_claims_survive_a_reopen(tmp_path: Path) -> None:
    path = tmp_path / "home" / "inbox.db"
    first = SqliteStore(path)
    ask = make_ask(first)
    minted = mint_claim(first, ask, channel="terminal", tier=None, now=NOW)
    first.close()

    second = SqliteStore(path)
    try:
        reloaded = second.get_claim(minted.claim.claim_id)
        assert reloaded is not None
        assert secret_matches(reloaded, minted.secret)
        assert (
            second.consume_claim(minted.claim.claim_id, ask_id=ask.ask_id, at=NOW) is True
        )
    finally:
        second.close()
