"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from src.config import (
    CameraConfig,
    Config,
    LLMConfig,
    MQTTConfig,
    MotionConfig,
    ScreenshotConfig,
    TelegramConfig,
    YoloConfig,
)


@pytest.mark.unit
class TestConfigDataclasses:
    """Test configuration dataclass creation."""

    def test_camera_config_defaults(self):
        """Test CameraConfig with default values."""
        config = CameraConfig()
        assert config.url == ""
        assert config.fps == 5
        assert config.resolution == (1280, 720)

    def test_motion_config_defaults(self):
        """Test MotionConfig with default values."""
        config = MotionConfig()
        assert config.sensitivity == 7
        assert config.min_area == 500
        assert config.cooldown_seconds == 5

    def test_yolo_config_defaults(self):
        """Test YoloConfig with default values."""
        config = YoloConfig()
        assert config.model == "yolov8n"
        assert config.confidence == 0.5
        assert config.classes == ["person", "car", "dog", "cat"]

    def test_llm_config_defaults(self):
        """Test LLMConfig with default values."""
        config = LLMConfig()
        assert config.api_key == ""
        assert config.model == "gpt-4-vision-preview"
        assert config.max_tokens == 1000
        assert config.timeout == 30

    def test_screenshot_config_defaults(self):
        """Test ScreenshotConfig with default values."""
        config = ScreenshotConfig()
        assert config.before_seconds == 3
        assert config.after_seconds == 3
        assert config.quality == 85
        assert config.max_stored == 100
        assert config.buffer_seconds == 10

    def test_mqtt_config_defaults(self):
        """Test MQTTConfig with default values."""
        config = MQTTConfig()
        assert config.host == "core-mosquitto"
        assert config.port == 1883
        assert config.username == ""
        assert config.password == ""
        assert config.topic_prefix == "smart_motion"
        assert config.discovery is True
        assert config.discovery_prefix == "homeassistant"
        assert config.qos == 1

    def test_telegram_config_defaults(self):
        """Test TelegramConfig with default values."""
        config = TelegramConfig()
        assert config.enabled is False
        assert config.bot_token == ""
        assert config.chat_ids == []
        assert config.rate_limit_seconds == 5

    def test_main_config_defaults(self):
        """Test main Config with default values."""
        config = Config()
        assert isinstance(config.camera, CameraConfig)
        assert isinstance(config.motion, MotionConfig)
        assert isinstance(config.yolo, YoloConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.screenshots, ScreenshotConfig)
        assert isinstance(config.mqtt, MQTTConfig)
        assert isinstance(config.telegram, TelegramConfig)
        assert config.log_level == "INFO"


@pytest.mark.unit
class TestConfigFromEnv:
    """Test loading configuration from environment variables."""

    def test_from_env_with_defaults(self):
        """Test loading config from env with all defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()

            # Should use default values
            assert config.camera.url == ""
            assert config.camera.fps == 5
            assert config.motion.sensitivity == 7
            assert config.yolo.model == "yolov8n"
            assert config.mqtt.host == "core-mosquitto"
            assert config.log_level == "INFO"

    def test_from_env_camera_config(self):
        """Test loading camera config from environment."""
        env_vars = {
            "CAMERA_URL": "rtsp://test:554/stream",
            "CAMERA_FPS": "10",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.camera.url == "rtsp://test:554/stream"
            assert config.camera.fps == 10

    def test_from_env_motion_config(self):
        """Test loading motion config from environment."""
        env_vars = {
            "MOTION_SENSITIVITY": "15",
            "MOTION_MIN_AREA": "1000",
            "MOTION_COOLDOWN": "10",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.motion.sensitivity == 15
            assert config.motion.min_area == 1000
            assert config.motion.cooldown_seconds == 10

    def test_from_env_yolo_config(self):
        """Test loading YOLO config from environment."""
        env_vars = {
            "YOLO_MODEL": "yolov8m",
            "YOLO_CONFIDENCE": "0.7",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.yolo.model == "yolov8m"
            assert config.yolo.confidence == 0.7

    def test_from_env_llm_config(self):
        """Test loading LLM config from environment."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key-12345",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.llm.api_key == "sk-test-key-12345"

    def test_from_env_screenshot_config(self):
        """Test loading screenshot config from environment."""
        env_vars = {
            "SCREENSHOT_BEFORE": "5",
            "SCREENSHOT_AFTER": "4",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.screenshots.before_seconds == 5
            assert config.screenshots.after_seconds == 4

    def test_from_env_mqtt_config(self):
        """Test loading MQTT config from environment."""
        env_vars = {
            "MQTT_HOST": "mqtt.example.com",
            "MQTT_PORT": "8883",
            "MQTT_USER": "testuser",
            "MQTT_PASSWORD": "testpass",
            "MQTT_TOPIC_PREFIX": "my_motion",
            "MQTT_DISCOVERY": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.mqtt.host == "mqtt.example.com"
            assert config.mqtt.port == 8883
            assert config.mqtt.username == "testuser"
            assert config.mqtt.password == "testpass"
            assert config.mqtt.topic_prefix == "my_motion"
            assert config.mqtt.discovery is False

    def test_from_env_mqtt_discovery_true(self):
        """Test MQTT discovery enabled from environment."""
        env_vars = {
            "MQTT_DISCOVERY": "true",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            assert config.mqtt.discovery is True

    def test_from_env_mqtt_discovery_case_insensitive(self):
        """Test MQTT discovery is case-insensitive."""
        env_vars = {
            "MQTT_DISCOVERY": "TRUE",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            assert config.mqtt.discovery is True

    def test_from_env_telegram_disabled(self):
        """Test Telegram disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()

            assert config.telegram.enabled is False
            assert config.telegram.bot_token == ""
            assert config.telegram.chat_ids == []

    def test_from_env_telegram_enabled(self):
        """Test loading Telegram config when enabled."""
        env_vars = {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "12345678",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.telegram.enabled is True
            assert config.telegram.bot_token == "123456:ABC-DEF"
            assert config.telegram.chat_ids == ["12345678"]

    def test_from_env_telegram_multiple_chat_ids(self):
        """Test loading multiple Telegram chat IDs."""
        env_vars = {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "12345678, 87654321, 11111111",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.telegram.chat_ids == ["12345678", "87654321", "11111111"]

    def test_from_env_telegram_empty_chat_id(self):
        """Test Telegram with empty chat ID."""
        env_vars = {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
            "TELEGRAM_CHAT_ID": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.telegram.chat_ids == []

    def test_from_env_log_level(self):
        """Test loading log level from environment."""
        env_vars = {
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            assert config.log_level == "DEBUG"

    def test_from_env_full_config(self):
        """Test loading complete configuration."""
        env_vars = {
            "CAMERA_URL": "rtsp://camera:554/stream",
            "CAMERA_FPS": "15",
            "MOTION_SENSITIVITY": "10",
            "YOLO_MODEL": "yolov8l",
            "OPENAI_API_KEY": "sk-test-key",
            "MQTT_HOST": "mqtt.local",
            "MQTT_PORT": "1883",
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": "bot_token",
            "TELEGRAM_CHAT_ID": "chat_id",
            "LOG_LEVEL": "WARNING",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()

            # Verify a few key values
            assert config.camera.url == "rtsp://camera:554/stream"
            assert config.yolo.model == "yolov8l"
            assert config.telegram.enabled is True
            assert config.log_level == "WARNING"


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_empty_config_fails(self):
        """Test validation fails with empty config."""
        config = Config()
        errors = config.validate()

        assert len(errors) >= 2
        assert "Camera URL is required" in errors
        assert "OpenAI API key is required" in errors

    def test_validate_missing_camera_url(self):
        """Test validation fails without camera URL."""
        config = Config()
        config.llm.api_key = "sk-test-key"

        errors = config.validate()

        assert "Camera URL is required" in errors

    def test_validate_missing_api_key(self):
        """Test validation fails without OpenAI API key."""
        config = Config()
        config.camera.url = "rtsp://test"

        errors = config.validate()

        assert "OpenAI API key is required" in errors

    def test_validate_telegram_enabled_missing_token(self):
        """Test validation fails when Telegram enabled but no token."""
        config = Config()
        config.camera.url = "rtsp://test"
        config.llm.api_key = "sk-test-key"
        config.telegram.enabled = True
        config.telegram.chat_ids = ["12345"]

        errors = config.validate()

        assert "Telegram bot token is required when enabled" in errors

    def test_validate_telegram_enabled_missing_chat_id(self):
        """Test validation fails when Telegram enabled but no chat ID."""
        config = Config()
        config.camera.url = "rtsp://test"
        config.llm.api_key = "sk-test-key"
        config.telegram.enabled = True
        config.telegram.bot_token = "bot_token"

        errors = config.validate()

        assert "Telegram chat ID is required when enabled" in errors

    def test_validate_telegram_enabled_all_required(self):
        """Test validation requires all Telegram fields when enabled."""
        config = Config()
        config.camera.url = "rtsp://test"
        config.llm.api_key = "sk-test-key"
        config.telegram.enabled = True

        errors = config.validate()

        assert "Telegram bot token is required when enabled" in errors
        assert "Telegram chat ID is required when enabled" in errors

    def test_validate_telegram_disabled_no_errors(self):
        """Test validation passes when Telegram disabled."""
        config = Config()
        config.camera.url = "rtsp://test"
        config.llm.api_key = "sk-test-key"
        config.telegram.enabled = False

        errors = config.validate()

        # Should not have Telegram-related errors
        telegram_errors = [e for e in errors if "Telegram" in e]
        assert len(telegram_errors) == 0

    def test_validate_valid_config(self):
        """Test validation passes with valid config."""
        config = Config()
        config.camera.url = "rtsp://camera:554/stream"
        config.llm.api_key = "sk-test-key-12345"

        errors = config.validate()

        assert len(errors) == 0

    def test_validate_valid_config_with_telegram(self):
        """Test validation passes with valid config including Telegram."""
        config = Config()
        config.camera.url = "rtsp://camera:554/stream"
        config.llm.api_key = "sk-test-key-12345"
        config.telegram.enabled = True
        config.telegram.bot_token = "123456:ABC-DEF"
        config.telegram.chat_ids = ["12345678"]

        errors = config.validate()

        assert len(errors) == 0
