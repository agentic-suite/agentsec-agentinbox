"""Attack packs are release-blocking and a broken gate fixture fails (M22 item 22.2)."""

from __future__ import annotations

import pytest

from agentinbox.packs import flood, injection, main, run_packs, spoof_replay_forge


def test_spoof_replay_forge_pack_is_green() -> None:
    result = spoof_replay_forge()

    assert result.ok, result.detail


def test_injection_pack_is_green() -> None:
    result = injection()

    assert result.ok, result.detail


def test_flood_pack_is_green() -> None:
    result = flood(total=200)

    assert result.ok, result.detail


def test_run_packs_and_cli(capsys: pytest.CaptureFixture[str]) -> None:
    report = run_packs()
    assert report.ok, [result.detail for result in report.results if not result.ok]
    assert {result.name for result in report.results} == {
        "spoof-replay-forge",
        "injection",
        "flood",
    }

    assert main([]) == 0
    out = capsys.readouterr().out
    assert "spoof-replay-forge" in out
    assert "flood" in out


def test_a_broken_gate_fixture_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mutation-style negative fixture: if secret comparison always succeeds, the wrong-secret
    # attempt approves and the spoof pack must go red (the gate would ship a broken build).
    monkeypatch.setattr("agentinbox.answers.secret_matches", lambda _claim, _secret: True)
    result = spoof_replay_forge()

    assert not result.ok
    assert "wrong secret" in result.detail or "replayed" in result.detail
