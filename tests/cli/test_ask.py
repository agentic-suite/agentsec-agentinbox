"""``agentinbox ask``: --file / --exec only execute on allow (M18 item 18.2)."""

from __future__ import annotations

import json
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

from agentinbox.answers import AnswerRequest, AnswerVerifier
from agentinbox.claims import mint_claim
from agentinbox.cli import main
from agentinbox.config import init_home, load_config, resolve_config_path
from agentinbox.contract import compute_action_identity
from agentinbox.store import AskRecord, utcnow
from agentinbox.store.loader import load_store
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def wait_for_pending(
    home: Path,
    *,
    timeout: float = 8.0,
    thread: threading.Thread | None = None,
    result: dict[str, int] | None = None,
) -> AskRecord:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if thread is not None and not thread.is_alive():
            raise AssertionError(f"the ask producer exited early: {result}")
        store = load_store("sqlite", home=home)
        try:
            pending = store.list_pending(now=utcnow(), limit=10)
        finally:
            store.close()
        if pending:
            return pending[0]
        time.sleep(0.02)
    raise AssertionError("the ask never appeared")


def answer(home: Path, ask: AskRecord, *, decision: str) -> None:
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
                decision=decision,
                reason="too broad" if decision == "deny" else None,
                typed_confirmation="run_command" if decision == "approve" else None,
            ),
            channel_authenticated=True,
        )
    finally:
        store.close()


def run_in_thread(argv: list[str]) -> tuple[threading.Thread, dict[str, int]]:
    result: dict[str, int] = {}

    def run() -> None:
        try:
            result["code"] = main(argv)
        except BaseException as exc:  # surfaced by the tests instead of a thread warning
            result["error"] = repr(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


def test_exec_runs_only_after_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = make_home(tmp_path)
    marker = tmp_path / "executed"

    thread, result = run_in_thread(
        ["--home", str(home), "ask", "--exec", f"touch {marker}"]
    )
    ask = wait_for_pending(home, thread=thread, result=result)
    answer(home, ask, decision="approve")
    thread.join(timeout=10)

    assert result["code"] == 0
    assert marker.exists()


def test_exec_never_runs_on_deny(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = make_home(tmp_path)
    marker = tmp_path / "never"

    thread, result = run_in_thread(
        ["--home", str(home), "ask", "--exec", f"touch {marker}"]
    )
    ask = wait_for_pending(home, thread=thread, result=result)
    answer(home, ask, decision="deny")
    thread.join(timeout=10)

    assert result["code"] == 2
    assert not marker.exists()


def test_exec_is_not_run_when_the_ask_expires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = make_home(tmp_path)
    marker = tmp_path / "expired"

    code = main(
        [
            "--home",
            str(home),
            "ask",
            "--exec",
            f"touch {marker}",
            "--ttl",
            "1",
        ]
    )

    assert code == 3
    assert not marker.exists()


def test_ask_file_returns_the_resolve_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = make_home(tmp_path)
    now = utcnow()
    arguments = {"command": "echo file"}
    body = payload(
        ask_id="ask_0123456789abcdef",
        arguments=arguments,
        action_identity=compute_action_identity(
            tool="shell", action="run_command", arguments=arguments
        ),
        expires_at=(now + timedelta(minutes=5))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
    )
    ask_file = tmp_path / "ask.json"
    ask_file.write_text(json.dumps(body), encoding="utf-8")

    thread, result = run_in_thread(
        ["--home", str(home), "--json", "ask", "--file", str(ask_file)]
    )
    ask = wait_for_pending(home, thread=thread, result=result)
    answer(home, ask, decision="approve")
    thread.join(timeout=10)

    assert result["code"] == 0
    assert '"reason_code": "allow_ask_approved"' in capsys.readouterr().out


def test_ask_publishes_while_a_daemon_owns_the_spool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentinbox.bus import SpoolBus

    monkeypatch.setattr("agentinbox.cli.getpass.getuser", lambda: "requester")
    home = make_home(tmp_path)
    marker = tmp_path / "published"
    daemon_bus = SpoolBus(home / "spool")
    try:
        thread, result = run_in_thread(
            ["--home", str(home), "ask", "--exec", f"touch {marker}"]
        )
        ask = wait_for_pending(home, thread=thread, result=result)

        jobs = []
        assert daemon_bus.consume(jobs.append) == 1
        assert jobs[0].ask_id == ask.ask_id

        answer(home, ask, decision="approve")
        thread.join(timeout=10)
    finally:
        daemon_bus.close()

    assert result["code"] == 0
    assert marker.exists()


def test_ask_requires_exactly_one_source(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "ask"]) == 1


def test_ask_file_errors_are_fail_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "ask", "--file", str(tmp_path / "missing")]) == 4
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    assert main(["--home", str(home), "ask", "--file", str(bad)]) == 4
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert main(["--home", str(home), "ask", "--file", str(invalid)]) == 4
    assert capsys.readouterr().err


def test_ask_with_an_unknown_class_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert (
        main(["--home", str(home), "ask", "--exec", "true", "--class", "nope"]) == 4
    )
    assert "unknown class" in capsys.readouterr().err


def test_ask_with_an_empty_exec_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "ask", "--exec", "   "]) == 1
    assert "non-empty" in capsys.readouterr().err
