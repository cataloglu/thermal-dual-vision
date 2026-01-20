"""
Unit tests for settings service.

Tests cover:
- Default config loading
- Config save and load
- Partial updates
- Secret masking
- Validation errors
- Invalid JSON handling
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from app.models.config import AppConfig
from app.services.settings import SettingsService


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        # Monkey patch the CONFIG_FILE path
        monkeypatch.setattr(SettingsService, "CONFIG_FILE", config_path)
        yield tmpdir


@pytest.fixture
def settings_service(temp_config_dir):
    """Create a fresh settings service instance for each test."""
    # Reset singleton
    SettingsService._instance = None
    service = SettingsService()
    return service


def test_load_default_config(settings_service):
    """Test loading default config when file doesn't exist."""
    config = settings_service.load_config()
    
    assert isinstance(config, AppConfig)
    assert config.detection.model == "yolov8n-person"
    assert config.detection.confidence_threshold == 0.25
    assert config.motion.sensitivity == 7
    assert config.thermal.enable_enhancement is True
    assert config.stream.protocol == "tcp"
    assert config.live.output_mode == "mjpeg"
    assert config.record.enabled is False
    assert config.ai.enabled is False
    assert config.telegram.enabled is False


def test_save_and_load_config(settings_service):
    """Test saving and loading config."""
    # Create custom config
    config = AppConfig()
    config.detection.model = "yolov8s-person"
    config.detection.confidence_threshold = 0.5
    config.motion.sensitivity = 8
    config.ai.enabled = True
    config.ai.api_key = "sk-test-api-key-12345"
    
    # Save config
    settings_service.save_config(config)
    
    # Load config
    loaded_config = settings_service.load_config()
    
    assert loaded_config.detection.model == "yolov8s-person"
    assert loaded_config.detection.confidence_threshold == 0.5
    assert loaded_config.motion.sensitivity == 8
    assert loaded_config.ai.enabled is True
    assert loaded_config.ai.api_key == "sk-test-api-key-12345"


def test_partial_update(settings_service):
    """Test partial config update."""
    # Load default config
    settings_service.load_config()
    
    # Update only detection settings
    partial_data = {
        "detection": {
            "model": "yolov8s-person",
            "confidence_threshold": 0.3
        }
    }
    
    updated = settings_service.update_settings(partial_data)
    
    # Check updated fields
    assert updated["detection"]["model"] == "yolov8s-person"
    assert updated["detection"]["confidence_threshold"] == 0.3
    
    # Check other fields remain default
    assert updated["detection"]["inference_fps"] == 5  # Default
    assert updated["motion"]["sensitivity"] == 7  # Default
    assert updated["thermal"]["enable_enhancement"] is True  # Default


def test_nested_partial_update(settings_service):
    """Test nested partial update."""
    settings_service.load_config()
    
    # Update nested field
    partial_data = {
        "live": {
            "webrtc": {
                "enabled": True,
                "go2rtc_url": "http://localhost:1984"
            }
        }
    }
    
    updated = settings_service.update_settings(partial_data)
    
    assert updated["live"]["webrtc"]["enabled"] is True
    assert updated["live"]["webrtc"]["go2rtc_url"] == "http://localhost:1984"
    assert updated["live"]["output_mode"] == "mjpeg"  # Default unchanged


def test_secrets_masked(settings_service):
    """Test that secrets are masked in get_settings."""
    # Create config with secrets
    config = AppConfig()
    config.ai.api_key = "sk-test-api-key-12345"
    config.telegram.bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    
    settings_service.save_config(config)
    
    # Get settings (should be masked)
    settings = settings_service.get_settings()
    
    assert settings["ai"]["api_key"] == "***REDACTED***"
    assert settings["telegram"]["bot_token"] == "***REDACTED***"


def test_empty_secrets_not_masked(settings_service):
    """Test that empty secrets are not masked."""
    settings_service.load_config()
    
    settings = settings_service.get_settings()
    
    # Empty secrets should remain empty
    assert settings["ai"]["api_key"] == ""
    assert settings["telegram"]["bot_token"] == ""


def test_validation_error_confidence_threshold(settings_service):
    """Test validation error for invalid confidence threshold."""
    settings_service.load_config()
    
    # Invalid confidence (out of range)
    partial_data = {
        "detection": {
            "confidence_threshold": 1.5  # Invalid: must be 0.0-1.0
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)
    
    assert "confidence_threshold" in str(exc_info.value)


def test_validation_error_inference_fps(settings_service):
    """Test validation error for invalid inference FPS."""
    settings_service.load_config()
    
    # Invalid FPS (out of range)
    partial_data = {
        "detection": {
            "inference_fps": 50  # Invalid: must be 1-30
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)
    
    assert "inference_fps" in str(exc_info.value)


def test_validation_error_sensitivity(settings_service):
    """Test validation error for invalid motion sensitivity."""
    settings_service.load_config()
    
    # Invalid sensitivity (out of range)
    partial_data = {
        "motion": {
            "sensitivity": 15  # Invalid: must be 1-10
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)
    
    assert "sensitivity" in str(exc_info.value)


def test_validation_error_disk_limit(settings_service):
    """Test validation error for invalid disk limit."""
    settings_service.load_config()
    
    # Invalid disk limit (out of range)
    partial_data = {
        "record": {
            "disk_limit_percent": 30  # Invalid: must be 50-95
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)
    
    assert "disk_limit_percent" in str(exc_info.value)


def test_validation_error_snapshot_quality(settings_service):
    """Test validation error for invalid snapshot quality."""
    settings_service.load_config()
    
    # Invalid quality (out of range)
    partial_data = {
        "telegram": {
            "snapshot_quality": 150  # Invalid: must be 0-100
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)
    
    assert "snapshot_quality" in str(exc_info.value)


def test_invalid_json(settings_service, temp_config_dir):
    """Test handling of invalid JSON in config file."""
    # Write invalid JSON to config file
    config_path = Path(temp_config_dir) / "config.json"
    with open(config_path, "w") as f:
        f.write("{invalid json content")
    
    # Should raise JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        settings_service.load_config()


def test_config_file_created_on_first_load(settings_service, temp_config_dir):
    """Test that config file is created on first load."""
    config_path = Path(temp_config_dir) / "config.json"
    
    # Config file should not exist initially
    assert not config_path.exists()
    
    # Load config (should create file)
    settings_service.load_config()
    
    # Config file should now exist
    assert config_path.exists()
    
    # Verify file content
    with open(config_path, "r") as f:
        data = json.load(f)
    
    assert "detection" in data
    assert "motion" in data
    assert "thermal" in data


def test_get_default_config(settings_service):
    """Test getting default config as dictionary."""
    default_config = settings_service.get_default_config()
    
    assert isinstance(default_config, dict)
    assert "detection" in default_config
    assert "motion" in default_config
    assert default_config["detection"]["model"] == "yolov8n-person"
    assert default_config["motion"]["sensitivity"] == 7


def test_concurrent_updates(settings_service):
    """Test that concurrent updates are handled safely."""
    import threading
    
    settings_service.load_config()
    
    errors = []
    
    def update_detection():
        try:
            settings_service.update_settings({
                "detection": {"confidence_threshold": 0.3}
            })
        except Exception as e:
            errors.append(e)
    
    def update_motion():
        try:
            settings_service.update_settings({
                "motion": {"sensitivity": 8}
            })
        except Exception as e:
            errors.append(e)
    
    # Run updates concurrently
    threads = [
        threading.Thread(target=update_detection),
        threading.Thread(target=update_motion)
    ]
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    # No errors should occur
    assert len(errors) == 0
    
    # Verify final state (one of the updates should win)
    settings = settings_service.get_settings()
    assert settings["detection"]["confidence_threshold"] in [0.25, 0.3]
    assert settings["motion"]["sensitivity"] in [7, 8]


def test_update_multiple_sections(settings_service):
    """Test updating multiple sections at once."""
    settings_service.load_config()
    
    partial_data = {
        "detection": {
            "model": "yolov8s-person",
            "confidence_threshold": 0.5
        },
        "motion": {
            "sensitivity": 9,
            "cooldown_seconds": 3
        },
        "thermal": {
            "enable_enhancement": False
        },
        "ai": {
            "enabled": True,
            "api_key": "sk-test-key"
        }
    }
    
    updated = settings_service.update_settings(partial_data)
    
    assert updated["detection"]["model"] == "yolov8s-person"
    assert updated["detection"]["confidence_threshold"] == 0.5
    assert updated["motion"]["sensitivity"] == 9
    assert updated["motion"]["cooldown_seconds"] == 3
    assert updated["thermal"]["enable_enhancement"] is False
    assert updated["ai"]["enabled"] is True
    assert updated["ai"]["api_key"] == "***REDACTED***"  # Masked


def test_validation_error_ai_key_format(settings_service):
    """Test validation error for invalid OpenAI API key format."""
    settings_service.load_config()

    partial_data = {
        "ai": {
            "enabled": True,
            "api_key": "invalid-key"
        }
    }

    with pytest.raises(ValidationError) as exc_info:
        settings_service.update_settings(partial_data)

    assert "api_key" in str(exc_info.value)


def test_singleton_pattern(temp_config_dir):
    """Test that SettingsService is a singleton."""
    # Reset singleton
    SettingsService._instance = None
    
    service1 = SettingsService()
    service2 = SettingsService()
    
    assert service1 is service2
