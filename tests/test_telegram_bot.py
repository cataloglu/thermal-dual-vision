"""Unit tests for Telegram bot functionality."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

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

    @pytest.mark.asyncio
    async def test_commands(self):
        """Test all command handlers with authorization and error handling."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"]
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

        # Test /help command
        await bot._cmd_help(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args[0][0]
        assert "Smart Motion Detector Bot" in call_args
        assert "Yetkisiz Erişim" not in call_args

        # Test /help command unauthorized
        await bot._cmd_help(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args[0][0]
        assert "Yetkisiz Erişim" in call_args

        # Reset mocks
        authorized_update.message.reset_mock()
        unauthorized_update.message.reset_mock()

        # Test /status command
        await bot._cmd_status(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args[0][0]
        assert "Sistem Durumu" in call_args
        assert "Yetkisiz Erişim" not in call_args

        # Test /status command unauthorized
        await bot._cmd_status(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args[0][0]
        assert "Yetkisiz Erişim" in call_args

        # Reset mocks
        authorized_update.message.reset_mock()
        unauthorized_update.message.reset_mock()

        # Test /arm command
        assert bot._armed is False
        await bot._cmd_arm(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args[0][0]
        assert "Sistem aktif edildi" in call_args
        assert bot._armed is True

        # Test /arm command unauthorized
        await bot._cmd_arm(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args[0][0]
        assert "Yetkisiz Erişim" in call_args

        # Reset mocks
        authorized_update.message.reset_mock()
        unauthorized_update.message.reset_mock()

        # Test /disarm command
        assert bot._armed is True
        await bot._cmd_disarm(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args[0][0]
        assert "Sistem pasif edildi" in call_args
        assert bot._armed is False

        # Test /disarm command unauthorized
        await bot._cmd_disarm(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args[0][0]
        assert "Yetkisiz Erişim" in call_args

        # Reset mocks
        authorized_update.message.reset_mock()
        unauthorized_update.message.reset_mock()

        # Test /snapshot command with callback
        callback_mock = Mock()
        bot.set_snapshot_callback(callback_mock)
        await bot._cmd_snapshot(authorized_update, context)
        authorized_update.message.reply_text.assert_called_once()
        call_args = authorized_update.message.reply_text.call_args[0][0]
        assert "Anlık görüntü alınıyor" in call_args
        callback_mock.assert_called_once()

        # Test /snapshot command unauthorized
        await bot._cmd_snapshot(unauthorized_update, context)
        unauthorized_update.message.reply_text.assert_called_once()
        call_args = unauthorized_update.message.reply_text.call_args[0][0]
        assert "Yetkisiz Erişim" in call_args

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

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_rapid_alerts(self):
        """Test rate limiting blocks alerts sent too rapidly."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"],
            rate_limit_seconds=0.1  # 100ms for fast test
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
            bot = TelegramBot(config)

            # Mock the application and bot
            bot.application = Mock()
            bot.application.bot.send_photo = AsyncMock()
            bot.application.bot.send_video = AsyncMock()

            # Create mock screenshots
            screenshots = Mock()
            screenshots.timestamp = datetime.now()
            screenshots.before = Mock()
            screenshots.early = Mock()
            screenshots.peak = Mock()
            screenshots.late = Mock()
            screenshots.after = Mock()

            # Create mock analysis
            analysis = Mock()
            analysis.tehdit_seviyesi = "orta"
            analysis.guven_skoru = 0.85
            analysis.detayli_analiz = "Test analysis"
            analysis.tespit_edilen_nesneler = ["test"]

            # Mock encode_frame_to_bytes to return test bytes
            with patch("src.telegram_bot.encode_frame_to_bytes", return_value=b"test_image"):
                # Record start time
                start_time = asyncio.get_event_loop().time()

                # Send first alert (should be immediate)
                await bot.send_alert(screenshots, analysis)
                first_alert_time = asyncio.get_event_loop().time()

                # Send second alert (should be rate limited)
                await bot.send_alert(screenshots, analysis)
                second_alert_time = asyncio.get_event_loop().time()

                # First alert should be immediate (within 50ms)
                assert first_alert_time - start_time < 0.05

                # Second alert should be delayed by at least the rate limit
                elapsed = second_alert_time - first_alert_time
                assert elapsed >= config.rate_limit_seconds

    @pytest.mark.asyncio
    async def test_rate_limiting_allows_alerts_after_interval(self):
        """Test rate limiting allows alerts after min_interval has passed."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"],
            rate_limit_seconds=0.05  # 50ms for fast test
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
            bot = TelegramBot(config)

            # Mock the application and bot
            bot.application = Mock()
            bot.application.bot.send_photo = AsyncMock()
            bot.application.bot.send_video = AsyncMock()

            # Create mock screenshots
            screenshots = Mock()
            screenshots.timestamp = datetime.now()
            screenshots.before = Mock()
            screenshots.early = Mock()
            screenshots.peak = Mock()
            screenshots.late = Mock()
            screenshots.after = Mock()

            # Create mock analysis
            analysis = Mock()
            analysis.tehdit_seviyesi = "orta"
            analysis.guven_skoru = 0.85
            analysis.detayli_analiz = "Test analysis"
            analysis.tespit_edilen_nesneler = ["test"]

            # Mock encode_frame_to_bytes to return test bytes
            with patch("src.telegram_bot.encode_frame_to_bytes", return_value=b"test_image"):
                # Send first alert
                await bot.send_alert(screenshots, analysis)

                # Wait for rate limit to pass
                await asyncio.sleep(0.06)

                # Send second alert (should not be blocked)
                start_time = asyncio.get_event_loop().time()
                await bot.send_alert(screenshots, analysis)
                end_time = asyncio.get_event_loop().time()

                # Second alert should be immediate since interval passed
                elapsed = end_time - start_time
                assert elapsed < 0.05  # Should be much less than rate limit

                # Both alerts should have been sent
                assert bot.application.bot.send_photo.call_count == 2
                assert bot.application.bot.send_video.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limiting_updates_last_detection_time(self):
        """Test send_alert updates last detection time after rate limiting."""
        config = TelegramConfig(
            bot_token="test_token_123",
            chat_ids=["123456789"],
            rate_limit_seconds=0.05
        )

        with patch("src.telegram_bot.TELEGRAM_AVAILABLE", True):
            bot = TelegramBot(config)

            # Mock the application and bot
            bot.application = Mock()
            bot.application.bot.send_photo = AsyncMock()
            bot.application.bot.send_video = AsyncMock()

            # Create mock screenshots with specific timestamp
            test_timestamp = datetime(2024, 1, 15, 14, 30, 25)
            screenshots = Mock()
            screenshots.timestamp = test_timestamp
            screenshots.before = Mock()
            screenshots.early = Mock()
            screenshots.peak = Mock()
            screenshots.late = Mock()
            screenshots.after = Mock()

            # Create mock analysis
            analysis = Mock()
            analysis.tehdit_seviyesi = "yuksek"
            analysis.guven_skoru = 0.95
            analysis.detayli_analiz = "Critical alert"
            analysis.tespit_edilen_nesneler = ["person"]

            # Mock encode_frame_to_bytes
            with patch("src.telegram_bot.encode_frame_to_bytes", return_value=b"test_image"):
                # Initially no detection time
                assert bot._last_detection_time is None

                # Send alert
                await bot.send_alert(screenshots, analysis)

                # Last detection time should be updated to screenshot timestamp
                assert bot._last_detection_time == test_timestamp


def test_alerts():
    """Comprehensive test for alert formatting and rate limiting.

    This test function serves as an entry point for the verification command
    and ensures all alert-related functionality works correctly.
    """
    # Test 1: Alert message formatting
    config = TelegramConfig(
        bot_token="test_token_123",
        chat_ids=["123456789"],
        rate_limit_seconds=5
    )

    bot = TelegramBot(config)

    # Create mock data
    screenshots = Mock()
    screenshots.timestamp = datetime(2024, 1, 15, 14, 30, 25)

    analysis = Mock()
    analysis.tehdit_seviyesi = "yuksek"
    analysis.guven_skoru = 0.92
    analysis.detayli_analiz = "Bahçede hareket eden bir kişi tespit edildi"
    analysis.tespit_edilen_nesneler = ["insan", "araba"]

    # Format alert message
    alert_text = bot._format_alert_message(screenshots, analysis)

    # Verify formatting
    assert "HAREKET ALGILANDI" in alert_text
    assert "2024-01-15 14:30:25" in alert_text
    assert "Yüksek" in alert_text  # Threat level should be capitalized
    assert "%92" in alert_text  # Confidence as percentage
    assert "Bahçede hareket eden bir kişi tespit edildi" in alert_text
    assert "insan, araba" in alert_text  # Objects as comma-separated

    # Test 2: Threat level mapping
    threat_levels = {
        "yok": "Yok",
        "dusuk": "Düşük",
        "orta": "Orta",
        "yuksek": "Yüksek"
    }

    for level_input, level_output in threat_levels.items():
        analysis.tehdit_seviyesi = level_input
        alert_text = bot._format_alert_message(screenshots, analysis)
        assert level_output in alert_text, f"Expected {level_output} for threat level {level_input}"

    # Test 3: Rate limiter initialization
    assert bot._alert_rate_limiter is not None
    assert bot._alert_rate_limiter.min_interval == config.rate_limit_seconds

    # Test 4: Alert formatting with empty objects list
    analysis.tespit_edilen_nesneler = []
    alert_text = bot._format_alert_message(screenshots, analysis)
    assert "🏷️ *Tespit:*" in alert_text  # Should still include label

    # Test 5: Alert formatting with single object
    analysis.tespit_edilen_nesneler = ["kedi"]
    alert_text = bot._format_alert_message(screenshots, analysis)
    assert "kedi" in alert_text
    assert "," not in alert_text.split("🏷️ *Tespit:*")[1]  # No comma for single item
