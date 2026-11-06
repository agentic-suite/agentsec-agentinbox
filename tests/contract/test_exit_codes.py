"""Exit-code contract tests (M0 item 0.3)."""

from __future__ import annotations

import pytest
from tests.contract.exit_codes import EXIT_CODES, FAILURE_CODES, RETRY_CODES

from agentinbox import exit_codes
from agentinbox.cli import main


def test_enum_matches_the_frozen_literal_map() -> None:
    actual = {member.name: int(member) for member in exit_codes.ExitCode}

    assert actual == EXIT_CODES


def test_codes_are_int_compatible() -> None:
    assert int(exit_codes.ExitCode.APPROVED) == 0
    assert exit_codes.ExitCode.DENIED == 2


def test_ci_classification_is_from_one_place() -> None:
    assert all(exit_codes.is_failure(code) for code in FAILURE_CODES)
    assert all(exit_codes.is_retry(code) for code in RETRY_CODES)
    assert not exit_codes.is_failure(exit_codes.ExitCode.APPROVED)
    assert not exit_codes.is_failure(exit_codes.ExitCode.PENDING)
    assert not exit_codes.is_retry(exit_codes.ExitCode.UNAVAILABLE)


def test_unavailable_is_fail_closed_not_usage() -> None:
    assert exit_codes.ExitCode.UNAVAILABLE != exit_codes.ExitCode.USAGE


def test_stubs_use_the_contract_constant(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ask"]) == exit_codes.ExitCode.UNAVAILABLE
    capsys.readouterr()


def test_usage_errors_never_use_the_denied_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["frobnicate"]) == exit_codes.ExitCode.USAGE
    assert main(["--frobnicate"]) == exit_codes.ExitCode.USAGE
    capsys.readouterr()
