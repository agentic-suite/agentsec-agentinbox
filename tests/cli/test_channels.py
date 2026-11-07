"""``agentinbox channels``: configured channels and honest health (M13 item 13.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox import cli
from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    return home


def rewrite(home: Path, *, old: str, new: str) -> None:
    path = home / "config.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
    )


def test_scaffold_reports_terminal_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "channels"]) == 0
    out = capsys.readouterr().out
    assert "terminal: enabled (ok)" in out
    assert "desktop: disabled" in out
    assert "webhook: disabled" in out


def test_webhook_with_missing_refs_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)
    rewrite(
        home,
        old="[channels.webhook]\nenabled = false",
        new=(
            '[channels.webhook]\nenabled = true\n'
            'url_ref = "env:NO_SUCH_HOOK_URL"\n'
            'hmac_key_ref = "env:NO_SUCH_HOOK_KEY"'
        ),
    )

    assert main(["--home", str(home), "channels"]) == 4
    assert "webhook: enabled (unavailable" in capsys.readouterr().out


def test_headless_desktop_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = make_home(tmp_path)
    rewrite(
        home,
        old="[channels.desktop]\nenabled = false",
        new="[channels.desktop]\nenabled = true",
    )
    monkeypatch.setattr(
        cli, "desktop_availability", lambda **_: (False, "headless SSH session")
    )

    assert main(["--home", str(home), "channels"]) == 4
    assert "headless" in capsys.readouterr().out


def test_missing_config_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "absent"
    home.mkdir(mode=0o700)
    assert main(["--home", str(home), "channels"]) == 4
    assert "config" in capsys.readouterr().err
