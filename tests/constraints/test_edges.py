"""Edge cases for constrained allows (M27)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from agentinbox.alternatives import (
    alternatives_for,
    is_selectable,
    prior_objections,
    recall_line,
    render_alternative,
    suggestions_for,
)
from agentinbox.answers import AnswerRejected, AnswerRequest, AnswerVerifier
from agentinbox.card import build_card
from agentinbox.claims import mint_claim
from agentinbox.config import ConfigError, init_home, load_config, resolve_config_path
from agentinbox.store.memory import MemoryStore
from tests.constraints.conftest import NOW, alternative, deny, ingest_ask
from tests.readiness.conftest import config, good_body, weak_body


def _request(ask, claim, secret, **overrides):  # type: ignore[no-untyped-def]
    data = {
        "ask_id": ask.ask_id,
        "claim_id": claim.claim_id,
        "secret": secret,
        "principal": "alice",
        "channel": "terminal",
        "decision": "approve",
        "typed_confirmation": "run_command",
    }
    data.update(overrides)
    return AnswerRequest(**data)


def test_conflicting_choice_combinations_are_refused() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store, alternatives=[alternative("staging")])
        minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW, secret="w" * 32)
        verifier = AnswerVerifier(store, config(), now=lambda: NOW)
        with pytest.raises(AnswerRejected) as both:
            verifier.submit(
                _request(
                    ask,
                    minted.claim,
                    minted.secret,
                    alternative_id="staging",
                    edits={"command": "x"},
                ),
                channel_authenticated=True,
            )
        assert both.value.cause == "conflicting_choice"

        with pytest.raises(AnswerRejected) as denied:
            verifier.submit(
                _request(
                    ask,
                    minted.claim,
                    minted.secret,
                    decision="deny",
                    alternative_id="staging",
                ),
                channel_authenticated=True,
            )
        assert denied.value.cause == "conflicting_choice"

        with pytest.raises(AnswerRejected) as unknown:
            verifier.submit(
                _request(
                    ask, minted.claim, minted.secret, alternative_id="missing"
                ),
                channel_authenticated=True,
            )
        assert unknown.value.cause == "unknown_alternative"
    finally:
        store.close()


def test_edits_on_a_class_without_a_schema_and_deny_edits_are_refused() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW, secret="v" * 32)
        verifier = AnswerVerifier(store, config(), now=lambda: NOW)
        with pytest.raises(AnswerRejected) as no_schema:
            verifier.submit(
                _request(ask, minted.claim, minted.secret, edits={"command": "x"}),
                channel_authenticated=True,
            )
        assert no_schema.value.cause == "edit_schema"

        cfg = replace(
            config(),
            classes={
                **config().classes,
                "irreversible": replace(
                    config().classes["irreversible"], edit_schema=("command",)
                ),
            },
        )
        with pytest.raises(AnswerRejected) as deny_edit:
            AnswerVerifier(store, cfg, now=lambda: NOW).submit(
                _request(
                    ask,
                    minted.claim,
                    minted.secret,
                    decision="deny",
                    edits={"command": "x"},
                ),
                channel_authenticated=True,
            )
        assert deny_edit.value.cause == "conflicting_choice"
    finally:
        store.close()


def test_suggestions_are_empty_when_nothing_is_broad() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(
            store,
            environment="local",
            arguments={"command": "echo safe", "max_rows": 10},
        )
        assert suggestions_for(ask) == ()
        rendered = build_card(ask, now=NOW).render("terminal")
    finally:
        store.close()
    assert "CHOICES" not in rendered


def test_alternative_helpers_and_recall_lines() -> None:
    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        denied = ingest_ask(store, session="denied")
        deny(store, denied, reason="missing diff")
        assert [item["ask_id"] for item in prior_objections(store, ask)] == [denied.ask_id]
        assert "denied once" in recall_line(prior_objections(store, denied) or [
            {"ask_id": "ask_x", "reason": "missing diff"}
        ])
        assert recall_line(()) == "none"
        advice = alternative("advice")
        advice["enforcer"] = None
        assert not is_selectable(advice)
        assert "advice only" in render_alternative(advice)
        assert alternatives_for(ask) == ()
    finally:
        store.close()


@pytest.mark.parametrize(
    "extra",
    [
        'readiness_enforce = "yes"\n',
        "readiness_min_score = 2\n",
        'required_evidence = "diff"\n',
        "evidence_max_age_seconds = 0\n",
        'on_contradiction = "maybe"\n',
        'edit_schema = "command"\n',
    ],
)
def test_invalid_readiness_and_edit_config_are_load_errors(
    tmp_path: Path, extra: str
) -> None:
    home = tmp_path / "home"
    path = resolve_config_path(home)
    init_home(home, path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n[classes.gated]\nttl_seconds = 300\n"
        + extra,
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(path)


def test_repair_prefers_a_bindable_alternative_and_red_is_pointless() -> None:
    from agentinbox.repair import repair_packet

    store = MemoryStore()
    try:
        body = weak_body()
        body["alternatives"] = [alternative("staging")]
        ask = ingest_ask(
            store,
            alternatives=[alternative("staging")],
            command="psql prod -c 'DROP TABLE x'",
        )
        packet = repair_packet(ask, reason="too broad")
    finally:
        store.close()
    assert packet["safe_alternative"] == "staging"
    assert packet["retry_worthiness"] in {"conditional", "pointless"}


def test_recall_skips_other_classes_tools_and_denials_without_repair() -> None:
    from agentinbox.store import AskStatus, TransitionRecord

    store = MemoryStore()
    try:
        target = ingest_ask(store)
        other_class = ingest_ask(store, session="other", **{"class": "readonly"})
        other_tool = ingest_ask(store, session="tool", tool="file")
        no_repair = ingest_ask(store, session="norepair")
        for ask in (other_class, other_tool, no_repair):
            store.cas_status(
                ask.ask_id,
                expected=AskStatus.PENDING,
                new=AskStatus.DENIED,
                transition=TransitionRecord(
                    ask_id=ask.ask_id,
                    at=NOW,
                    kind="answer",
                    from_status=AskStatus.PENDING,
                    to_status=AskStatus.DENIED,
                    detail={"decision": "deny"},
                ),
            )
        assert prior_objections(store, target) == ()
        assert render_alternative(alternative("staging")).startswith("staging —")
        many = ingest_ask(store, session="many")
        for index in range(3):
            denied = ingest_ask(store, session=f"d{index}")
            deny(store, denied, reason=f"reason {index}")
        assert len(prior_objections(store, many, limit=1)) == 1
    finally:
        store.close()


def test_a_lost_cas_is_reported_as_late(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentinbox.answers import AnswerVerifier
    from agentinbox.claims import mint_claim

    store = MemoryStore()
    try:
        ask = ingest_ask(store)
        minted = mint_claim(store, ask, channel="terminal", tier=None, now=NOW, secret="u" * 32)
        verifier = AnswerVerifier(store, config(), now=lambda: NOW)
        monkeypatch.setattr(store, "cas_status", lambda *a, **k: False)
        with pytest.raises(AnswerRejected) as rejected:
            verifier.submit(
                _request(ask, minted.claim, minted.secret), channel_authenticated=True
            )
        assert rejected.value.cause == "late"
    finally:
        store.close()


def test_card_ttl_unknown_and_session_tail_text() -> None:
    from agentinbox.card import Block, Card, Field
    from agentinbox.store import AskRecord

    card = Card(
        ask_id="ask_0123456789abcdef",
        status="pending",
        ttl_seconds=None,
        fingerprint="sha256:aaa…",
        blocks=(Block("ACTION", (Field("class", "irreversible"),)),),
        redactions=(),
    )
    assert "ttl=unknown" in card.render("terminal")

    store = MemoryStore()
    try:
        body = good_body(session_id="tail")
        body["context"] = {**body["context"], "session_tail": ["plain text tail"]}
        from agentinbox.ingest import ingest
        from agentinbox.trust import ProducerIdentity

        ask = ingest(
            body,
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        ).ask
        rendered = build_card(ask, now=NOW).render("terminal")
    finally:
        store.close()
    assert "plain text tail" in rendered
    assert isinstance(ask, AskRecord)


@pytest.mark.parametrize(
    "section",
    [
        '[channels.terminal]\nenabled = true\nallow_as = "yes"\n',
        '[audit]\nretention = "forever"\n',
    ],
)
def test_other_config_type_errors_are_named(tmp_path: Path, section: str) -> None:
    home = tmp_path / "home"
    path = resolve_config_path(home)
    init_home(home, path)
    path.write_text(path.read_text(encoding="utf-8") + "\n" + section, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
