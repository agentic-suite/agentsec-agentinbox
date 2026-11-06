"""Driver admission via entry points (M1 item 1.6).

An unlisted driver, or one that has not passed this conformance suite version, is refused at
load — never at runtime (E11 / PRD 19 honesty rule).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from agentinbox.store import (
    CONFORMANCE_VERSION,
    CapabilityError,
    DriverNotAdmittedError,
    DriverSpec,
    StoreCapabilities,
)
from agentinbox.store.loader import load_store
from agentinbox.store.memory import MemoryStore
from agentinbox.store.sqlite import SqliteStore


class FakeEntryPoint:
    def __init__(self, name: str, target: Any) -> None:
        self.name = name
        self._target = target

    def load(self) -> Any:
        return self._target


def spec(
    *,
    version: str = CONFORMANCE_VERSION,
    capabilities: StoreCapabilities | None = None,
    factory: Callable[[Path], Any] | None = None,
) -> DriverSpec:
    return DriverSpec(
        name="fake",
        conformance_version=version,
        capabilities=capabilities or StoreCapabilities(single_writer=True),
        factory=factory or (lambda home: MemoryStore()),
    )


def test_builtin_memory_driver_loads() -> None:
    store = load_store("memory")

    assert isinstance(store, MemoryStore)


def test_builtin_sqlite_driver_uses_the_home_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"

    store = load_store("sqlite", home=home)

    assert isinstance(store, SqliteStore)
    assert store.path == home / "inbox.db"
    store.close()


def test_unknown_driver_is_refused_with_the_group_named() -> None:
    with pytest.raises(DriverNotAdmittedError, match=r"agentinbox\.store"):
        load_store("postgres")


def test_driver_with_stale_conformance_is_refused() -> None:
    entry_points = [FakeEntryPoint("fake", spec(version="0"))]

    with pytest.raises(DriverNotAdmittedError, match="conformance"):
        load_store("fake", entry_points=entry_points)


def test_non_driver_object_is_refused() -> None:
    entry_points = [FakeEntryPoint("fake", object())]

    with pytest.raises(DriverNotAdmittedError, match="DriverSpec"):
        load_store("fake", entry_points=entry_points)


def test_required_capability_is_checked_before_construction() -> None:
    constructed: list[Path] = []
    entry_points = [
        FakeEntryPoint("fake", spec(factory=lambda home: constructed.append(home) or MemoryStore()))
    ]

    with pytest.raises(CapabilityError, match="multi_writer"):
        load_store("fake", entry_points=entry_points, required_capabilities=("multi_writer",))

    assert constructed == []


def test_single_writer_requirement_passes() -> None:
    entry_points = [FakeEntryPoint("fake", spec())]

    store = load_store("fake", entry_points=entry_points, required_capabilities=("single_writer",))

    assert isinstance(store, MemoryStore)


def test_driver_construction_errors_are_not_swallowed(tmp_path: Path) -> None:
    def boom(home: Path) -> Any:
        raise RuntimeError("cannot open")

    entry_points = [FakeEntryPoint("fake", spec(factory=boom))]

    with pytest.raises(RuntimeError, match="cannot open"):
        load_store("fake", entry_points=entry_points)
