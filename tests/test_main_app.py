"""Integration tests for Smart Motion Detector main application."""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest

from src.config import Config
from src.main import SmartMotionDetector


@pytest.fixture
def test_config() -> Config:
    """Create test configuration."""
    config = Config()
    config.telegram.enabled = True
    config.telegram.bot_token = "test_token_123"
    config.telegram.chat_ids = ["123456789"]
    config.mqtt.host = "test-broker"
    config.mqtt.port = 1883
    config.llm.api_key = "test_api_key"
    return config


@pytest.fixture
def mock_modules():
    """Mock all module imports."""
    mocks = {
        "mqtt_client": None,
        "telegram_bot": None,
        "llm_analyzer": None,
        "motion_detector": None,
        "yolo_detector": None,
        "screenshot_manager": None,
    }

    with patch("src.main.MQTTClient") as mqtt_mock, \
         patch("src.main.TelegramBot") as telegram_mock, \
         patch("src.main.LLMAnalyzer") as llm_mock, \
         patch("src.main.MotionDetector") as motion_mock, \
         patch("src.main.YOLODetector") as yolo_mock, \
         patch("src.main.ScreenshotManager") as screenshot_mock:

        # Configure MQTT mock
        mqtt_instance = AsyncMock()
        mqtt_instance.connect = AsyncMock()
        mqtt_instance.disconnect = AsyncMock()
        mqtt_instance.is_connected = True
        mqtt_instance.publish_motion = AsyncMock()
        mqtt_mock.return_value = mqtt_instance
        mocks["mqtt_client"] = mqtt_instance

        # Configure Telegram mock
        telegram_instance = AsyncMock()
        telegram_instance.start = AsyncMock()
        telegram_instance.stop = AsyncMock()
        telegram_instance.is_running = True
        telegram_instance.send_alert = AsyncMock()
        telegram_mock.return_value = telegram_instance
        mocks["telegram_bot"] = telegram_instance

        # Configure LLM mock
        llm_instance = Mock()
        llm_instance.analyze = AsyncMock()
        llm_mock.return_value = llm_instance
        mocks["llm_analyzer"] = llm_instance

        # Configure Motion Detector mock
        motion_instance = AsyncMock()
        motion_instance.stop = AsyncMock()
        motion_mock.return_value = motion_instance
        mocks["motion_detector"] = motion_instance

        # Configure YOLO mock
        yolo_instance = Mock()
        yolo_instance.detect = Mock(return_value=[])
        yolo_instance.cleanup = Mock()
        yolo_mock.return_value = yolo_instance
        mocks["yolo_detector"] = yolo_instance

        # Configure Screenshot Manager mock
        screenshot_instance = AsyncMock()
        screenshot_instance.cleanup = AsyncMock()
        screenshot_mock.return_value = screenshot_instance
        mocks["screenshot_manager"] = screenshot_instance

        yield mocks


class TestSmartMotionDetectorInitialization:
    """Test Smart Motion Detector initialization."""

    def test_initialization_with_valid_config(self, test_config: Config):
        """Test detector initializes with valid configuration."""
        detector = SmartMotionDetector(test_config)

        assert detector.config == test_config
        assert detector._armed is False
        assert detector._start_time is None
        assert detector._last_detection_time is None
        assert detector.motion_detector is None
        assert detector.yolo_detector is None
        assert detector.screenshot_manager is None
        assert detector.llm_analyzer is None
        assert detector.mqtt_client is None
        assert detector.telegram_bot is None
        assert detector._web_app is None
        assert detector._web_runner is None

    def test_initialization_logs_creation(self, test_config: Config):
        """Test that initialization logs detector creation."""
        with patch("src.main.logger") as mock_logger:
            SmartMotionDetector(test_config)
            mock_logger.info.assert_called_with("Smart Motion Detector initialized")


class TestSmartMotionDetectorLifecycle:
    """Test detector lifecycle (start/stop)."""

    @pytest.mark.asyncio
    async def test_start_initializes_all_modules(
        self, test_config: Config, mock_modules
    ):
        """Test start() initializes all available modules."""
        detector = SmartMotionDetector(test_config)

        await detector.start()

        # Verify modules were initialized
        assert detector.mqtt_client is not None
        assert detector.telegram_bot is not None
        assert detector.llm_analyzer is not None
        assert detector.motion_detector is not None
        assert detector.yolo_detector is not None
        assert detector.screenshot_manager is not None
        assert detector._start_time is not None

        # Verify modules were started
        mock_modules["mqtt_client"].connect.assert_called_once()
        mock_modules["telegram_bot"].start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_initializes_health_check_server(
        self, test_config: Config, mock_modules
    ):
        """Test start() initializes HTTP health check server."""
        detector = SmartMotionDetector(test_config)

        # Mock aiohttp components
        with patch("src.main.web.Application") as app_mock, \
             patch("src.main.web.AppRunner") as runner_mock, \
             patch("src.main.web.TCPSite") as site_mock:

            app_instance = Mock()
            app_instance.router = Mock()
            app_instance.router.add_get = Mock()
            app_mock.return_value = app_instance

            runner_instance = AsyncMock()
            runner_instance.setup = AsyncMock()
            runner_mock.return_value = runner_instance

            site_instance = AsyncMock()
            site_instance.start = AsyncMock()
            site_mock.return_value = site_instance

            await detector.start()

            # Verify HTTP server was set up
            app_mock.assert_called_once()
            app_instance.router.add_get.assert_called_once_with(
                '/health', detector._health_endpoint
            )
            runner_mock.assert_called_once_with(app_instance)
            runner_instance.setup.assert_called_once()
            site_mock.assert_called_once_with(runner_instance, '0.0.0.0', 8099)
            site_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_handles_module_failures_gracefully(
        self, test_config: Config, mock_modules
    ):
        """Test start() continues when individual modules fail."""
        # Make MQTT connect fail
        mock_modules["mqtt_client"].connect.side_effect = Exception("Connection failed")

        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Should still complete startup despite MQTT failure
        assert detector._start_time is not None
        # MQTT client should be None after failure
        assert detector.mqtt_client is None

    @pytest.mark.asyncio
    async def test_stop_cleans_up_all_modules(
        self, test_config: Config, mock_modules
    ):
        """Test stop() cleans up all modules in reverse order."""
        detector = SmartMotionDetector(test_config)

        # Mock web runner for cleanup
        detector._web_runner = AsyncMock()
        detector._web_runner.cleanup = AsyncMock()

        await detector.start()
        await detector.stop()

        # Verify modules were stopped/cleaned up
        mock_modules["mqtt_client"].disconnect.assert_called_once()
        mock_modules["telegram_bot"].stop.assert_called_once()
        mock_modules["motion_detector"].stop.assert_called_once()
        mock_modules["screenshot_manager"].cleanup.assert_called_once()
        mock_modules["yolo_detector"].cleanup.assert_called_once()

        # Verify state was reset
        assert detector._armed is False
        assert detector._last_detection_time is None
        assert detector.mqtt_client is None
        assert detector.telegram_bot is None
        assert detector.llm_analyzer is None
        assert detector.motion_detector is None
        assert detector.yolo_detector is None
        assert detector.screenshot_manager is None

    @pytest.mark.asyncio
    async def test_stop_handles_cleanup_failures_gracefully(
        self, test_config: Config, mock_modules
    ):
        """Test stop() continues cleanup even when individual modules fail."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Make telegram stop fail
        mock_modules["telegram_bot"].stop.side_effect = Exception("Stop failed")

        # Should complete cleanup despite failures
        await detector.stop()

        # Verify other modules were still stopped
        mock_modules["mqtt_client"].disconnect.assert_called_once()
        # State should still be reset
        assert detector._armed is False

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self, test_config: Config):
        """Test stop() can be called safely when detector not started."""
        detector = SmartMotionDetector(test_config)
        # Should not raise error
        await detector.stop()

    @pytest.mark.asyncio
    async def test_stop_cleans_up_health_check_server(
        self, test_config: Config, mock_modules
    ):
        """Test stop() cleans up HTTP health check server."""
        detector = SmartMotionDetector(test_config)

        # Mock web runner
        detector._web_runner = AsyncMock()
        detector._web_runner.cleanup = AsyncMock()

        await detector.start()
        await detector.stop()

        # Verify cleanup was called
        detector._web_runner.cleanup.assert_called_once()
        assert detector._web_runner is None
        assert detector._web_app is None


class TestSmartMotionDetectorArmDisarm:
    """Test arm/disarm functionality."""

    def test_arm_sets_armed_state(self, test_config: Config):
        """Test arm() sets armed state to True."""
        detector = SmartMotionDetector(test_config)

        assert detector.is_armed() is False

        detector.arm()

        assert detector.is_armed() is True

    def test_disarm_clears_armed_state(self, test_config: Config):
        """Test disarm() sets armed state to False."""
        detector = SmartMotionDetector(test_config)
        detector.arm()

        assert detector.is_armed() is True

        detector.disarm()

        assert detector.is_armed() is False

    def test_arm_logs_state_change(self, test_config: Config):
        """Test arm() logs state change."""
        detector = SmartMotionDetector(test_config)

        with patch("src.main.logger") as mock_logger:
            detector.arm()
            mock_logger.info.assert_called_with("Smart Motion Detector armed")

    def test_disarm_logs_state_change(self, test_config: Config):
        """Test disarm() logs state change."""
        detector = SmartMotionDetector(test_config)
        detector.arm()

        with patch("src.main.logger") as mock_logger:
            detector.disarm()
            mock_logger.info.assert_called_with("Smart Motion Detector disarmed")

    def test_multiple_arm_disarm_cycles(self, test_config: Config):
        """Test multiple arm/disarm cycles work correctly."""
        detector = SmartMotionDetector(test_config)

        for _ in range(3):
            detector.arm()
            assert detector.is_armed() is True

            detector.disarm()
            assert detector.is_armed() is False


class TestSmartMotionDetectorHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status_dict(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() returns complete status dictionary."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        health = await detector.health_check()

        assert "status" in health
        assert "armed" in health
        assert "start_time" in health
        assert "last_detection" in health
        assert "modules" in health

    @pytest.mark.asyncio
    async def test_health_check_includes_module_status(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() includes status for all modules."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        health = await detector.health_check()

        assert "mqtt" in health["modules"]
        assert "telegram" in health["modules"]
        assert "llm" in health["modules"]
        assert "yolo" in health["modules"]
        assert "screenshots" in health["modules"]
        assert "motion" in health["modules"]

    @pytest.mark.asyncio
    async def test_health_check_reflects_armed_state(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() reflects current armed state."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Check disarmed state
        health = await detector.health_check()
        assert health["armed"] is False

        # Arm and check again
        detector.arm()
        health = await detector.health_check()
        assert health["armed"] is True

    @pytest.mark.asyncio
    async def test_health_check_includes_start_time(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() includes start time after startup."""
        detector = SmartMotionDetector(test_config)

        # Before start
        health = await detector.health_check()
        assert health["start_time"] is None

        # After start
        await detector.start()
        health = await detector.health_check()
        assert health["start_time"] is not None
        assert isinstance(health["start_time"], str)

    @pytest.mark.asyncio
    async def test_health_check_includes_last_detection(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() includes last detection time."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # No detection yet
        health = await detector.health_check()
        assert health["last_detection"] is None

        # Simulate detection
        detector._last_detection_time = datetime.now()
        health = await detector.health_check()
        assert health["last_detection"] is not None

    @pytest.mark.asyncio
    async def test_health_check_reports_mqtt_connection(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() reports MQTT connection status."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        health = await detector.health_check()

        assert health["modules"]["mqtt"]["available"] is True
        assert health["modules"]["mqtt"]["connected"] is True

    @pytest.mark.asyncio
    async def test_health_check_reports_telegram_status(
        self, test_config: Config, mock_modules
    ):
        """Test health_check() reports Telegram bot status."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        health = await detector.health_check()

        assert health["modules"]["telegram"]["available"] is True
        assert health["modules"]["telegram"]["running"] is True

    @pytest.mark.asyncio
    async def test_health_check_when_modules_unavailable(
        self, test_config: Config
    ):
        """Test health_check() when modules are not available."""
        detector = SmartMotionDetector(test_config)

        health = await detector.health_check()

        # All modules should be unavailable
        assert health["modules"]["mqtt"]["available"] is False
        assert health["modules"]["telegram"]["available"] is False
        assert health["modules"]["llm"]["available"] is False

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_json(
        self, test_config: Config, mock_modules
    ):
        """Test HTTP health endpoint returns JSON response."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Mock request
        mock_request = Mock()

        with patch("src.main.web.json_response") as json_mock:
            await detector._health_endpoint(mock_request)
            json_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_endpoint_handles_errors(
        self, test_config: Config, mock_modules
    ):
        """Test HTTP health endpoint handles errors gracefully."""
        detector = SmartMotionDetector(test_config)

        # Mock health_check to raise error
        with patch.object(detector, "health_check", side_effect=Exception("Test error")):
            mock_request = Mock()

            with patch("src.main.web.json_response") as json_mock:
                await detector._health_endpoint(mock_request)

                # Should return error response
                call_args = json_mock.call_args
                assert "status" in call_args[0][0]
                assert call_args[0][0]["status"] == "error"
                assert call_args[1]["status"] == 500


class TestSmartMotionDetectorSignalHandlers:
    """Test signal handler setup."""

    def test_setup_signal_handlers_registers_handlers(self, test_config: Config):
        """Test setup_signal_handlers() registers SIGTERM and SIGINT."""
        detector = SmartMotionDetector(test_config)

        with patch("signal.signal") as signal_mock:
            detector.setup_signal_handlers()

            # Verify both signals were registered
            assert signal_mock.call_count == 2
            calls = signal_mock.call_args_list

            # Check SIGTERM
            assert any(call[0][0] == 15 for call in calls)  # SIGTERM = 15
            # Check SIGINT
            assert any(call[0][0] == 2 for call in calls)  # SIGINT = 2

    def test_signal_handler_logs_shutdown(self, test_config: Config):
        """Test signal handler logs graceful shutdown."""
        detector = SmartMotionDetector(test_config)
        detector.setup_signal_handlers()

        # Get the registered handler
        with patch("signal.signal") as signal_mock:
            detector.setup_signal_handlers()
            handler = signal_mock.call_args_list[0][0][1]

            # Call handler with mock signal
            with patch("src.main.logger") as mock_logger, \
                 patch("asyncio.get_event_loop") as loop_mock:
                loop_instance = Mock()
                loop_instance.is_running.return_value = False
                loop_mock.return_value = loop_instance

                handler(15, None)  # SIGTERM

                # Verify logging occurred
                assert mock_logger.info.called


class TestSmartMotionDetectorEventPipeline:
    """Test motion detection event pipeline."""

    @pytest.mark.asyncio
    async def test_motion_callback_ignores_when_disarmed(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback does nothing when detector is disarmed."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Ensure disarmed
        detector.disarm()

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        with patch("src.main.logger") as mock_logger:
            await detector._on_motion_detected(frame, timestamp)

            # Should log debug message and return
            debug_calls = [call for call in mock_logger.debug.call_args_list]
            assert any("system is disarmed" in str(call) for call in debug_calls)

        # YOLO should not be called
        mock_modules["yolo_detector"].detect.assert_not_called()

    @pytest.mark.asyncio
    async def test_motion_callback_processes_when_armed(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback processes event when armed."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Arm the detector
        detector.arm()

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        await detector._on_motion_detected(frame, timestamp)

        # YOLO should be called
        mock_modules["yolo_detector"].detect.assert_called_once_with(frame)

        # Last detection time should be updated
        assert detector._last_detection_time == timestamp

    @pytest.mark.asyncio
    async def test_motion_callback_runs_full_pipeline(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback executes full event pipeline."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Mock LLM analysis result
        mock_analysis = Mock()
        mock_analysis.gercek_hareket = True
        mock_analysis.guven_skoru = 0.95
        mock_analysis.tehdit_seviyesi = "orta"
        mock_modules["llm_analyzer"].analyze.return_value = mock_analysis

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        # Reduce wait time for testing
        detector.config.screenshots.after_seconds = 0.1

        await detector._on_motion_detected(frame, timestamp)

        # Verify pipeline steps
        mock_modules["yolo_detector"].detect.assert_called_once()
        mock_modules["llm_analyzer"].analyze.assert_called_once()
        mock_modules["mqtt_client"].publish_motion.assert_called_once()
        mock_modules["telegram_bot"].send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_motion_callback_handles_yolo_failure(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback continues when YOLO detection fails."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Make YOLO fail
        mock_modules["yolo_detector"].detect.side_effect = Exception("YOLO failed")

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        # Reduce wait time
        detector.config.screenshots.after_seconds = 0.1

        # Should not raise, pipeline should continue
        await detector._on_motion_detected(frame, timestamp)

        # LLM should still be called
        mock_modules["llm_analyzer"].analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_motion_callback_handles_llm_failure(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback continues when LLM analysis fails."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Make LLM fail
        mock_modules["llm_analyzer"].analyze.side_effect = Exception("LLM failed")

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        detector.config.screenshots.after_seconds = 0.1

        # Should not raise
        await detector._on_motion_detected(frame, timestamp)

        # MQTT and Telegram should not be called without analysis
        mock_modules["mqtt_client"].publish_motion.assert_not_called()
        mock_modules["telegram_bot"].send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_motion_callback_waits_for_after_screenshot(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback waits configured time for after screenshot."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Set wait time
        wait_time = 0.2
        detector.config.screenshots.after_seconds = wait_time

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        start_time = asyncio.get_event_loop().time()
        await detector._on_motion_detected(frame, timestamp)
        elapsed_time = asyncio.get_event_loop().time() - start_time

        # Should have waited at least the configured time
        assert elapsed_time >= wait_time

    @pytest.mark.asyncio
    async def test_motion_callback_skips_notifications_when_mqtt_disconnected(
        self, test_config: Config, mock_modules
    ):
        """Test motion callback skips MQTT when disconnected."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Disconnect MQTT
        mock_modules["mqtt_client"].is_connected = False

        # Mock LLM analysis
        mock_analysis = Mock()
        mock_analysis.gercek_hareket = True
        mock_modules["llm_analyzer"].analyze.return_value = mock_analysis

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        detector.config.screenshots.after_seconds = 0.1

        await detector._on_motion_detected(frame, timestamp)

        # MQTT should not be called
        mock_modules["mqtt_client"].publish_motion.assert_not_called()


class TestSmartMotionDetectorIntegration:
    """Integration tests for full startup/shutdown cycles."""

    @pytest.mark.asyncio
    async def test_full_startup_shutdown_cycle(
        self, test_config: Config, mock_modules
    ):
        """Test complete startup and shutdown cycle."""
        detector = SmartMotionDetector(test_config)

        # Start detector
        await detector.start()

        # Verify startup
        assert detector._start_time is not None
        assert detector.mqtt_client is not None
        assert detector.telegram_bot is not None

        # Verify modules started
        mock_modules["mqtt_client"].connect.assert_called_once()
        mock_modules["telegram_bot"].start.assert_called_once()

        # Arm the detector
        detector.arm()
        assert detector.is_armed() is True

        # Check health
        health = await detector.health_check()
        assert health["status"] == "ok"
        assert health["armed"] is True

        # Disarm
        detector.disarm()
        assert detector.is_armed() is False

        # Stop detector
        await detector.stop()

        # Verify shutdown
        mock_modules["mqtt_client"].disconnect.assert_called_once()
        mock_modules["telegram_bot"].stop.assert_called_once()
        assert detector._armed is False
        assert detector.mqtt_client is None

    @pytest.mark.asyncio
    async def test_multiple_startup_shutdown_cycles(
        self, test_config: Config, mock_modules
    ):
        """Test multiple startup/shutdown cycles work correctly."""
        detector = SmartMotionDetector(test_config)

        for i in range(2):
            # Reset mocks
            mock_modules["mqtt_client"].connect.reset_mock()
            mock_modules["telegram_bot"].start.reset_mock()

            # Start
            await detector.start()
            assert detector._start_time is not None

            # Arm
            detector.arm()
            assert detector.is_armed() is True

            # Stop
            await detector.stop()
            assert detector._armed is False

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self, test_config: Config, mock_modules
    ):
        """Test concurrent health checks and state changes."""
        detector = SmartMotionDetector(test_config)
        await detector.start()

        # Run multiple operations concurrently
        async def arm_disarm():
            detector.arm()
            await asyncio.sleep(0.01)
            detector.disarm()

        async def check_health():
            return await detector.health_check()

        # Execute concurrently
        results = await asyncio.gather(
            arm_disarm(),
            check_health(),
            check_health(),
            check_health()
        )

        # Should complete without errors
        health_results = [r for r in results if r is not None]
        assert len(health_results) == 3
        for health in health_results:
            assert "status" in health

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_optional_modules(
        self, test_config: Config
    ):
        """Test detector works with minimal modules."""
        # Don't use mock_modules fixture - let imports be None
        detector = SmartMotionDetector(test_config)

        # Should start successfully even without modules
        await detector.start()

        # Health check should report unavailable modules
        health = await detector.health_check()
        assert health["status"] in ["ok", "degraded"]

        # Arm/disarm should still work
        detector.arm()
        assert detector.is_armed() is True

        # Stop should work
        await detector.stop()

    @pytest.mark.asyncio
    async def test_event_pipeline_with_minimal_modules(
        self, test_config: Config
    ):
        """Test event pipeline degrades gracefully with missing modules."""
        detector = SmartMotionDetector(test_config)
        await detector.start()
        detector.arm()

        # Simulate motion with no modules available
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        timestamp = datetime.now()

        detector.config.screenshots.after_seconds = 0.1

        # Should not raise error
        await detector._on_motion_detected(frame, timestamp)

        # Should update last detection time
        assert detector._last_detection_time == timestamp
