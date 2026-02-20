"""
Integration tests for camera API endpoints.

Tests the FastAPI endpoint for POST /api/cameras/test.
"""
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_get_cameras_status_exists(client):
    """Camera monitor endpoint should exist and return expected shape."""
    response = client.get("/api/cameras/status")
    assert response.status_code == 200
    data = response.json()
    assert "cameras" in data
    assert "go2rtc_ok" in data
    assert isinstance(data["cameras"], list)


@patch('cv2.VideoCapture')
def test_post_cameras_test_thermal_success(mock_video_capture, client):
    """Test POST /api/cameras/test with thermal camera success."""
    # Mock VideoCapture
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    # Test request
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["snapshot_base64"] is not None
    assert data["snapshot_base64"].startswith("data:image/jpeg;base64,")
    assert data["latency_ms"] is not None
    assert data["latency_ms"] >= 0  # Can be 0 in fast mocked tests
    assert data["error_reason"] is None


@patch('cv2.VideoCapture')
def test_post_cameras_test_color_success(mock_video_capture, client):
    """Test POST /api/cameras/test with color camera success."""
    # Mock VideoCapture
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    # Test request
    request_data = {
        "type": "color",
        "rtsp_url_color": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101",
        "channel_color": 101
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["snapshot_base64"] is not None
    assert data["latency_ms"] is not None


@patch('cv2.VideoCapture')
def test_post_cameras_test_dual_success(mock_video_capture, client):
    """Test POST /api/cameras/test with dual camera success."""
    # Mock VideoCapture
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    # Test request
    request_data = {
        "type": "dual",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "rtsp_url_color": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101",
        "channel_thermal": 201,
        "channel_color": 101
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["snapshot_base64"] is not None
    assert data["latency_ms"] is not None


@patch('cv2.VideoCapture')
def test_post_cameras_test_connection_failed(mock_video_capture, client):
    """Test POST /api/cameras/test with connection failure."""
    # Mock VideoCapture that fails to open
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = False
    
    # Test request
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 500
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "RTSP_CONNECTION_FAILED"


def test_post_cameras_test_validation_error_thermal_missing_url(client):
    """Test POST /api/cameras/test validation error - thermal URL missing."""
    # Test request without thermal URL
    request_data = {
        "type": "thermal",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error


def test_post_cameras_test_validation_error_color_missing_url(client):
    """Test POST /api/cameras/test validation error - color URL missing."""
    # Test request without color URL
    request_data = {
        "type": "color",
        "channel_color": 101
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error


def test_post_cameras_test_validation_error_dual_missing_thermal(client):
    """Test POST /api/cameras/test validation error - dual missing thermal URL."""
    # Test request without thermal URL
    request_data = {
        "type": "dual",
        "rtsp_url_color": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101",
        "channel_color": 101
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error


def test_post_cameras_test_validation_error_dual_missing_color(client):
    """Test POST /api/cameras/test validation error - dual missing color URL."""
    # Test request without color URL
    request_data = {
        "type": "dual",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error


def test_post_cameras_test_invalid_type(client):
    """Test POST /api/cameras/test with invalid camera type."""
    # Test request with invalid type
    request_data = {
        "type": "invalid",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201"
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error


@patch('cv2.VideoCapture')
def test_post_cameras_test_tcp_protocol_added(mock_video_capture, client):
    """Test that RTSP URL is passed through unchanged."""
    # Mock VideoCapture
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    # Test request
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 200
    
    # Verify VideoCapture was called without forced TCP parameter
    call_args = mock_video_capture.call_args
    url_used = call_args[0][0]
    assert "?tcp" not in url_used and "&tcp" not in url_used


@patch('cv2.VideoCapture')
def test_post_cameras_test_frame_read_failure(mock_video_capture, client):
    """Test POST /api/cameras/test with frame read failure."""
    # Mock VideoCapture that opens but fails to read
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (False, None)
    
    # Test request
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 500
    data = response.json()
    detail = data.get("detail", data)
    
    assert detail["error"] is True
    assert detail["code"] == "RTSP_CONNECTION_FAILED"


@patch('cv2.VideoCapture')
def test_post_cameras_test_hikvision_url_format(mock_video_capture, client):
    """Test POST /api/cameras/test with Hikvision URL format."""
    # Mock VideoCapture
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    # Test request with Hikvision URL format
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100:554/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["snapshot_base64"] is not None


@patch('cv2.VideoCapture')
@patch('time.sleep')
def test_post_cameras_test_retry_on_failure(mock_sleep, mock_video_capture, client):
    """Test that camera test retries on failure."""
    # Mock VideoCapture that fails
    mock_cap = mock_video_capture.return_value
    mock_cap.isOpened.return_value = False
    
    # Test request
    request_data = {
        "type": "thermal",
        "rtsp_url_thermal": "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201",
        "channel_thermal": 201
    }
    
    response = client.post("/api/cameras/test", json=request_data)
    
    assert response.status_code == 500
    
    # Verify retries occurred
    assert mock_video_capture.call_count == 3  # MAX_RETRY_ATTEMPTS
    assert mock_sleep.call_count == 2  # Delays between retries
