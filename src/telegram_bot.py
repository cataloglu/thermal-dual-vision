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
