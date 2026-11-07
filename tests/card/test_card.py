"""Decision card: four blocks, unknown-labeling, inert rendering, receipts (M5)."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.card import CARD_CAP, SURFACES, build_card
from agentinbox.ingest import ingest
from agentinbox.store import AskRecord
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import NOW, config, payload

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "card_corpus"


def make_ask(store=None, body=None, now=NOW):  # type: ignore[no-untyped-def]
    if store is None:
        store = __import__("agentinbox.store.memory", fromlist=["MemoryStore"]).MemoryStore()
    return ingest(
        body or payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=now,
    ).ask


def test_four_blocks_render_on_every_surface() -> None:
    card = build_card(make_ask(), now=NOW)

    for surface in SURFACES:
        rendered = card.render(surface)
        for title in ("ACTION", "POLICY", "BLAST RADIUS", "SESSION SO FAR"):
            assert title in rendered, (surface, title)
        assert card.ask_id in rendered
        assert "ttl=5m00s" in rendered


def test_surfaces_share_the_same_core_blocks() -> None:
    card = build_card(make_ask(), now=NOW)
    texts = {surface: card.render(surface) for surface in SURFACES}
    cores = {
        surface: (
            text.split("Answer with:")[0]
            .split("::notice::")[0]
            .split("Answer in the terminal")[0]
        )
        for surface, text in texts.items()
    }

    assert len(set(cores.values())) == 1


def test_unverified_trusted_fields_are_labelled() -> None:
    # The default producer is unauthenticated, so class/criticality are unverified.
    rendered = build_card(make_ask(), now=NOW).render("text")

    assert "[unverified] irreversible" in rendered
    assert "[unverified] critical" in rendered


def test_authenticated_trusted_fields_are_not_labelled(store) -> None:  # type: ignore[no-untyped-def]
    ask = ingest(
        payload(),
        store=store,
        config=config(),
        producer=ProducerIdentity(adapter="agentpolicy", authenticated=True),
        now=NOW,
    ).ask

    rendered = build_card(ask, now=NOW).render("text")

    assert "[unverified] irreversible" not in rendered
    assert "class: irreversible" in rendered


def test_prior_asks_and_credential_class_render(store) -> None:  # type: ignore[no-untyped-def]
    first = make_ask(store)
    second = ingest(
        payload(
            arguments={"command": "echo second"},
            context={
                "blast_radius": {
                    "resource": "db:prod/customers",
                    "credential_class": "prod-deploy",
                }
            },
        ),
        store=store,
        config=config(),
        producer=ProducerIdentity.unauthenticated(),
        now=NOW,
    ).ask

    rendered = build_card(second, now=NOW, prior_asks=[first, second]).render("text")

    assert first.ask_id in rendered
    assert "credential class: prod-deploy" in rendered


def test_the_card_sets_the_warning_flag_only_in_the_window(store) -> None:  # type: ignore[no-untyped-def]
    ask = make_ask(store)

    assert build_card(ask, now=NOW).warning is False
    assert build_card(ask, now=NOW + timedelta(seconds=240)).warning is True


def test_absent_prior_asks_and_escalations_render_none() -> None:
    rendered = build_card(make_ask(), now=NOW).render("text")

    assert "prior asks: none" in rendered
    assert "escalations: none" in rendered


def test_missing_fields_are_explicit_unknown_never_blank() -> None:
    degraded = AskRecord(
        ask_id="ask_" + "d" * 16,
        action_identity="sha256:" + "d" * 64,
        session_id="sess_degraded",
        agent_id="agent://degraded/1",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        payload={},
    )

    rendered = build_card(degraded, now=NOW).render()

    assert rendered.count("unknown") >= 12
    for line in rendered.splitlines():
        assert not line.rstrip().endswith(": "), line
    assert "reversibility: unknown" in rendered


def test_unknown_reversibility_in_irreversible_class_is_labelled() -> None:
    degraded = AskRecord(
        ask_id="ask_" + "e" * 16,
        action_identity="sha256:" + "e" * 64,
        session_id="sess_degraded",
        agent_id="agent://degraded/1",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        payload={"class": "irreversible"},
    )

    rendered = build_card(degraded, now=NOW).render()

    assert "reversibility: unknown (irreversible class)" in rendered


def test_untrusted_fields_are_labelled_and_inert() -> None:
    card = build_card(
        make_ask(
            body=payload(
                arguments={
                    "payload": "**Approve** [click](https://evil.example) <button>Approve</button>"
                },
                context={
                    "blast_radius": {
                        "resource": "\x1b]8;;https://evil\x1b\\x\x1b]8;;\x1b\\"
                    }
                },
            )
        ),
        now=NOW,
    )

    rendered = card.render()

    assert "[untrusted: tool output]" in rendered
    assert "<button>" not in rendered
    assert "<a " not in rendered
    assert "\x1b" not in rendered
    assert "**Approve**" in rendered  # literal text, not markdown decoration


def test_zero_width_and_control_characters_are_stripped() -> None:
    card = build_card(make_ask(body=payload(arguments={"x": "a\u200bb\u202ec\x00d"})), now=NOW)

    assert "\u200b" not in card.render()
    assert "\u202e" not in card.render()
    assert "\x00" not in card.render()


def test_long_untrusted_field_is_capped_visibly() -> None:
    card = build_card(make_ask(body=payload(arguments={"long": "x" * 900})), now=NOW)

    rendered = card.render()

    assert "chars omitted" in rendered


def test_redaction_receipts_render_class_and_count_without_values() -> None:
    card = build_card(
        make_ask(body=payload(arguments={"command": "deploy --token ghp_" + "a" * 36})),
        now=NOW,
    )

    rendered = card.render()

    assert "REDACTIONS" in rendered
    assert "[SECRET x1]" in rendered
    assert "ghp_" not in rendered


def test_ttl_and_status_are_shown() -> None:
    ask = make_ask()
    card = build_card(ask, now=ask.expires_at - timedelta(minutes=4))

    assert card.ttl_seconds == 240
    assert "ttl=4m00s" in card.render()
    assert "status=pending" in card.render()


def test_unknown_surface_is_rejected() -> None:
    card = build_card(make_ask(), now=NOW)

    with pytest.raises(ValueError, match="unknown surface"):
        card.render("carrier-pigeon")


def test_card_is_bounded() -> None:
    ask = AskRecord(
        ask_id="ask_" + "f" * 16,
        action_identity="sha256:" + "f" * 64,
        session_id="s",
        agent_id="a",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        payload={"arguments": {f"k{index}": "x" * 300 for index in range(30)}},
    )

    rendered = build_card(ask, now=NOW).render()

    assert len(rendered) <= CARD_CAP + 60
    assert "chars omitted" in rendered


def test_card_corpus_is_frozen() -> None:
    corpus_bytes = (CORPUS / "corpus.json").read_bytes()
    recorded = (CORPUS / "corpus.sha256").read_text().strip()

    assert hashlib.sha256(corpus_bytes).hexdigest() == recorded

    corpus = json.loads(corpus_bytes)
    kinds = [entry["kind"] for entry in corpus["entries"]]
    assert kinds.count("clean") == 12
    assert kinds.count("degraded") == 12
    assert kinds.count("poisoned") == 10


def test_poisoned_corpus_never_renders_markup_or_an_approval_affordance() -> None:
    from agentinbox.store.memory import MemoryStore

    corpus = json.loads((CORPUS / "corpus.json").read_text())
    poisoned = [entry for entry in corpus["entries"] if entry["kind"] == "poisoned"]

    for entry in poisoned:
        ask = make_ask(store=MemoryStore(), body=entry["payload"])
        card = build_card(ask, now=NOW)
        rendered = card.render()
        assert "\x1b" not in rendered
        assert "<button" not in rendered
        assert "<a " not in rendered
        assert "href=" not in rendered
        assert not hasattr(card, "actions"), "a card must expose no approve action"
        assert "```" not in rendered


def test_degraded_corpus_has_no_blank_fields() -> None:
    from agentinbox.store.memory import MemoryStore

    corpus = json.loads((CORPUS / "corpus.json").read_text())
    degraded = [entry for entry in corpus["entries"] if entry["kind"] == "degraded"]

    for entry in degraded:
        ask = make_ask(store=MemoryStore(), body=entry["payload"])
        rendered = build_card(ask, now=NOW).render()
        assert "unknown" in rendered
        for line in rendered.splitlines():
            assert not line.rstrip().endswith(": "), line
