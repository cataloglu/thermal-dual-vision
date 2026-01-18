"""Base pipeline interface for camera processing."""

from abc import ABC, abstractmethod
import threading
from typing import Protocol

from src.config import Config


class BasePipeline(ABC):
    """Base interface for camera pipelines."""

    camera_type: str = ""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.stop_event = threading.Event()

    def stop(self) -> None:
        """Signal pipeline to stop."""
        self.stop_event.set()

    @classmethod
    def supports(cls, camera_type: str) -> bool:
        """Return True if pipeline supports the camera type."""
        return cls.camera_type == camera_type

    @abstractmethod
    def run(self) -> None:
        """Run the pipeline main loop."""
        raise NotImplementedError


class PipelineFactory(Protocol):
    """Factory interface for creating pipelines."""

    def __call__(self, config: Config) -> BasePipeline:
        ...  # pragma: no cover
