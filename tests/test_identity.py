"""Repository identity & governance docs (M0 item 0.7).

The repo must describe what actually exists right now — no "installable" claim before the
package installs, and no placeholder governance files.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_readme_is_current_not_a_future_claim() -> None:
    readme = read("README.md")

    assert "code not started" not in readme
    # v0.1.0 shipped; the README must say so and keep the known-issue caveat.
    assert "released" in readme.lower()
    assert "known issues" in readme.lower()
    assert "47 pass / 6 fail" in readme.lower()


def test_readme_documents_the_working_install() -> None:
    readme = read("README.md")

    assert "make setup" in readme
    assert "agentinbox --version" in readme
    assert "zero" in readme.lower() or "no runtime dependencies" in readme.lower()


def test_readme_links_the_design_and_contributing_docs() -> None:
    readme = read("README.md")

    assert "docs/design/v0.1.0/foundation.md" in readme
    assert "CONTRIBUTING.md" in readme


def test_contributing_exists_and_links_the_plan_of_record() -> None:
    contributing = read("CONTRIBUTING.md")

    assert "docs/prd/05-features.md" in contributing
    assert "docs/wbs/v0.1.0/wbs-v0.1.0-index.md" in contributing
    assert "docs/prd/12-traceability.md" in contributing


def test_contributing_states_the_working_rules() -> None:
    contributing = read("CONTRIBUTING.md").lower()

    assert "test-first" in contributing or "red" in contributing
    assert "signed-off-by" in contributing


def test_codeowners_has_no_placeholder() -> None:
    owners = read("CODEOWNERS")

    assert "Replace with" not in owners
    assert "@" in owners


def test_security_policy_points_private_reports() -> None:
    security = read("SECURITY.md").lower()

    assert "privately" in security
    assert "security" in security


def test_license_is_apache_2() -> None:
    assert "Apache License" in read("LICENSE")
    assert "Version 2.0" in read("LICENSE")
