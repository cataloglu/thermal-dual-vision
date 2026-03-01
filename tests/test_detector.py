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
    
    # Filter by aspect ratio
    filtered = inference_service.filter_by_aspect_ratio(detections)
    
    # Should keep only detections with ratio 0.3-0.8
    assert len(filtered) == 2
    assert filtered[0]["aspect_ratio"] == 0.4
    assert filtered[1]["aspect_ratio"] == 0.75


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


def test_thermal_suppression_wakeup_ratio_trigger():
    """Suppression should wake up on clear ratio-based motion jump."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._should_wakeup_thermal_suppression(
        current_area=2600,
        prev_area=800,
        wakeup_ratio=2.5,
        min_wakeup_area=1200,
    ) is True


def test_thermal_suppression_wakeup_gradual_trigger():
    """Suppression should also wake up on meaningful gradual growth."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._should_wakeup_thermal_suppression(
        current_area=1700,
        prev_area=1000,
        wakeup_ratio=2.5,
        min_wakeup_area=1200,
    ) is True
    assert worker._should_wakeup_thermal_suppression(
        current_area=1200,
        prev_area=1000,
        wakeup_ratio=2.5,
        min_wakeup_area=1200,
    ) is False


def test_thermal_suppression_wakeup_no_false_positive():
    """Suppression should NOT wake when area is below thresholds."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._should_wakeup_thermal_suppression(
        current_area=0,
        prev_area=500,
        wakeup_ratio=2.5,
        min_wakeup_area=1200,
    ) is False
    assert worker._should_wakeup_thermal_suppression(
        current_area=800,
        prev_area=400,
        wakeup_ratio=2.5,
        min_wakeup_area=1200,
    ) is False


def test_count_active_motion_cameras_uses_motion_active_state():
    """Active camera count should read runtime `motion_active` flags."""
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.motion_state = {
        "cam-1": {"motion_active": True},
        "cam-2": {"motion_active": False},
        "cam-3": {"active": True},  # legacy fallback key
        "cam-4": {"other": 1},
    }
    assert worker._count_active_motion_cameras() == 2


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


def test_thermal_probe_interval_scales_with_camera_load():
    """Suppression probes should become faster when multiple cameras are active."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._thermal_probe_interval_seconds(30, active_motion_cameras=1) == 2.0
    assert worker._thermal_probe_interval_seconds(30, active_motion_cameras=2) == 1.0
    # Never below safety floor.
    assert worker._thermal_probe_interval_seconds(6, active_motion_cameras=4) >= 0.8


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
    assert min_frames == 3
    assert max_gap == 1
    assert recovery_conf >= 0.65

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


def test_thermal_suppression_policy_delays_suppression_under_load():
    """Suppression should trigger later and shorter under concurrent load."""
    worker = DetectorWorker.__new__(DetectorWorker)
    streak_single, secs_single = worker._thermal_suppression_policy(15, 30, active_motion_cameras=1)
    assert streak_single >= 30
    assert secs_single <= 15

    streak_busy, secs_busy = worker._thermal_suppression_policy(15, 30, active_motion_cameras=2)
    assert streak_busy >= 45
    assert secs_busy <= 12

    streak_very_busy, secs_very_busy = worker._thermal_suppression_policy(
        15,
        30,
        active_motion_cameras=4,
    )
    assert streak_very_busy >= streak_busy
    assert secs_very_busy <= secs_busy


def test_thermal_suppression_motion_hold_prefers_live_motion_signal():
    """Suppression hold should keep inference active when motion stays meaningful."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._should_hold_thermal_suppression_for_motion(
        current_area=780,
        adaptive_min_area=700,
        active_motion_cameras=4,
    ) is True
    assert worker._should_hold_thermal_suppression_for_motion(
        current_area=640,
        adaptive_min_area=700,
        active_motion_cameras=2,
    ) is False
    assert worker._should_hold_thermal_suppression_for_motion(
        current_area=820,
        adaptive_min_area=700,
        active_motion_cameras=1,
    ) is True


def test_thermal_suppression_rearm_scales_with_camera_load():
    """Suppression re-arm grace should be longer under higher concurrent load."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._thermal_suppression_rearm_seconds(active_motion_cameras=1) == 16.0
    assert worker._thermal_suppression_rearm_seconds(active_motion_cameras=2) == 22.0
    assert worker._thermal_suppression_rearm_seconds(active_motion_cameras=4) == 26.0


def test_thermal_confidence_policy_relaxes_only_with_multi_cam_and_strong_motion():
    """Thermal confidence floor should relax under concurrent strong motion only."""
    worker = DetectorWorker.__new__(DetectorWorker)
    # Single camera: keep configured threshold.
    assert worker._thermal_confidence_policy(0.55, active_motion_cameras=1, motion_area_now=2000, base_min_area=400) == 0.55
    # Multi-camera but weak motion: no relax.
    assert worker._thermal_confidence_policy(0.55, active_motion_cameras=2, motion_area_now=700, base_min_area=400) == 0.55
    # Multi-camera + strong motion: relax a bit.
    assert worker._thermal_confidence_policy(
        0.55, active_motion_cameras=2, motion_area_now=1000, base_min_area=400
    ) == pytest.approx(0.48, abs=1e-6)
    # Heavy concurrent load + strong motion: relax more.
    assert worker._thermal_confidence_policy(
        0.55, active_motion_cameras=4, motion_area_now=1200, base_min_area=400
    ) == pytest.approx(0.45, abs=1e-6)


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
    # Auto mode stays on OpenCV after fallback (stability-first).
    assert worker._select_capture_backend_for_reopen(
        current_backend="opencv",
        configured_backend="auto",
        fallback_until_ts=140.0,
        now_ts=150.0,
    ) == "opencv"


def test_ffmpeg_exit_opencv_fallback_seconds_prefers_longer_on_clean_exit():
    """ffmpeg exit code 0 should trigger longer temporary OpenCV fallback."""
    worker = DetectorWorker.__new__(DetectorWorker)
    assert worker._ffmpeg_exit_opencv_fallback_seconds(0) == 600.0
    assert worker._ffmpeg_exit_opencv_fallback_seconds(1) == 240.0


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


def test_effective_thermal_motion_area_uses_recent_peak():
    """Recent peak area should smooth one-frame drops for suppression decisions."""
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.thermal_motion_peak_area = {"cam-1": 1000}
    worker.thermal_motion_peak_ts = {"cam-1": 100.0}
    assert worker._effective_thermal_motion_area(
        camera_id="cam-1",
        current_area=600,
        now_ts=103.0,
    ) == 850
    assert worker._effective_thermal_motion_area(
        camera_id="cam-1",
        current_area=600,
        now_ts=108.0,
    ) == 600


def test_thermal_bbox_center_spread_detects_motion_vs_static():
    """Spread helper should separate moving and static bbox tracks."""
    worker = DetectorWorker.__new__(DetectorWorker)
    static_frames = [
        [{"bbox": [100, 60, 160, 220], "confidence": 0.70}]
        for _ in range(5)
    ]
    moving_frames = [
        [{"bbox": [100 + (i * 8), 60, 160 + (i * 8), 220], "confidence": 0.70}]
        for i in range(5)
    ]
    assert worker._thermal_bbox_center_spread(static_frames) == 0.0
    assert worker._thermal_bbox_center_spread(moving_frames) >= 8.0


def test_thermal_bbox_median_iou_separates_static_and_moving_tracks():
    """IoU signature should be high for static jitter and lower for moving boxes."""
    worker = DetectorWorker.__new__(DetectorWorker)
    static_jitter_frames = [
        [{"bbox": [100 + (i * 2), 60, 160 + (i * 2), 220], "confidence": 0.70}]
        for i in range(5)
    ]
    moving_frames = [
        [{"bbox": [100 + (i * 12), 60, 160 + (i * 12), 220], "confidence": 0.70}]
        for i in range(5)
    ]
    assert worker._thermal_bbox_median_iou(static_jitter_frames) > 0.88
    assert worker._thermal_bbox_median_iou(moving_frames) < 0.88


def test_thermal_bbox_net_displacement_separates_drift_from_static():
    """Net displacement should stay near zero for oscillation around same point."""
    worker = DetectorWorker.__new__(DetectorWorker)
    static_frames = [
        [{"bbox": [100, 60, 160, 220], "confidence": 0.70}]
        for _ in range(5)
    ]
    moving_frames = [
        [{"bbox": [100 + (i * 12), 60, 160 + (i * 12), 220], "confidence": 0.70}]
        for i in range(5)
    ]
    oscillating_frames = [
        [{"bbox": [100 + dx, 60, 160 + dx, 220], "confidence": 0.70}]
        for dx in (8, 40, 10, 38, 9)
    ]
    assert worker._thermal_bbox_net_displacement(static_frames) == 0.0
    assert worker._thermal_bbox_net_displacement(moving_frames) >= 40.0
    assert worker._thermal_bbox_net_displacement(oscillating_frames) < 5.0


def test_thermal_bbox_edge_touch_ratio_detects_border_hugging_boxes():
    """Edge-touch ratio should be high for border-hugging static boxes."""
    worker = DetectorWorker.__new__(DetectorWorker)
    edge_frames = [
        [{"bbox": [0 + i, 2, 120 + i, 510], "confidence": 0.70}]
        for i in range(5)
    ]
    ratio = worker._thermal_bbox_edge_touch_ratio(
        detection_frames=edge_frames,
        frame_width=640,
        frame_height=512,
    )
    assert ratio >= 0.8


def test_thermal_static_guard_blocks_static_weak_motion_on_idle_scene():
    """Idle-scene static thermal boxes should require stronger evidence."""
    worker = DetectorWorker.__new__(DetectorWorker)
    static_frames = [
        [{"bbox": [120, 70, 170, 230], "confidence": 0.72}]
        for _ in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=static_frames,
        motion_area_now=900,
        active_motion_cameras=1,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is False


def test_thermal_static_guard_blocks_low_conf_false_positives():
    """Low-conf (0.52-0.64) thermal ghosts should be blocked even with multi-cam motion."""
    worker = DetectorWorker.__new__(DetectorWorker)
    for conf in (0.52, 0.58, 0.64):
        frames = [[{"bbox": [120, 70, 170, 230], "confidence": conf}] for _ in range(5)]
        assert worker._passes_thermal_static_event_guard(
            detection_frames=frames,
            motion_area_now=1200,
            active_motion_cameras=4,
            confidence_threshold=0.55,
            base_min_area=260,
        ) is False, f"conf={conf} should be blocked"

    # Even with slightly larger center spread, static jitter should still be blocked.
    jitter_frames = [
        [{"bbox": [120 + (i * 2), 70, 170 + (i * 2), 230], "confidence": 0.64}]
        for i in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=jitter_frames,
        motion_area_now=2000,
        active_motion_cameras=4,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is False

    # Border-hugging jitter boxes should be blocked even with moderate confidence.
    edge_jitter = [
        [{"bbox": [0 + (i * 2), 0, 130 + (i * 2), 510], "confidence": 0.72}]
        for i in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=edge_jitter,
        motion_area_now=2600,
        active_motion_cameras=4,
        confidence_threshold=0.55,
        base_min_area=260,
        frame_width=640,
        frame_height=512,
    ) is False

    # Edge oscillation with high spread but tiny net displacement should also be blocked.
    edge_oscillation = [
        [{"bbox": [x, 0, x + 130, 510], "confidence": 0.70}]
        for x in (8, 42, 10, 40, 9)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=edge_oscillation,
        motion_area_now=2600,
        active_motion_cameras=4,
        confidence_threshold=0.55,
        base_min_area=260,
        frame_width=640,
        frame_height=512,
    ) is False


def test_thermal_static_guard_allows_moving_track_or_multi_camera_load():
    """Guard should allow moving tracks and block low-conf static ghosts even with multi-cam."""
    worker = DetectorWorker.__new__(DetectorWorker)
    moving_frames = [
        [{"bbox": [120 + (i * 9), 70, 170 + (i * 9), 230], "confidence": 0.70}]
        for i in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=moving_frames,
        motion_area_now=900,
        active_motion_cameras=1,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is True

    # Low-conf static ghost with multi-cam remains blocked.
    static_frames_low_conf = [
        [{"bbox": [120, 70, 170, 230], "confidence": 0.62}]
        for _ in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=static_frames_low_conf,
        motion_area_now=850,
        active_motion_cameras=3,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is False

    # Mid-conf static ghost is still blocked even if motion area is elevated.
    static_frames_mid_conf = [
        [{"bbox": [120, 70, 170, 230], "confidence": 0.68}]
        for _ in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=static_frames_mid_conf,
        motion_area_now=2200,
        active_motion_cameras=3,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is False

    # High-confidence static box can pass only with strong motion evidence.
    static_frames_high_conf = [
        [{"bbox": [120, 70, 170, 230], "confidence": 0.82}]
        for _ in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=static_frames_high_conf,
        motion_area_now=2200,
        active_motion_cameras=3,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is True

    # Mid confidence moving track should pass when movement signature is clear.
    moving_mid_conf = [
        [{"bbox": [120 + (i * 12), 70, 170 + (i * 12), 230], "confidence": 0.70}]
        for i in range(5)
    ]
    assert worker._passes_thermal_static_event_guard(
        detection_frames=moving_mid_conf,
        motion_area_now=1100,
        active_motion_cameras=3,
        confidence_threshold=0.55,
        base_min_area=260,
    ) is True


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
