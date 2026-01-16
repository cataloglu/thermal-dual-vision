"""Telegram bot for Smart Motion Detector."""

from typing import Optional

try:
    from telegram.ext import Application
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Application = None

from .config import TelegramConfig
from .logger import get_logger


class TelegramBot:
    """Telegram bot for motion detection alerts and remote control."""

    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram bot.

        Args:
            config: Telegram bot configuration
        """
        self.config = config
        self.logger = get_logger("telegram_bot")

        # Build Application
        self.application: Optional[Application] = None

        if not TELEGRAM_AVAILABLE:
            self.logger.warning("python-telegram-bot not installed, bot disabled")
            return

        if config.bot_token:
            self.application = (
                Application.builder()
                .token(config.bot_token)
                .build()
            )
            self.logger.info("Telegram Application initialized")
        else:
            self.logger.warning("No bot token provided, Application not created")

    async def start(self) -> None:
        """
        Start the Telegram bot.

        Initializes and starts the Application if available.
        """
        if not TELEGRAM_AVAILABLE:
            self.logger.warning("Cannot start bot: python-telegram-bot not installed")
            return

        if not self.application:
            self.logger.warning("Cannot start bot: Application not initialized")
            return

        try:
            await self.application.initialize()
            await self.application.start()
            self.logger.info("Telegram bot started")
        except Exception as e:
            self.logger.error(f"Failed to start Telegram bot: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop the Telegram bot.

        Gracefully stops and shuts down the Application if running.
        """
        if not TELEGRAM_AVAILABLE:
            self.logger.debug("Bot not available, nothing to stop")
            return

        if not self.application:
            self.logger.debug("Application not initialized, nothing to stop")
            return

        try:
            await self.application.stop()
            await self.application.shutdown()
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop Telegram bot: {e}")
            raise
