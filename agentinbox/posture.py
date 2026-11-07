"""Own-posture checks (M22 item 22.6): no-ML manifest, SBOM dry run, security.txt.

Design: ``docs/design/v0.1.0/security-closeout.md`` §6. These are repo-level checks, not claims
about a deployment; publishing ``security.txt`` and signing the SBOM remain release steps.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentinbox import __version__

#: Dependency-name fragments that would put a model in the decision path (PRD 06 / "no ML").
FORBIDDEN_DEPENDENCIES = (
    "torch",
    "tensorflow",
    "keras",
    "scikit-learn",
    "sklearn",
    "transformers",
    "openai",
    "anthropic",
    "llama",
    "onnx",
    "numpy",
    "pandas",
)

DEFAULT_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
DEFAULT_SECURITY_TXT = Path(__file__).resolve().parents[1] / "docs" / "security.txt"


def dependency_manifest(pyproject: Path | None = None) -> dict[str, Any]:
    """Return the runtime dependency set and any forbidden (ML) package."""
    source = Path(pyproject) if pyproject is not None else DEFAULT_PYPROJECT
    document = tomllib.loads(source.read_text(encoding="utf-8"))
    project = document.get("project", {})
    runtime = [str(item) for item in project.get("dependencies", [])]
    violations = [
        dependency
        for dependency in runtime
        if any(fragment in dependency.lower() for fragment in FORBIDDEN_DEPENDENCIES)
    ]
    return {
        "runtime": runtime,
        "violations": violations,
        "ok": not violations,
        "zero_runtime_dependencies": not runtime,
    }


def generate_sbom(pyproject: Path | None = None) -> dict[str, Any]:
    """A CycloneDX 1.5 document for the package (dry run; signing happens at release)."""
    manifest = dependency_manifest(pyproject)
    components = [
        {
            "type": "library",
            "name": dependency.split()[0].split("=")[0].split("<")[0].split(">")[0],
            "scope": "required",
        }
        for dependency in manifest["runtime"]
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            "component": {
                "type": "application",
                "name": "agentsec-agentinbox",
                "version": __version__,
                "licenses": [{"license": {"id": "Apache-2.0"}}],
            },
        },
        "components": components,
    }


def check_security_txt(path: Path | None = None) -> list[str]:
    """Validate a committed RFC 9116 ``security.txt``; return problems (empty = valid)."""
    target = Path(path) if path is not None else DEFAULT_SECURITY_TXT
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"security.txt is unreadable: {exc}"]
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        fields[key.strip().lower()] = value.strip()

    problems: list[str] = []
    if not fields.get("contact"):
        problems.append("missing Contact")
    if not fields.get("policy"):
        problems.append("missing Policy")
    expires = fields.get("expires")
    if not expires:
        problems.append("missing Expires")
    else:
        try:
            moment = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        except ValueError:
            problems.append("Expires is not ISO-8601")
        else:
            if moment <= datetime.now(UTC):
                problems.append("Expires is in the past")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentinbox-posture", description="own-posture checks (M22)"
    )
    parser.add_argument("command", choices=("manifest", "sbom", "security-txt"))
    args = parser.parse_args(argv)

    if args.command == "manifest":
        manifest = dependency_manifest()
        print(
            f"runtime dependencies: {len(manifest['runtime'])} "
            f"(zero: {manifest['zero_runtime_dependencies']})"
        )
        for violation in manifest["violations"]:
            print(f"forbidden dependency: {violation}", file=sys.stderr)
        return 0 if manifest["ok"] else 1
    if args.command == "sbom":
        import json

        print(json.dumps(generate_sbom(), indent=2, sort_keys=True))
        return 0
    problems = check_security_txt()
    for problem in problems:
        print(problem, file=sys.stderr)
    return 0 if not problems else 1


__all__ = [
    "DEFAULT_PYPROJECT",
    "DEFAULT_SECURITY_TXT",
    "FORBIDDEN_DEPENDENCIES",
    "check_security_txt",
    "dependency_manifest",
    "generate_sbom",
    "main",
]
