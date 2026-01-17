"""Telegram bot for Smart Motion Detector."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Optional

try:
    from telegram import InputMediaPhoto, Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Application = None
    Update = None
    CommandHandler = None
    InputMediaPhoto = None

    # Create mock ContextTypes for type hints when telegram is not available
    class _MockContextTypes:
        DEFAULT_TYPE = Any
    ContextTypes = _MockContextTypes()

from .config import TelegramConfig
from .logger import get_logger
from .utils import RateLimiter, encode_frame_to_bytes, retry_async

if TYPE_CHECKING:
    from .llm_analyzer import AnalysisResult, ScreenshotSet


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

        # State tracking
        self._armed = False
        self._last_detection_time: Optional[datetime] = None
        self._start_time = datetime.now()
        self._started = False

        # Rate limiting
        self._alert_rate_limiter = RateLimiter(min_interval=config.rate_limit_seconds)

        # Callbacks
        self._arm_callback: Optional[Callable[[], None]] = None
        self._disarm_callback: Optional[Callable[[], None]] = None
        self._snapshot_callback: Optional[Callable[[], None]] = None

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
            # Register command handlers
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("arm", self._cmd_arm))
            self.application.add_handler(CommandHandler("disarm", self._cmd_disarm))
            self.application.add_handler(CommandHandler("snapshot", self._cmd_snapshot))
            self.logger.debug("Command handlers registered")

            # Register error handler for uncaught exceptions
            self.application.add_error_handler(self._error_handler)
            self.logger.debug("Error handler registered")

            await self.application.initialize()
            await self.application.start()
            self._started = True
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
            self._started = False
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop Telegram bot: {e}")
            raise

    @retry_async(max_attempts=3, delay=1.0, backoff=2.0)
    async def send_message(self, text: str) -> None:
        """
        Send a text message to all configured chat IDs.

        Args:
            text: Message text to send
        """
        if not TELEGRAM_AVAILABLE:
            self.logger.warning("Cannot send message: python-telegram-bot not installed")
            return

        if not self.application:
            self.logger.warning("Cannot send message: Application not initialized")
            return

        if not self.config.chat_ids:
            self.logger.warning("Cannot send message: No chat IDs configured")
            return

        for chat_id in self.config.chat_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=int(chat_id),
                    text=text,
                    parse_mode="Markdown"
                )
                self.logger.debug(f"Message sent to chat_id: {chat_id}")
            except Exception as e:
                self.logger.error(f"Failed to send message to chat_id {chat_id}: {e}")

    @retry_async(max_attempts=3, delay=1.0, backoff=2.0)
    async def send_alert(self, screenshots: "ScreenshotSet", analysis: "AnalysisResult") -> None:
        """
        Send motion detection alert with message and 3 images as media group.

        Args:
            screenshots: ScreenshotSet containing before/now/after images and timestamp
            analysis: AnalysisResult containing analysis details
        """
        if not TELEGRAM_AVAILABLE:
            self.logger.warning("Cannot send alert: python-telegram-bot not installed")
            return

        if not self.application:
            self.logger.warning("Cannot send alert: Application not initialized")
            return

        if not self.config.chat_ids:
            self.logger.warning("Cannot send alert: No chat IDs configured")
            return

        # Apply rate limiting
        async with self._alert_rate_limiter:
            # Update last detection time
            self._last_detection_time = screenshots.timestamp

            # Format alert message
            alert_text = self._format_alert_message(screenshots, analysis)

            # Convert frames to JPEG bytes
            try:
                before_bytes = encode_frame_to_bytes(screenshots.before_frame)
                now_bytes = encode_frame_to_bytes(screenshots.now_frame)
                after_bytes = encode_frame_to_bytes(screenshots.after_frame)
            except Exception as e:
                self.logger.error(f"Failed to encode frames: {e}")
                return

            # Create media group (first photo has caption with alert message)
            media_group = [
                InputMediaPhoto(media=before_bytes, caption=alert_text, parse_mode="Markdown"),
                InputMediaPhoto(media=now_bytes),
                InputMediaPhoto(media=after_bytes)
            ]

            # Send to all configured chat IDs
            for chat_id in self.config.chat_ids:
                try:
                    await self.application.bot.send_media_group(
                        chat_id=int(chat_id),
                        media=media_group
                    )
                    self.logger.info(f"Alert sent to chat_id: {chat_id}")
                except Exception as e:
                    self.logger.error(f"Failed to send alert to chat_id {chat_id}: {e}")

    def _format_alert_message(self, screenshots: Any, analysis: Any) -> str:
        """
        Format motion detection alert message.

        Args:
            screenshots: ScreenshotSet containing before/now/after images and timestamp
            analysis: AnalysisResult containing analysis details

        Returns:
            Formatted alert message with emoji, timestamp, threat level, confidence, analysis, and detected objects
        """
        # Format timestamp
        timestamp_str = screenshots.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Format threat level (capitalize first letter for display)
        threat_level_map = {
            "yok": "Yok",
            "dusuk": "Düşük",
            "orta": "Orta",
            "yuksek": "Yüksek"
        }
        threat_level = threat_level_map.get(
            analysis.tehdit_seviyesi.lower(),
            analysis.tehdit_seviyesi.capitalize()
        )

        # Format confidence as percentage
        confidence_percent = int(analysis.guven_skoru * 100)

        # Format detected objects as comma-separated list
        detected_objects = ", ".join(analysis.tespit_edilen_nesneler)

        # Build alert message
        alert_text = (
            "🚨 *HAREKET ALGILANDI*\n\n"
            f"📅 *Zaman:* {timestamp_str}\n"
            f"⚠️ *Tehdit:* {threat_level}\n"
            f"🎯 *Güven:* %{confidence_percent}\n\n"
            f"📝 *Analiz:*\n{analysis.detayli_analiz}\n\n"
            f"🏷️ *Tespit:* {detected_objects}"
        )

        return alert_text

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

    def _handle_help(self) -> str:
        """
        Generate formatted help message with all available bot commands.

        Returns:
            Formatted help text with command descriptions
        """
        help_text = (
            "🤖 *Smart Motion Detector Bot*\n\n"
            "📋 *Kullanılabilir Komutlar:*\n\n"
            "/status - Sistem durumu (armed, son algılama, uptime)\n"
            "/arm - Hareket algılamayı aktif et\n"
            "/disarm - Hareket algılamayı pasif et\n"
            "/snapshot - Anlık görüntü al ve gönder\n"
            "/help - Bu yardım mesajını göster\n\n"
            "💡 Bot sadece yetkili chat ID'ler tarafından kullanılabilir."
        )
        return help_text

    def _handle_status(self) -> str:
        """
        Generate formatted status message with system state.

        Returns:
            Formatted status text with armed state, last detection, and uptime
        """
        # Armed state
        armed_status = "🟢 Aktif" if self._armed else "🔴 Pasif"

        # Last detection
        if self._last_detection_time:
            detection_str = self._last_detection_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            detection_str = "Henüz algılama yok"

        # Uptime calculation
        uptime_delta = datetime.now() - self._start_time
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            uptime_str = f"{days} gün, {hours} saat, {minutes} dakika"
        elif hours > 0:
            uptime_str = f"{hours} saat, {minutes} dakika"
        else:
            uptime_str = f"{minutes} dakika, {seconds} saniye"

        status_text = (
            "📊 *Sistem Durumu*\n\n"
            f"🛡️ *Durum:* {armed_status}\n"
            f"🕐 *Son Algılama:* {detection_str}\n"
            f"⏱️ *Çalışma Süresi:* {uptime_str}"
        )
        return status_text

    def _handle_arm(self) -> str:
        """
        Handle /arm command to activate motion detection.

        Returns:
            Formatted message confirming armed state
        """
        if self._armed:
            self.logger.info("System already armed")
            return "⚠️ *Sistem zaten aktif*\n\nHareket algılama çalışıyor."

        self._armed = True
        self.logger.info("System armed via Telegram command")

        # Call the arm callback if registered
        if self._arm_callback:
            try:
                self._arm_callback()
            except Exception as e:
                self.logger.error(f"Error calling arm callback: {e}")

        return "✅ *Sistem aktif edildi*\n\nHareket algılama başlatıldı."

    def _handle_disarm(self) -> str:
        """
        Handle /disarm command to deactivate motion detection.

        Returns:
            Formatted message confirming disarmed state
        """
        if not self._armed:
            self.logger.info("System already disarmed")
            return "⚠️ *Sistem zaten pasif*\n\nHareket algılama çalışmıyor."

        self._armed = False
        self.logger.info("System disarmed via Telegram command")

        # Call the disarm callback if registered
        if self._disarm_callback:
            try:
                self._disarm_callback()
            except Exception as e:
                self.logger.error(f"Error calling disarm callback: {e}")

        return "🔴 *Sistem pasif edildi*\n\nHareket algılama durduruldu."

    def _handle_snapshot(self) -> str:
        """
        Handle /snapshot command to request and send a snapshot.

        Returns:
            Formatted message confirming snapshot request
        """
        self.logger.info("Snapshot requested via Telegram command")

        # Call the snapshot callback if registered
        if self._snapshot_callback:
            try:
                self._snapshot_callback()
            except Exception as e:
                self.logger.error(f"Error calling snapshot callback: {e}")
                return "❌ *Hata*\n\nAnlık görüntü alınamadı. Lütfen tekrar deneyin."

        return "📸 *Anlık görüntü alınıyor...*\n\nGörüntü hazırlanıyor ve gönderilecek."

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            if not self._check_authorization(update.effective_chat.id):
                await update.message.reply_text("⛔ *Yetkisiz Erişim*\n\nBu botu kullanma yetkiniz yok.", parse_mode="Markdown")
                return

            help_text = self._handle_help()
            await update.message.reply_text(help_text, parse_mode="Markdown")
            self.logger.info(f"Help command processed for chat_id: {update.effective_chat.id}")
        except Exception as e:
            self.logger.error(f"Error handling /help command: {e}")
            try:
                await update.message.reply_text("❌ *Hata*\n\nKomut işlenirken bir hata oluştu.", parse_mode="Markdown")
            except Exception:
                pass

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /status command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            if not self._check_authorization(update.effective_chat.id):
                await update.message.reply_text("⛔ *Yetkisiz Erişim*\n\nBu botu kullanma yetkiniz yok.", parse_mode="Markdown")
                return

            status_text = self._handle_status()
            await update.message.reply_text(status_text, parse_mode="Markdown")
            self.logger.info(f"Status command processed for chat_id: {update.effective_chat.id}")
        except Exception as e:
            self.logger.error(f"Error handling /status command: {e}")
            try:
                await update.message.reply_text("❌ *Hata*\n\nDurum bilgisi alınırken bir hata oluştu.", parse_mode="Markdown")
            except Exception:
                pass

    async def _cmd_arm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /arm command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            if not self._check_authorization(update.effective_chat.id):
                await update.message.reply_text("⛔ *Yetkisiz Erişim*\n\nBu botu kullanma yetkiniz yok.", parse_mode="Markdown")
                return

            arm_text = self._handle_arm()
            await update.message.reply_text(arm_text, parse_mode="Markdown")
            self.logger.info(f"Arm command processed for chat_id: {update.effective_chat.id}")
        except Exception as e:
            self.logger.error(f"Error handling /arm command: {e}")
            try:
                await update.message.reply_text("❌ *Hata*\n\nSistem aktif edilirken bir hata oluştu.", parse_mode="Markdown")
            except Exception:
                pass

    async def _cmd_disarm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /disarm command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            if not self._check_authorization(update.effective_chat.id):
                await update.message.reply_text("⛔ *Yetkisiz Erişim*\n\nBu botu kullanma yetkiniz yok.", parse_mode="Markdown")
                return

            disarm_text = self._handle_disarm()
            await update.message.reply_text(disarm_text, parse_mode="Markdown")
            self.logger.info(f"Disarm command processed for chat_id: {update.effective_chat.id}")
        except Exception as e:
            self.logger.error(f"Error handling /disarm command: {e}")
            try:
                await update.message.reply_text("❌ *Hata*\n\nSistem pasif edilirken bir hata oluştu.", parse_mode="Markdown")
            except Exception:
                pass

    async def _cmd_snapshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /snapshot command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            if not self._check_authorization(update.effective_chat.id):
                await update.message.reply_text("⛔ *Yetkisiz Erişim*\n\nBu botu kullanma yetkiniz yok.", parse_mode="Markdown")
                return

            snapshot_text = self._handle_snapshot()
            await update.message.reply_text(snapshot_text, parse_mode="Markdown")
            self.logger.info(f"Snapshot command processed for chat_id: {update.effective_chat.id}")
        except Exception as e:
            self.logger.error(f"Error handling /snapshot command: {e}")
            try:
                await update.message.reply_text("❌ *Hata*\n\nAnlık görüntü alınırken bir hata oluştu.", parse_mode="Markdown")
            except Exception:
                pass

    def set_arm_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to be called when system is armed.

        Args:
            callback: Function to call when /arm command is executed
        """
        self._arm_callback = callback
        self.logger.debug("Arm callback registered")

    def set_disarm_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to be called when system is disarmed.

        Args:
            callback: Function to call when /disarm command is executed
        """
        self._disarm_callback = callback
        self.logger.debug("Disarm callback registered")

    def set_snapshot_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback function to be called when snapshot is requested.

        Args:
            callback: Function to call when /snapshot command is executed
        """
        self._snapshot_callback = callback
        self.logger.debug("Snapshot callback registered")

    @property
    def is_running(self) -> bool:
        """Return True when the bot is started and running."""
        return self._started

    async def _error_handler(self, update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle uncaught errors from the Telegram bot.

        Args:
            update: Telegram update object (may be None for some errors)
            context: Telegram context object containing the error
        """
        self.logger.error(
            f"Telegram bot error: {context.error}",
            exc_info=context.error
        )
