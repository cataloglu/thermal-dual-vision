"""
Unit tests for camera service.

Tests cover:
- TCP protocol forcing
- Snapshot base64 format
- Latency measurement
- Buffer size settings
- Timeout handling
- Retry logic
- Dual camera testing
"""
import base64
import time
from unittest.mock import Mock, patch, MagicMock

import cv2
import numpy as np
import pytest

from app.services.camera import CameraService


@pytest.fixture
def camera_service():
    """Create camera service instance."""
    return CameraService()


def test_force_tcp_protocol(camera_service):
    """Test that TCP protocol is not forcibly appended."""
    # URL without query parameters
    url1 = "rtsp://admin:12345@192.168.1.100:554/Streaming/Channels/101"
    result1 = camera_service.force_tcp_protocol(url1)
    assert result1 == url1
    
    # URL with existing query parameters
    url2 = "rtsp://admin:12345@192.168.1.100:554/stream?param=value"
    result2 = camera_service.force_tcp_protocol(url2)
    assert result2 == url2
    
    # URL already has tcp parameter
    url3 = "rtsp://admin:12345@192.168.1.100:554/stream?tcp"
    result3 = camera_service.force_tcp_protocol(url3)
    assert result3 == url3  # Should not change URL
    
    # Empty URL
    url4 = ""
    result4 = camera_service.force_tcp_protocol(url4)
    assert result4 == ""


@patch('cv2.VideoCapture')
def test_snapshot_base64_format(mock_video_capture, camera_service):
    """Test that snapshot is returned in correct base64 format."""
    # Create mock frame
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Mock VideoCapture
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, mock_frame)
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url)
    
    assert result["success"] is True
    assert result["snapshot_base64"] is not None
    
    # Check format
    snapshot = result["snapshot_base64"]
    assert snapshot.startswith("data:image/jpeg;base64,")
    
    # Verify base64 is valid
    base64_data = snapshot.split(",")[1]
    try:
        decoded = base64.b64decode(base64_data)
        assert len(decoded) > 0
    except Exception as e:
        pytest.fail(f"Invalid base64 data: {e}")


@patch('cv2.VideoCapture')
def test_latency_measurement(mock_video_capture, camera_service):
    """Test that latency is measured correctly."""
    # Create mock frame
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Mock VideoCapture with delay
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    
    def read_with_delay():
        time.sleep(0.1)  # Simulate 100ms delay
        return (True, mock_frame)
    
    mock_cap.read.side_effect = read_with_delay
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url)
    
    assert result["success"] is True
    assert result["latency_ms"] is not None
    assert result["latency_ms"] > 0
    assert result["latency_ms"] >= 100  # At least 100ms due to our delay


@patch('cv2.VideoCapture')
def test_buffer_size_setting(mock_video_capture, camera_service):
    """Test that buffer size is set to 1 for low latency."""
    # Mock VideoCapture
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    camera_service.test_rtsp_connection(url)
    
    # Verify buffer size was set
    mock_cap.set.assert_any_call(cv2.CAP_PROP_BUFFERSIZE, 1)


@patch('cv2.VideoCapture')
def test_timeout_handling(mock_video_capture, camera_service):
    """Test that connection timeout is handled properly."""
    # Mock VideoCapture that fails to open
    mock_cap = Mock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url, timeout=1)
    
    assert result["success"] is False
    assert result["error_reason"] is not None
    assert "Connection failed" in result["error_reason"]


@patch('cv2.VideoCapture')
@patch('time.sleep')
def test_retry_logic(mock_sleep, mock_video_capture, camera_service):
    """Test exponential backoff retry logic."""
    # Mock VideoCapture that fails
    mock_cap = Mock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap
    
    # Test connection (should retry 3 times)
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url)
    
    # Verify retries
    assert mock_video_capture.call_count == 3  # MAX_RETRY_ATTEMPTS
    
    # Verify exponential backoff delays
    assert mock_sleep.call_count == 2  # 2 delays (not after last attempt)
    mock_sleep.assert_any_call(1)  # First retry: 1s
    mock_sleep.assert_any_call(2)  # Second retry: 2s
    
    # Verify failure
    assert result["success"] is False


@patch('cv2.VideoCapture')
def test_dual_camera_both_channels(mock_video_capture, camera_service):
    """Test dual camera with both thermal and color channels."""
    # Create mock frames
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Mock VideoCapture
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, mock_frame)
    mock_video_capture.return_value = mock_cap
    
    # Test dual camera
    thermal_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201"
    color_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101"
    
    result = camera_service.test_dual_camera(thermal_url, color_url)
    
    assert result["success"] is True
    assert result["snapshot_base64"] is not None  # Should return thermal snapshot
    assert result["latency_ms"] is not None
    
    # Verify both cameras were tested
    assert mock_video_capture.call_count == 2


@patch('cv2.VideoCapture')
def test_dual_camera_thermal_fails(mock_video_capture, camera_service):
    """Test dual camera when thermal channel fails."""
    # Mock VideoCapture that fails
    mock_cap = Mock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap
    
    # Test dual camera
    thermal_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201"
    color_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101"
    
    result = camera_service.test_dual_camera(thermal_url, color_url)
    
    assert result["success"] is False
    assert "Thermal camera failed" in result["error_reason"]


@patch('cv2.VideoCapture')
def test_dual_camera_color_fails(mock_video_capture, camera_service):
    """Test dual camera when color channel fails."""
    # Mock VideoCapture - first call succeeds (thermal), second fails (color)
    call_count = [0]
    
    def create_mock_cap(*args, **kwargs):
        call_count[0] += 1
        mock_cap = Mock()
        if call_count[0] == 1:
            # Thermal succeeds
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        else:
            # Color fails
            mock_cap.isOpened.return_value = False
        return mock_cap
    
    mock_video_capture.side_effect = create_mock_cap
    
    # Test dual camera
    thermal_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/201"
    color_url = "rtsp://admin:12345@192.168.1.100/Streaming/Channels/101"
    
    result = camera_service.test_dual_camera(thermal_url, color_url)
    
    assert result["success"] is False
    assert "Color camera failed" in result["error_reason"]


@patch('cv2.VideoCapture')
def test_frame_read_failure(mock_video_capture, camera_service):
    """Test handling of frame read failure."""
    # Mock VideoCapture that opens but fails to read
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (False, None)
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url)
    
    assert result["success"] is False
    assert "Failed to read frame" in result["error_reason"]


@patch('cv2.VideoCapture')
def test_codec_setting(mock_video_capture, camera_service):
    """Test that codec is not forcibly set."""
    # Mock VideoCapture
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    camera_service.test_rtsp_connection(url)
    
    # Verify no explicit codec override was set
    assert not any(
        call_args[0][0] == cv2.CAP_PROP_FOURCC
        for call_args in mock_cap.set.call_args_list
    )


@patch('cv2.VideoCapture')
def test_resource_cleanup(mock_video_capture, camera_service):
    """Test that VideoCapture is properly released."""
    # Mock VideoCapture
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    camera_service.test_rtsp_connection(url)
    
    # Verify release was called
    mock_cap.release.assert_called_once()


@patch('cv2.VideoCapture')
def test_resource_cleanup_on_error(mock_video_capture, camera_service):
    """Test that VideoCapture is released even on error."""
    # Mock VideoCapture that opens but fails to read
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.side_effect = Exception("Read error")
    mock_video_capture.return_value = mock_cap
    
    # Test connection
    url = "rtsp://admin:12345@192.168.1.100/stream"
    result = camera_service.test_rtsp_connection(url)
    
    # Verify failure
    assert result["success"] is False
    
    # Verify release was called despite error
    assert mock_cap.release.call_count >= 1
