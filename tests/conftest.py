"""Suite-wide fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from agentinbox.store.memory import MemoryStore


@pytest.fixture
def store() -> Iterator[MemoryStore]:
    driver = MemoryStore()
    try:
        yield driver
    finally:
        driver.close()
