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

    def _check_authorization(self, chat_id: int) -> bool:
        """
        Check if a chat ID is authorized to use the bot.

        Args:
            chat_id: Telegram chat ID to check

        Returns:
            True if chat ID is authorized, False otherwise
        """
        chat_id_str = str(chat_id)

        if not self.config.chat_ids:
            self.logger.warning("No authorized chat IDs configured")
            return False

        is_authorized = chat_id_str in self.config.chat_ids

        if not is_authorized:
            self.logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")

        return is_authorized
