"""YOLO object detection module for Smart Motion Detector."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from src.config import YoloConfig
from src.logger import get_logger

logger = get_logger("yolo")


@dataclass
class Detection:
    """Represents a single object detection result."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    class_id: int


class YoloDetector:
    """
    YOLOv8-based object detector with lazy model loading.

    The model is loaded on first detection call to optimize startup time.
    Supports confidence threshold and class-based filtering.
    """

    def __init__(self, config: YoloConfig):
        """
        Initialize YOLO detector with configuration.

        Args:
            config: YoloConfig instance with model settings
        """
        self.config = config
        self._model: Optional[object] = None
        self._class_names: Optional[List[str]] = None
        logger.info(
            f"YoloDetector initialized with model={config.model}, "
            f"confidence={config.confidence}, classes={config.classes}"
        )

    def _load_model(self) -> None:
        """
        Lazy load the YOLO model on first use.

        This method is called automatically on the first detect() call.
        Uses ultralytics YOLO implementation.
        """
        if self._model is not None:
            return

        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {self.config.model}")
            self._model = YOLO(self.config.model)

            # Store class names from model
            self._class_names = self._model.names

            logger.info(
                f"YOLO model loaded successfully. "
                f"Available classes: {len(self._class_names)}"
            )
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
