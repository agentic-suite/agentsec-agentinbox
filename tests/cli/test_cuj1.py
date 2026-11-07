"""CUJ-1: init → first recorded approval stays well under the five-minute promise (M18 item 18.4).

The test measures the local path (init → ask → authenticated answer → resolve). The full
install-to-approval timing on the field-test box is recorded at M24; `pip install` is excluded here
because CI has no install step of its own.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.store import AskRecord, utcnow
from agentinbox.store.loader import load_store

PROMISE_SECONDS = 300


def test_init_to_first_approval_is_well_under_the_promise(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    started = time.monotonic()

    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    result: dict[str, int] = {}

    def produce() -> None:
        result["code"] = main(["--home", str(home), "ask", "--exec", "true"])

    thread = threading.Thread(target=produce, daemon=True)
    thread.start()

    ask = _wait_for_pending(home)
    _approve(home, ask)
    thread.join(timeout=10)

    elapsed = time.monotonic() - started
    assert result["code"] == 0
    assert elapsed < PROMISE_SECONDS


def _wait_for_pending(home: Path, *, timeout: float = 8.0) -> AskRecord:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        store = load_store("sqlite", home=home)
        try:
            pending = store.list_pending(now=utcnow(), limit=10)
        finally:
            store.close()
        if pending:
            return pending[0]
        time.sleep(0.02)
    raise AssertionError("no ask appeared")


def _approve(home: Path, ask: AskRecord) -> None:
    config = load_config(resolve_config_path(home))
    store = load_store("sqlite", home=home)
    now = utcnow()
    try:
        minted = mint_claim(store, ask, channel="terminal", tier=None, now=now)
        AnswerVerifier(store, config, now=lambda: now).submit(
            AnswerRequest(
                ask_id=ask.ask_id,
                claim_id=minted.claim.claim_id,
                secret=minted.secret,
                principal="alice",
                channel="terminal",
                decision="approve",
                typed_confirmation="run_command",
            ),
            channel_authenticated=True,
        )
    finally:
        store.close()
