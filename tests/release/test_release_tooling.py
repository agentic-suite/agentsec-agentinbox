"""M33 33.2 — the release gate commands must actually execute via ``python -m``.

The modules expose ``main()`` but originally had no ``__main__`` guard, so
``make packs``/``scan``/``posture`` were silent no-ops. These subprocess checks
pin the real CLI entry points.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(*args: str, cwd: Path = REPO) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_claims_lint_module_entrypoint_fails_a_seeded_overclaim(tmp_path: Path) -> None:
    bad = tmp_path / "README.md"
    bad.write_text("agentinbox is enterprise-ready\n", encoding="utf-8")
    result = run("agentinbox.claimslint", str(bad))
    assert result.returncode == 1
    assert "ENTERPRISE_READY" in result.stderr


def test_scanner_module_entrypoint_runs_the_self_test() -> None:
    result = run("agentinbox.scanner", "--self-test")
    assert result.returncode == 0
    assert "seeded" in result.stdout


def test_packs_module_entrypoint_runs_the_release_packs() -> None:
    result = run("agentinbox.packs")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_posture_module_entrypoint_runs_manifest_and_security_txt() -> None:
    manifest = run("agentinbox.posture", "manifest")
    assert manifest.returncode == 0, manifest.stderr
    security = run("agentinbox.posture", "security-txt")
    assert security.returncode == 0, security.stderr
