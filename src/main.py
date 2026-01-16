"""Main application orchestrator for Smart Motion Detector."""

from datetime import datetime
from typing import Optional

import numpy as np

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

    async def stop(self) -> None:
        """
        Stop Smart Motion Detector and cleanup all modules.

        Stops and cleans up all modules in reverse order of initialization.
        """
        try:
            logger.info("Stopping Smart Motion Detector")

            # Stop modules in reverse order of initialization
            # Motion detector
            if self.motion_detector:
                try:
                    if hasattr(self.motion_detector, 'stop'):
                        await self.motion_detector.stop()
                    logger.info("Motion detector stopped")
                except Exception as e:
                    logger.warning(f"Error stopping motion detector: {e}")
                finally:
                    self.motion_detector = None

            # Screenshot manager
            if self.screenshot_manager:
                try:
                    if hasattr(self.screenshot_manager, 'cleanup'):
                        await self.screenshot_manager.cleanup()
                    logger.info("Screenshot manager cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up screenshot manager: {e}")
                finally:
                    self.screenshot_manager = None

            # YOLO detector
            if self.yolo_detector:
                try:
                    if hasattr(self.yolo_detector, 'cleanup'):
                        self.yolo_detector.cleanup()
                    logger.info("YOLO detector cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up YOLO detector: {e}")
                finally:
                    self.yolo_detector = None

            # LLM analyzer
            if self.llm_analyzer:
                try:
                    if hasattr(self.llm_analyzer, 'cleanup'):
                        await self.llm_analyzer.cleanup()
                    logger.info("LLM analyzer cleaned up")
                except Exception as e:
                    logger.warning(f"Error cleaning up LLM analyzer: {e}")
                finally:
                    self.llm_analyzer = None

            # Telegram bot
            if self.telegram_bot:
                try:
                    await self.telegram_bot.stop()
                    logger.info("Telegram bot stopped")
                except Exception as e:
                    logger.warning(f"Error stopping Telegram bot: {e}")
                finally:
                    self.telegram_bot = None

            # MQTT client
            if self.mqtt_client:
                try:
                    await self.mqtt_client.disconnect()
                    logger.info("MQTT client disconnected")
                except Exception as e:
                    logger.warning(f"Error disconnecting MQTT client: {e}")
                finally:
                    self.mqtt_client = None

            # Reset state
            self._armed = False
            self._last_detection_time = None

            logger.info("Smart Motion Detector stopped successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise

    async def _on_motion_detected(self, frame: np.ndarray, timestamp: datetime) -> None:
        """
        Motion detection callback handler.

        Called by MotionDetector when motion is detected. Orchestrates the
        full event pipeline: YOLO → Screenshots → LLM → Notifications.

        Args:
            frame: Current frame where motion was detected
            timestamp: Time of motion detection
        """
        # Check if system is armed
        if not self._armed:
            logger.debug(f"Motion detected at {timestamp.isoformat()}, but system is disarmed - ignoring")
            return

        logger.info(f"Motion detected at {timestamp.isoformat()}, starting event pipeline")

        # Update last detection time
        self._last_detection_time = timestamp

        # TODO: Implement full event pipeline (subtask-3-2):
        # 1. Run YOLO detection on frame
        # 2. Capture screenshots (before + now)
        # 3. Wait for after_seconds
        # 4. Capture after screenshot
        # 5. Run LLM analysis
        # 6. Publish to MQTT and send to Telegram (parallel)
