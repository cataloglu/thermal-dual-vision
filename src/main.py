"""Main application entry point for Smart Motion Detector."""

import asyncio
import signal
import sys
from typing import Optional

from src.config import Config
from src.health_endpoint import HealthEndpoint
from src.logger import get_logger
from src.metrics import MetricsCollector

# Initialize logger
logger = get_logger("main")


class SmartMotionDetector:
    """Main application coordinator for Smart Motion Detector."""

    def __init__(self, config: Config) -> None:
        """
        Initialize Smart Motion Detector application.

        Args:
            config: Application configuration
        """
        self.config = config
        self.running = False

        # Initialize metrics collector
        self.metrics = MetricsCollector()
        logger.info("MetricsCollector initialized")

        # Initialize health endpoint
        self.health_endpoint = HealthEndpoint(
            metrics_collector=self.metrics,
            host="0.0.0.0",
            port=8099
        )

        # Components (to be initialized)
        self.motion_detector: Optional[object] = None
        self.yolo_detector: Optional[object] = None
        self.llm_analyzer: Optional[object] = None
        self.mqtt_client: Optional[object] = None
        self.telegram_bot: Optional[object] = None
        self.screenshot_manager: Optional[object] = None

        logger.info("SmartMotionDetector initialized")

    async def start(self) -> None:
        """Start the application and all components."""
        try:
            logger.info("Starting Smart Motion Detector...")

            # Start health endpoint
            await self.health_endpoint.start()

            # TODO: Initialize and start other components
            # - Camera capture
            # - Motion detector
            # - YOLO detector
            # - LLM analyzer
            # - MQTT client
            # - Telegram bot

            self.running = True
            logger.info("Smart Motion Detector started successfully")

        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise

    async def stop(self) -> None:
        """Stop the application and cleanup resources."""
        try:
            logger.info("Stopping Smart Motion Detector...")
            self.running = False

            # Stop health endpoint
            await self.health_endpoint.stop()

            # TODO: Stop and cleanup other components

            logger.info("Smart Motion Detector stopped")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def metrics_logging_loop(self) -> None:
        """Periodically log performance metrics."""
        logger.info("Starting metrics logging loop")

        try:
            while self.running:
                # Log metrics every 30 seconds
                await asyncio.sleep(30)

                if self.running:
                    self.metrics.log_metrics()

        except asyncio.CancelledError:
            logger.info("Metrics logging loop cancelled")
        except Exception as e:
            logger.error(f"Error in metrics logging loop: {e}")

    async def main_loop(self) -> None:
        """Main application processing loop."""
        logger.info("Starting main processing loop")

        try:
            while self.running:
                # Main processing logic will go here
                # - Capture frames
                # - Detect motion
                # - Run YOLO detection
                # - Analyze with LLM
                # - Send notifications

                # For now, just sleep
                await asyncio.sleep(0.1)

                # Record frame for FPS tracking
                self.metrics.record_frame()

        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise

    async def run(self) -> None:
        """Run the application with all components."""
        try:
            # Start the application
            await self.start()

            # Create tasks for concurrent operations
            metrics_task = asyncio.create_task(self.metrics_logging_loop())
            main_task = asyncio.create_task(self.main_loop())

            # Wait for tasks
            await asyncio.gather(metrics_task, main_task)

        except asyncio.CancelledError:
            logger.info("Application run cancelled")
        finally:
            await self.stop()


async def main() -> None:
    """Application entry point."""
    # Load configuration from environment
    config = Config.from_env()

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Configuration loaded and validated")

    # Create application instance
    app = SmartMotionDetector(config)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        app.running = False

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Run the application
        await app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
