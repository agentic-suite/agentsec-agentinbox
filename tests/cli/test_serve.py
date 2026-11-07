"""``agentinbox serve``: one daemon owns the spool and drains jobs (M9)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pytest

from agentinbox.bus import JobKind, SpoolBus, new_job
from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path


def make_home(tmp_path: Path, *, desktop: bool = False) -> Path:
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    if desktop:
        text = config_path.read_text(encoding="utf-8").replace(
            "[channels.desktop]\nenabled = false",
            "[channels.desktop]\nenabled = true",
        )
        config_path.write_text(text, encoding="utf-8")
    return home


def test_serve_once_drains_the_spool(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    now = datetime.now(UTC)
    bus = SpoolBus(home / "spool", now=lambda: now)
    try:
        assert bus.publish(new_job(JobKind.DELIVER, ask_id="ask-none", now=now))
    finally:
        bus.close()

    assert main(["--home", str(home), "serve", "--once"]) == 0
    assert list((home / "spool" / "jobs").glob("*.json")) == []
    assert len(list((home / "spool" / "done").glob("*.json"))) == 1


def test_serve_refuses_a_spool_owned_by_another_daemon(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    holder = SpoolBus(home / "spool")
    try:
        assert main(["--home", str(home), "serve", "--once"]) == 4
    finally:
        holder.close()
    assert "another daemon owns the spool" in capsys.readouterr().err


def test_serve_rejects_unknown_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    assert main(["--home", str(home), "serve", "--once", "--bogus"]) == 1
    assert "unrecognized arguments" in capsys.readouterr().err


class FakeDesktop:
    instances: ClassVar[list[FakeDesktop]] = []

    def __init__(self, *, config) -> None:  # type: ignore[no-untyped-def]
        self.config = config
        self.digests: list[dict[str, object]] = []
        self.delivered: list[str] = []
        FakeDesktop.instances.append(self)

    def deliver(self, ask, card) -> None:  # type: ignore[no-untyped-def]
        self.delivered.append(ask.ask_id)

    def notify_digest(self, **kwargs: object) -> None:
        self.digests.append(kwargs)


def test_serve_hands_digest_jobs_to_the_desktop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentinbox.store import to_iso

    home = make_home(tmp_path, desktop=True)
    FakeDesktop.instances.clear()
    monkeypatch.setattr("agentinbox.cli.DesktopChannel", FakeDesktop)
    now = datetime.now(UTC)
    bus = SpoolBus(home / "spool", now=lambda: now)
    try:
        bus.publish(
            new_job(
                JobKind.DIGEST,
                ask_id="ask-0",
                now=now,
                payload={"window_start": to_iso(now), "count": 200},
            )
        )
    finally:
        bus.close()

    assert main(["--home", str(home), "serve", "--once"]) == 0
    instances = FakeDesktop.instances
    assert len(instances) == 1
    assert instances[0].digests == [
        {"window_start": now, "first_ask_id": "ask-0", "count": 200}
    ]


def test_serve_reports_a_malformed_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path, desktop=True)
    monkeypatch.setattr("agentinbox.cli.DesktopChannel", FakeDesktop)
    now = datetime.now(UTC)
    bus = SpoolBus(home / "spool", now=lambda: now)
    try:
        bus.publish(new_job(JobKind.DIGEST, ask_id="ask-0", now=now, payload={}))
    finally:
        bus.close()

    assert main(["--home", str(home), "serve", "--once"]) == 0
    assert "digest delivery failed" in capsys.readouterr().err


def test_serve_loop_stops_on_a_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = make_home(tmp_path)

    class FakeBus:
        def run(self, handler, stop) -> None:  # type: ignore[no-untyped-def]
            raise KeyboardInterrupt

        def consume(self, handler) -> int:  # type: ignore[no-untyped-def]
            return 0

        def close(self) -> None:
            return None

    monkeypatch.setattr("agentinbox.cli.load_bus", lambda *a, **k: FakeBus())
    assert main(["--home", str(home), "serve"]) == 0


def test_serve_fails_closed_without_a_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "absent"
    home.mkdir(mode=0o700)
    assert main(["--home", str(home), "serve", "--once"]) == 4
    assert "config" in capsys.readouterr().err
