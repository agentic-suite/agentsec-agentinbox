"""Own-posture checks: no-ML manifest, SBOM dry run, security.txt (M22 item 22.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.posture import (
    check_security_txt,
    dependency_manifest,
    generate_sbom,
    main,
)


def test_the_runtime_has_zero_dependencies_and_no_ml() -> None:
    manifest = dependency_manifest()

    assert manifest["ok"]
    assert manifest["zero_runtime_dependencies"]
    assert manifest["runtime"] == []


def test_a_forbidden_dependency_fails_the_manifest(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nversion = "0"\ndependencies = ["torch>=2"]\n',
        encoding="utf-8",
    )

    manifest = dependency_manifest(pyproject)

    assert not manifest["ok"]
    assert manifest["violations"] == ["torch>=2"]


def test_sbom_is_cyclonedx_and_names_the_package() -> None:
    bom = generate_sbom()

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.5"
    assert bom["metadata"]["component"]["name"] == "agentsec-agentinbox"
    assert bom["components"] == []


def test_security_txt_is_valid_and_an_expired_file_fails(tmp_path: Path) -> None:
    assert check_security_txt() == []

    expired = tmp_path / "security.txt"
    expired.write_text(
        "Contact: mailto:security@example.com\nPolicy: https://example.com/policy\n"
        "Expires: 2020-01-01T00:00:00.000Z\n",
        encoding="utf-8",
    )
    problems = check_security_txt(expired)
    assert "Expires is in the past" in problems


def test_security_txt_validation_reports_every_problem(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("Preferred-Languages: en\n", encoding="utf-8")
    problems = check_security_txt(empty)
    assert "missing Contact" in problems
    assert "missing Policy" in problems
    assert "missing Expires" in problems

    malformed = tmp_path / "malformed.txt"
    malformed.write_text(
        "Contact: mailto:x@example.com\nPolicy: https://example.com\n"
        "Expires: not-a-date\n",
        encoding="utf-8",
    )
    assert "Expires is not ISO-8601" in check_security_txt(malformed)
    assert check_security_txt(tmp_path / "absent.txt")[0].startswith(
        "security.txt is unreadable"
    )


def test_posture_cli_modes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["manifest"]) == 0
    assert "runtime dependencies" in capsys.readouterr().out

    assert main(["sbom"]) == 0
    assert "CycloneDX" in capsys.readouterr().out

    assert main(["security-txt"]) == 0


def test_posture_cli_fails_on_a_forbidden_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nversion = "0"\ndependencies = ["torch>=2"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("agentinbox.posture.DEFAULT_PYPROJECT", pyproject)

    assert main(["manifest"]) == 1
    assert "forbidden dependency" in capsys.readouterr().err


def test_posture_cli_fails_on_an_invalid_security_txt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "security.txt"
    bad.write_text("Contact: mailto:x@example.com\n", encoding="utf-8")
    monkeypatch.setattr("agentinbox.posture.DEFAULT_SECURITY_TXT", bad)

    assert main(["security-txt"]) == 1
    assert "Policy" in capsys.readouterr().err
