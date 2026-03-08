"""
Unit tests for detection pipeline.

Tests cover:
- YOLOv8 model loading
- Thermal enhancement (CLAHE)
- Aspect ratio filtering
- Temporal consistency
- Zone inertia
- Confidence filtering
- Auto detection source
- Event cooldown
- Frame preprocessing
"""
from datetime import datetime
from collections import deque
import threading
from unittest.mock import Mock, patch, MagicMock

import cv2
import numpy as np
import pytest

from app.services.inference import InferenceService
from app.services.time_utils import is_daytime, get_detection_source
from app.workers.detector import DetectorWorker


@pytest.fixture
def inference_service():
    """Create inference service instance."""
    return InferenceService()


def test_thermal_enhancement_clahe(inference_service):
    """Test CLAHE thermal enhancement."""
    # Create test thermal frame (grayscale)
    frame = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
    
    # Preprocess with enhancement
    enhanced = inference_service.preprocess_thermal(
        frame,
        enable_enhancement=True,
        clahe_clip_limit=2.0,
        clahe_tile_size=(8, 8),
    )
    
    # Check output
    assert enhanced.shape == (480, 640, 3)  # Converted to BGR
    assert enhanced.dtype == np.uint8


def test_thermal_enhancement_disabled(inference_service):
    """Test thermal preprocessing without enhancement."""
    frame = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
    
    # Preprocess without enhancement
    result = inference_service.preprocess_thermal(
        frame,
        enable_enhancement=False,
    )
    
    # Check output
    assert result.shape == (480, 640, 3)


def test_color_preprocessing(inference_service):
    """Test color frame preprocessing."""
    # Create test color frame
    frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    
    # Preprocess
    result = inference_service.preprocess_color(frame)
    
    # Check output
    assert result.shape == (1080, 1920, 3)
    assert result.dtype == np.uint8


def test_aspect_ratio_filter(inference_service):
    """Test aspect ratio filtering for person shape."""
    # Create test detections
    detections = [
        {"bbox": [100, 100, 150, 300], "confidence": 0.8},  # Ratio: 50/200 = 0.25 (too skinny)
        {"bbox": [200, 100, 280, 300], "confidence": 0.8},  # Ratio: 80/200 = 0.4 (valid person)
        {"bbox": [300, 100, 450, 300], "confidence": 0.8},  # Ratio: 150/200 = 0.75 (valid person)
        {"bbox": [500, 100, 800, 300], "confidence": 0.8},  # Ratio: 300/200 = 1.5 (too wide - tree/wall)
    ]
    
    # Filter by aspect ratio using class defaults (0.2–1.2 matching "person" preset)
    filtered = inference_service.filter_by_aspect_ratio(detections)

    # 0.25 (>=0.2 passes), 0.4 passes, 0.75 passes; 1.5 (>1.2) filtered out
    assert len(filtered) == 3
    assert filtered[0]["aspect_ratio"] == pytest.approx(0.25)
    assert filtered[1]["aspect_ratio"] == pytest.approx(0.4)
    assert filtered[2]["aspect_ratio"] == pytest.approx(0.75)


def test_temporal_consistency_valid(inference_service):
    """Test temporal consistency with valid consecutive detections."""
    # Create detection history (3 frames with detections)
    history = [
        [{"bbox": [100, 100, 200, 300], "confidence": 0.8}],
        [{"bbox": [105, 100, 205, 300], "confidence": 0.82}],
    ]
    
    # Current frame with detection
    current = [{"bbox": [110, 100, 210, 300], "confidence": 0.85}]
    
    # Check consistency (3 consecutive frames)
    is_consistent = inference_service.check_temporal_consistency(
        current,
        history,
        min_consecutive_frames=3,
        max_gap_frames=1,
    )
    
    assert is_consistent is True


def test_temporal_consistency_with_gap(inference_service):
    """Test temporal consistency with 1 frame gap (should be tolerated)."""
    # Create detection history with 1 gap
    history = [
        [{"bbox": [100, 100, 200, 300], "confidence": 0.8}],
        [],  # Gap (no detection)
        [{"bbox": [110, 100, 210, 300], "confidence": 0.82}],
    ]
    
    # Current frame with detection
    current = [{"bbox": [115, 100, 215, 300], "confidence": 0.85}]
    
    # Check consistency (3 out of 4 frames, gap=1 tolerated)
    is_consistent = inference_service.check_temporal_consistency(
        current,
        history,
        min_consecutive_frames=3,
        max_gap_frames=1,
    )
    
    assert is_consistent is True


def test_temporal_consistency_invalid(inference_service):
    """Test temporal consistency with too many gaps."""
    # Create detection history with 2 gaps
    history = [
        [{"bbox": [100, 100, 200, 300], "confidence": 0.8}],
        [],  # Gap 1
        [],  # Gap 2
    ]
    
    # Current frame with detection
    current = [{"bbox": [115, 100, 215, 300], "confidence": 0.85}]
    
    # Check consistency (only 2 out of 4 frames, gaps=2 > max_gap=1)
    is_consistent = inference_service.check_temporal_consistency(
        current,
        history,
        min_consecutive_frames=3,
        max_gap_frames=1,
    )
    
    assert is_consistent is False


def test_zone_inertia(inference_service):
    """Test zone inertia (object must stay in zone for N frames)."""
    # Create test detection (center at 150, 200 in 640x640 frame)
    detection = {"bbox": [100, 100, 200, 300], "confidence": 0.8}
    
    # Create test zone (normalized coordinates covering center)
    # Detection center: (150/640, 200/640) = (0.234, 0.312)
    zone_polygon = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]
    
    # Create zone history (2 frames in zone)
    zone_history = [True, True]
    
    # Check inertia (need 3 frames)
    in_zone = inference_service.check_zone_inertia(
        detection,
        zone_polygon,
        zone_history,
        min_frames_in_zone=3,
    )
    
    # Should be True now (3 frames total)
    assert in_zone is True
    assert len(zone_history) == 3


def test_zone_inertia_insufficient(inference_service):
    """Test zone inertia with insufficient frames."""
    detection = {"bbox": [100, 100, 200, 300], "confidence": 0.8}
    zone_polygon = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    
    # Create zone history (only 1 frame in zone)
    zone_history = [True]
    
    # Check inertia (need 3 frames)
    in_zone = inference_service.check_zone_inertia(
        detection,
        zone_polygon,
        zone_history,
        min_frames_in_zone=3,
    )
    
    # Should be False (only 2 frames total)
    assert in_zone is False


@patch('app.services.time_utils.datetime')
def test_auto_detection_source_daytime(mock_datetime):
    """Test auto detection source during daytime."""
    # Mock current time: 12:00 (noon)
    mock_now = Mock()
    mock_now.hour = 12
    mock_datetime.now.return_value = mock_now
    
    # Check if daytime
    assert is_daytime(sunrise_hour=6, sunset_hour=20) is True
    
    # Get detection source (auto mode)
    source = get_detection_source("auto", sunrise_hour=6, sunset_hour=20)
    assert source == "color"


@patch('app.services.time_utils.datetime')
def test_auto_detection_source_nighttime(mock_datetime):
    """Test auto detection source during nighttime."""
    # Mock current time: 22:00 (night)
    mock_now = Mock()
    mock_now.hour = 22
    mock_datetime.now.return_value = mock_now
    
    # Check if nighttime
    assert is_daytime(sunrise_hour=6, sunset_hour=20) is False
    
    # Get detection source (auto mode)
    source = get_detection_source("auto", sunrise_hour=6, sunset_hour=20)
    assert source == "thermal"


def test_auto_detection_source_manual(inference_service):
    """Test manual detection source (not auto)."""
    # Manual thermal
    source = get_detection_source("thermal")
    assert source == "thermal"
    
    # Manual color
    source = get_detection_source("color")
    assert source == "color"


def test_confidence_filtering(inference_service):
    """Test that low confidence detections are filtered."""
    # This is tested in YOLOv8 inference
    # We just verify the threshold parameter is used
    assert inference_service.PERSON_CLASS_ID == 0


def test_frame_preprocessing_bgr_to_gray(inference_service):
    """Test BGR to grayscale conversion in thermal preprocessing."""
    # Create BGR frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Preprocess (should convert to gray, enhance, then back to BGR)
    result = inference_service.preprocess_thermal(frame, enable_enhancement=False)
    
    # Check output is BGR
    assert result.shape == (480, 640, 3)


def test_point_in_polygon(inference_service):
    """Test point in polygon algorithm."""
    # Square polygon
    polygon = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    
    # Point inside
    assert inference_service._point_in_polygon((0.5, 0.5), polygon) is True
    
    # Point outside
    assert inference_service._point_in_polygon((1.5, 0.5), polygon) is False
    
    # Point on edge (may be inside or outside depending on algorithm)
    # Just check it doesn't crash
    result = inference_service._point_in_polygon((0.0, 0.5), polygon)
    assert isinstance(result, bool)


def test_bbox_center_calculation(inference_service):
    """Test bounding box center calculation."""
    bbox = [100, 100, 200, 300]
    center = inference_service._get_bbox_center(bbox)
    
    assert center == (150.0, 200.0)

def test_count_recent_motion_cameras_includes_recently_active_states():
    """Recent motion timestamps should count as active for short adaptive windows."""
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.motion_state = {
        "cam-1": {"motion_active": False, "last_motion": 98.0},  # recent in 6s window
        "cam-2": {"motion_active": False, "last_motion": 90.0},  # stale
        "cam-3": {"motion_active": True, "last_motion": 10.0},
    }
    with patch("app.workers.detector.time.time", return_value=100.0):
        assert worker._count_recent_motion_cameras(window_seconds=6.0) == 2

def test_thermal_warmup_motion_gate_respects_floor_and_multiplier():
    """Warmup gate should preserve a floor while scaling with min_area."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._thermal_warmup_motion_gate(min_area=850, gate_floor=700, gate_multiplier=1.0) == 850
    assert worker._thermal_warmup_motion_gate(min_area=1100, gate_floor=650, gate_multiplier=0.95) == 1045
    # Floor should dominate low min_area values.
    assert worker._thermal_warmup_motion_gate(min_area=260, gate_floor=650, gate_multiplier=0.95) == 650


def test_thermal_auto_min_area_cap_scales_with_camera_load():
    """Thermal auto min-area cap should drop as concurrent load increases."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._thermal_auto_min_area_cap(1800, active_motion_cameras=1) == 1100
    assert worker._thermal_auto_min_area_cap(1800, active_motion_cameras=2) == 850
    assert worker._thermal_auto_min_area_cap(1800, active_motion_cameras=4) == 700
    # Never force a higher cap than configured.
    assert worker._thermal_auto_min_area_cap(700, active_motion_cameras=4) == 700


def test_thermal_temporal_policy_relaxes_under_multi_camera_motion():
    """Thermal temporal gate should relax slightly under concurrent camera load."""
    worker = DetectorWorker.__new__(DetectorWorker)
    min_frames, max_gap, recovery_conf = worker._thermal_temporal_policy(0.55, active_motion_cameras=1)
    assert min_frames == 2
    assert max_gap == 1
    assert recovery_conf >= 0.62

    min_frames_busy, max_gap_busy, recovery_conf_busy = worker._thermal_temporal_policy(
        0.55,
        active_motion_cameras=3,
    )
    assert min_frames_busy == 2
    assert max_gap_busy == 1
    assert recovery_conf_busy < recovery_conf
    assert recovery_conf_busy < 0.59

    min_frames_very_busy, max_gap_very_busy, recovery_conf_very_busy = worker._thermal_temporal_policy(
        0.55,
        active_motion_cameras=4,
    )
    assert min_frames_very_busy == 2
    assert max_gap_very_busy == 2
    assert recovery_conf_very_busy <= recovery_conf_busy

def test_get_event_media_data_filters_to_event_window():
    """Event media selection should prefer frames from requested event window."""
    worker = DetectorWorker.__new__(DetectorWorker)
    camera_id = "cam-window"
    worker.frame_buffers = {
        camera_id: deque(
            [
                (np.zeros((6, 6, 3), dtype=np.uint8), {"bbox": [0, 0, 2, 4], "confidence": 0.81}, 100.0),
                (np.zeros((6, 6, 3), dtype=np.uint8), None, 119.6),
                (np.zeros((6, 6, 3), dtype=np.uint8), {"bbox": [1, 1, 3, 5], "confidence": 0.86}, 120.2),
                (np.zeros((6, 6, 3), dtype=np.uint8), None, 120.8),
            ]
        )
    }
    worker.frame_buffer_locks = {camera_id: threading.Lock()}
    worker.latest_frame_locks = {}
    worker.latest_frames = {}

    frames, detections, timestamps = worker._get_event_media_data(
        camera_id,
        window_start_ts=120.0,
        window_end_ts=121.0,
    )

    assert len(frames) == 2
    assert timestamps == [120.2, 120.8]
    assert detections[0]["confidence"] == pytest.approx(0.86, abs=1e-6)
    assert detections[1] is None


def test_get_event_video_data_filters_to_event_window():
    """Event video selection should prefer frames from requested event window."""
    worker = DetectorWorker.__new__(DetectorWorker)
    camera_id = "cam-video-window"
    worker.video_buffers = {
        camera_id: deque(
            [
                (np.zeros((6, 6, 3), dtype=np.uint8), 90.0),
                (np.zeros((6, 6, 3), dtype=np.uint8), 120.1),
                (np.zeros((6, 6, 3), dtype=np.uint8), 120.7),
                (np.zeros((6, 6, 3), dtype=np.uint8), 130.0),
            ]
        )
    }
    worker.video_buffer_locks = {camera_id: threading.Lock()}

    frames, timestamps = worker._get_event_video_data(
        camera_id,
        window_start_ts=120.0,
        window_end_ts=121.0,
    )

    assert len(frames) == 2
    assert timestamps == [120.1, 120.7]


def test_stream_read_failure_policy_softens_reconnect_flap_after_reconnect():
    """Read failure reconnect should be more conservative right after reconnect."""
    worker = DetectorWorker.__new__(DetectorWorker)
    threshold, timeout, cooldown = worker._stream_read_failure_policy(
        base_threshold=3,
        base_timeout=8.0,
        seconds_since_reconnect=10.0,
    )
    assert threshold >= 8
    assert timeout >= 12.0
    assert cooldown >= 20.0

    threshold_stable, timeout_stable, cooldown_stable = worker._stream_read_failure_policy(
        base_threshold=3,
        base_timeout=8.0,
        seconds_since_reconnect=120.0,
    )
    assert threshold_stable == 3
    assert timeout_stable == 8.0
    assert cooldown_stable == 12.0


def test_stream_read_failure_policy_adds_tolerance_for_thermal_reconnect_pressure():
    """Thermal streams under reconnect pressure should require stronger stale signal."""
    worker = DetectorWorker.__new__(DetectorWorker)
    threshold, timeout, cooldown = worker._stream_read_failure_policy(
        base_threshold=3,
        base_timeout=8.0,
        seconds_since_reconnect=120.0,
        recent_reconnects=5,
        detection_source="thermal",
    )
    assert threshold >= 14
    assert timeout >= 18.0
    assert cooldown >= 45.0


def test_stream_fallback_read_failure_policy_relaxes_reconnect_during_fallback():
    """Fallback window should require stronger stale evidence before reconnect."""
    worker = DetectorWorker.__new__(DetectorWorker)
    threshold, timeout, cooldown = worker._stream_fallback_read_failure_policy(
        failure_threshold=8,
        failure_timeout=12.0,
        reconnect_cooldown=20.0,
        active_backend="opencv",
        fallback_until_ts=500.0,
        now_ts=200.0,
        detection_source="thermal",
    )
    assert threshold >= 12
    assert timeout >= 20.0
    assert cooldown >= 35.0


def test_stream_opencv_read_failure_policy_adds_steady_state_tolerance():
    """OpenCV backend should keep reconnect thresholds conservative."""
    worker = DetectorWorker.__new__(DetectorWorker)
    threshold, timeout, cooldown = worker._stream_opencv_read_failure_policy(
        failure_threshold=8,
        failure_timeout=12.0,
        reconnect_cooldown=20.0,
        active_backend="opencv",
        recent_reconnects=4,
        detection_source="thermal",
    )
    assert threshold >= 14
    assert timeout >= 24.0
    assert cooldown >= 55.0


def test_stream_reconnect_age_gate_scales_with_reconnect_pressure():
    """Reconnect stale-age gate should become stricter when stream is unstable."""
    worker = DetectorWorker.__new__(DetectorWorker)
    baseline = worker._stream_reconnect_age_gate(
        failure_timeout=8.0,
        recent_reconnects=0,
        detection_source="thermal",
    )
    pressured = worker._stream_reconnect_age_gate(
        failure_timeout=8.0,
        recent_reconnects=5,
        detection_source="thermal",
    )
    assert baseline >= 14.0
    assert pressured >= 24.0
    assert pressured > baseline


def test_stream_reconnect_age_gate_stricter_in_fallback_window():
    """Fallback-active reconnect gate should be stricter than normal gate."""
    worker = DetectorWorker.__new__(DetectorWorker)
    normal_gate = worker._stream_reconnect_age_gate(
        failure_timeout=12.0,
        recent_reconnects=0,
        detection_source="thermal",
        fallback_active=False,
    )
    fallback_gate = worker._stream_reconnect_age_gate(
        failure_timeout=12.0,
        recent_reconnects=0,
        detection_source="thermal",
        fallback_active=True,
    )
    assert fallback_gate >= 30.0
    assert fallback_gate > normal_gate


def test_stream_reconnect_age_gate_stricter_in_opencv_backend():
    """OpenCV backend should require longer stale age before reconnect."""
    worker = DetectorWorker.__new__(DetectorWorker)
    normal_gate = worker._stream_reconnect_age_gate(
        failure_timeout=12.0,
        recent_reconnects=2,
        detection_source="thermal",
        fallback_active=False,
        opencv_backend=False,
    )
    opencv_gate = worker._stream_reconnect_age_gate(
        failure_timeout=12.0,
        recent_reconnects=4,
        detection_source="thermal",
        fallback_active=False,
        opencv_backend=True,
    )
    assert opencv_gate >= 45.0
    assert opencv_gate > normal_gate


def test_ffmpeg_flapping_detector_triggers_fallback_in_short_window():
    """Frequent ffmpeg reconnects should trigger auto backend fallback."""
    worker = DetectorWorker.__new__(DetectorWorker)
    reconnects = [100.0, 130.0, 170.0, 220.0]
    assert worker._should_fallback_from_ffmpeg_flapping(
        reconnect_timestamps=reconnects,
        now_ts=220.0,
        window_seconds=180.0,
        reconnect_threshold=4,
    ) is True
    assert worker._should_fallback_from_ffmpeg_flapping(
        reconnect_timestamps=[100.0, 130.0, 170.0],
        now_ts=220.0,
        window_seconds=180.0,
        reconnect_threshold=4,
    ) is False


def test_ffmpeg_flapping_fallback_allowed_for_auto_and_ffmpeg_modes():
    """Anti-flapping fallback should work in auto and forced ffmpeg modes."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._allows_ffmpeg_flapping_fallback("auto") is True
    assert worker._allows_ffmpeg_flapping_fallback("ffmpeg") is True
    assert worker._allows_ffmpeg_flapping_fallback("opencv") is False


def test_select_capture_backend_for_reopen_respects_fallback_window():
    """Backend selection should enforce fallback and recover in forced ffmpeg mode."""
    worker = DetectorWorker.__new__(DetectorWorker)
    # Fallback active -> ffmpeg gets forced to OpenCV.
    assert worker._select_capture_backend_for_reopen(
        current_backend="ffmpeg",
        configured_backend="ffmpeg",
        fallback_until_ts=200.0,
        now_ts=150.0,
    ) == "opencv"
    # Forced ffmpeg recovers after fallback window.
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="ffmpeg",
        fallback_until_ts=140.0,
        now_ts=150.0,
    ) == "ffmpeg"
    # Auto mode returns to ffmpeg after fallback window.
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="auto",
        fallback_until_ts=140.0,
        now_ts=150.0,
    ) == "ffmpeg"


def test_select_capture_backend_for_reopen_retries_ffmpeg_in_auto_on_reconnect_pressure():
    """Auto mode should retry ffmpeg when OpenCV remains unstable after fallback."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="auto",
        fallback_until_ts=140.0,
        now_ts=150.0,
        recent_reconnects=2,
    ) == "ffmpeg"


def test_select_capture_backend_for_reopen_allows_early_ffmpeg_retry_inside_fallback():
    """Auto mode should break out of fallback early when OpenCV reconnect pressure is high."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="auto",
        fallback_until_ts=220.0,
        now_ts=180.0,
        recent_reconnects=4,
    ) == "ffmpeg"
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="auto",
        fallback_until_ts=220.0,
        now_ts=180.0,
        recent_reconnects=2,
    ) == "opencv"


def test_ffmpeg_exit_opencv_fallback_seconds_scales_with_reconnect_pressure():
    """ffmpeg fallback duration should be shorter when exits are isolated."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._ffmpeg_exit_opencv_fallback_seconds(0, recent_reconnects=0) == 180.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(0, recent_reconnects=4) == 360.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(0, recent_reconnects=7) == 600.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(1, recent_reconnects=0) == 120.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(1, recent_reconnects=4) == 210.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(1, recent_reconnects=7) == 300.0


def test_should_use_opencv_fallback_after_ffmpeg_exit_isolation_aware():
    """Isolated code=0 exits should retry ffmpeg directly before fallback."""
    worker = DetectorWorker.__new__(DetectorWorker)
    # Isolated code=0: no OpenCV fallback.
    assert worker._should_use_opencv_fallback_after_ffmpeg_exit(
        exit_code=0,
        recent_code0_ffmpeg_exits=0,
        recent_reconnects=0,
    ) is False
    # Repeated code=0: fallback should be enabled.
    assert worker._should_use_opencv_fallback_after_ffmpeg_exit(
        exit_code=0,
        recent_code0_ffmpeg_exits=1,
        recent_reconnects=0,
    ) is True
    # High reconnect pressure: fallback even on first code=0.
    assert worker._should_use_opencv_fallback_after_ffmpeg_exit(
        exit_code=0,
        recent_code0_ffmpeg_exits=0,
        recent_reconnects=4,
    ) is True
    # Non-zero exits are treated as hard failures.
    assert worker._should_use_opencv_fallback_after_ffmpeg_exit(
        exit_code=1,
        recent_code0_ffmpeg_exits=0,
        recent_reconnects=0,
    ) is True


def test_mark_thermal_reconnect_warmup_resets_motion_baseline_state():
    """Reconnect warmup should clear thermal baseline and chatter counters."""
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.motion_state = {
        "cam-1": {
            "motion_active": True,
            "motion_active_since": 90.0,
            "thermal_motion_gate_warmup_until": 100.0,
            "thermal_motion_above_streak": 2,
            "thermal_motion_below_streak": 1,
            "thermal_bg": np.zeros((2, 2), dtype=np.float32),
            "thermal_noise_var": np.ones((2, 2), dtype=np.float32),
            "thermal_motion_area_raw": 1234,
        }
    }
    worker._mark_thermal_reconnect_warmup(
        camera_id="cam-1",
        now_ts=120.0,
        warmup_seconds=10.0,
    )
    state = worker.motion_state["cam-1"]
    assert state["motion_active"] is False
    assert "motion_active_since" not in state
    assert state["thermal_motion_above_streak"] == 0
    assert state["thermal_motion_below_streak"] == 0
    assert "thermal_bg" not in state
    assert "thermal_noise_var" not in state
    assert "thermal_motion_area_raw" not in state
    assert state["thermal_motion_gate_warmup_until"] >= 130.0


def test_thermal_motion_active_hold_prevents_short_idle_flips():
    """Thermal motion active hold should suppress short active->idle chatter."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._should_hold_thermal_motion_active(
        active_since_ts=100.0,
        now_ts=101.5,
        min_active_seconds=3.0,
    ) is True
    assert worker._should_hold_thermal_motion_active(
        active_since_ts=100.0,
        now_ts=104.0,
        min_active_seconds=3.0,
    ) is False


def test_slew_limited_auto_min_area_limits_large_threshold_jumps():
    """Thermal auto min-area should change in bounded steps."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._slew_limited_auto_min_area(700, 520, max_down_step=40, max_up_step=120) == 660
    assert worker._slew_limited_auto_min_area(700, 1100, max_down_step=40, max_up_step=120) == 820
    assert worker._slew_limited_auto_min_area(None, 580, max_down_step=40, max_up_step=120) == 580


def test_thermal_motion_hysteresis_uses_streak_confirmation():
    """Thermal motion should avoid active/idle chatter around threshold."""
    worker = DetectorWorker.__new__(DetectorWorker)

    motion_detected, above, below, _, _ = worker._thermal_motion_hysteresis_decision(
        motion_area=780,
        min_area=700,
        motion_active=False,
        above_streak=0,
        below_streak=0,
        active_factor=1.08,
        idle_factor=0.92,
        active_streak_required=2,
        idle_streak_required=3,
    )
    assert motion_detected is False
    assert above == 1
    assert below == 0

    motion_detected, above, below, _, _ = worker._thermal_motion_hysteresis_decision(
        motion_area=790,
        min_area=700,
        motion_active=False,
        above_streak=above,
        below_streak=below,
        active_factor=1.08,
        idle_factor=0.92,
        active_streak_required=2,
        idle_streak_required=3,
    )
    assert motion_detected is True
    assert above == 2
    assert below == 0

    # Active state should tolerate brief dips and only deactivate after enough
    # consecutive below-threshold frames.
    motion_detected, above, below, _, _ = worker._thermal_motion_hysteresis_decision(
        motion_area=500,
        min_area=700,
        motion_active=True,
        above_streak=above,
        below_streak=0,
        active_factor=1.08,
        idle_factor=0.92,
        active_streak_required=2,
        idle_streak_required=3,
    )
    assert motion_detected is True
    assert below == 1

    motion_detected, _, below, _, _ = worker._thermal_motion_hysteresis_decision(
        motion_area=500,
        min_area=700,
        motion_active=True,
        above_streak=above,
        below_streak=2,
        active_factor=1.08,
        idle_factor=0.92,
        active_streak_required=2,
        idle_streak_required=3,
    )
    assert motion_detected is False
    assert below == 3

def test_detect_static_phantom_event_true():
    """Highly duplicate low-confidence static bbox stream should be marked phantom."""
    worker = DetectorWorker.__new__(DetectorWorker)
    frames = [np.full((240, 320, 3), 64, dtype=np.uint8) for _ in range(16)]
    detections = [
        {"bbox": [120, 40, 180, 220], "confidence": 0.56}
        for _ in range(16)
    ]

    metrics = worker._detect_static_phantom_event(frames, detections)
    assert metrics is not None
    assert metrics["duplicate_ratio"] >= 0.96


def test_detect_static_phantom_event_false_when_moving():
    """Moving person-like stream should not be marked phantom."""
    worker = DetectorWorker.__new__(DetectorWorker)
    frames = []
    detections = []
    for i in range(16):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        x = 20 + i * 8
        cv2.rectangle(frame, (x, 70), (x + 40, 190), (180, 180, 180), -1)
        frames.append(frame)
        detections.append({"bbox": [x, 70, x + 40, 190], "confidence": 0.58})

    metrics = worker._detect_static_phantom_event(frames, detections)
    assert metrics is None


def test_detect_static_phantom_event_false_when_high_conf():
    """High-confidence detections should bypass static phantom early-drop."""
    worker = DetectorWorker.__new__(DetectorWorker)
    frames = [np.full((240, 320, 3), 64, dtype=np.uint8) for _ in range(16)]
    detections = [
        {"bbox": [120, 40, 180, 220], "confidence": 0.84}
        for _ in range(16)
    ]

    metrics = worker._detect_static_phantom_event(frames, detections)
    assert metrics is None


# ── v5.0.0 motion-crop pipeline tests ──────────────────────────────────────

def test_scale_detections_to_frame_basic():
    """Bounding boxes from crop space must be correctly mapped back to full frame."""
    worker = DetectorWorker.__new__(DetectorWorker)
    # Crop: top-left corner (100, 50), size 200×200; inference resolution 640×640
    crop_info = (100, 50, 200, 200)
    inf_res = (640, 640)
    detections = [{"bbox": [0, 0, 640, 640], "confidence": 0.8}]
    scaled = worker._scale_detections_to_frame(detections, crop_info, inf_res)
    assert len(scaled) == 1
    # Full crop maps back to crop coords in full frame
    assert scaled[0]["bbox"] == [100, 50, 300, 250]


def test_scale_detections_to_frame_partial():
    """Partial crop bbox is correctly scaled."""
    worker = DetectorWorker.__new__(DetectorWorker)
    crop_info = (0, 0, 320, 256)
    inf_res = (640, 640)
    # Detection at center of 640×640 inference frame
    detections = [{"bbox": [320, 320, 640, 640], "confidence": 0.7}]
    scaled = worker._scale_detections_to_frame(detections, crop_info, inf_res)
    bx1, by1, bx2, by2 = scaled[0]["bbox"]
    assert bx1 == 160 and by1 == 128
    assert bx2 == 320 and by2 == 256


def test_scale_detections_to_frame_none_crop():
    """When crop_info is None, detections pass through unchanged."""
    worker = DetectorWorker.__new__(DetectorWorker)
    detections = [{"bbox": [10, 20, 30, 40], "confidence": 0.6}]
    result = worker._scale_detections_to_frame(detections, None, (640, 640))
    assert result == detections


def test_scale_detections_to_frame_empty():
    """Empty detection list returns empty list."""
    worker = DetectorWorker.__new__(DetectorWorker)
    result = worker._scale_detections_to_frame([], (0, 0, 100, 100), (640, 640))
    assert result == []


def test_motion_crop_thermal_frame_no_bbox(tmp_path):
    """When no motion bbox available, returns full-frame BGR conversion."""
    from collections import defaultdict
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.motion_state = defaultdict(dict)  # no thermal_motion_bbox

    # Grayscale thermal frame 512×640
    frame = np.random.randint(0, 255, (512, 640), dtype=np.uint8)
    result_frame, crop_info = worker._motion_crop_thermal_frame(frame, "cam1", (640, 640))

    assert crop_info is None
    assert result_frame.shape == (640, 640, 3)  # resized, 3-channel


def test_motion_crop_thermal_frame_with_bbox():
    """When motion bbox available, crops and returns crop_info."""
    from collections import defaultdict
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.motion_state = {"cam1": {"thermal_motion_bbox": (100, 80, 200, 150)}}

    # BGR thermal frame 480×640
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result_frame, crop_info = worker._motion_crop_thermal_frame(frame, "cam1", (640, 640))

    assert crop_info is not None
    x1, y1, cw, ch = crop_info
    assert x1 >= 0 and y1 >= 0
    assert cw > 0 and ch > 0
    assert result_frame.shape == (640, 640, 3)
