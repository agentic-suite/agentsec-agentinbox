"""M33 33.2/33.1 — CLI-path coverage for the claims lint and matrix entry points."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import agentinbox.claimslint as claimslint
import agentinbox.compatmatrix as compatmatrix
from agentinbox.compatmatrix import ROWS


def test_claims_lint_main_paths(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text("a normal claim about approvals\n", encoding="utf-8")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "bad.rst").write_text("we are enterprise-ready\n", encoding="utf-8")
    (sub / "skip.txt").write_text("x", encoding="utf-8")

    buffer = io.StringIO()
    errors = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(errors):
        assert claimslint.main([str(tmp_path)]) == 1
    assert "ENTERPRISE_READY" in errors.getvalue()
    # a plain file target works too
    with redirect_stdout(buffer), redirect_stderr(errors):
        assert claimslint.main([str(sub / "bad.rst")]) == 1
    with redirect_stdout(buffer), redirect_stderr(errors):
        assert claimslint.main([str(good)]) == 0


def test_claims_lint_ignores_unreadable_input(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert claimslint.main([str(missing)]) == 0


def test_matrix_no_args_defaults_to_repo_targets(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    fake = tmp_path / "fake-repo"
    (fake / "docs").mkdir(parents=True)
    (fake / "README.md").write_text("readme\n", encoding="utf-8")
    monkeypatch.setattr(claimslint, "_ROOT", fake)
    buffer = io.StringIO()
    errors = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(errors):
        assert claimslint.main([]) == 0
    assert "readme" not in errors.getvalue()


def test_matrix_write_and_check(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "MATRIX.md"
    monkeypatch.setattr(compatmatrix, "_OUTPUT", target)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        assert compatmatrix.main(["--write"]) == 0
    assert target.is_file()

    with redirect_stdout(buffer):
        assert compatmatrix.main(["--check"]) == 0

    target.write_text("stale", encoding="utf-8")
    with redirect_stdout(buffer):
        assert compatmatrix.main(["--check"]) == 1
    # rewrite for downstream callers
    with redirect_stdout(buffer):
        assert compatmatrix.main(["--write"]) == 0


def test_matrix_check_fails_when_missing(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(compatmatrix, "_OUTPUT", tmp_path / "absent.md")
    assert compatmatrix.main(["--check"]) == 1


def test_matrix_rows_render_into_a_table() -> None:
    text = compatmatrix.render()
    for row in ROWS:
        assert row.surface in text
        assert f"**{row.label}**" in text
