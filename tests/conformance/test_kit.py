"""The conformance kit gates integrations and fails a broken adapter (M19 item 19.3)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentinbox.cli import main
from agentinbox.config import (
    ChannelConfig,
    ClassConfig,
    Config,
    ProducerConfig,
    init_home,
    resolve_config_path,
)
from agentinbox.conformance import ConformanceReport, run_conformance
from agentinbox.store import CreateResult
from agentinbox.store.memory import MemoryStore
from tests.ask.conftest import NOW

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "conformance" / "ask.json"


def config() -> Config:
    return Config(
        classes={"irreversible": ClassConfig(ttl_seconds=300)},
        roster={"tier-1": {"terminal": ("alice",)}},
        channels={"terminal": ChannelConfig(enabled=True)},
        producers={"agentpolicy": ProducerConfig(key_ref="env:ADAPTER_KEY")},
    )


def test_the_reference_config_passes_every_check() -> None:
    report = run_conformance(config(), now=NOW)

    assert isinstance(report, ConformanceReport)
    assert report.ok
    names = {check.name for check in report.checks}
    assert names >= {
        "config.class",
        "contract.ask",
        "redaction",
        "idempotent-ingest",
        "resolve.pending",
        "exit-codes",
        "events",
        "channels",
        "producers",
    }


def test_a_broken_store_fails_the_kit() -> None:
    class BrokenStore(MemoryStore):
        def create_or_get_by_identity(self, ask, *, dedupe_window_s: int = 900):  # type: ignore[no-untyped-def]
            result = super().create_or_get_by_identity(
                ask, dedupe_window_s=dedupe_window_s
            )
            return CreateResult(ask=replace(result.ask), created=False)

    report = run_conformance(config(), store_factory=BrokenStore, now=NOW)

    assert not report.ok
    assert any(check.name == "contract.ask" and not check.ok for check in report.checks)


def test_a_config_without_classes_fails() -> None:
    report = run_conformance(Config(), now=NOW)
    assert not report.ok
    assert report.checks[0].name == "config.class"


def test_a_leaky_store_fails_the_redaction_check() -> None:
    class LeakyStore(MemoryStore):
        def create_or_get_by_identity(self, ask, *, dedupe_window_s: int = 900):  # type: ignore[no-untyped-def]
            result = super().create_or_get_by_identity(
                ask, dedupe_window_s=dedupe_window_s
            )
            return CreateResult(ask=result.ask, created=True)

        def get(self, ask_id: str):  # type: ignore[no-untyped-def]
            ask = super().get(ask_id)
            return None if ask is None else replace(ask, payload={})

    report = run_conformance(config(), store_factory=LeakyStore, now=NOW)
    assert not report.ok
    assert any(check.name == "redaction" and not check.ok for check in report.checks)


def test_a_non_idempotent_store_fails_the_kit() -> None:
    class AlwaysCreatedStore(MemoryStore):
        def create_or_get_by_identity(self, ask, *, dedupe_window_s: int = 900):  # type: ignore[no-untyped-def]
            result = super().create_or_get_by_identity(
                ask, dedupe_window_s=dedupe_window_s
            )
            return CreateResult(ask=result.ask, created=True)

    report = run_conformance(config(), store_factory=AlwaysCreatedStore, now=NOW)
    assert not report.ok
    assert any(
        check.name == "idempotent-ingest" and not check.ok for check in report.checks
    )


def test_a_literal_producer_key_fails() -> None:
    broken = replace(
        config(), producers={"x": ProducerConfig(key_ref="literal-secret")}
    )
    report = run_conformance(broken, now=NOW)
    assert not report.ok
    assert any(check.name == "producers" and not check.ok for check in report.checks)


def test_the_shipped_fixture_is_contract_valid() -> None:
    from agentinbox.ingest import ingest
    from agentinbox.store.memory import MemoryStore
    from agentinbox.trust import ProducerIdentity

    body = json.loads(FIXTURE.read_text(encoding="utf-8"))
    store = MemoryStore()
    try:
        result = ingest(
            body,
            store=store,
            config=config(),
            producer=ProducerIdentity.unauthenticated(),
            now=NOW,
        )
    finally:
        store.close()

    assert result.created is True


def test_the_cli_runs_the_kit(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))

    assert main(["--home", str(home), "conformance"]) == 0
    out = capsys.readouterr().out
    assert "contract.ask" in out
    assert "FAIL" not in out


def test_the_cli_reports_a_broken_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    init_home(home, resolve_config_path(home))
    (home / "config.toml").write_text("[classes.x]\nttl_seconds = 0\n", encoding="utf-8")

    assert main(["--home", str(home), "conformance"]) == 4
    assert "ttl_seconds" in capsys.readouterr().err
