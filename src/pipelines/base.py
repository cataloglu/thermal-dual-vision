"""Base pipeline interface for camera processing."""

from abc import ABC, abstractmethod
from typing import Protocol

from src.config import Config


class BasePipeline(ABC):
    """Base interface for camera pipelines."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def run(self) -> None:
        """Run the pipeline main loop."""
        raise NotImplementedError


class PipelineFactory(Protocol):
    """Factory interface for creating pipelines."""

    def __call__(self, config: Config) -> BasePipeline:
        ...  # pragma: no cover
