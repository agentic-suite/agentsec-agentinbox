"""Timeboxed windows, session grants, burn-down, compression, repeated denies (M30)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agentinbox.card import build_card
from agentinbox.grants import (
    GrantError,
    active_grants,
    compress,
    end_session,
    expire_due_grants,
    grant_for_card,
    grants,
    issue_grant,
    repeated_denials,
    revoke_grant,
)
from agentinbox.store.memory import MemoryStore
from tests.bundles.conftest import ingest_ask
from tests.constraints.conftest import deny
from tests.readiness.conftest import NOW, config


def _window(store, **overrides):  # type: ignore[no-untyped-def]
    values = {
        "scope": "class",
        "class_name": "irreversible",
        "owner": "alice",
        "reason": "deploy window",
        "issued_by": "alice",
        "ttl_seconds": 300,
        "max_uses": 3,
        "max_per_minute": 10,
        "at": NOW,
    }
    values.update(overrides)
    return issue_grant(store, config(), **values)


def test_a_live_window_approves_until_the_ceiling_then_reverts() -> None:
    store = MemoryStore()
    try:
        grant = _window(store)
        asks = [
            ingest_ask(store, session=f"s{index}", command=f"echo step-{index}")
            for index in range(4)
        ]
        after = [store.get(ask.ask_id) for ask in asks]
        detail = [
            item
            for item in store.transitions_for(asks[0].ask_id)
            if item.kind == "answer"
        ][-1].detail
        events = [entry.kind for entry in store.audit_entries() if entry.kind.startswith("grant-")]
    finally:
        store.close()

    assert [item.status.value for item in after if item is not None] == [
        "approved",
        "approved",
        "approved",
        "pending",
    ]
    assert detail["authorization"]["source"] == "window-grant"
    assert detail["authorization"]["grant_id"] == grant.grant_id
    assert detail["authorization"]["burndown"]["uses"] == 1
    assert "grant-issued" in events
    assert "grant-used" in events


def test_burn_down_renders_on_the_card_including_spent() -> None:
    store = MemoryStore()
    try:
        _window(store, max_uses=3)
        ask = ingest_ask(store)
        burn = grant_for_card(store, ask, now=NOW)
        card = build_card(ask, now=NOW, grant=burn).render("terminal")
    finally:
        store.close()

    assert burn is not None
    assert burn["status"] == "active"
    assert "GRANT" in card
    assert "1/3" in card
    assert "issued by" in card


def test_the_rate_ceiling_blocks_a_burst() -> None:
    store = MemoryStore()
    try:
        _window(store, max_uses=10, max_per_minute=1)
        first = ingest_ask(store, session="a", command="echo a")
        second = ingest_ask(store, session="b", command="echo b")
        first_stored = store.get(first.ask_id)
        second_stored = store.get(second.ask_id)
    finally:
        store.close()

    assert first_stored is not None
    assert first_stored.status.value == "approved"
    assert second_stored is not None
    assert second_stored.status.value == "pending"


def test_an_expired_window_reverts_to_per_ask_and_is_audited() -> None:
    store = MemoryStore()
    try:
        grant = _window(store, ttl_seconds=60, at=NOW - timedelta(minutes=5))
        ask = ingest_ask(store)
        stored = store.get(ask.ask_id)
        expired = expire_due_grants(store, at=NOW)
        events = [entry.kind for entry in store.audit_entries() if entry.kind == "grant-expired"]
    finally:
        store.close()

    assert grant.grant_id in expired
    assert stored is not None
    assert stored.status.value == "pending"
    assert events == ["grant-expired"]


def test_a_session_holds_one_grant_and_session_end_expires_it_loudly() -> None:
    store = MemoryStore()
    try:
        grant = _window(store, scope="session", session_id="sess_a")
        with pytest.raises(GrantError):
            _window(store, scope="session", session_id="sess_a")
        covered = ingest_ask(store, session="sess_a")
        other = ingest_ask(store, session="sess_b")
        expired = end_session(store, "sess_a", at=NOW + timedelta(minutes=1))
        after = ingest_ask(store, session="sess_a", command="echo later")
        covered_stored = store.get(covered.ask_id)
        other_stored = store.get(other.ask_id)
        later_stored = store.get(after.ask_id)
        state = next(item for item in grants(store) if item.grant_id == grant.grant_id)
    finally:
        store.close()

    assert covered_stored is not None
    assert covered_stored.status.value == "approved"
    assert other_stored is not None
    assert other_stored.status.value == "pending"
    assert expired == (grant.grant_id,)
    assert later_stored is not None
    assert later_stored.status.value == "pending"
    assert state.status == "expired"


def test_revocation_is_immediate_and_loud() -> None:
    store = MemoryStore()
    try:
        grant = _window(store)
        revoke_grant(store, grant.grant_id, by="alice", reason="change freeze", at=NOW)
        ask = ingest_ask(store)
        stored = store.get(ask.ask_id)
        active = active_grants(store, now=NOW)
        revoked = [entry for entry in store.audit_entries() if entry.kind == "grant-revoked"]
    finally:
        store.close()

    assert stored is not None
    assert stored.status.value == "pending"
    assert active == ()
    assert len(revoked) == 1


def test_compression_is_a_view_with_every_row_present() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"c{index}", command="echo identical")
            for index in range(12)
        ]
        group = compress(store, asks[0])
        rendered = group.render()
    finally:
        store.close()

    assert group.count == 12
    assert len({ask.ask_id for ask in group.asks}) == 12
    assert rendered.startswith("COMPRESSED x12")
    assert all(ask.ask_id in rendered for ask in asks)


def test_repeated_denials_surface_without_hardening_or_approving() -> None:
    store = MemoryStore()
    try:
        asks = [
            ingest_ask(store, session=f"d{index}", command="echo denied")
            for index in range(5)
        ]
        for ask in asks:
            deny(store, ask, reason="not now")
        items = repeated_denials(store, threshold=5)
        below = repeated_denials(store, threshold=6)
        states = [store.get(ask.ask_id) for ask in asks]
    finally:
        store.close()

    assert len(items) == 1
    assert items[0]["count"] == 5
    assert len(items[0]["ask_ids"]) == 5
    assert below == []
    assert all(item is not None for item in states)
    assert all(item.status.value == "denied" for item in states if item is not None)


@pytest.mark.parametrize(
    "overrides",
    [
        {"scope": "global"},
        {"class_name": "missing"},
        {"session_id": None, "scope": "session"},
        {"ttl_seconds": 0},
        {"max_uses": 0},
        {"max_per_minute": 0},
        {"owner": ""},
        {"reason": ""},
    ],
)
def test_invalid_grants_are_refused(overrides) -> None:  # type: ignore[no-untyped-def]
    store = MemoryStore()
    try:
        with pytest.raises(GrantError):
            _window(store, **overrides)
    finally:
        store.close()


def test_grant_and_compression_edge_filters() -> None:
    from agentinbox.grants import grant_covering
    from agentinbox.store import AskStatus

    store = MemoryStore()
    try:
        grant = _window(store)
        revoke_grant(store, grant.grant_id, by="alice", reason="freeze", at=NOW)
        assert grants(store)[0].status == "revoked"
        with pytest.raises(GrantError):
            revoke_grant(store, grant.grant_id, by="alice", reason="")
        read_only = ingest_ask(store, session="ro", **{"class": "readonly"})
        assert grant_covering(store, read_only, now=NOW) is None

        session_grant = _window(
            store, scope="session", session_id="other", class_name="irreversible"
        )
        assert session_grant.session_id == "other"
        outside = ingest_ask(store, session="sess_x", command="echo outside")
        assert grant_covering(store, outside, now=NOW) is None

        stale = _window(store, ttl_seconds=60, at=NOW - timedelta(minutes=10))
        assert stale.grant_id
        stale_ask = ingest_ask(store, session="stale", command="echo stale")
        stale_card = grant_for_card(store, stale_ask, now=NOW)
        assert stale_card is not None
        assert stale_card["status"] == "revoked"

        denied = ingest_ask(store, session="denied", command="echo denied")
        deny(store, denied, reason="no")
        store.append_audit(kind="incident-off", ref_id="incident", at=NOW, payload={})
        store.append_audit(
            kind="transition",
            ref_id="ask_0000000000000000",
            at=NOW,
            payload={"kind": "created"},
        )
        store.append_audit(
            kind="transition",
            ref_id="ask_1111111111111111",
            at=NOW,
            payload={"kind": "answer", "to_status": AskStatus.DENIED.value},
        )
        assert compress(store, outside).count == 1
        assert repeated_denials(store, threshold=1)
        expire_due_grants(store, at=NOW + timedelta(hours=1))
        assert expire_due_grants(store, at=NOW + timedelta(hours=2)) == ()
    finally:
        store.close()


def test_doctor_reports_active_grants_and_sla(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from agentinbox import doctor

    home = tmp_path / "home"
    home.mkdir()
    (home / "inbox.db").write_bytes(b"")

    from agentinbox.store import utcnow

    grant_store = MemoryStore()
    _window(grant_store, at=utcnow(), ttl_seconds=3600)
    monkeypatch.setattr(
        "agentinbox.store.loader.load_store", lambda *a, **k: grant_store
    )
    active = doctor._grants(home, config())
    assert "grant_0001" in active.detail

    sla_store = MemoryStore()
    monkeypatch.setattr(
        "agentinbox.store.loader.load_store", lambda *a, **k: sla_store
    )
    from agentinbox import outcomes

    monkeypatch.setattr(
        outcomes,
        "outcome_sla_pending",
        lambda *a, **k: [{"ask_id": "ask_0123456789abcdef"}],
    )
    sla = doctor._outcome_sla(home, config())
    assert sla.status == doctor.WARN
    assert "ask_0123456789abcdef" in sla.detail
