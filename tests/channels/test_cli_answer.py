"""CLI answer/inbox: scripts can never approve (M7 item 7.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.store import AskStatus
from agentinbox.store.sqlite import SqliteStore
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload

CONFIG = """
[classes.irreversible]
ttl_seconds = 300
warn_seconds = 60
self_review = "deny"
require_reason_on_deny = true
ladder = ["tier-1"]

[roster.tier-1]
terminal = ["alice"]

[channels.terminal]
enabled = true

[store]
driver = "sqlite"
"""


def home_with_ask(tmp_path: Path):
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    config_path.write_text(CONFIG, encoding="utf-8")
    config = load_config(config_path)
    moment = datetime.now(UTC)
    body = payload()
    expires = (moment + timedelta(minutes=5)).isoformat(timespec="microseconds")
    body["expires_at"] = expires.replace("+00:00", "Z")
    store = SqliteStore(home / "inbox.db")
    ask = ingest(
        body,
        store=store,
        config=config,
        producer=ProducerIdentity.unauthenticated(),
        now=moment,
    ).ask
    store.close()
    return home, config_path, ask


def test_non_interactive_answer_returns_pending_and_never_approves(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    home, _config_path, ask = home_with_ask(tmp_path)

    code = main(["--home", str(home), "answer", ask.ask_id, "--approve"])

    assert code == 5
    assert '"status": "pending"' in capsys.readouterr().out
    store = SqliteStore(home / "inbox.db")
    try:
        stored = store.get(ask.ask_id)
        assert stored is not None
        assert stored.status is AskStatus.PENDING
    finally:
        store.close()


def test_inbox_lists_pending_asks(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    home, _config_path, ask = home_with_ask(tmp_path)

    code = main(["--home", str(home), "inbox"])

    assert code == 5
    out = capsys.readouterr().out
    assert ask.ask_id in out
    assert "irreversible" in out


def test_inbox_json_shape(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    home, _config_path, ask = home_with_ask(tmp_path)

    assert main(["--json", "--home", str(home), "inbox"]) == 5
    payload_text = capsys.readouterr().out
    assert ask.ask_id in payload_text
    assert '"class": "irreversible"' in payload_text


def test_unknown_ask_is_a_deny(tmp_path: Path) -> None:
    home, _config_path, _ask = home_with_ask(tmp_path)

    assert main(["--home", str(home), "answer", "ask_missing", "--approve"]) == 2


def test_answer_bad_config_returns_unavailable(tmp_path: Path) -> None:
    assert main(["--home", str(tmp_path / "missing"), "answer", "ask_x", "--approve"]) == 4


def test_inbox_bad_config_returns_unavailable(tmp_path: Path) -> None:
    assert main(["--home", str(tmp_path / "missing"), "inbox"]) == 4


def test_inbox_with_no_pending_returns_zero(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    home, _config_path, ask = home_with_ask(tmp_path)
    store = SqliteStore(home / "inbox.db")
    try:
        transition(
            store,
            ask.ask_id,
            AskStatus.CANCELLED,
            kind="cancelled",
            at=datetime.now(UTC),
        )
    finally:
        store.close()

    assert main(["--home", str(home), "inbox"]) == 0
    assert "no pending asks" in capsys.readouterr().out


def test_answer_as_without_allow_as_returns_unavailable(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    home, _config_path, ask = home_with_ask(tmp_path)

    class _TTY:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", _TTY())

    assert main(["--home", str(home), "answer", ask.ask_id, "--approve", "--as", "bob"]) == 4
