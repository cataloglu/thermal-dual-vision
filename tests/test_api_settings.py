"""
Integration tests for settings API endpoints.

Tests the FastAPI endpoints for GET and PUT /api/settings.
"""
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.settings import SettingsService


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        # Monkey patch the CONFIG_FILE path
        monkeypatch.setattr(SettingsService, "CONFIG_FILE", config_path)
        # Reset singleton
        SettingsService._instance = None
        yield tmpdir


@pytest.fixture
def client(temp_config_dir):
    """Create test client with temporary config."""
    return TestClient(app)


def test_get_settings_default(client):
    """Test GET /api/settings returns default config."""
    response = client.get("/api/settings")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check all sections exist
    assert "detection" in data
    assert "motion" in data
    assert "thermal" in data
    assert "stream" in data
    assert "live" in data
    assert "record" in data
    assert "event" in data
    assert "media" in data
    assert "ai" in data
    assert "telegram" in data
    
    # Check default values
    assert data["detection"]["model"] == "yolov8s-person"
    assert data["detection"]["confidence_threshold"] == 0.50
    assert data["motion"]["sensitivity"] == 8
    assert data["thermal"]["enable_enhancement"] is True
    assert data["stream"]["protocol"] == "tcp"
    assert data["live"]["output_mode"] == "mjpeg"


def test_put_settings_partial_update(client):
    """Test PUT /api/settings with partial update."""
    # Update only detection settings
    update_data = {
        "detection": {
            "model": "yolov8s-person",
            "confidence_threshold": 0.5
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check updated fields
    assert data["detection"]["model"] == "yolov8s-person"
    assert data["detection"]["confidence_threshold"] == 0.5
    
    # Check other fields remain default
    assert data["detection"]["inference_fps"] == 5
    assert data["motion"]["sensitivity"] == 8


def test_put_settings_multiple_sections(client):
    """Test PUT /api/settings updating multiple sections."""
    update_data = {
        "detection": {
            "model": "yolov8s-person",
            "inference_fps": 10
        },
        "motion": {
            "sensitivity": 8,
            "cooldown_seconds": 3
        },
        "thermal": {
            "enable_enhancement": False
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["detection"]["model"] == "yolov8s-person"
    assert data["detection"]["inference_fps"] == 10
    assert data["motion"]["sensitivity"] == 8
    assert data["motion"]["cooldown_seconds"] == 3
    assert data["thermal"]["enable_enhancement"] is False


def test_put_settings_secrets_masked(client):
    """Test that secrets are masked in PUT response."""
    update_data = {
        "ai": {
            "enabled": True,
            "api_key": "sk-test-api-key-12345"
        },
        "telegram": {
            "enabled": True,
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    # Secrets should be masked
    assert data["ai"]["api_key"] == "***REDACTED***"
    assert data["telegram"]["bot_token"] == "***REDACTED***"
    
    # But enabled flags should be updated
    assert data["ai"]["enabled"] is True
    assert data["telegram"]["enabled"] is True


def test_get_settings_secrets_masked(client):
    """Test that secrets are masked in GET response."""
    # First, set secrets via PUT
    update_data = {
        "ai": {
            "api_key": "sk-secret-key"
        },
        "telegram": {
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        }
    }
    client.put("/api/settings", json=update_data)
    
    # Then GET settings
    response = client.get("/api/settings")
    
    assert response.status_code == 200
    data = response.json()
    
    # Secrets should be masked
    assert data["ai"]["api_key"] == "***REDACTED***"
    assert data["telegram"]["bot_token"] == "***REDACTED***"


def test_put_settings_validation_error_confidence(client):
    """Test PUT /api/settings validation error for invalid confidence."""
    update_data = {
        "detection": {
            "confidence_threshold": 1.5  # Invalid: must be 0.0-1.0
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"
    assert "confidence_threshold" in str(detail)


def test_put_settings_validation_error_fps(client):
    """Test PUT /api/settings validation error for invalid FPS."""
    update_data = {
        "detection": {
            "inference_fps": 50  # Invalid: must be 1-30
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_validation_error_sensitivity(client):
    """Test PUT /api/settings validation error for invalid sensitivity."""
    update_data = {
        "motion": {
            "sensitivity": 15  # Invalid: must be 1-10
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_validation_error_bot_token_format(client):
    """Test PUT /api/settings validation error for invalid bot token."""
    update_data = {
        "telegram": {
            "enabled": True,
            "bot_token": "invalid-token"
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"
    assert "bot_token" in str(detail)


def test_put_settings_validation_error_chat_id_format(client):
    """Test PUT /api/settings validation error for invalid chat IDs."""
    update_data = {
        "telegram": {
            "enabled": True,
            "chat_ids": ["abc123"]
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"
    assert "chat_ids" in str(detail)


def test_put_settings_validation_error_ai_key_format(client):
    """Test PUT /api/settings validation error for invalid AI API key."""
    update_data = {
        "ai": {
            "enabled": True,
            "api_key": "invalid-key"
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"
    assert "api_key" in str(detail)


def test_put_settings_validation_error_disk_limit(client):
    """Test PUT /api/settings validation error for invalid disk limit."""
    update_data = {
        "media": {
            "disk_limit_percent": 30  # Invalid: must be 50-95
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_validation_error_snapshot_quality(client):
    """Test PUT /api/settings validation error for invalid snapshot quality."""
    update_data = {
        "telegram": {
            "snapshot_quality": 150  # Invalid: must be 0-100
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_nested_update(client):
    """Test PUT /api/settings with nested object update."""
    update_data = {
        "live": {
            "output_mode": "webrtc",
            "webrtc": {
                "enabled": True,
                "go2rtc_url": "http://localhost:1984"
            }
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["live"]["output_mode"] == "webrtc"
    assert data["live"]["webrtc"]["enabled"] is True
    assert data["live"]["webrtc"]["go2rtc_url"] == "http://localhost:1984"


def test_settings_persistence(client):
    """Test that settings persist across requests."""
    # Update settings
    update_data = {
        "detection": {
            "model": "yolov8s-person",
            "confidence_threshold": 0.6
        }
    }
    
    response1 = client.put("/api/settings", json=update_data)
    assert response1.status_code == 200
    
    # Get settings (should reflect update)
    response2 = client.get("/api/settings")
    assert response2.status_code == 200
    data = response2.json()
    
    assert data["detection"]["model"] == "yolov8s-person"
    assert data["detection"]["confidence_threshold"] == 0.6


def test_put_settings_invalid_model(client):
    """Test PUT /api/settings validation error for invalid model."""
    update_data = {
        "detection": {
            "model": "invalid-model"  # Invalid: must be yolov8n-person or yolov8s-person
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_invalid_protocol(client):
    """Test PUT /api/settings validation error for invalid protocol."""
    update_data = {
        "stream": {
            "protocol": "http"  # Invalid: must be tcp or udp
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_put_settings_invalid_output_mode(client):
    """Test PUT /api/settings validation error for invalid output mode."""
    update_data = {
        "live": {
            "output_mode": "hls"  # Invalid: must be mjpeg or webrtc
        }
    }
    
    response = client.put("/api/settings", json=update_data)
    
    assert response.status_code == 400
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "VALIDATION_ERROR"


def test_post_settings_reset(client):
    """Test POST /api/settings/reset returns defaults."""
    update_data = {
        "detection": {
            "model": "yolov8s-person"
        }
    }
    response = client.put("/api/settings", json=update_data)
    assert response.status_code == 200

    response = client.post("/api/settings/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["detection"]["model"] == "yolov8s-person"
