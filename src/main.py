"""Main application orchestrator for Smart Motion Detector."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

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

    def arm(self) -> None:
        """
        Arm the motion detector.

        When armed, the detector will process motion events and send alerts.
        """
        self._armed = True
        logger.info("Smart Motion Detector armed")

    def disarm(self) -> None:
        """
        Disarm the motion detector.

        When disarmed, motion events will be ignored and no alerts will be sent.
        """
        self._armed = False
        logger.info("Smart Motion Detector disarmed")

    def is_armed(self) -> bool:
        """
        Check if the motion detector is armed.

        Returns:
            True if armed, False otherwise
        """
        return self._armed

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all modules and return status.

        Returns:
            Dictionary containing overall status and module-specific health information
        """
        health = {
            "status": "ok",
            "armed": self._armed,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "last_detection": self._last_detection_time.isoformat() if self._last_detection_time else None,
            "modules": {}
        }

        # Check MQTT client
        if self.mqtt_client:
            health["modules"]["mqtt"] = {
                "available": True,
                "connected": self.mqtt_client.is_connected
            }
        else:
            health["modules"]["mqtt"] = {
                "available": False,
                "connected": False
            }

        # Check Telegram bot
        if self.telegram_bot:
            health["modules"]["telegram"] = {
                "available": True,
                "running": self.telegram_bot.is_running
            }
        else:
            health["modules"]["telegram"] = {
                "available": False,
                "running": False
            }

        # Check LLM analyzer
        health["modules"]["llm"] = {
            "available": self.llm_analyzer is not None
        }

        # Check YOLO detector
        health["modules"]["yolo"] = {
            "available": self.yolo_detector is not None
        }

        # Check Screenshot manager
        health["modules"]["screenshots"] = {
            "available": self.screenshot_manager is not None
        }

        # Check Motion detector
        health["modules"]["motion"] = {
            "available": self.motion_detector is not None
        }

        # Determine overall status based on critical modules
        if not health["modules"]["motion"]["available"]:
            health["status"] = "degraded"

        return health

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

        try:
            # Step 1: YOLO Detection (if available)
            yolo_detections = None
            if self.yolo_detector:
                try:
                    yolo_detections = self.yolo_detector.detect(frame)
                    logger.info(f"YOLO detection completed: {len(yolo_detections)} objects detected")
                except Exception as e:
                    logger.error(f"YOLO detection failed: {e}")
            else:
                logger.debug("YOLO detector not available, skipping detection")

            # Step 2: Screenshot Capture (before + now)
            # For now, we'll use the current frame for both before and now
            # until ScreenshotManager is implemented with buffering
            before_frame = frame.copy()
            now_frame = frame.copy()

            logger.debug("Screenshots captured (before + now)")

            # Step 3: Wait for after_seconds
            after_seconds = self.config.screenshots.after_seconds
            logger.debug(f"Waiting {after_seconds} seconds for 'after' screenshot")
            await asyncio.sleep(after_seconds)

            # Step 4: Screenshot Capture (after)
            # For now, we'll use the same frame until camera integration is complete
            # In production, this would capture a new frame from the camera
            after_frame = frame.copy()
            logger.debug("After screenshot captured")

            # Step 5: Create ScreenshotSet for LLM analysis
            if LLMAnalyzer:
                # Import ScreenshotSet from llm_analyzer
                from src.llm_analyzer import ScreenshotSet

                screenshots = ScreenshotSet(
                    before=before_frame,
                    now=now_frame,
                    after=after_frame,
                    timestamp=timestamp
                )
                logger.debug("ScreenshotSet created")
            else:
                logger.warning("LLMAnalyzer not available, cannot create ScreenshotSet")
                screenshots = None

            # Step 6: LLM Analysis
            analysis = None
            if self.llm_analyzer and screenshots:
                try:
                    logger.info("Starting LLM analysis")
                    analysis = await self.llm_analyzer.analyze(screenshots)
                    logger.info(
                        f"LLM analysis completed: gercek_hareket={analysis.gercek_hareket}, "
                        f"guven_skoru={analysis.guven_skoru:.2f}, "
                        f"tehdit_seviyesi={analysis.tehdit_seviyesi}"
                    )
                except Exception as e:
                    logger.error(f"LLM analysis failed: {e}")
            else:
                if not self.llm_analyzer:
                    logger.debug("LLM analyzer not available, skipping analysis")

            # Step 7: Parallel MQTT publish and Telegram send
            notification_tasks = []

            # MQTT publish (if connected)
            if self.mqtt_client and self.mqtt_client.is_connected:
                try:
                    mqtt_task = self.mqtt_client.publish_motion(
                        detected=True,
                        analysis=analysis
                    )
                    notification_tasks.append(mqtt_task)
                    logger.debug("MQTT publish task scheduled")
                except Exception as e:
                    logger.error(f"Failed to schedule MQTT publish: {e}")
            else:
                logger.debug("MQTT client not connected, skipping publish")

            # Telegram alert (if available and analysis succeeded)
            if self.telegram_bot and analysis and screenshots:
                try:
                    telegram_task = self.telegram_bot.send_alert(
                        screenshots=screenshots,
                        analysis=analysis
                    )
                    notification_tasks.append(telegram_task)
                    logger.debug("Telegram alert task scheduled")
                except Exception as e:
                    logger.error(f"Failed to schedule Telegram alert: {e}")
            else:
                if not self.telegram_bot:
                    logger.debug("Telegram bot not available, skipping alert")
                elif not analysis:
                    logger.debug("No analysis result, skipping Telegram alert")

            # Execute notification tasks in parallel
            if notification_tasks:
                try:
                    logger.info(f"Executing {len(notification_tasks)} notification tasks in parallel")
                    results = await asyncio.gather(*notification_tasks, return_exceptions=True)

                    # Log results
                    for idx, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Notification task {idx} failed: {result}")
                        else:
                            logger.debug(f"Notification task {idx} completed successfully")

                    logger.info("All notification tasks completed")
                except Exception as e:
                    logger.error(f"Error executing notification tasks: {e}")
            else:
                logger.debug("No notification tasks to execute")

            logger.info(f"Event pipeline completed for detection at {timestamp.isoformat()}")

        except Exception as e:
            logger.error(f"Error in event pipeline: {e}", exc_info=True)
