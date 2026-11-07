"""CLI surface contract (M0 item 0.2).

Every command in the frozen surface must exist, ``--help`` must work and exit ``0``, and every
unimplemented command must refuse honestly with exit ``4`` — never a decision-looking ``0``.
Usage mistakes (unknown command/option) exit ``1``.
"""

from __future__ import annotations

import pytest

from agentinbox.cli import main

COMMANDS = [
    "serve",
    "ask",
    "inbox",
    "answer",
    "gate",
    "export",
    "verify-log",
    "channels",
    "report",
    "doctor",
    "init",
    "version",
]

REAL = {
    "version",
    "init",
    "doctor",
    "answer",
    "inbox",
    "serve",
    "gate",
    "channels",
    "export",
    "verify-log",
}
STUBS = [command for command in COMMANDS if command not in REAL]


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out

    for command in COMMANDS:
        assert command in out, f"missing command in --help: {command}"


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_has_help(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([command, "--help"]) == 0
    assert command in capsys.readouterr().out


@pytest.mark.parametrize("command", STUBS)
def test_unimplemented_command_refuses_honestly(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([command]) == 4
    captured = capsys.readouterr()

    assert captured.out == ""
    assert "not implemented in v0.1.0" in captured.err
    assert command in captured.err


def test_stub_accepts_foreign_flags_and_still_refuses(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["ask", "--file", "ask.json", "--channel", "terminal"]) == 4
    assert "not implemented in v0.1.0" in capsys.readouterr().err


def test_unknown_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["frobnicate"]) == 1
    captured = capsys.readouterr()

    assert "invalid choice" in captured.err
    assert captured.out == ""


def test_unknown_global_option_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--frobnicate"]) == 1
    assert "unrecognized arguments" in capsys.readouterr().err


def test_version_command_is_real(capsys: pytest.CaptureFixture[str]) -> None:
    import agentinbox

    assert main(["version"]) == 0
    assert agentinbox.__version__ in capsys.readouterr().out


def test_version_flag_is_real(capsys: pytest.CaptureFixture[str]) -> None:
    import agentinbox

    assert main(["--version"]) == 0
    assert agentinbox.__version__ in capsys.readouterr().out


def test_global_flags_are_accepted_before_the_command() -> None:
    assert main(["--json", "--no-color", "version"]) == 0
