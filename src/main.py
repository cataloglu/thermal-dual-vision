"""Main application orchestrator for Smart Motion Detector."""

from datetime import datetime
from typing import Optional

from src.config import Config
from src.logger import get_logger

# Import existing modules with graceful error handling
try:
    from src.mqtt_client import MQTTClient
except ImportError:
    MQTTClient = None

try:
    from src.telegram_bot import TelegramBot
except ImportError:
    TelegramBot = None

try:
    from src.llm_analyzer import LLMAnalyzer
except ImportError:
    LLMAnalyzer = None

# Placeholder imports for modules not yet implemented
try:
    from src.motion_detector import MotionDetector
except ImportError:
    MotionDetector = None

try:
    from src.yolo_detector import YOLODetector
except ImportError:
    YOLODetector = None

try:
    from src.screenshot_manager import ScreenshotManager
except ImportError:
    ScreenshotManager = None

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

        # Module instances (initialized in start())
        self.motion_detector: Optional[MotionDetector] = None
        self.yolo_detector: Optional[YOLODetector] = None
        self.screenshot_manager: Optional[ScreenshotManager] = None
        self.llm_analyzer: Optional[LLMAnalyzer] = None
        self.mqtt_client: Optional[MQTTClient] = None
        self.telegram_bot: Optional[TelegramBot] = None

        logger.info("Smart Motion Detector initialized")
