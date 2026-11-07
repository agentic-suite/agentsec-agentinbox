"""Offline day: local-only completeness and no telemetry (M21 item 21.5, CUJ-12/SC-26)."""

from __future__ import annotations

import json
import socket
from datetime import timedelta
from pathlib import Path

import pytest

import agentinbox
from agentinbox.card import build_card
from agentinbox.cli import main
from agentinbox.config import (
    ChannelConfig,
    ClassConfig,
    Config,
    init_home,
    load_config,
    resolve_config_path,
)
from agentinbox.ingest import ingest
from agentinbox.lifecycle import transition
from agentinbox.ops import offline_posture
from agentinbox.store import AskStatus, utcnow
from agentinbox.store.loader import load_store
from agentinbox.trust import ProducerIdentity
from tests.ask.conftest import payload


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def test_offline_posture_ignores_local_channels() -> None:
    config = Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        channels={
            "terminal": ChannelConfig(enabled=True),
            "desktop": ChannelConfig(enabled=True),
        },
    )
    posture = offline_posture(config)

    assert posture.offline_complete is True
    assert posture.external_channels == ()
    assert "offline-complete" in posture.detail


def test_offline_posture_names_an_enabled_external_channel() -> None:
    config = Config(
        channels={
            "terminal": ChannelConfig(enabled=True),
            "webhook": ChannelConfig(
                enabled=True,
                url_ref="env:WEBHOOK_URL",
                hmac_key_ref="env:WEBHOOK_KEY",
            ),
        }
    )
    posture = offline_posture(config)

    assert posture.offline_complete is False
    assert posture.external_channels == ("webhook",)
    assert "webhook" in posture.detail


def test_doctor_reports_offline_mode_green(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "offline" in out
    assert "offline-complete" in out


def test_doctor_warns_when_an_external_channel_is_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("WEBHOOK_KEY", "key")
    home = make_home(tmp_path)
    config_path = resolve_config_path(home)
    text = config_path.read_text(encoding="utf-8").replace(
        "[channels.webhook]\nenabled = false",
        '[channels.webhook]\nenabled = true\nurl_ref = "env:WEBHOOK_URL"\n'
        'hmac_key_ref = "env:WEBHOOK_KEY"',
    )
    config_path.write_text(text, encoding="utf-8")

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "offline" in out
    assert "webhook" in out


def block_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    original = socket.socket.connect

    def guarded(self, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) else address
        if host in {"127.0.0.1", "::1", "localhost"}:
            return original(self, address)
        raise AssertionError(f"offline day attempted a network call to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    original_ex = socket.socket.connect_ex

    def guarded_ex(self, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) else address
        if host in {"127.0.0.1", "::1", "localhost"}:
            return original_ex(self, address)
        raise AssertionError(f"offline day attempted a network call to {address!r}")

    monkeypatch.setattr(socket.socket, "connect_ex", guarded_ex)


def test_offline_day_terminal_ci_audit_export_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    block_external_network(monkeypatch)
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))
    now = utcnow()
    store = load_store("sqlite", home=home)
    try:
        ask = ingest(
            payload(
                expires_at=(now + timedelta(minutes=5))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            ),
            store=store,
            config=config,
            producer=ProducerIdentity.unauthenticated(),
            now=now,
        ).ask

        card = build_card(ask, now=now, transitions=store.transitions_for(ask.ask_id))
        rendered = card.render("terminal")
        assert ask.ask_id in rendered
        assert "irreversible" in rendered

        assert transition(
            store,
            ask.ask_id,
            AskStatus.APPROVED,
            kind="answer",
            at=now,
            principal="alice",
            channel="terminal",
            detail={"decision": "approved"},
        )
    finally:
        store.close()

    out = tmp_path / "export.jsonl"
    assert main(["--home", str(home), "export", "--ask", ask.ask_id, "--out", str(out)]) == 0
    assert out.exists()
    capsys.readouterr()

    assert main(["--home", str(home), "verify-log"]) == 0
    assert "verify" in capsys.readouterr().out
    assert main(["--home", str(home), "report", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["local_only"] is True
    assert report["total_asks"] == 1
    assert main(["--home", str(home), "doctor"]) == 0
    assert "offline-complete" in capsys.readouterr().out


def test_the_only_network_code_is_the_explicit_adapters() -> None:
    package = Path(agentinbox.__file__).parent
    allowed = {"webhook.py", "agentpolicy.py"}
    offenders = []
    for path in package.rglob("*.py"):
        if path.name in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "urllib.request" in text or "http.client" in text:
            offenders.append(path.relative_to(package))
    assert offenders == []


def test_the_scaffold_disables_external_channels(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    config = load_config(resolve_config_path(home))

    assert config.channels["terminal"].enabled is True
    assert config.channels["desktop"].enabled is False
    assert config.channels["webhook"].enabled is False
    assert offline_posture(config).offline_complete is True
