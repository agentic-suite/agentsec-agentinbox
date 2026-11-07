"""Packaging contract tests (M0 item 0.1).

The distribution is ``agentsec-agentinbox``; the import package and console script are
``agentinbox``; both ``agentinbox`` and ``python -m agentinbox`` must work; and the runtime
must have **zero** third-party dependencies so the install stays local-first and standalone.
"""

from __future__ import annotations

import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path


def test_package_importable_with_version() -> None:
    import agentinbox

    version = agentinbox.__version__

    assert re.fullmatch(r"\d+\.\d+\.\d+(?:\.dev\d+)?", version), version


def test_distribution_metadata_is_agentsec_agentinbox() -> None:
    dist = metadata.distribution("agentsec-agentinbox")

    assert dist.metadata["Name"].lower() == "agentsec-agentinbox"
    assert not dist.metadata["Requires-Dist"] or all(
        "extra ==" in req for req in dist.metadata.get_all("Requires-Dist") or []
    ), "runtime must have no third-party dependencies"


def test_console_script_entry_point_declared() -> None:
    entry_points = metadata.entry_points(group="console_scripts")
    match = [ep for ep in entry_points if ep.name == "agentinbox"]

    assert match, "agentinbox console script is not installed"
    assert match[0].value == "agentinbox.cli:main"


def test_module_invocation_reports_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "agentinbox", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("agentinbox ")


def test_console_script_and_module_agree() -> None:
    import agentinbox

    console_script = Path(sys.executable).parent / "agentinbox"
    via_module = subprocess.run(
        [sys.executable, "-m", "agentinbox", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    via_script = subprocess.run(
        [str(console_script), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert via_module.returncode == 0
    assert via_script.returncode == 0, via_script.stderr
    assert via_module.stdout == via_script.stdout
    assert agentinbox.__version__ in via_module.stdout
