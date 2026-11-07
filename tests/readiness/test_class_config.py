"""Class-owned readiness config + explain (M26 item 26.6, R86)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentinbox.config import ConfigError, init_home, load_config, resolve_config_path
from agentinbox.doctor import render_explain, run_checks


def make_home(tmp_path: Path, extra: str) -> Path:
    home = tmp_path / "home"
    path = resolve_config_path(home)
    init_home(home, path)
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")
    return home


def test_enforce_without_a_threshold_refuses_to_start(tmp_path: Path) -> None:
    home = make_home(
        tmp_path,
        "\n[classes.gated]\nttl_seconds = 300\nreadiness_enforce = true\n",
    )
    with pytest.raises(ConfigError, match="readiness_min_score"):
        load_config(resolve_config_path(home))


def test_a_class_can_own_its_evidence_expectations(tmp_path: Path) -> None:
    home = make_home(
        tmp_path,
        "\n[classes.gated]\nttl_seconds = 300\nreadiness_enforce = true\n"
        'readiness_min_score = 0.7\nrequired_evidence = ["diff"]\n'
        'on_contradiction = "reject"\nevidence_max_age_seconds = 3600\n',
    )
    config = load_config(resolve_config_path(home))
    ask_class = config.classes["gated"]

    assert ask_class.readiness_enforce is True
    assert ask_class.readiness_min_score == 0.7
    assert ask_class.required_evidence == ("diff",)
    assert ask_class.on_contradiction == "reject"
    assert ask_class.evidence_max_age_seconds == 3600

    report = run_checks(home, resolve_config_path(home))
    explanation = render_explain(report, home, resolve_config_path(home))
    assert explanation is not None
    assert "readiness_min_score=0.7" in explanation
    assert "required_evidence=['diff']" in explanation


def test_legacy_classes_keep_readiness_off() -> None:
    from tests.readiness.conftest import config

    assert config().classes["irreversible"].readiness_enforce is False
