"""``doctor`` desktop reachability check (M8 item 8.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox import doctor
from agentinbox.cli import main
from agentinbox.config import init_home, resolve_config_path


def make_home(tmp_path: Path, *, desktop: bool = False) -> Path:
    home = tmp_path / "home"
    config_path = resolve_config_path(home)
    init_home(home, config_path)
    text = config_path.read_text(encoding="utf-8")
    text = text.replace(
        "[channels.desktop]\nenabled = false",
        f"[channels.desktop]\nenabled = {'true' if desktop else 'false'}",
    )
    config_path.write_text(text, encoding="utf-8")
    return home


def test_disabled_desktop_is_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = make_home(tmp_path)

    assert main(["--home", str(home), "doctor"]) == 0
    out = capsys.readouterr().out
    assert "desktop" in out
    assert "disabled" in out


def test_enabled_but_unavailable_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = make_home(tmp_path, desktop=True)
    monkeypatch.setattr(
        doctor, "desktop_availability", lambda **_: (False, "headless SSH session")
    )

    assert main(["--home", str(home), "doctor"]) == 4
    out = capsys.readouterr().out
    assert "desktop" in out
    assert "headless" in out


def test_enabled_and_available_is_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = make_home(tmp_path, desktop=True)
    monkeypatch.setattr(doctor, "desktop_availability", lambda **_: (True, "osascript"))

    assert main(["--home", str(home), "doctor"]) == 0
    assert "desktop" in capsys.readouterr().out
