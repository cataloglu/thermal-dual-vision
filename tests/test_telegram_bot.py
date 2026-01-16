"""Unit tests for Telegram bot functionality."""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.config import TelegramConfig
from src.telegram_bot import TelegramBot


class TestTelegramBotInitialization:
    """Test bot initialization and setup."""

    def test_bot_initialization_with_valid_config(self):
        """Test bot initializes with valid configuration."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789", "987654321"],
            rate_limit_seconds=5,
            send_images=True
        )

        bot = TelegramBot(config)

        assert bot.config == config
        assert bot._armed is False
        assert bot._last_detection_time is None
        assert bot._start_time is not None
        assert bot._arm_callback is None
        assert bot._disarm_callback is None
        assert bot._snapshot_callback is None

    def test_bot_initialization_without_telegram_library(self):
        """Test bot handles missing python-telegram-bot gracefully."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", False):
            bot = TelegramBot(config)
            assert bot.application is None

    def test_bot_initialization_without_token(self):
        """Test bot handles missing token gracefully."""
        config = TelegramConfig(
            bot_token="",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        assert bot.config == config


class TestTelegramBotLifecycle:
    """Test bot start and stop methods."""

    @pytest.mark.asyncio
    async def test_start_without_telegram_available(self):
        """Test start() when python-telegram-bot is not available."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", False):
            bot = TelegramBot(config)
            await bot.start()  # Should not raise error

    @pytest.mark.asyncio
    async def test_start_without_application(self):
        """Test start() when Application is not initialized."""
        config = TelegramConfig(
            bot_token="",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot.application = None
        await bot.start()  # Should not raise error

    @pytest.mark.asyncio
    async def test_stop_without_telegram_available(self):
        """Test stop() when python-telegram-bot is not available."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", False):
            bot = TelegramBot(config)
            await bot.stop()  # Should not raise error

    @pytest.mark.asyncio
    async def test_stop_without_application(self):
        """Test stop() when Application is not initialized."""
        config = TelegramConfig(
            bot_token="",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot.application = None
        await bot.stop()  # Should not raise error


class TestTelegramBotAuthorization:
    """Test authorization checking."""

    def test_check_authorization_with_valid_chat_id(self):
        """Test authorization passes for valid chat ID."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789", "987654321"]
        )

        bot = TelegramBot(config)

        assert bot._check_authorization(123456789) is True
        assert bot._check_authorization(987654321) is True

    def test_check_authorization_with_invalid_chat_id(self):
        """Test authorization fails for invalid chat ID."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)

        assert bot._check_authorization(999999999) is False

    def test_check_authorization_with_no_chat_ids(self):
        """Test authorization fails when no chat IDs configured."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=[]
        )

        bot = TelegramBot(config)

        assert bot._check_authorization(123456789) is False

    @pytest.mark.asyncio
    async def test_authorization(self):
        """Test authorization whitelist for command handlers."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789", "987654321"]
        )

        bot = TelegramBot(config)

        # Create mock update with authorized chat ID
        authorized_update = Mock()
        authorized_update.effective_chat.id = 123456789
        authorized_update.message = AsyncMock()

        # Create mock update with unauthorized chat ID
        unauthorized_update = Mock()
        unauthorized_update.effective_chat.id = 999999999
        unauthorized_update.message = AsyncMock()

        # Mock context
        context = Mock()

        # Test authorized chat ID can execute command
        await bot._cmd_status(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args
        assert "Yetkisiz Erişim" not in call_args[0][0]
        assert "Sistem Durumu" in call_args[0][0]

        # Test unauthorized chat ID is blocked
        await bot._cmd_status(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args
        assert "Yetkisiz Erişim" in call_args[0][0]
        assert "Sistem Durumu" not in call_args[0][0]

        # Test second authorized chat ID
        second_authorized_update = Mock()
        second_authorized_update.effective_chat.id = 987654321
        second_authorized_update.message = AsyncMock()

        await bot._cmd_help(second_authorized_update, context)
        second_authorized_update.message.reply_text.assert_called_once()
        call_args = second_authorized_update.message.reply_text.call_args
        assert "Yetkisiz Erişim" not in call_args[0][0]
        assert "Smart Motion Detector Bot" in call_args[0][0]


class TestTelegramBotCommands:
    """Test command handlers."""

    def test_handle_help_returns_help_text(self):
        """Test /help command returns formatted help text."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        help_text = bot._handle_help()

        assert "Smart Motion Detector Bot" in help_text
        assert "/status" in help_text
        assert "/arm" in help_text
        assert "/disarm" in help_text
        assert "/snapshot" in help_text
        assert "/help" in help_text

    def test_handle_status_with_no_detection(self):
        """Test /status command when no detection has occurred."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        status_text = bot._handle_status()

        assert "Sistem Durumu" in status_text
        assert "Pasif" in status_text
        assert "Henüz algılama yok" in status_text

    def test_handle_status_when_armed(self):
        """Test /status command when system is armed."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot._armed = True
        status_text = bot._handle_status()

        assert "Aktif" in status_text

    def test_handle_status_with_detection(self):
        """Test /status command shows last detection time."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        test_time = datetime(2024, 1, 15, 14, 30, 25)
        bot._last_detection_time = test_time
        status_text = bot._handle_status()

        assert "2024-01-15 14:30:25" in status_text

    def test_handle_arm_activates_system(self):
        """Test /arm command activates motion detection."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        arm_text = bot._handle_arm()

        assert bot._armed is True
        assert "Sistem aktif edildi" in arm_text

    def test_handle_arm_when_already_armed(self):
        """Test /arm command when already armed."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot._armed = True
        arm_text = bot._handle_arm()

        assert "zaten aktif" in arm_text

    def test_handle_arm_calls_callback(self):
        """Test /arm command calls registered callback."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        callback_mock = Mock()
        bot.set_arm_callback(callback_mock)

        bot._handle_arm()

        callback_mock.assert_called_once()

    def test_handle_disarm_deactivates_system(self):
        """Test /disarm command deactivates motion detection."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot._armed = True
        disarm_text = bot._handle_disarm()

        assert bot._armed is False
        assert "Sistem pasif edildi" in disarm_text

    def test_handle_disarm_when_already_disarmed(self):
        """Test /disarm command when already disarmed."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        disarm_text = bot._handle_disarm()

        assert "zaten pasif" in disarm_text

    def test_handle_disarm_calls_callback(self):
        """Test /disarm command calls registered callback."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot._armed = True
        callback_mock = Mock()
        bot.set_disarm_callback(callback_mock)

        bot._handle_disarm()

        callback_mock.assert_called_once()

    def test_handle_snapshot_calls_callback(self):
        """Test /snapshot command calls registered callback."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        callback_mock = Mock()
        bot.set_snapshot_callback(callback_mock)

        snapshot_text = bot._handle_snapshot()

        callback_mock.assert_called_once()
        assert "Anlık görüntü alınıyor" in snapshot_text

    def test_handle_snapshot_without_callback(self):
        """Test /snapshot command without callback registered."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        snapshot_text = bot._handle_snapshot()

        assert "Anlık görüntü alınıyor" in snapshot_text


class TestTelegramBotAlerts:
    """Test alert formatting and sending."""

    def test_format_alert_message(self):
        """Test alert message formatting."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)

        # Create mock screenshot set
        screenshots = Mock()
        screenshots.timestamp = datetime(2024, 1, 15, 14, 30, 25)

        # Create mock analysis result
        analysis = Mock()
        analysis.tehdit_seviyesi = "orta"
        analysis.guven_skoru = 0.85
        analysis.detayli_analiz = "Bahçede yürüyen bir kişi tespit edildi..."
        analysis.tespit_edilen_nesneler = ["insan", "köpek"]

        alert_text = bot._format_alert_message(screenshots, analysis)

        assert "HAREKET ALGILANDI" in alert_text
        assert "2024-01-15 14:30:25" in alert_text
        assert "Orta" in alert_text
        assert "%85" in alert_text
        assert "Bahçede yürüyen bir kişi tespit edildi" in alert_text
        assert "insan, köpek" in alert_text

    def test_format_alert_message_threat_level_mapping(self):
        """Test threat level is properly mapped in Turkish."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)

        screenshots = Mock()
        screenshots.timestamp = datetime.now()

        # Test different threat levels
        threat_levels = {
            "yok": "Yok",
            "dusuk": "Düşük",
            "orta": "Orta",
            "yuksek": "Yüksek"
        }

        for level_input, level_output in threat_levels.items():
            analysis = Mock()
            analysis.tehdit_seviyesi = level_input
            analysis.guven_skoru = 0.85
            analysis.detayli_analiz = "Test analysis"
            analysis.tespit_edilen_nesneler = ["test"]

            alert_text = bot._format_alert_message(screenshots, analysis)
            assert level_output in alert_text

    @pytest.mark.asyncio
    async def test_send_message_without_telegram_available(self):
        """Test send_message() when python-telegram-bot is not available."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", False):
            bot = TelegramBot(config)
            await bot.send_message("Test message")  # Should not raise error

    @pytest.mark.asyncio
    async def test_send_message_without_application(self):
        """Test send_message() when Application is not initialized."""
        config = TelegramConfig(
            bot_token="",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot.application = None
        await bot.send_message("Test message")  # Should not raise error

    @pytest.mark.asyncio
    async def test_send_message_without_chat_ids(self):
        """Test send_message() when no chat IDs configured."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=[]
        )

        bot = TelegramBot(config)
        await bot.send_message("Test message")  # Should not raise error

    @pytest.mark.asyncio
    async def test_send_alert_without_telegram_available(self):
        """Test send_alert() when python-telegram-bot is not available."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", False):
            bot = TelegramBot(config)
            screenshots = Mock()
            analysis = Mock()
            await bot.send_alert(screenshots, analysis)  # Should not raise error

    @pytest.mark.asyncio
    async def test_send_alert_without_application(self):
        """Test send_alert() when Application is not initialized."""
        config = TelegramConfig(
            bot_token="",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        bot.application = None
        screenshots = Mock()
        analysis = Mock()
        await bot.send_alert(screenshots, analysis)  # Should not raise error


class TestTelegramBotCallbacks:
    """Test callback registration."""

    def test_set_arm_callback(self):
        """Test arm callback registration."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        callback_mock = Mock()
        bot.set_arm_callback(callback_mock)

        assert bot._arm_callback == callback_mock

    def test_set_disarm_callback(self):
        """Test disarm callback registration."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        callback_mock = Mock()
        bot.set_disarm_callback(callback_mock)

        assert bot._disarm_callback == callback_mock

    def test_set_snapshot_callback(self):
        """Test snapshot callback registration."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
        )

        bot = TelegramBot(config)
        callback_mock = Mock()
        bot.set_snapshot_callback(callback_mock)

        assert bot._snapshot_callback == callback_mock


class TestTelegramBotRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_initialized(self):
        """Test rate limiter is initialized with correct interval."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"],
            rate_limit_seconds=10
        )

        bot = TelegramBot(config)

        assert bot._alert_rate_limiter is not None
        assert bot._alert_rate_limiter.min_interval == 10
