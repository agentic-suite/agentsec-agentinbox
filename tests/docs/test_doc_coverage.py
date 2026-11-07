"""Docs coverage: every command, flag, config key, and required page is documented (M23)."""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from agentinbox.cli import build_parser
from agentinbox.config import (
    SCAFFOLD,
    AuditConfig,
    BusConfig,
    ChannelConfig,
    ClassConfig,
    Config,
    LimitsConfig,
    ProducerConfig,
    StoreConfig,
    ThrottleConfig,
    WebuiConfig,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def test_every_command_and_flag_is_documented() -> None:
    parser = build_parser()
    cli_doc = (DOCS / "reference" / "cli.md").read_text(encoding="utf-8")
    group = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    options: set[str] = set()
    for action in parser._actions:
        options.update(action.option_strings)
    for sub in group.choices.values():
        for action in sub._actions:
            options.update(action.option_strings)

    for command in group.choices:
        assert command in cli_doc, f"command not documented: {command}"
    for option in sorted(options):
        if option in {"-h", "--help"}:
            continue
        assert option in cli_doc, f"option not documented: {option}"


def test_every_config_key_is_documented() -> None:
    config_doc = (DOCS / "reference" / "config.md").read_text(encoding="utf-8")
    classes = (
        Config,
        ClassConfig,
        ThrottleConfig,
        ChannelConfig,
        LimitsConfig,
        BusConfig,
        StoreConfig,
        WebuiConfig,
        AuditConfig,
        ProducerConfig,
    )
    for dataclass_type in classes:
        for field in dataclasses.fields(dataclass_type):
            assert field.name in config_doc, (
                f"config field not documented: {dataclass_type.__name__}.{field.name}"
            )
    for key in (
        "ttl_seconds",
        "warn_seconds",
        "self_review",
        "require_reason_on_deny",
        "require_signed_producer",
        "per_agent_burst",
        "per_agent_rate_per_min",
        "flood_window_seconds",
        "max_hold_rounds",
        "max_evidence_revisions",
        "max_thread_entries",
        "allow_as",
        "url_ref",
        "hmac_key_ref",
        "key_ref",
        "retention",
        "bind",
        "driver",
    ):
        assert key in config_doc, f"scaffold key not documented: {key}"
    assert "[classes.irreversible]" in SCAFFOLD


def test_all_eight_runbooks_exist_with_the_required_shape() -> None:
    runbooks = sorted((DOCS / "runbooks").glob("rb-*.md"))
    assert len(runbooks) == 8, [path.name for path in runbooks]
    for runbook in runbooks:
        text = runbook.read_text(encoding="utf-8").lower()
        assert "symptom" in text, f"{runbook.name}: no symptoms"
        assert "steps" in text, f"{runbook.name}: no steps"
        assert "verify" in text, f"{runbook.name}: no verification"


def test_adapter_recipes_are_complete() -> None:
    adapters = "\n".join(
        path.read_text(encoding="utf-8") for path in (DOCS / "adapters").glob("*.md")
    )
    for required in (
        "Claude Code",
        "Codex",
        "GitHub Actions",
        "GitLab",
        "Jenkins",
        "Argo",
        "MCP",
        "Temporal",
    ):
        assert required in adapters, f"missing adapter recipe: {required}"


def test_quickstart_guides_and_readme_are_live() -> None:
    quickstart = (DOCS / "tutorials" / "quickstart.md").read_text(encoding="utf-8")
    assert "agentinbox init" in quickstart
    assert "agentinbox ask --exec" in quickstart
    assert "agentinbox answer" in quickstart

    assert (DOCS / "guides" / "approver-guide.md").is_file()
    assert (DOCS / "guides" / "enterprise-honesty.md").is_file()
    assert (DOCS / "plans" / "docs-plan.md").is_file()
    assert (DOCS / "reference" / "screenshots" / "README.md").is_file()

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/tutorials/quickstart.md" in readme
    assert "docs/runbooks/" in readme
    assert "docs/reference/" in readme
