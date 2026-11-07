"""Last-good configuration reload (M20 item 20.5).

A reload reads the file again. On any failure the previous config stays in force, the error is
returned and surfaced by the caller, and the failure is recorded as
``inbox-config-changed(failed)``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agentinbox.config import Config, ConfigError, load_config


@dataclass(frozen=True, slots=True)
class ReloadResult:
    ok: bool
    config: Config
    error: str | None = None


class ConfigHolder:
    """Holds the effective config and refuses to apply an invalid replacement."""

    def __init__(
        self,
        path: Path,
        *,
        loader: Callable[[Path], Config] = load_config,
    ) -> None:
        self.path = path
        self._loader = loader
        self._config = loader(path)

    @property
    def config(self) -> Config:
        return self._config

    def reload(self) -> ReloadResult:
        try:
            candidate = self._loader(self.path)
        except ConfigError as exc:
            return ReloadResult(ok=False, config=self._config, error=str(exc))
        self._config = candidate
        return ReloadResult(ok=True, config=candidate)


__all__ = ["ConfigHolder", "ReloadResult"]
