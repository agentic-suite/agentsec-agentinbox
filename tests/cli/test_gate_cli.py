"""``agentinbox gate`` CLI wiring: exit codes and the printed card (M10)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.store import AskStatus, utcnow
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def seed(home: Path, *, status: AskStatus | None = None) -> str:
    config_path = resolve_config_path(home)
    config = load_config(config_path)
    store = load_store("sqlite", home=home)
    now = utcnow()
    try:
        ask = ingest(
            payload(
                expires_at=(now + timedelta(seconds=300))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        ).ask
        if status is not None:
            assert transition(
                store,
                ask.ask_id,
                status,
                kind="answered",
                at=now,
                principal="alice",
                channel="terminal",
            )
    finally:
        store.close()
    return ask.ask_id


def test_pending_gate_returns_five(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    ask_id = seed(home)

    assert main(["--home", str(home), "gate", "--ask", ask_id]) == 5
    captured = capsys.readouterr()
    assert ask_id in captured.out
    assert "fingerprint" in captured.out
    assert "pending" in captured.out


def test_approved_gate_returns_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    ask_id = seed(home, status=AskStatus.APPROVED)

    assert main(["--home", str(home), "gate", "--ask", ask_id]) == 0
    assert "approved" in capsys.readouterr().out


def test_denied_gate_returns_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    ask_id = seed(home, status=AskStatus.DENIED)

    assert main(["--home", str(home), "gate", "--ask", ask_id]) == 2
    assert "denied" in capsys.readouterr().out


def test_unknown_ask_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "gate", "--ask", "ask_missing"]) == 4
    assert "unknown" in capsys.readouterr().out


def test_lapsed_budget_returns_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    ask_id = seed(home)

    assert (
        main(
            [
                "--home",
                str(home),
                "gate",
                "--ask",
                ask_id,
                "--wait",
                "--timeout",
                "0.01",
            ]
        )
        == 3
    )
    assert "budget" in capsys.readouterr().out


def test_missing_ask_flag_is_a_usage_error(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "gate"]) == 1


def test_bad_config_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    (home / "config.toml").write_text("[classes.x]\nttl_seconds = 0\n", encoding="utf-8")
    assert main(["--home", str(home), "gate", "--ask", "ask_any"]) == 4
    assert "ttl_seconds" in capsys.readouterr().err
