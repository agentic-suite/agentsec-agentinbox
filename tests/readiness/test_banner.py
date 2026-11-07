"""Quality banner and similar-case guidance (M26 item 26.5, R83/R85)."""

from __future__ import annotations

from agentinbox.card import build_card
from agentinbox.ingest import ingest
from agentinbox.readiness import similar_cases
from agentinbox.store.memory import MemoryStore
from agentinbox.trust import ProducerIdentity
from tests.readiness.conftest import NOW, config, good_body, weak_body


def _signed() -> ProducerIdentity:
    return ProducerIdentity(adapter="agentpolicy", authenticated=True, principal="maya@team")


def test_a_weak_ask_renders_its_banner_above_the_blocks() -> None:
    store = MemoryStore()
    try:
        ask = ingest(
            weak_body(), store=store, config=config(), producer=_signed(), now=NOW
        ).ask
        rendered = build_card(ask, now=NOW).render("terminal")
    finally:
        store.close()

    assert "READINESS: yellow" in rendered
    assert rendered.index("READINESS:") < rendered.index("ACTION")
    assert "missing" in rendered


def test_a_green_ask_hides_the_banner() -> None:
    store = MemoryStore()
    try:
        ask = ingest(
            good_body(), store=store, config=config(), producer=_signed(), now=NOW
        ).ask
        rendered = build_card(ask, now=NOW).render("terminal")
    finally:
        store.close()

    assert "READINESS:" not in rendered


def test_similar_cases_are_labelled_precedent_and_limited_to_three() -> None:
    store = MemoryStore()
    try:
        first = ingest(
            good_body(session_id="s1", arguments={"command": "psql -c 'select 1'"}),
            store=store,
            config=config(),
            producer=_signed(),
            now=NOW,
        ).ask
        second = ingest(
            good_body(session_id="s2", arguments={"command": "psql -c 'select 2'"}),
            store=store,
            config=config(),
            producer=_signed(),
            now=NOW,
        ).ask
        current = ingest(
            good_body(session_id="s3", arguments={"command": "psql -c 'select 3'"}),
            store=store,
            config=config(),
            producer=_signed(),
            now=NOW,
        ).ask
        cases = similar_cases(store, current)
        rendered = build_card(
            current, now=NOW, similar_cases=cases
        ).render("terminal")
    finally:
        store.close()

    assert {case["ask_id"] for case in cases} == {first.ask_id, second.ask_id}
    assert "similar cases: precedent only" in rendered
    assert first.ask_id in rendered


def test_banner_reports_contradictions_even_in_the_green_band() -> None:
    from agentinbox.readiness import banner_for

    line = banner_for(
        {
            "band": "green",
            "contradictions": ["staging_vs_prod"],
            "missing": [],
            "evidence": "strong",
        }
    )
    assert line is not None
    assert "contradictions: staging_vs_prod" in line
