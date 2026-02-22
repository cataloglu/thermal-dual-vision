"""
Telegram service for Smart Motion Detector v2.

Handles Telegram bot notifications for events.
"""
import logging
import time
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from telegram import Bot
from telegram.error import TelegramError

from app.services.settings import get_settings_service


logger = logging.getLogger(__name__)


class TelegramService:
    """
    Telegram notification service.
    
    Handles:
    - Event notifications with media
    - Rate limiting (5 seconds between messages)
    - Cooldown mechanism
    - Connection testing
    """
    
    def __init__(self):
        """Initialize Telegram service."""
        self.settings_service = get_settings_service()
        self.last_message_time: Dict[str, float] = {}
        self.cooldown_until: Dict[str, float] = {}
        self._message_timestamps: deque = deque()
        logger.info("TelegramService initialized")
    
    async def send_event_notification(
        self,
        event: Dict[str, Any],
        camera: Optional[Dict[str, Any]] = None,
        collage_path: Optional[Path] = None,
        mp4_path: Optional[Path] = None,
        gif_path: Optional[Path] = None,
    ) -> bool:
        """
        Send event notification to Telegram.
        
        Args:
            event: Event data (id, camera_id, timestamp, confidence, summary)
            camera: Camera data (optional, for name)
            collage_path: Path to collage image (optional)
            mp4_path: Path to MP4 timelapse (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        bot: Bot | None = None
        try:
            # Load config
            config = self.settings_service.load_config()
            
            # Check if Telegram is enabled
            if not config.telegram.enabled:
                logger.debug("Telegram is disabled")
                return False
            
            # Check bot token
            if not config.telegram.bot_token or config.telegram.bot_token == "***REDACTED***":
                logger.warning("Telegram bot token not configured")
                return False
            
            # Check chat IDs
            if not config.telegram.chat_ids:
                logger.warning("No Telegram chat IDs configured")
                return False
            
            # Check rate limit
            camera_id = event.get('camera_id', 'unknown')
            if not self._check_rate_limit(camera_id, config.telegram.rate_limit_seconds):
                logger.debug(f"Rate limit active for camera {camera_id}")
                return False
            
            # Check cooldown
            if not self._check_cooldown(camera_id, config.telegram.cooldown_seconds):
                logger.debug(f"Cooldown active for camera {camera_id}")
                return False
            
            # Check max messages per minute (global rate limit)
            max_per_min = getattr(config.telegram, "max_messages_per_min", 20) or 20
            if not self._check_max_messages_per_min(max_per_min):
                logger.debug("Max messages per minute limit reached")
                return False
            
            # Create bot (session closed in finally to prevent HTTP connection leak)
            bot = Bot(token=config.telegram.bot_token)
            
            # Format message
            message = self._format_message(event, camera)
            
            # Send to all chat IDs
            success = False
            for chat_id in config.telegram.chat_ids:
                try:
                    # Send photo with caption if collage available
                    if collage_path and collage_path.exists() and config.telegram.send_images:
                        with open(collage_path, 'rb') as photo:
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=photo,
                                caption=message,
                                parse_mode='HTML'
                            )
                    else:
                        # Send text only
                        await bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='HTML'
                        )
                    
                    # Send MP4 timelapse if available
                    if mp4_path and config.telegram.send_images:
                        if self._is_playable_mp4(mp4_path):
                            try:
                                size_mb = mp4_path.stat().st_size / 1024 / 1024
                            except Exception:
                                size_mb = None
                            logger.info(
                                "Telegram video send queued (event=%s, size=%sMB)",
                                event.get("id"),
                                f"{size_mb:.2f}" if size_mb is not None else "unknown",
                            )
                            try:
                                with open(mp4_path, 'rb') as video:
                                    await bot.send_video(
                                        chat_id=chat_id,
                                        video=video,
                                        caption="🎥 Event Video",
                                        supports_streaming=True
                                    )
                                logger.info("Telegram video sent (event=%s)", event.get("id"))
                            except TelegramError as e:
                                logger.warning(
                                    "Telegram send_video failed (event=%s): %s. Sending as document.",
                                    event.get("id"),
                                    e,
                                )
                                try:
                                    with open(mp4_path, 'rb') as video:
                                        await bot.send_document(
                                            chat_id=chat_id,
                                            document=video,
                                            caption="🎥 Event Video",
                                        )
                                    logger.info("Telegram video sent as document (event=%s)", event.get("id"))
                                except TelegramError as doc_err:
                                    logger.error(
                                        "Telegram send_document failed (event=%s): %s",
                                        event.get("id"),
                                        doc_err,
                                    )
                        else:
                            logger.warning(
                                "Telegram video skipped (event=%s): mp4 not playable",
                                event.get("id"),
                            )
                    elif gif_path and gif_path.exists() and config.telegram.send_images:
                        with open(gif_path, 'rb') as animation:
                            await bot.send_animation(
                                chat_id=chat_id,
                                animation=animation,
                                caption="🎞️ Event Preview",
                            )
                    
                    logger.info(f"Telegram notification sent to {chat_id}")
                    success = True
                    
                except TelegramError as e:
                    logger.error(f"Failed to send to {chat_id}: {e}")
            
            # Update rate limit
            if success:
                self._update_rate_limit(camera_id)
                self._set_cooldown(camera_id, config.telegram.cooldown_seconds)
                self._record_message_sent()
            
            return success

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
        finally:
            if bot is not None:
                try:
                    await bot.session.close()
                except Exception:
                    pass
    
    def _format_message(
        self,
        event: Dict[str, Any],
        camera: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format Telegram message.
        
        Args:
            event: Event data
            camera: Camera data (optional)
            
        Returns:
            Formatted message text
        """
        camera_name = camera.get('name', event.get('camera_id', 'Unknown')) if camera else event.get('camera_id', 'Unknown')
        timestamp = event.get('timestamp', 'Unknown')
        confidence = event.get('confidence', 0) * 100
        summary = event.get('summary', 'Motion detected')

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%d.%m.%Y %H:%M:%S UTC')
        except Exception:
            time_str = timestamp

        # Format message
        message = f"""🚨 <b>{camera_name} - Motion Detected</b>

⏰ <b>Time:</b> {time_str}
🎯 <b>Confidence:</b> {confidence:.0f}%

📝 <b>Summary:</b>
{summary}"""

        return message

    def _is_playable_mp4(self, mp4_path: Path) -> bool:
        if not mp4_path or not mp4_path.exists():
            return False
        try:
            if mp4_path.stat().st_size < 1024:
                return False
        except Exception:
            return False
        return True
    
    def _check_rate_limit(self, camera_id: str, rate_limit_seconds: int) -> bool:
        """
        Check if rate limit allows sending.
        
        Args:
            camera_id: Camera ID
            rate_limit_seconds: Rate limit in seconds
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        last_time = self.last_message_time.get(camera_id, 0)
        
        if now - last_time < rate_limit_seconds:
            return False
        
        return True
    
    def _update_rate_limit(self, camera_id: str):
        """
        Update rate limit timestamp.
        
        Args:
            camera_id: Camera ID
        """
        self.last_message_time[camera_id] = time.time()
    
    def _check_cooldown(self, camera_id: str, cooldown_seconds: int) -> bool:
        """
        Check if cooldown period has passed.
        
        Args:
            camera_id: Camera ID
            cooldown_seconds: Cooldown in seconds
            
        Returns:
            True if allowed, False if in cooldown
        """
        now = time.time()
        cooldown_until = self.cooldown_until.get(camera_id, 0)
        
        if now < cooldown_until:
            return False
        
        return True
    
    def _set_cooldown(self, camera_id: str, cooldown_seconds: int):
        """
        Set cooldown period.
        
        Args:
            camera_id: Camera ID
            cooldown_seconds: Cooldown in seconds
        """
        self.cooldown_until[camera_id] = time.time() + cooldown_seconds

    def _check_max_messages_per_min(self, max_per_min: int) -> bool:
        """
        Check if we're within the max messages per minute limit.
        
        Args:
            max_per_min: Maximum messages allowed per minute
            
        Returns:
            True if allowed, False if limit reached
        """
        now = time.time()
        cutoff = now - 60.0
        while self._message_timestamps and self._message_timestamps[0] < cutoff:
            self._message_timestamps.popleft()
        return len(self._message_timestamps) < max_per_min

    def _record_message_sent(self):
        """Record that a message was sent (for max_messages_per_min tracking)."""
        self._message_timestamps.append(time.time())
    
    async def test_connection(
        self,
        bot_token: str,
        chat_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Test Telegram connection.
        
        Args:
            bot_token: Telegram bot token
            chat_ids: List of chat IDs
            
        Returns:
            Dict with success status and message
        """
        try:
            # Create bot
            bot = Bot(token=bot_token)
            
            # Get bot info
            start_time = time.time()
            me = await bot.get_me()
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Test send to first chat ID
            if chat_ids:
                test_message = f"✅ Test mesajı başarılı!\n\nBot: @{me.username}\nLatency: {latency_ms}ms"
                await bot.send_message(
                    chat_id=chat_ids[0],
                    text=test_message
                )
            
            return {
                "success": True,
                "bot_username": me.username,
                "latency_ms": latency_ms,
                "error_reason": None
            }
            
        except TelegramError as e:
            logger.error(f"Telegram test failed: {e}")
            return {
                "success": False,
                "bot_username": None,
                "latency_ms": None,
                "error_reason": str(e)
            }
        except Exception as e:
            logger.error(f"Telegram test error: {e}")
            return {
                "success": False,
                "bot_username": None,
                "latency_ms": None,
                "error_reason": str(e)
            }
    
    def is_enabled(self) -> bool:
        """
        Check if Telegram is enabled.
        
        Returns:
            True if Telegram is enabled and configured
        """
        try:
            config = self.settings_service.load_config()
            has_token = config.telegram.bot_token and config.telegram.bot_token != "***REDACTED***"
            has_chats = bool(config.telegram.chat_ids)
            return bool(config.telegram.enabled and has_token and has_chats)
        except Exception:
            return False


# Global singleton instance
_telegram_service: Optional[TelegramService] = None


def get_telegram_service() -> TelegramService:
    """
    Get or create the global Telegram service instance.
    
    Returns:
        TelegramService: Global Telegram service instance
    """
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service
