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

    async def start(self) -> None:
        """
        Start Smart Motion Detector and initialize all modules.

        Initializes and starts all available modules in the correct order.
        """
        try:
            logger.info("Starting Smart Motion Detector")
            self._start_time = datetime.now()

            # Initialize MQTT client
            if MQTTClient:
                try:
                    self.mqtt_client = MQTTClient(self.config.mqtt)
                    await self.mqtt_client.connect()
                    logger.info("MQTT client started")
                except Exception as e:
                    logger.warning(f"MQTT client not started: {e}")
                    self.mqtt_client = None
            else:
                logger.warning("MQTTClient not available")

            # Initialize Telegram bot
            if TelegramBot and self.config.telegram.enabled:
                try:
                    self.telegram_bot = TelegramBot(self.config.telegram)
                    await self.telegram_bot.start()
                    logger.info("Telegram bot started")
                except Exception as e:
                    logger.warning(f"Telegram bot not started: {e}")
                    self.telegram_bot = None
            elif self.config.telegram.enabled:
                logger.warning("Telegram enabled but TelegramBot not available")

            # Initialize LLM analyzer
            if LLMAnalyzer:
                self.llm_analyzer = LLMAnalyzer(self.config.llm)
                logger.info("LLM analyzer initialized")
            else:
                logger.warning("LLMAnalyzer not available")

            # Initialize YOLO detector
            if YOLODetector:
                self.yolo_detector = YOLODetector(self.config.yolo)
                logger.info("YOLO detector initialized")
            else:
                logger.warning("YOLODetector not available")

            # Initialize Screenshot manager
            if ScreenshotManager:
                self.screenshot_manager = ScreenshotManager(self.config.screenshots)
                logger.info("Screenshot manager initialized")
            else:
                logger.warning("ScreenshotManager not available")

            # Initialize Motion detector
            if MotionDetector:
                self.motion_detector = MotionDetector(self.config.motion)
                logger.info("Motion detector initialized")
            else:
                logger.warning("MotionDetector not available")

            logger.info("Smart Motion Detector started successfully")

        except Exception as e:
            logger.error(f"Failed to start Smart Motion Detector: {e}")
            raise
