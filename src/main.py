"""Main application orchestrator for Smart Motion Detector."""

from datetime import datetime
from typing import Optional

from src.config import Config
from src.logger import get_logger

logger = get_logger("main")


class SmartMotionDetector:
    """
    Main application orchestrator for Smart Motion Detector.

    Manages lifecycle of all modules (motion detection, YOLO, screenshots,
    LLM analysis, MQTT, Telegram) and coordinates the event pipeline.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize Smart Motion Detector.

        Args:
            config: Application configuration
        """
        self.config = config
        self._armed = False
        self._start_time: Optional[datetime] = None
        self._last_detection_time: Optional[datetime] = None

        logger.info("Smart Motion Detector initialized")
