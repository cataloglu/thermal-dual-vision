"""Stage registry for pipeline plugins."""

from __future__ import annotations

from typing import Callable, Dict, Protocol

from src.config import Config


class Stage(Protocol):
    """Protocol for pipeline stages."""

    def __call__(self, frame):
        ...  # pragma: no cover


StageFactory = Callable[[Config], Stage]


class StageRegistry:
    """Registry for pipeline stages."""

    def __init__(self) -> None:
        self._stages: Dict[str, StageFactory] = {}

    def register(self, name: str, factory: StageFactory) -> None:
        """Register a stage factory under a unique name."""
        if name in self._stages:
            raise ValueError(f"Stage '{name}' is already registered")
        self._stages[name] = factory

    def get(self, name: str) -> StageFactory:
        """Get a stage factory by name."""
        return self._stages[name]

    def list(self) -> Dict[str, StageFactory]:
        """Return a copy of registered stages."""
        return dict(self._stages)


registry = StageRegistry()
