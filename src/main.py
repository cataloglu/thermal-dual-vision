"""Main application entry point for Smart Motion Detector."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from src.config import Config
from src.logger import setup_logger, get_logger


class Application:
    """Main application class."""

    def __init__(self, config: Config):
        """Initialize application with configuration."""
        self.config = config
        self.logger = get_logger("main")
        self.running = False

        # Component placeholders - will be initialized when components are ready
        self.mqtt_client: Optional[any] = None
        self.telegram_bot: Optional[any] = None
        # self.motion_detector: Optional[any] = None
        # self.yolo_processor: Optional[any] = None
        # self.web_server: Optional[any] = None

    async def start(self):
        """Start all application components."""
        self.logger.info("Initializing Smart Motion Detector components...")

        # TODO: Initialize components as they are implemented
        # For now, we just demonstrate the structure

        # Initialize MQTT client
        # if self.config.mqtt.host:
        #     from src.mqtt_client import MQTTClient
        #     self.mqtt_client = MQTTClient(self.config.mqtt)
        #     await self.mqtt_client.connect()
        #     self.logger.info("MQTT client connected")

        # Initialize Telegram bot if enabled
        # if self.config.telegram.enabled:
        #     from src.telegram_bot import TelegramBot
        #     self.telegram_bot = TelegramBot(self.config.telegram)
        #     await self.telegram_bot.start()
        #     self.logger.info("Telegram bot started")

        # Initialize motion detector
        # self.motion_detector = MotionDetector(self.config)
        # await self.motion_detector.start()

        # Start web UI server on port 8099 (for ingress)
        # self.web_server = WebServer(port=8099)
        # await self.web_server.start()

        self.running = True
        self.logger.info("Smart Motion Detector started successfully")
        self.logger.info(f"Camera URL: {self.config.camera.url}")
        self.logger.info(f"YOLO Model: {self.config.yolo.model}")
        self.logger.info(f"MQTT: {self.config.mqtt.host}:{self.config.mqtt.port}")

    async def stop(self):
        """Stop all application components gracefully."""
        self.logger.info("Stopping Smart Motion Detector...")
        self.running = False

        # Stop components in reverse order
        # if self.web_server:
        #     await self.web_server.stop()

        # if self.motion_detector:
        #     await self.motion_detector.stop()

        # if self.telegram_bot:
        #     await self.telegram_bot.stop()

        # if self.mqtt_client:
        #     await self.mqtt_client.disconnect()

        self.logger.info("Smart Motion Detector stopped")

    async def run(self):
        """Run the application main loop."""
        await self.start()

        # Keep running until interrupted
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("Application cancelled")
        finally:
            await self.stop()


def setup_signal_handlers(app: Application, loop: asyncio.AbstractEventLoop):
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger = get_logger("signal")
        logger.info(f"Received signal {signum}, initiating shutdown...")

        # Schedule stop on the event loop
        asyncio.ensure_future(app.stop(), loop=loop)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def main():
    """Main entry point."""
    # Load configuration from environment
    config = Config.from_env()

    # Setup root logger with configured level
    setup_logger("smart_motion", level=config.log_level)
    logger = get_logger("main")

    logger.info("=" * 60)
    logger.info("Smart Motion Detector - Home Assistant Add-on")
    logger.info("=" * 60)

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Configuration validated successfully")

    # Create application instance
    app = Application(config)

    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Setup signal handlers
    setup_signal_handlers(app, loop)

    # Run application
    try:
        loop.run_until_complete(app.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        loop.close()
        logger.info("Application terminated")


if __name__ == "__main__":
    main()
