"""Driver selection by entry point (E11 / PRD 19 honesty rule).

Only drivers that declare **this** conformance-suite version are admitted. Capability
requirements are checked before the driver is constructed, so an unsupported configuration
fails closed at load instead of surprising a request later.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib import metadata
from pathlib import Path
from typing import Any

from agentinbox.store.base import (
    CONFORMANCE_VERSION,
    AskStore,
    CapabilityError,
    DriverNotAdmittedError,
    DriverSpec,
)

ENTRY_POINT_GROUP = "agentinbox.store"
DEFAULT_HOME = Path.home() / ".agentinbox"
_CAPABILITIES = frozenset({"single_writer", "multi_writer", "cluster_safe"})


def load_store(
    name: str = "sqlite",
    *,
    home: Path | None = None,
    entry_points: Iterable[Any] | None = None,
    required_capabilities: Iterable[str] = (),
) -> AskStore:
    """Resolve, admit, and construct a store driver (never a silent fallback)."""
    available = (
        list(entry_points)
        if entry_points is not None
        else list(metadata.entry_points(group=ENTRY_POINT_GROUP))
    )
    matches = [entry for entry in available if getattr(entry, "name", None) == name]
    if not matches:
        known = ", ".join(sorted(str(getattr(entry, "name", "?")) for entry in available)) or "none"
        raise DriverNotAdmittedError(
            f"store driver {name!r} is not installed (entry point group {ENTRY_POINT_GROUP}); "
            f"available: {known}"
        )

    spec = matches[0].load()
    if not isinstance(spec, DriverSpec):
        raise DriverNotAdmittedError(
            f"store driver {name!r} must expose a DriverSpec, not {type(spec).__name__}"
        )
    if spec.conformance_version != CONFORMANCE_VERSION:
        raise DriverNotAdmittedError(
            f"store driver {name!r} declares conformance {spec.conformance_version!r}; "
            f"this build admits only {CONFORMANCE_VERSION!r} (run the conformance suite)"
        )

    for capability in required_capabilities:
        if capability not in _CAPABILITIES:
            raise ValueError(f"unknown capability: {capability!r}")
        if not getattr(spec.capabilities, capability):
            raise CapabilityError(
                f"store driver {name!r} cannot guarantee {capability!r}; refuse to start"
            )

    return spec.factory(home or DEFAULT_HOME)


__all__ = ["DEFAULT_HOME", "ENTRY_POINT_GROUP", "load_store"]
