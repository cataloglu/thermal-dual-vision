"""Integration tests for standalone mode config loading."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import Config


class TestStandaloneConfigLoading:
    """Test config loading in standalone mode (HA_MODE=false)."""

    def test_ha_mode_false_from_env(self):
        """Test that HA_MODE=false is correctly set from environment."""
        os.environ["HA_MODE"] = "false"

        config = Config.from_env()

        assert config.ha_mode is False

        # Cleanup
        del os.environ["HA_MODE"]

    def test_ha_mode_true_from_env(self):
        """Test that HA_MODE=true is correctly set from environment."""
        os.environ["HA_MODE"] = "true"

        config = Config.from_env()

        assert config.ha_mode is True

        # Cleanup
        del os.environ["HA_MODE"]

    def test_ha_mode_default_is_true(self):
        """Test that HA_MODE defaults to true when not set."""
        # Ensure HA_MODE is not set
        if "HA_MODE" in os.environ:
            del os.environ["HA_MODE"]

        config = Config.from_env()

        assert config.ha_mode is True

    def test_config_yaml_is_read(self):
        """Test that config.yaml is correctly parsed."""
        # Use the actual config.yaml file
        config_path = Path("config/config.yaml")

        if not config_path.exists():
            pytest.skip("config/config.yaml not found")

        config = Config.from_yaml(config_path)

        # Verify values from YAML
        assert config.ha_mode is False
        assert config.camera.url == "rtsp://example.com/stream"
        assert config.camera.fps == 5
        assert config.motion.sensitivity == 7
        assert config.mqtt.host == "localhost"
        assert config.mqtt.username == "yaml-user"
        assert config.mqtt.password == "yaml-pass"
        assert config.llm.api_key == "yaml-api-key"

    def test_env_vars_override_yaml(self):
        """Test that environment variables override YAML values."""
        # Create a temporary YAML config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_config = {
                'camera': {'url': 'rtsp://yaml.com/stream', 'fps': 5},
                'motion': {'sensitivity': 7},
                'mqtt': {'host': 'yaml-host', 'port': 1883, 'username': 'yaml-user'},
                'llm': {'api_key': 'yaml-api-key'},
                'log_level': 'INFO',
                'ha_mode': False
            }
            yaml.dump(yaml_config, f)
            temp_path = f.name

        try:
            # Set environment variables that should override YAML
            os.environ["CAMERA_URL"] = "rtsp://env.com/stream"
            os.environ["CAMERA_FPS"] = "10"
            os.environ["MOTION_SENSITIVITY"] = "5"
            os.environ["MQTT_HOST"] = "env-host"
            os.environ["MQTT_USER"] = "env-user"
            os.environ["OPENAI_API_KEY"] = "env-api-key"
            os.environ["LOG_LEVEL"] = "DEBUG"
            os.environ["HA_MODE"] = "true"

            # Load config with priority: env > yaml > defaults
            config = Config.from_sources(temp_path)

            # Verify environment variables took precedence
            assert config.camera.url == "rtsp://env.com/stream"
            assert config.camera.fps == 10
            assert config.motion.sensitivity == 5
            assert config.mqtt.host == "env-host"
            assert config.mqtt.username == "env-user"
            assert config.llm.api_key == "env-api-key"
            assert config.log_level == "DEBUG"
            assert config.ha_mode is True

            # Verify YAML values are used when env vars are not set
            assert config.mqtt.port == 1883  # Not overridden, from YAML

        finally:
            # Cleanup
            os.unlink(temp_path)
            for key in ["CAMERA_URL", "CAMERA_FPS", "MOTION_SENSITIVITY",
                       "MQTT_HOST", "MQTT_USER", "OPENAI_API_KEY", "LOG_LEVEL", "HA_MODE"]:
                if key in os.environ:
                    del os.environ[key]

    def test_defaults_when_no_yaml_or_env(self):
        """Test that default values are used when neither YAML nor env vars are set."""
        # Ensure no relevant env vars are set
        env_vars = ["CAMERA_URL", "CAMERA_FPS", "MOTION_SENSITIVITY", "MQTT_HOST",
                   "MQTT_PORT", "OPENAI_API_KEY", "HA_MODE"]
        saved_env = {}
        for key in env_vars:
            if key in os.environ:
                saved_env[key] = os.environ[key]
                del os.environ[key]

        try:
            # Load config without YAML file
            config = Config.from_sources(None)

            # Verify defaults
            assert config.camera.url == ""
            assert config.camera.fps == 5
            assert config.motion.sensitivity == 7
            assert config.motion.min_area == 500
            assert config.mqtt.host == "core-mosquitto"
            assert config.mqtt.port == 1883
            assert config.llm.api_key == ""
            assert config.ha_mode is True  # Default

        finally:
            # Restore env vars
            for key, value in saved_env.items():
                os.environ[key] = value

    def test_priority_order_integration(self):
        """Test complete priority order: env > yaml > defaults."""
        # Create a temporary YAML config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_config = {
                'camera': {'url': 'rtsp://yaml.com/stream', 'fps': 15},
                'motion': {'sensitivity': 8, 'min_area': 600},
                'mqtt': {'host': 'yaml-mqtt', 'port': 1884},
            }
            yaml.dump(yaml_config, f)
            temp_path = f.name

        try:
            # Set only some env vars
            os.environ["CAMERA_URL"] = "rtsp://env.com/stream"
            os.environ["HA_MODE"] = "false"

            config = Config.from_sources(temp_path)

            # From env (highest priority)
            assert config.camera.url == "rtsp://env.com/stream"
            assert config.ha_mode is False

            # From YAML (medium priority)
            assert config.camera.fps == 15
            assert config.motion.sensitivity == 8
            assert config.mqtt.host == "yaml-mqtt"
            assert config.mqtt.port == 1884

            # From defaults (lowest priority)
            assert config.motion.cooldown_seconds == 5  # Not in YAML or env
            assert config.yolo.model == "yolov8n"  # Not in YAML or env

        finally:
            # Cleanup
            os.unlink(temp_path)
            for key in ["CAMERA_URL", "HA_MODE"]:
                if key in os.environ:
                    del os.environ[key]

    def test_standalone_mode_with_actual_config_file(self):
        """Test loading with the actual config/config.yaml in standalone mode."""
        config_path = Path("config/config.yaml")

        if not config_path.exists():
            pytest.skip("config/config.yaml not found")

        # Set HA_MODE to false
        os.environ["HA_MODE"] = "false"

        # Override one value from YAML with env var
        os.environ["MQTT_HOST"] = "env-override-mqtt"

        try:
            config = Config.from_sources(config_path)

            # Verify HA_MODE is false
            assert config.ha_mode is False

            # Verify YAML values are loaded
            assert config.camera.url == "rtsp://example.com/stream"
            assert config.llm.api_key == "yaml-api-key"
            assert config.mqtt.username == "yaml-user"

            # Verify env override
            assert config.mqtt.host == "env-override-mqtt"

        finally:
            # Cleanup
            for key in ["HA_MODE", "MQTT_HOST"]:
                if key in os.environ:
                    del os.environ[key]

    def test_missing_yaml_file_uses_defaults(self):
        """Test that missing YAML file gracefully falls back to defaults."""
        # Use a non-existent path
        config = Config.from_sources("config/nonexistent.yaml")

        # Should use defaults
        assert config.camera.fps == 5
        assert config.motion.sensitivity == 7
        assert config.ha_mode is True

    def test_telegram_config_from_yaml(self):
        """Test Telegram configuration loading from YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_config = {
                'telegram': {
                    'enabled': True,
                    'bot_token': 'yaml-bot-token',
                    'chat_ids': ['12345', '67890'],
                    'rate_limit_seconds': 10
                }
            }
            yaml.dump(yaml_config, f)
            temp_path = f.name

        try:
            config = Config.from_yaml(temp_path)

            assert config.telegram.enabled is True
            assert config.telegram.bot_token == 'yaml-bot-token'
            assert config.telegram.chat_ids == ['12345', '67890']
            assert config.telegram.rate_limit_seconds == 10

        finally:
            os.unlink(temp_path)

    def test_telegram_config_env_override(self):
        """Test Telegram configuration override from environment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_config = {
                'telegram': {
                    'enabled': False,
                    'bot_token': 'yaml-bot-token',
                    'chat_ids': ['12345']
                }
            }
            yaml.dump(yaml_config, f)
            temp_path = f.name

        try:
            os.environ["TELEGRAM_ENABLED"] = "true"
            os.environ["TELEGRAM_BOT_TOKEN"] = "env-bot-token"
            os.environ["TELEGRAM_CHAT_ID"] = "99999,88888"

            config = Config.from_sources(temp_path)

            # Env vars should override YAML
            assert config.telegram.enabled is True
            assert config.telegram.bot_token == 'env-bot-token'
            assert config.telegram.chat_ids == ['99999', '88888']

        finally:
            os.unlink(temp_path)
            for key in ["TELEGRAM_ENABLED", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
                if key in os.environ:
                    del os.environ[key]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
