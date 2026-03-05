"""
Detection worker for Smart Motion Detector v2.

This worker handles YOLOv8 person detection pipeline including:
- RTSP stream ingestion
- Thermal/color preprocessing
- YOLOv8 inference
- Advanced filtering (aspect ratio, temporal consistency, zone inertia)
- Event generation
"""
import logging
import math
import os
import copy
import threading
import time
import asyncio
import shutil
import subprocess
from collections import defaultdict, deque
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np
import psutil
from sqlalchemy.orm import Session

from app.db.models import Camera, Event, CameraStatus
from app.db.session import session_scope
from app.services.camera import CameraService
from app.services.events import get_event_service
from app.services.ai import get_ai_service
from app.services.inference import get_inference_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.telegram import get_telegram_service
from app.services.time_utils import get_detection_source
from app.services.websocket import get_websocket_manager
from app.services.mqtt import get_mqtt_service
from app.services.go2rtc import get_go2rtc_service
from app.services.metrics import get_metrics_service
from app.services.ai_constants import AI_NEGATIVE_MARKERS, AI_POSITIVE_MARKERS
from app.utils.rtsp import redact_rtsp_url


logger = logging.getLogger(__name__)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DetectorWorker:
    """
    Detection worker for person detection pipeline.
    
    Manages per-camera detection threads with YOLOv8 inference.
    """
    
    DETECTION_LOOP_PARITY_CHECKLIST = (
        "stream_reconnect",
        "status_updates",
        "motion_gate",
        "temporal_consistency",
        "cooldown_gate",
        "event_creation",
        "media_generation",
    )

    def __init__(self):
        """Initialize detector worker."""
        self.running = False
        self.threads: Dict[str, threading.Thread] = {}
        self.camera_stop_events: Dict[str, threading.Event] = {}
        
        # Services
        self.camera_service = CameraService()
        self.inference_service = get_inference_service()
        self.event_service = get_event_service()
        self.ai_service = get_ai_service()
        self.settings_service = get_settings_service()
        self.media_service = get_media_service()
        self.websocket_manager = get_websocket_manager()
        self.telegram_service = get_telegram_service()
        self.mqtt_service = get_mqtt_service()
        self.go2rtc_service = get_go2rtc_service()
        self.metrics_service = get_metrics_service()
        
        # Per-camera state
        self.frame_buffers: Dict[str, deque] = defaultdict(deque)
        self.frame_counters: Dict[str, int] = defaultdict(int)
        self.frame_buffer_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.video_buffers: Dict[str, deque] = defaultdict(deque)
        self.video_buffer_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.video_last_sample: Dict[str, float] = {}
        self.latest_frames: Dict[str, np.ndarray] = {}
        self.latest_frame_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.detection_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))
        self.zone_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=5)))
        self.last_event_time: Dict[str, float] = {}
        self.event_start_time: Dict[str, Optional[float]] = {}
        self.motion_state: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.zone_cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.last_status_update: Dict[str, float] = {}
        self.codec_cache: Dict[str, str] = {}
        self.ffmpeg_frame_shapes: Dict[str, Tuple[int, int]] = {}
        self.ffmpeg_last_errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=3))
        self.ffmpeg_error_lock = threading.Lock()
        self.ffmpeg_fallback_until: Dict[str, float] = {}
        self.last_detection_log: Dict[str, float] = {}
        self.last_detection_pipeline_log: Dict[str, float] = {}
        self.last_gate_log: Dict[str, float] = {}
        self.last_fallback_log: Dict[str, float] = {}
        self.no_detection_streak: Dict[str, int] = defaultdict(int)
        self.empty_inference_streak: Dict[str, int] = defaultdict(int)
        self.suppressed_until: Dict[str, float] = {}
        self.last_motion_area: Dict[str, int] = defaultdict(int)
        self.last_suppression_probe: Dict[str, float] = {}
        self.suppression_rearm_until: Dict[str, float] = {}
        self.thermal_motion_peak_area: Dict[str, int] = defaultdict(int)
        self.thermal_motion_peak_ts: Dict[str, float] = {}
        self.last_relaxed_infer_time: Dict[str, float] = {}
        self.last_thermal_allclass_infer_time: Dict[str, float] = {}
        self.thermal_recovery_hold_detections: Dict[str, List[Dict[str, Any]]] = {}
        self.thermal_recovery_hold_until: Dict[str, float] = {}
        self.stale_gate_hits: Dict[str, int] = defaultdict(int)
        self.last_reconnect_ts: Dict[str, float] = {}
        self.stream_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.stream_stats_lock = threading.Lock()
        
        logger.info("DetectorWorker initialized")
    
    def start(self) -> None:
        """
        Start detection worker.
        
        Loads YOLOv8 model and starts per-camera detection threads.
        """
        if self.running:
            logger.warning("DetectorWorker already running")
            return
        
        try:
            # Load settings
            config = self.settings_service.load_config()
            
            # Load YOLOv8 model
            model_name = config.detection.model.replace("-person", "")  # yolov8n-person → yolov8n
            self.inference_service.load_model(model_name)
            
            self.running = True
            logger.info("DetectorWorker started")
            logger.info(
                "Detector parity checklist active: %s",
                ",".join(self.DETECTION_LOOP_PARITY_CHECKLIST),
            )

            # Start detection threads for enabled cameras
            # Legacy: empty/null stream_roles => run detection (backward compat)
            with session_scope() as db:
                db.expire_on_commit = False
                cameras = db.query(Camera).filter(Camera.enabled.is_(True)).all()
                started = 0
                for camera in cameras:
                    roles = camera.stream_roles if isinstance(camera.stream_roles, list) else []
                    if roles and "detect" not in roles:
                        continue  # Explicitly excludes detect
                    self.start_camera_detection(self._camera_snapshot(camera))
                    started += 1
                logger.info("DetectorWorker camera threads started: %s", started)
            
        except Exception as e:
            self.running = False
            logger.error(f"Failed to start DetectorWorker: {e}")
            raise
    
    def stop(self) -> None:
        """Stop detection worker and cleanup resources."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to finish
        for stop_event in self.camera_stop_events.values():
            stop_event.set()
        for camera_id, thread in self.threads.items():
            logger.info(f"Stopping detection thread for camera {camera_id}")
            thread.join(timeout=5)
        
        self.threads.clear()
        self.camera_stop_events.clear()
        self.frame_buffers.clear()
        self.frame_counters.clear()
        self.frame_buffer_locks.clear()
        self.video_buffers.clear()
        self.video_buffer_locks.clear()
        self.video_last_sample.clear()
        self.detection_history.clear()
        self.zone_history.clear()
        self.last_event_time.clear()
        self.event_start_time.clear()
        self.motion_state.clear()
        self.zone_cache.clear()
        self.last_status_update.clear()
        self.codec_cache.clear()
        self.latest_frames.clear()
        self.latest_frame_locks.clear()
        self.stale_gate_hits.clear()
        self.last_suppression_probe.clear()
        self.suppression_rearm_until.clear()
        self.thermal_motion_peak_area.clear()
        self.thermal_motion_peak_ts.clear()
        self.last_thermal_allclass_infer_time.clear()
        self.thermal_recovery_hold_detections.clear()
        self.thermal_recovery_hold_until.clear()
        self.last_reconnect_ts.clear()
        self.ffmpeg_fallback_until.clear()
        logger.info("DetectorWorker stopped")
    
    def stop_camera_detection(self, camera_id: str) -> None:
        """Stop detection thread for a single camera if running."""
        stop_event = self.camera_stop_events.get(camera_id)
        if stop_event:
            stop_event.set()
        thread = self.threads.get(camera_id)
        if thread:
            logger.info("Stopping detection thread for camera %s", camera_id)
            thread.join(timeout=5)
        self.threads.pop(camera_id, None)
        self.camera_stop_events.pop(camera_id, None)
        self._cleanup_camera_state(camera_id)

    def _cleanup_camera_state(self, camera_id: str) -> None:
        self.frame_buffers.pop(camera_id, None)
        self.frame_counters.pop(camera_id, None)
        self.frame_buffer_locks.pop(camera_id, None)
        self.video_buffers.pop(camera_id, None)
        self.video_buffer_locks.pop(camera_id, None)
        self.video_last_sample.pop(camera_id, None)
        self.detection_history.pop(camera_id, None)
        self.zone_history.pop(camera_id, None)
        self.last_event_time.pop(camera_id, None)
        self.event_start_time.pop(camera_id, None)
        self.motion_state.pop(camera_id, None)
        self.zone_cache.pop(camera_id, None)
        self.last_status_update.pop(camera_id, None)
        self.codec_cache.pop(camera_id, None)
        self.latest_frames.pop(camera_id, None)
        self.latest_frame_locks.pop(camera_id, None)
        self.last_detection_log.pop(camera_id, None)
        self.last_detection_pipeline_log.pop(camera_id, None)
        self.last_gate_log.pop(camera_id, None)
        self.last_fallback_log.pop(camera_id, None)
        self.no_detection_streak.pop(camera_id, None)
        self.last_relaxed_infer_time.pop(camera_id, None)
        self.stale_gate_hits.pop(camera_id, None)
        self.empty_inference_streak.pop(camera_id, None)
        self.suppressed_until.pop(camera_id, None)
        self.last_motion_area.pop(camera_id, None)
        self.last_suppression_probe.pop(camera_id, None)
        self.suppression_rearm_until.pop(camera_id, None)
        self.thermal_motion_peak_area.pop(camera_id, None)
        self.thermal_motion_peak_ts.pop(camera_id, None)
        self.last_thermal_allclass_infer_time.pop(camera_id, None)
        self.thermal_recovery_hold_detections.pop(camera_id, None)
        self.thermal_recovery_hold_until.pop(camera_id, None)
        self.last_reconnect_ts.pop(camera_id, None)
        self.ffmpeg_frame_shapes.pop(camera_id, None)
        with self.ffmpeg_error_lock:
            self.ffmpeg_last_errors.pop(camera_id, None)
        self.ffmpeg_fallback_until.pop(camera_id, None)
        with self.stream_stats_lock:
            self.stream_stats.pop(camera_id, None)

    def _should_wakeup_thermal_suppression(
        self,
        current_area: int,
        prev_area: int,
        wakeup_ratio: float,
        min_wakeup_area: int,
    ) -> bool:
        """Decide whether thermal suppression should be lifted early."""
        if current_area <= 0:
            return False

        if current_area >= min_wakeup_area and current_area > (prev_area * wakeup_ratio):
            return True

        # Slow-walking humans can increase area gradually and never hit ratio.
        # Allow wake-up if area grows by a meaningful absolute delta.
        growth_delta = max(0, current_area - prev_area)
        min_delta = max(300, int(min_wakeup_area * 0.5))
        gradual_floor = max(1200, int(min_wakeup_area * 0.7))
        return current_area >= gradual_floor and growth_delta >= min_delta

    def _count_active_motion_cameras(self) -> int:
        """Count cameras currently marked as motion-active."""
        try:
            return sum(
                1
                for state in self.motion_state.values()
                if isinstance(state, dict)
                and (
                    bool(state.get("motion_active", False))
                    or bool(state.get("active", False))
                )
            )
        except Exception:
            return 0

    def _count_recent_motion_cameras(self, window_seconds: float = 6.0) -> int:
        """Count cameras with active/recent motion to smooth short state flickers."""
        try:
            now_ts = time.time()
            window = max(0.5, float(window_seconds))
            count = 0
            for state in self.motion_state.values():
                if not isinstance(state, dict):
                    continue
                if bool(state.get("motion_active", False)) or bool(state.get("active", False)):
                    count += 1
                    continue
                last_motion = float(state.get("last_motion", 0.0) or 0.0)
                if last_motion > 0.0 and (now_ts - last_motion) <= window:
                    count += 1
            return count
        except Exception:
            return 0

    @staticmethod
    def _thermal_probe_interval_seconds(
        suppression_secs: int,
        active_motion_cameras: int,
    ) -> float:
        """
        Probe cadence while suppressed.

        Base cadence keeps CPU savings; multi-camera motion gets faster probes
        to avoid missing short walk-throughs under shared-inference contention.
        """
        base_interval = max(1.0, min(5.0, float(suppression_secs) / 15.0))
        if active_motion_cameras >= 2:
            return max(0.8, min(base_interval, 1.0))
        return base_interval

    @staticmethod
    def _thermal_warmup_motion_gate(
        min_area: int,
        gate_floor: int,
        gate_multiplier: float,
    ) -> int:
        """
        Compute motion-area gate used during thermal warmup/reconnect windows.

        This keeps tiny reconnect jitters blocked while allowing strong motion
        to pass without waiting for the full warmup timeout.
        """
        base_min = max(1, int(min_area))
        floor = max(1, int(gate_floor))
        multiplier = max(0.5, float(gate_multiplier))
        return max(floor, int(base_min * multiplier))

    @staticmethod
    def _thermal_auto_min_area_cap(
        configured_ceiling: int,
        active_motion_cameras: int,
    ) -> int:
        """
        Cap thermal auto min-area so learned thresholds don't drift too high.

        Multi-camera concurrent motion needs lower caps to keep short/far person
        walk-throughs from being filtered out by the motion gate.
        """
        cap = max(200, int(configured_ceiling))
        if active_motion_cameras >= 4:
            return min(cap, 700)
        if active_motion_cameras >= 2:
            return min(cap, 850)
        return min(cap, 1100)

    @staticmethod
    def _should_fallback_from_ffmpeg_flapping(
        reconnect_timestamps: List[float],
        now_ts: float,
        window_seconds: float = 180.0,
        reconnect_threshold: int = 4,
    ) -> bool:
        """Detect frequent ffmpeg reconnects in a short window."""
        if not reconnect_timestamps:
            return False
        window = max(30.0, float(window_seconds))
        threshold = max(2, int(reconnect_threshold))
        recent = sum(1 for ts in reconnect_timestamps if (now_ts - float(ts)) <= window)
        return recent >= threshold

    @staticmethod
    def _allows_ffmpeg_flapping_fallback(capture_backend: str) -> bool:
        """Allow anti-flapping fallback for auto and forced ffmpeg modes."""
        return str(capture_backend or "auto").lower() in ("auto", "ffmpeg")

    @staticmethod
    def _select_capture_backend_for_reopen(
        current_backend: str,
        configured_backend: str,
        fallback_until_ts: float,
        now_ts: float,
        recent_reconnects: int = 0,
    ) -> str:
        """
        Resolve backend choice during reopen attempts.

        - While temporary fallback is active, force OpenCV.
        - In forced ffmpeg mode, retry ffmpeg after fallback window.
        - In auto mode, retry ffmpeg after fallback window (prefer ffmpeg as
          primary path once temporary fallback period has elapsed).
        - In auto mode, allow early ffmpeg retry even inside fallback window when
          reconnect pressure becomes high (OpenCV path likely unstable too).
        """
        current = str(current_backend or "opencv").lower()
        configured = str(configured_backend or "auto").lower()
        fallback_until = float(fallback_until_ts or 0.0)
        now = float(now_ts)
        pressure = max(0, int(recent_reconnects))

        if current == "ffmpeg" and configured in ("auto", "ffmpeg") and fallback_until > now:
            return "opencv"
        if current == "opencv" and configured == "ffmpeg" and fallback_until <= now:
            return "ffmpeg"
        if (
            current == "opencv"
            and configured == "auto"
            and fallback_until > now
            and pressure >= 3
        ):
            return "ffmpeg"
        if (
            current == "opencv"
            and configured == "auto"
            and fallback_until <= now
        ):
            return "ffmpeg"
        return current

    @staticmethod
    def _ffmpeg_exit_opencv_fallback_seconds(
        exit_code: Optional[int],
        recent_reconnects: int = 0,
    ) -> float:
        """
        Temporary OpenCV fallback duration after ffmpeg process exits.

        Exit code 0 is common in silent go2rtc/ffmpeg stream resets.
        Use shorter fallback for isolated exits, but keep it longer under
        reconnect pressure to avoid backend oscillation.
        """
        code = int(exit_code) if exit_code is not None else -1
        pressure = max(0, int(recent_reconnects))
        if code == 0:
            if pressure >= 6:
                return 600.0
            if pressure >= 3:
                return 360.0
            return 180.0
        if pressure >= 6:
            return 300.0
        if pressure >= 3:
            return 210.0
        return 120.0

    @staticmethod
    def _should_use_opencv_fallback_after_ffmpeg_exit(
        exit_code: Optional[int],
        recent_code0_ffmpeg_exits: int = 0,
        recent_reconnects: int = 0,
    ) -> bool:
        """
        Decide whether ffmpeg exit should trigger temporary OpenCV fallback.

        - Non-zero exits are treated as hard failures -> fallback immediately.
        - Exit code 0 is often a transient upstream reset; do not fallback on
          isolated events. Fallback only if it repeats soon or reconnect pressure
          is already high.
        """
        code = int(exit_code) if exit_code is not None else -1
        code0_exits = max(0, int(recent_code0_ffmpeg_exits))
        pressure = max(0, int(recent_reconnects))
        if code != 0:
            return True
        if pressure >= 3:
            return True
        return code0_exits >= 1

    def _mark_thermal_reconnect_warmup(
        self,
        camera_id: str,
        now_ts: float,
        warmup_seconds: float,
    ) -> None:
        """Reset thermal motion baseline/state after stream reconnect."""
        state = self.motion_state.get(camera_id)
        if not isinstance(state, dict):
            state = {}
        warmup_until = float(now_ts) + max(4.0, float(warmup_seconds))
        state["thermal_motion_gate_warmup_until"] = max(
            float(state.get("thermal_motion_gate_warmup_until", 0.0)),
            warmup_until,
        )
        state["motion_active"] = False
        state.pop("motion_active_since", None)
        state["thermal_motion_above_streak"] = 0
        state["thermal_motion_below_streak"] = 0
        state["last_motion"] = float(now_ts)
        state.pop("thermal_bg", None)
        state.pop("thermal_noise_var", None)
        state.pop("thermal_motion_persisted", None)
        state.pop("thermal_motion_area_raw", None)
        self.motion_state[camera_id] = state

    @staticmethod
    def _should_hold_thermal_motion_active(
        active_since_ts: float,
        now_ts: float,
        min_active_seconds: float,
    ) -> bool:
        """Keep thermal motion active briefly to avoid active/idle chatter."""
        min_hold = max(0.0, float(min_active_seconds))
        if min_hold <= 0.0:
            return False
        started = float(active_since_ts or 0.0)
        if started <= 0.0:
            return False
        return (float(now_ts) - started) < min_hold

    @staticmethod
    def _stream_read_failure_policy(
        base_threshold: int,
        base_timeout: float,
        seconds_since_reconnect: float,
        recent_reconnects: int = 0,
        detection_source: Optional[str] = None,
    ) -> Tuple[int, float, float]:
        """
        Stabilize reconnect decisions to avoid read-failure reconnect flapping.

        Right after a reconnect, allow extra tolerance for decoder/stream warmup.
        """
        threshold = max(1, int(base_threshold))
        timeout = max(4.0, float(base_timeout))
        reconnect_cooldown = max(8.0, min(30.0, timeout * 1.5))
        reconnect_pressure = max(0, int(recent_reconnects))
        source = str(detection_source or "").lower()

        # Thermal streams tolerate brief stutters better if we avoid eager reopen.
        if source == "thermal":
            threshold = max(threshold + 2, 6)
            timeout = max(timeout + 3.0, 11.0)
            reconnect_cooldown = max(reconnect_cooldown, 14.0)

        if 0.0 <= float(seconds_since_reconnect) < 45.0:
            threshold = max(threshold + 3, 8)
            timeout = max(timeout + 4.0, 12.0)
            reconnect_cooldown = max(reconnect_cooldown, 20.0)

        # Reconnect pressure means upstream is unstable (camera/go2rtc/network).
        # Avoid reconnect loops by requiring a stronger stale signal.
        if reconnect_pressure >= 3:
            threshold = max(threshold + 2, 10)
            timeout = max(timeout + 4.0, 14.0)
            reconnect_cooldown = max(reconnect_cooldown, 30.0)
        if reconnect_pressure >= 5:
            threshold = max(threshold + 4, 14)
            timeout = max(timeout + 6.0, 18.0)
            reconnect_cooldown = max(reconnect_cooldown, 45.0)

        return threshold, timeout, reconnect_cooldown

    @staticmethod
    def _stream_fallback_read_failure_policy(
        failure_threshold: int,
        failure_timeout: float,
        reconnect_cooldown: float,
        active_backend: Optional[str],
        fallback_until_ts: float,
        now_ts: float,
        detection_source: Optional[str] = None,
    ) -> Tuple[int, float, float]:
        """
        During temporary OpenCV fallback, avoid eager reconnect loops.

        FFmpeg has already failed in this window; short RTSP hiccups should not
        immediately trigger another reopen while fallback is trying to stabilize.
        """
        backend = str(active_backend or "").lower()
        if backend != "opencv" or float(now_ts) >= float(fallback_until_ts):
            return int(failure_threshold), float(failure_timeout), float(reconnect_cooldown)

        threshold = max(int(failure_threshold) + 3, 10)
        timeout = max(float(failure_timeout) + 8.0, 18.0)
        cooldown = max(float(reconnect_cooldown), 30.0)
        if str(detection_source or "").lower() == "thermal":
            threshold = max(threshold, 12)
            timeout = max(timeout, 20.0)
            cooldown = max(cooldown, 35.0)
        return threshold, timeout, cooldown

    @staticmethod
    def _stream_opencv_read_failure_policy(
        failure_threshold: int,
        failure_timeout: float,
        reconnect_cooldown: float,
        active_backend: Optional[str],
        recent_reconnects: int = 0,
        detection_source: Optional[str] = None,
    ) -> Tuple[int, float, float]:
        """
        Keep reconnect logic conservative while running on OpenCV backend.

        Some cameras can produce short decode/read gaps on OpenCV restreams.
        Reopening too quickly in that mode tends to create periodic reconnect
        loops, so require stronger stale evidence before reconnecting.
        """
        backend = str(active_backend or "").lower()
        if backend != "opencv":
            return int(failure_threshold), float(failure_timeout), float(reconnect_cooldown)

        pressure = max(0, int(recent_reconnects))
        source = str(detection_source or "").lower()

        threshold = max(int(failure_threshold), 9)
        timeout = max(float(failure_timeout), 15.0)
        cooldown = max(float(reconnect_cooldown), 25.0)

        if source == "thermal":
            threshold = max(threshold, 11)
            timeout = max(timeout, 17.0)
            cooldown = max(cooldown, 30.0)

        if pressure >= 3:
            threshold = max(threshold, 14)
            timeout = max(timeout, 24.0)
            cooldown = max(cooldown, 55.0)
        if pressure >= 5:
            threshold = max(threshold, 18)
            timeout = max(timeout, 32.0)
            cooldown = max(cooldown, 90.0)

        return threshold, timeout, cooldown

    @staticmethod
    def _stream_reconnect_age_gate(
        failure_timeout: float,
        recent_reconnects: int,
        detection_source: Optional[str] = None,
        fallback_active: bool = False,
        opencv_backend: bool = False,
    ) -> float:
        """
        Require a longer no-frame age before reconnecting under unstable streams.

        This reduces reconnect oscillation during short upstream RTSP hiccups.
        """
        timeout = max(4.0, float(failure_timeout))
        pressure = max(0, int(recent_reconnects))
        source = str(detection_source or "").lower()

        stale_age = max(10.0, timeout * 1.6)
        if source == "thermal":
            stale_age = max(stale_age, 14.0)
        if pressure >= 3:
            stale_age = max(stale_age, timeout * 2.0, 18.0)
        if pressure >= 5:
            stale_age = max(stale_age, timeout * 2.5, 24.0)
        if bool(fallback_active):
            # While in ffmpeg->opencv fallback window, require stronger stale
            # evidence before reconnecting again.
            stale_age = max(stale_age, timeout * 1.8, 30.0)
        if bool(opencv_backend):
            # Even after fallback window ends, OpenCV streams can have short
            # decoder hiccups. Reconnect only with stronger stale evidence.
            stale_age = max(stale_age, timeout * 2.1, 36.0)
            if pressure >= 3:
                stale_age = max(stale_age, 45.0)
            if pressure >= 5:
                stale_age = max(stale_age, 60.0)
        return stale_age

    @staticmethod
    def _slew_limited_auto_min_area(
        previous_learned: Optional[int],
        learned_target: int,
        max_down_step: int,
        max_up_step: int,
    ) -> int:
        """Limit per-update threshold jumps to reduce thermal min-area chatter."""
        target = int(learned_target)
        if previous_learned is None:
            return target

        prev = int(previous_learned)
        down_step = max(1, int(max_down_step))
        up_step = max(1, int(max_up_step))

        if target < prev:
            return max(target, prev - down_step)
        if target > prev:
            return min(target, prev + up_step)
        return target

    @staticmethod
    def _thermal_motion_hysteresis_decision(
        motion_area: int,
        min_area: int,
        motion_active: bool,
        above_streak: int,
        below_streak: int,
        active_factor: float,
        idle_factor: float,
        active_streak_required: int,
        idle_streak_required: int,
    ) -> Tuple[bool, int, int, int, int]:
        """Two-sided hysteresis with streak confirmation for thermal motion."""
        active_factor = max(1.0, float(active_factor))
        idle_factor = max(0.5, min(1.0, float(idle_factor)))
        on_threshold = int(max(1, int(min_area) * active_factor))
        off_threshold = int(max(1, int(min_area) * idle_factor))

        above = max(0, int(above_streak))
        below = max(0, int(below_streak))
        need_on = max(1, int(active_streak_required))
        need_off = max(1, int(idle_streak_required))
        area = int(motion_area)

        if motion_active:
            if area >= off_threshold:
                return True, above, 0, on_threshold, off_threshold
            below += 1
            return below < need_off, above, below, on_threshold, off_threshold

        if area >= on_threshold:
            above += 1
            return above >= need_on, above, 0, on_threshold, off_threshold

        return False, 0, 0, on_threshold, off_threshold

    @staticmethod
    def _thermal_temporal_policy(
        confidence_threshold: float,
        active_motion_cameras: int,
    ) -> Tuple[int, int, float]:
        """Adaptive temporal gate for thermal detections under concurrent load."""
        if active_motion_cameras >= 4:
            return 2, 2, max(float(confidence_threshold) + 0.02, 0.50)
        if active_motion_cameras >= 2:
            return 2, 1, max(float(confidence_threshold) + 0.03, 0.52)
        # Single-camera walk-throughs can be short in thermal streams; keeping
        # this at 3 frames causes frequent misses under low/variable inference FPS.
        # Static-ghost and confidence gates still run afterwards.
        return 2, 1, max(float(confidence_threshold) + 0.07, 0.62)

    @staticmethod
    def _coerce_allclass_to_person(
        detections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert class-agnostic fallback detections into person candidates.

        This is used only in thermal recovery mode when person-only inference
        repeatedly returns empty results under active motion.
        """
        coerced: List[Dict[str, Any]] = []
        for det in detections or []:
            if not isinstance(det, dict):
                continue
            bbox = det.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue
            try:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                conf = float(det.get("confidence", 0.0))
            except Exception:
                continue
            if conf <= 0.0:
                continue
            coerced.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "confidence": conf,
                    "class_id": 0,
                    "class_name": "person",
                }
            )
        return coerced

    @staticmethod
    def _thermal_recovery_hold_window_seconds(active_motion_cameras: int) -> float:
        """Short hold window to keep thermal recovery tracks temporally stable."""
        cams = max(0, int(active_motion_cameras))
        if cams >= 3:
            return 1.00
        if cams >= 2:
            return 0.80
        return 0.65

    @staticmethod
    def _clone_recovery_detections(
        detections: List[Dict[str, Any]],
        confidence_decay: float = 0.03,
    ) -> List[Dict[str, Any]]:
        """Clone cached detections with slight confidence decay for hold frames."""
        cloned: List[Dict[str, Any]] = []
        decay = max(0.0, float(confidence_decay))
        for det in detections or []:
            if not isinstance(det, dict):
                continue
            bbox = det.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue
            try:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                conf = float(det.get("confidence", 0.0))
            except Exception:
                continue
            new_conf = max(0.18, conf - decay)
            cloned.append(
                {
                    "bbox": [x1, y1, x2, y2],
                    "confidence": new_conf,
                    "class_id": int(det.get("class_id", 0)),
                    "class_name": str(det.get("class_name", "person") or "person"),
                }
            )
        return cloned

    @staticmethod
    def _thermal_bbox_center_spread(
        detection_frames: List[List[Dict[str, Any]]],
        sample_frames: int = 5,
    ) -> float:
        """Estimate center spread across recent thermal detections."""
        if not detection_frames:
            return 0.0
        frames = detection_frames[-max(2, int(sample_frames)) :]
        centers_x: List[float] = []
        centers_y: List[float] = []
        for frame_dets in frames:
            dets_with_bbox = [
                det for det in (frame_dets or []) if isinstance(det, dict) and det.get("bbox")
            ]
            if not dets_with_bbox:
                continue
            best_det = max(dets_with_bbox, key=lambda det: float(det.get("confidence", 0.0)))
            x1, y1, x2, y2 = best_det["bbox"]
            centers_x.append((float(x1) + float(x2)) / 2.0)
            centers_y.append((float(y1) + float(y2)) / 2.0)
        if len(centers_x) < 2:
            return 0.0
        return max(max(centers_x) - min(centers_x), max(centers_y) - min(centers_y))

    @staticmethod
    def _thermal_bbox_net_displacement(
        detection_frames: List[List[Dict[str, Any]]],
        sample_frames: int = 5,
    ) -> float:
        """Net center displacement between first and last recent best boxes."""
        if not detection_frames:
            return 0.0
        frames = detection_frames[-max(2, int(sample_frames)) :]
        centers: List[Tuple[float, float]] = []
        for frame_dets in frames:
            dets_with_bbox = [
                det for det in (frame_dets or []) if isinstance(det, dict) and det.get("bbox")
            ]
            if not dets_with_bbox:
                continue
            best_det = max(dets_with_bbox, key=lambda det: float(det.get("confidence", 0.0)))
            x1, y1, x2, y2 = map(float, best_det["bbox"])
            centers.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
        if len(centers) < 2:
            return 0.0
        sx, sy = centers[0]
        ex, ey = centers[-1]
        return float(np.hypot(ex - sx, ey - sy))

    @staticmethod
    def _thermal_bbox_area_growth_ratio(
        detection_frames: List[List[Dict[str, Any]]],
        sample_frames: int = 5,
    ) -> float:
        """
        Estimate best-box area growth across recent frames.

        Helps detect approach/retreat motion where center displacement can stay
        low but object scale changes significantly.
        """
        if not detection_frames:
            return 1.0
        frames = detection_frames[-max(2, int(sample_frames)) :]
        areas: List[float] = []
        for frame_dets in frames:
            dets_with_bbox = [
                det for det in (frame_dets or []) if isinstance(det, dict) and det.get("bbox")
            ]
            if not dets_with_bbox:
                continue
            best_det = max(dets_with_bbox, key=lambda det: float(det.get("confidence", 0.0)))
            x1, y1, x2, y2 = map(float, best_det["bbox"])
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)
            area = w * h
            if area > 0.0:
                areas.append(area)
        if len(areas) < 2:
            return 1.0
        min_area = max(min(areas), 1.0)
        max_area = max(areas)
        return float(max_area / min_area)

    @staticmethod
    def _bbox_iou(box_a: List[float], box_b: List[float]) -> float:
        """Compute IoU for two [x1, y1, x2, y2] boxes."""
        ax1, ay1, ax2, ay2 = map(float, box_a)
        bx1, by1, bx2, by2 = map(float, box_b)
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - inter_area
        if union <= 0.0:
            return 0.0
        return inter_area / union

    @classmethod
    def _thermal_bbox_median_iou(
        cls,
        detection_frames: List[List[Dict[str, Any]]],
        sample_frames: int = 5,
    ) -> float:
        """Median IoU of consecutive best boxes across recent frames."""
        if not detection_frames:
            return 0.0
        frames = detection_frames[-max(2, int(sample_frames)) :]
        boxes: List[List[float]] = []
        for frame_dets in frames:
            dets_with_bbox = [
                det for det in (frame_dets or []) if isinstance(det, dict) and det.get("bbox")
            ]
            if not dets_with_bbox:
                continue
            best_det = max(dets_with_bbox, key=lambda det: float(det.get("confidence", 0.0)))
            boxes.append(best_det["bbox"])
        if len(boxes) < 2:
            return 0.0
        ious = [
            cls._bbox_iou(boxes[idx - 1], boxes[idx])
            for idx in range(1, len(boxes))
        ]
        if not ious:
            return 0.0
        return float(np.median(np.array(ious, dtype=np.float32)))

    @classmethod
    def _thermal_bbox_edge_touch_ratio(
        cls,
        detection_frames: List[List[Dict[str, Any]]],
        frame_width: int,
        frame_height: int,
        sample_frames: int = 5,
        margin_ratio: float = 0.03,
    ) -> float:
        """Share of recent best boxes touching frame borders."""
        if not detection_frames:
            return 0.0
        w = max(1, int(frame_width))
        h = max(1, int(frame_height))
        margin_x = max(2.0, float(w) * float(margin_ratio))
        margin_y = max(2.0, float(h) * float(margin_ratio))
        frames = detection_frames[-max(2, int(sample_frames)) :]
        touches = 0
        total = 0
        for frame_dets in frames:
            dets_with_bbox = [
                det for det in (frame_dets or []) if isinstance(det, dict) and det.get("bbox")
            ]
            if not dets_with_bbox:
                continue
            best_det = max(dets_with_bbox, key=lambda det: float(det.get("confidence", 0.0)))
            x1, y1, x2, y2 = map(float, best_det["bbox"])
            total += 1
            if (
                x1 <= margin_x
                or y1 <= margin_y
                or x2 >= (float(w) - margin_x)
                or y2 >= (float(h) - margin_y)
            ):
                touches += 1
        if total == 0:
            return 0.0
        return float(touches) / float(total)

    @classmethod
    def _passes_thermal_static_event_guard(
        cls,
        detection_frames: List[List[Dict[str, Any]]],
        motion_area_now: int,
        active_motion_cameras: int,
        confidence_threshold: float,
        base_min_area: int,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        deep_recovery_mode: bool = False,
    ) -> bool:
        """
        Block static thermal ghosts on idle scenes while preserving multi-cam recall.

        Require meaningful bbox travel for low/mid confidence tracks.
        Static tracks can pass only with strong confidence + strong motion area.
        """
        current_dets = detection_frames[-1] if detection_frames else []
        best_conf = max((float(det.get("confidence", 0.0)) for det in current_dets), default=0.0)
        recovery_mode = bool(deep_recovery_mode)
        if recovery_mode:
            # Keep recovery mode permissive enough for low-conf thermal hits,
            # while still requiring clear motion signature downstream.
            min_conf_floor = max(float(confidence_threshold) + 0.00, 0.24)
        else:
            min_conf_floor = max(float(confidence_threshold) + 0.15, 0.67)
        spread = cls._thermal_bbox_center_spread(detection_frames=detection_frames, sample_frames=5)
        median_iou = cls._thermal_bbox_median_iou(detection_frames=detection_frames, sample_frames=5)
        net_displacement = cls._thermal_bbox_net_displacement(
            detection_frames=detection_frames,
            sample_frames=5,
        )
        area_growth = cls._thermal_bbox_area_growth_ratio(
            detection_frames=detection_frames,
            sample_frames=5,
        )
        directional_ratio = float(net_displacement) / max(float(spread), 1.0)
        edge_touch_ratio = 0.0
        if frame_width and frame_height:
            edge_touch_ratio = cls._thermal_bbox_edge_touch_ratio(
                detection_frames=detection_frames,
                frame_width=int(frame_width),
                frame_height=int(frame_height),
                sample_frames=5,
            )
        recent_frames = detection_frames[-5:] if detection_frames else []
        observed_frames = 0
        for frame_dets in recent_frames:
            if any(
                isinstance(det, dict) and det.get("bbox")
                for det in (frame_dets or [])
            ):
                observed_frames += 1
        sparse_recovery_track = False
        if recovery_mode and observed_frames < 3:
            # Sparse history can make real walk-through tracks look static.
            # Keep a guarded pass path for deep-recovery detections.
            sparse_recovery_track = (
                best_conf >= max(float(confidence_threshold) + 0.00, 0.30)
                and int(motion_area_now) >= max(1200, int(base_min_area) * 2)
                and edge_touch_ratio < 0.80
            )

        # Border-hugging boxes are usually static background artifacts.
        edge_strict_conf = max(
            float(confidence_threshold) + 0.25,
            0.68 if recovery_mode else 0.78,
        )
        if edge_touch_ratio >= 0.80 and best_conf < edge_strict_conf:
            return False
        # Border-side oscillation usually indicates vegetation sway, not a walk-through.
        edge_soft_conf = max(
            float(confidence_threshold) + 0.20,
            0.64 if recovery_mode else 0.74,
        )
        if edge_touch_ratio >= 0.60 and best_conf < edge_soft_conf:
            if spread >= 8.0 and directional_ratio < 0.55:
                return False

        # Low-confidence + static/jitter signature => block.
        approach_motion = area_growth >= 1.25
        strong_approach_motion = area_growth >= 1.40
        if best_conf < min_conf_floor:
            if recovery_mode:
                # In deep recovery, require at least 2 static indicators.
                static_signals = 0
                if spread < 11.0:
                    static_signals += 1
                if median_iou > 0.90:
                    static_signals += 1
                if directional_ratio < 0.55:
                    static_signals += 1
                static_like = static_signals >= 2
            else:
                static_like = (
                    spread < 12.0
                    or median_iou > 0.88
                    or directional_ratio < 0.60
                )
            if static_like and not (
                sparse_recovery_track
                or
                strong_approach_motion and int(motion_area_now) >= max(1000, int(base_min_area) * 2)
            ):
                return False
        if sparse_recovery_track:
            return True

        # Real walk-through signature: enough travel + lower overlap over time.
        movement_conf_floor = (
            max(float(confidence_threshold) - 0.04, 0.24)
            if recovery_mode
            else max(min_conf_floor, 0.68)
        )
        # Avoid over-tightening movement gate when user/global min_area is set
        # aggressively high for noisy scenes (e.g. 650-900). We still require
        # clear movement signature, but cap the min_area contribution.
        guard_min_area = min(max(260, int(base_min_area)), 420)
        movement_motion_gate = max(780, int(guard_min_area * 2.0))
        if active_motion_cameras >= 2:
            movement_motion_gate = max(movement_motion_gate, int(guard_min_area * 2.2))
        if recovery_mode:
            # Do not scale strictly with user/auto min_area (often 900-1100+),
            # otherwise deep-recovery tracks around 1200-1800 area get blocked.
            recovery_gate = max(900, int(guard_min_area * 2.3))
            movement_motion_gate = max(
                movement_motion_gate,
                recovery_gate,
            )
        if (
            (
                (
                    spread >= 12.0
                    and median_iou <= 0.88
                    and directional_ratio >= 0.60
                    and net_displacement >= max(8.0, float(spread) * 0.55)
                )
                or approach_motion
            )
            and (best_conf + 1e-6) >= movement_conf_floor
            and int(motion_area_now) >= movement_motion_gate
        ):
            return True
        if recovery_mode:
            # Sustained deep-recovery tracks with clear travel should bypass the
            # strict static fallback path.
            persistent_recovery_track = (
                observed_frames >= 4
                and (best_conf + 1e-6) >= max(float(confidence_threshold) + 0.01, 0.24)
                and int(motion_area_now) >= max(1000, int(base_min_area) * 15 // 10)
                and edge_touch_ratio < 0.70
                and (
                    net_displacement >= 4.0
                    or (area_growth >= 1.08 and directional_ratio >= 0.40)
                )
            )
            if persistent_recovery_track:
                return True

        # Static box acceptance requires stronger evidence.
        if active_motion_cameras >= 2:
            strong_conf = max(float(confidence_threshold) + 0.22, 0.80)
            strong_motion = max(1900, int(base_min_area) * 5)
        else:
            strong_conf = max(float(confidence_threshold) + 0.27, 0.87)
            strong_motion = max(2200, int(base_min_area) * 6)
        return best_conf >= strong_conf and int(motion_area_now) >= strong_motion

    @staticmethod
    def _thermal_suppression_policy(
        base_streak: int,
        base_duration_secs: int,
        active_motion_cameras: int,
    ) -> Tuple[int, int]:
        """
        Adaptive suppression policy for thermal streams under concurrent load.

        Multi-camera scenarios prioritize recall: require longer empty streaks
        before suppressing, and keep suppression windows shorter.
        """
        streak = max(5, int(base_streak))
        duration = max(5, int(base_duration_secs))
        if active_motion_cameras >= 4:
            # Dense concurrent motion: almost disable suppression to avoid misses.
            return max(streak * 8, 180), min(duration, 6)
        if active_motion_cameras >= 2:
            return max(streak * 6, 120), min(duration, 8)
        # Single-camera thermal setups are vulnerable to repeated
        # suppress/unsuppress loops during real walk-throughs.
        return max(streak * 5, 70), min(duration, 8)

    @staticmethod
    def _thermal_confidence_policy(
        base_confidence: float,
        active_motion_cameras: int,
        motion_area_now: int,
        base_min_area: int,
    ) -> float:
        """
        Recall-biased thermal confidence floor under concurrent motion.

        Relax confidence only when motion signal is meaningfully above baseline,
        so weak idle-scene noise doesn't get a lower confidence floor.
        """
        conf = max(0.25, float(base_confidence))
        motion_area = max(0, int(motion_area_now))
        min_area = max(1, int(base_min_area))
        strong_motion_gate = max(800, min_area * 2)
        very_strong_motion_gate = max(900, min_area * 2)

        if active_motion_cameras >= 4 and motion_area >= very_strong_motion_gate:
            return max(0.25, conf - 0.10)
        if active_motion_cameras >= 2 and motion_area >= strong_motion_gate:
            return max(0.25, conf - 0.07)
        return conf

    @staticmethod
    def _thermal_deep_recovery_threshold(
        base_confidence: float,
        motion_area_now: int,
        base_min_area: int,
        no_detection_streak: int,
        active_motion_cameras: int,
    ) -> Optional[float]:
        """
        Extra-lenient thermal retry threshold for prolonged no-detection periods.

        Used only under strong motion + repeated misses to recover walk-throughs
        that remain below the regular thermal confidence floor.
        """
        streak = max(0, int(no_detection_streak))
        if streak < 4:
            return None

        min_area = max(1, int(base_min_area))
        motion_area = max(0, int(motion_area_now))
        if active_motion_cameras >= 2:
            strong_motion_gate = max(1000, int(min_area * 2.0))
        else:
            strong_motion_gate = max(1300, int(min_area * 2.5))
        if motion_area < strong_motion_gate:
            return None

        base = max(0.25, float(base_confidence))
        relax_delta = 0.22 if active_motion_cameras >= 2 else 0.18
        threshold = max(0.18, base - relax_delta)

        # Single-camera thermal streams with very strong motion can still miss
        # at base-0.18; allow deeper retry to prevent repeated event misses.
        if active_motion_cameras <= 1:
            if motion_area >= max(2400, int(min_area * 3.0)):
                threshold = max(0.20, threshold - 0.06)
            if motion_area >= max(7000, int(min_area * 6.0)):
                threshold = max(0.20, threshold - 0.05)
            # Prolonged single-camera no-detection streaks need a deeper retry
            # floor, or recovery keeps oscillating without event creation.
            if streak >= 20 and motion_area >= max(1300, int(min_area * 2.0)):
                threshold = max(0.22, threshold - 0.05)
            if streak >= 90 and motion_area >= max(1600, int(min_area * 2.2)):
                threshold = max(0.22, threshold - 0.04)

        if active_motion_cameras >= 4 and motion_area >= max(1600, int(min_area * 3.0)):
            threshold = max(0.16, threshold - 0.04)

        if threshold >= base:
            return None
        return float(threshold)

    @staticmethod
    def _should_hold_thermal_suppression_for_motion(
        current_area: int,
        adaptive_min_area: int,
        active_motion_cameras: int,
    ) -> bool:
        """
        Keep inference unsuppressed while motion signal remains meaningful.

        Prevents rapid suppress/unsuppress loops during genuine scene activity.
        """
        area = int(current_area)
        if area <= 0:
            return False
        adaptive_min = max(200, int(adaptive_min_area))
        if active_motion_cameras >= 4:
            hold_floor = max(560, int(adaptive_min * 0.90))
        elif active_motion_cameras >= 2:
            hold_floor = max(650, int(adaptive_min * 0.95))
        else:
            hold_floor = max(800, int(adaptive_min * 1.10))
        return area >= hold_floor

    @staticmethod
    def _thermal_suppression_rearm_seconds(active_motion_cameras: int) -> float:
        """Grace window before suppression can re-arm again."""
        if active_motion_cameras >= 4:
            return 26.0
        if active_motion_cameras >= 2:
            return 22.0
        return 16.0

    def _update_thermal_motion_peak(
        self,
        camera_id: str,
        current_area: int,
        now_ts: float,
        window_seconds: float = 6.0,
    ) -> None:
        """Track short-lived thermal area peaks to smooth single-frame dips."""
        area_map = getattr(self, "thermal_motion_peak_area", None)
        ts_map = getattr(self, "thermal_motion_peak_ts", None)
        if area_map is None or ts_map is None:
            self.thermal_motion_peak_area = defaultdict(int)
            self.thermal_motion_peak_ts = {}
            area_map = self.thermal_motion_peak_area
            ts_map = self.thermal_motion_peak_ts
        area = max(0, int(current_area))
        if area <= 0:
            return
        prev_ts = float(ts_map.get(camera_id, 0.0))
        prev_peak = int(area_map.get(camera_id, 0))
        if prev_ts <= 0.0 or (now_ts - prev_ts) > float(max(1.0, window_seconds)):
            area_map[camera_id] = area
        else:
            area_map[camera_id] = max(prev_peak, area)
        ts_map[camera_id] = float(now_ts)

    def _effective_thermal_motion_area(
        self,
        camera_id: str,
        current_area: int,
        now_ts: float,
        window_seconds: float = 6.0,
    ) -> int:
        """Blend current area with recent peak to avoid jitter-driven drops."""
        area = max(0, int(current_area))
        area_map = getattr(self, "thermal_motion_peak_area", {}) or {}
        ts_map = getattr(self, "thermal_motion_peak_ts", {}) or {}
        peak_ts = float(ts_map.get(camera_id, 0.0))
        if peak_ts <= 0.0 or (now_ts - peak_ts) > float(max(1.0, window_seconds)):
            return area
        peak = int(area_map.get(camera_id, 0))
        return max(area, int(peak * 0.85))

    def _reset_motion_buffers(self, camera_id: str, prebuffer_seconds: float) -> None:
        # Always acquire frame lock before video lock to prevent deadlock
        frame_lock = self.frame_buffer_locks[camera_id]
        video_lock = self.video_buffer_locks[camera_id]
        with frame_lock:
            with video_lock:
                buffer = self.frame_buffers.get(camera_id)
                if buffer is not None and prebuffer_seconds > 0:
                    cutoff = time.time() - prebuffer_seconds
                    trimmed = deque((item for item in buffer if item[2] >= cutoff), maxlen=buffer.maxlen)
                    self.frame_buffers[camera_id] = trimmed
                vbuffer = self.video_buffers.get(camera_id)
                if vbuffer is not None and prebuffer_seconds > 0:
                    cutoff = time.time() - prebuffer_seconds
                    trimmed = deque((item for item in vbuffer if item[1] >= cutoff), maxlen=vbuffer.maxlen)
                    self.video_buffers[camera_id] = trimmed
        self.frame_counters[camera_id] = 0
        self.detection_history[camera_id].clear()

    def _camera_snapshot(self, camera: Camera) -> SimpleNamespace:
        """Create a detached camera snapshot safe for worker threads."""
        return SimpleNamespace(
            id=camera.id,
            name=camera.name,
            type=camera.type,
            detection_source=camera.detection_source,
            rtsp_url=camera.rtsp_url,
            rtsp_url_thermal=camera.rtsp_url_thermal,
            rtsp_url_color=camera.rtsp_url_color,
            rtsp_url_detection=camera.rtsp_url_detection,
            motion_config=copy.deepcopy(camera.motion_config) if isinstance(camera.motion_config, dict) else camera.motion_config,
            zones=copy.deepcopy(camera.zones) if isinstance(camera.zones, list) else camera.zones,
            stream_roles=list(camera.stream_roles) if isinstance(camera.stream_roles, list) else camera.stream_roles,
            enabled=bool(camera.enabled),
        )

    def start_camera_detection(self, camera: Any) -> None:
        """
        Start detection thread for a camera.
        
        Args:
            camera: Camera snapshot/model instance
        """
        camera_snapshot = self._camera_snapshot(camera) if isinstance(camera, Camera) else camera
        camera_id = camera_snapshot.id

        if camera_id in self.threads:
            logger.warning(f"Detection thread already running for camera {camera_id}")
            return
        
        stop_event = threading.Event()
        self.camera_stop_events[camera_id] = stop_event
        thread = threading.Thread(
            target=self._detection_loop,
            args=(camera_snapshot, stop_event),
            daemon=True,
            name=f"detector-{camera_id}"
        )
        thread.start()
        self.threads[camera_id] = thread
        
        logger.info(f"Started detection thread for camera {camera_id}")
    
    def _detection_loop(self, camera: Any, stop_event: threading.Event) -> None:
        """
        Main detection loop for a camera.
        
        Args:
            camera: Camera snapshot/model instance
        """
        camera_id = camera.id
        cap = None
        reader_stop = stop_event
        latest_frame: Dict[str, Optional[np.ndarray]] = {"frame": None}
        frame_lock = threading.Lock()
        reader_thread: Optional[threading.Thread] = None
        
        try:
            # Get settings
            config = self.settings_service.load_config()
            last_config_refresh = time.time()

            # Initialize cooldown from last persisted event to survive restarts
            with session_scope() as db:
                latest = (
                    db.query(Event)
                    .filter(Event.camera_id == camera_id)
                    .order_by(Event.timestamp.desc())
                    .first()
                )
                if latest and latest.timestamp:
                    self.last_event_time[camera_id] = latest.timestamp.timestamp()
                    logger.info(
                        "Loaded last event time for camera %s: %s",
                        camera_id,
                        latest.timestamp.isoformat(),
                    )
            
            # Determine detection source (auto mode support)
            detection_source = get_detection_source(camera.detection_source.value)
            detection_source, restream_source, rtsp_url = self._resolve_detection_stream(
                camera,
                detection_source,
            )
            
            restream_url = self._get_go2rtc_restream_url(camera_id, restream_source)
            # Scrypted-style: only go2rtc. Ya var ya yok.
            rtsp_urls = self._get_detection_rtsp_urls(camera_id, restream_source, rtsp_url)
            if not rtsp_urls:
                logger.error(f"Camera {camera_id}: go2rtc required but not available. Enable go2rtc.")
                return
            
            logger.info(
                "Starting detection for camera %s: %s",
                camera_id,
                redact_rtsp_url(rtsp_urls[0]),
            )

            capture_backend = getattr(config.stream, "capture_backend", "auto")
            ffmpeg_proc = None
            ffmpeg_frame_shape = None
            ffmpeg_frame_size = None
            active_backend = "opencv"
            cap = None
            active_url = None

            if capture_backend in ("auto", "ffmpeg"):
                ffmpeg_proc, active_url, ffmpeg_frame_shape = self._open_ffmpeg_with_fallbacks(
                    rtsp_urls,
                    config,
                    camera_id,
                )
                if ffmpeg_proc and ffmpeg_frame_shape:
                    active_backend = "ffmpeg"
                    ffmpeg_frame_size = ffmpeg_frame_shape[0] * ffmpeg_frame_shape[1] * 3
                elif capture_backend == "ffmpeg":
                    logger.warning(
                        "FFmpeg capture failed for camera %s; falling back to OpenCV",
                        camera_id,
                    )

            if active_backend != "ffmpeg":
                # Open video capture with codec fallback
                cap, active_url = self._open_capture_with_fallbacks(rtsp_urls, config, camera_id)

                if not cap or not cap.isOpened():
                    logger.error(f"Failed to open camera {camera_id}")
                    self._update_camera_status(camera_id, CameraStatus.DOWN, None)
                    return

            logger.info("Capture backend for camera %s: %s", camera_id, active_backend)
            
            # FPS control
            target_fps = config.detection.inference_fps
            frame_delay = 1.0 / target_fps
            record_fps = float(getattr(config.event, "record_fps", target_fps))
            record_fps = max(1.0, min(record_fps, 30.0))
            reader_delay = 1.0 / record_fps
            last_inference_time = 0
            buffer_size = max(config.event.frame_buffer_size, 10)
            last_cpu_check = 0.0
            stream_log_interval = 30.0
            protocol = config.stream.protocol

            self._init_stream_stats(camera_id)
            ffmpeg_reconnect_times: deque[float] = deque(maxlen=12)

            def reader_loop() -> None:
                nonlocal cap, active_url, rtsp_urls, ffmpeg_proc, ffmpeg_frame_shape, ffmpeg_frame_size, active_backend
                failures = 0
                open_failures = 0

                def _capture_ready() -> bool:
                    if active_backend == "ffmpeg":
                        return (
                            ffmpeg_proc is not None
                            and ffmpeg_proc.poll() is None
                            and ffmpeg_frame_size
                        )
                    return cap is not None and cap.isOpened()

                def _open_capture_backend(is_reconnect: bool = False) -> bool:
                    nonlocal cap, active_url, ffmpeg_proc, ffmpeg_frame_shape, ffmpeg_frame_size, active_backend
                    if self._allows_ffmpeg_flapping_fallback(capture_backend):
                        now_ts = time.time()
                        fallback_until = float(self.ffmpeg_fallback_until.get(camera_id, 0.0))
                        reconnect_pressure = (
                            self._count_recent_reconnects(camera_id, window_seconds=300.0)
                            if is_reconnect
                            else 0
                        )
                        selected_backend = self._select_capture_backend_for_reopen(
                            current_backend=active_backend,
                            configured_backend=capture_backend,
                            fallback_until_ts=fallback_until,
                            now_ts=now_ts,
                            recent_reconnects=reconnect_pressure,
                        )
                        if selected_backend != active_backend:
                            if selected_backend == "opencv":
                                logger.warning(
                                    "Camera %s using temporary OpenCV fallback for %.0fs after ffmpeg exits",
                                    camera_id,
                                    max(0.0, fallback_until - now_ts),
                                )
                            else:
                                if fallback_until > now_ts:
                                    logger.info(
                                        "Camera %s retrying ffmpeg backend early (OpenCV reconnect pressure=%s, fallback_left=%.0fs)",
                                        camera_id,
                                        reconnect_pressure,
                                        max(0.0, fallback_until - now_ts),
                                    )
                                else:
                                    logger.info(
                                        "Camera %s retrying ffmpeg backend after fallback window",
                                        camera_id,
                                    )
                            active_backend = selected_backend

                    if active_backend == "ffmpeg":
                        ffmpeg_proc, active_url, ffmpeg_frame_shape = self._open_ffmpeg_with_fallbacks(
                            rtsp_urls,
                            config,
                            camera_id,
                            is_reconnect=is_reconnect,
                        )
                        if ffmpeg_proc and ffmpeg_frame_shape:
                            ffmpeg_frame_size = ffmpeg_frame_shape[0] * ffmpeg_frame_shape[1] * 3
                            if is_reconnect:
                                now_ts = time.time()
                                self.last_reconnect_ts[camera_id] = now_ts
                                reconnect_warmup = max(
                                    8.0,
                                    float(getattr(config.motion, "thermal_reconnect_warmup_seconds", 6.0)) + 4.0,
                                )
                                self._mark_thermal_reconnect_warmup(
                                    camera_id=camera_id,
                                    now_ts=now_ts,
                                    warmup_seconds=reconnect_warmup,
                                )
                                ffmpeg_reconnect_times.append(now_ts)
                                self._update_stream_stats(
                                    camera_id,
                                    reconnect_increment=1,
                                    last_reconnect_reason="ffmpeg_reopen",
                                )
                                if (
                                    self._allows_ffmpeg_flapping_fallback(capture_backend)
                                    and self._should_fallback_from_ffmpeg_flapping(
                                        reconnect_timestamps=list(ffmpeg_reconnect_times),
                                        now_ts=now_ts,
                                    )
                                ):
                                    logger.warning(
                                        "Camera %s ffmpeg reconnect flapping detected (mode=%s); falling back to OpenCV backend",
                                        camera_id,
                                        capture_backend,
                                    )
                                    self._stop_ffmpeg_capture(ffmpeg_proc)
                                    ffmpeg_proc = None
                                    active_backend = "opencv"
                                else:
                                    return True
                            else:
                                return True
                        if capture_backend == "auto":
                            active_backend = "opencv"
                    if active_backend == "opencv":
                        cap, active_url = self._open_capture_with_fallbacks(rtsp_urls, config, camera_id)
                        if cap is not None and cap.isOpened():
                            if is_reconnect:
                                now_ts = time.time()
                                self.last_reconnect_ts[camera_id] = now_ts
                                reconnect_warmup = max(
                                    8.0,
                                    float(getattr(config.motion, "thermal_reconnect_warmup_seconds", 6.0)) + 4.0,
                                )
                                self._mark_thermal_reconnect_warmup(
                                    camera_id=camera_id,
                                    now_ts=now_ts,
                                    warmup_seconds=reconnect_warmup,
                                )
                                logger.info("Reconnected camera %s (opencv backend)", camera_id)
                            return True
                    return False

                try:
                    while self.running and not reader_stop.is_set():
                        self._log_stream_summary(
                            camera_id=camera_id,
                            interval=stream_log_interval,
                            protocol=protocol,
                        )
                        if not _capture_ready():
                            if active_backend == "ffmpeg":
                                exit_code = ffmpeg_proc.poll() if ffmpeg_proc else None
                                if ffmpeg_proc is not None and exit_code is not None:
                                    reconnect_pressure = self._count_recent_reconnects(
                                        camera_id,
                                        window_seconds=300.0,
                                    )
                                    recent_code0_exits = self._count_recent_reconnect_reasons(
                                        camera_id,
                                        reasons={"ffmpeg_exit_0"},
                                        window_seconds=180.0,
                                    )
                                    use_fallback = self._should_use_opencv_fallback_after_ffmpeg_exit(
                                        exit_code=exit_code,
                                        recent_code0_ffmpeg_exits=recent_code0_exits,
                                        recent_reconnects=reconnect_pressure,
                                    )
                                    if (
                                        self._allows_ffmpeg_flapping_fallback(capture_backend)
                                        and use_fallback
                                    ):
                                        now_ts = time.time()
                                        fallback_seconds = self._ffmpeg_exit_opencv_fallback_seconds(
                                            exit_code,
                                            recent_reconnects=reconnect_pressure,
                                        )
                                        self.ffmpeg_fallback_until[camera_id] = max(
                                            float(self.ffmpeg_fallback_until.get(camera_id, 0.0)),
                                            now_ts + fallback_seconds,
                                        )
                                    self._update_stream_stats(
                                        camera_id,
                                        reconnect_increment=1,
                                        last_reconnect_reason=f"ffmpeg_exit_{int(exit_code)}",
                                    )
                                    error_hint = self._latest_ffmpeg_error_hint(camera_id)
                                    logger.warning(
                                        "Camera %s ffmpeg capture exited (code=%s); reopening%s",
                                        camera_id,
                                        exit_code,
                                        f" | ffmpeg: {error_hint}" if error_hint else "",
                                    )
                                    if int(exit_code) == 0 and not use_fallback:
                                        logger.info(
                                            "Camera %s ffmpeg exit code=0 appears isolated; retrying ffmpeg without OpenCV fallback",
                                            camera_id,
                                        )
                                    if int(exit_code) == 0 and use_fallback:
                                        logger.warning(
                                            "Camera %s code=0 exit repeated (recent=%s, pressure=%s); enabling temporary OpenCV fallback",
                                            camera_id,
                                            recent_code0_exits,
                                            reconnect_pressure,
                                        )
                            if not _open_capture_backend(is_reconnect=True):
                                open_failures += 1
                                if open_failures >= max(config.stream.max_reconnect_attempts, 1):
                                    logger.warning(
                                        "STREAM camera=%s reopen_failed=%s delay=%ss",
                                        camera_id,
                                        open_failures,
                                        config.stream.reconnect_delay_seconds,
                                    )
                                    open_failures = 0
                                    time.sleep(max(config.stream.reconnect_delay_seconds, 1))
                                failures = 0
                                time.sleep(1)
                                continue
                            open_failures = 0

                        try:
                            if active_backend == "ffmpeg":
                                frame = self._read_ffmpeg_frame(
                                    ffmpeg_proc,
                                    ffmpeg_frame_size,
                                    ffmpeg_frame_shape,
                                )
                                ret = frame is not None
                            else:
                                ret, frame = cap.read()

                            if not ret or frame is None:
                                failures += 1
                                self._update_stream_stats(
                                    camera_id,
                                    failed_increment=1,
                                    last_error="read_failed",
                                )
                                base_failure_threshold = max(
                                    1,
                                    int(getattr(config.stream, "read_failure_threshold", 3)),
                                )
                                base_failure_timeout = float(
                                    getattr(config.stream, "read_failure_timeout_seconds", 8.0)
                                )
                                now = time.time()
                                last_reconnect = float(self.last_reconnect_ts.get(camera_id, 0.0))
                                since_reconnect = (
                                    now - last_reconnect if last_reconnect > 0.0 else float("inf")
                                )
                                recent_reconnects = self._count_recent_reconnects(
                                    camera_id,
                                    window_seconds=300.0,
                                )
                                (
                                    failure_threshold,
                                    failure_timeout,
                                    reconnect_cooldown,
                                ) = self._stream_read_failure_policy(
                                    base_failure_threshold,
                                    base_failure_timeout,
                                    since_reconnect,
                                    recent_reconnects=recent_reconnects,
                                    detection_source=detection_source,
                                )
                                fallback_until = float(self.ffmpeg_fallback_until.get(camera_id, 0.0))
                                fallback_active = (
                                    str(active_backend).lower() == "opencv"
                                    and now < fallback_until
                                )
                                (
                                    failure_threshold,
                                    failure_timeout,
                                    reconnect_cooldown,
                                ) = self._stream_fallback_read_failure_policy(
                                    failure_threshold=failure_threshold,
                                    failure_timeout=failure_timeout,
                                    reconnect_cooldown=reconnect_cooldown,
                                    active_backend=active_backend,
                                    fallback_until_ts=fallback_until,
                                    now_ts=now,
                                    detection_source=detection_source,
                                )
                                (
                                    failure_threshold,
                                    failure_timeout,
                                    reconnect_cooldown,
                                ) = self._stream_opencv_read_failure_policy(
                                    failure_threshold=failure_threshold,
                                    failure_timeout=failure_timeout,
                                    reconnect_cooldown=reconnect_cooldown,
                                    active_backend=active_backend,
                                    recent_reconnects=recent_reconnects,
                                    detection_source=detection_source,
                                )
                                if failures >= failure_threshold:
                                    last_frame_age = self._get_last_frame_age(camera_id, now)
                                    is_stale = last_frame_age is None or last_frame_age >= failure_timeout
                                    if is_stale:
                                        reconnect_age_gate = self._stream_reconnect_age_gate(
                                            failure_timeout=failure_timeout,
                                            recent_reconnects=recent_reconnects,
                                            detection_source=detection_source,
                                            fallback_active=fallback_active,
                                            opencv_backend=str(active_backend).lower() == "opencv",
                                        )
                                        if (
                                            last_frame_age is not None
                                            and last_frame_age < reconnect_age_gate
                                        ):
                                            time.sleep(0.2)
                                            continue
                                        if now - last_reconnect < reconnect_cooldown:
                                            time.sleep(0.2)
                                            continue
                                        logger.info("Reconnecting camera %s after read failures", camera_id)
                                        if active_backend == "ffmpeg":
                                            self._stop_ffmpeg_capture(ffmpeg_proc)
                                            ffmpeg_proc = None
                                        else:
                                            try:
                                                cap.release()
                                            except Exception:
                                                pass
                                            cap = None
                                        active_url = None
                                        failures = 0
                                        self._update_stream_stats(
                                            camera_id,
                                            reconnect_increment=1,
                                            last_reconnect_reason="read_failures",
                                        )
                                        self.last_reconnect_ts[camera_id] = now
                                        if config.stream.reconnect_delay_seconds:
                                            time.sleep(config.stream.reconnect_delay_seconds)
                                time.sleep(0.2)
                                continue

                            # Optimization: Resize large frames immediately to save memory
                            # YOLO usually needs 640x640, so keeping 1080p in memory is wasteful
                            if frame.shape[1] > 1280: 
                                height = int(frame.shape[0] * 1280 / frame.shape[1])
                                frame = cv2.resize(frame, (1280, height))

                            failures = 0
                            self._update_stream_stats(
                                camera_id,
                                read_increment=1,
                                last_frame_time=time.time(),
                            )
                            with frame_lock:
                                latest_frame["frame"] = frame
                            with self.latest_frame_locks[camera_id]:
                                self.latest_frames[camera_id] = frame
                            record_fps_local = max(1.0, float(record_fps))
                            prebuffer_seconds = float(getattr(config.event, "prebuffer_seconds", 0.0))
                            postbuffer_seconds = float(getattr(config.event, "postbuffer_seconds", 0.0))
                            window_seconds = max(prebuffer_seconds + postbuffer_seconds, 1.0)
                            video_buffer_size = max(
                                int(math.ceil(window_seconds * record_fps_local)),
                                10,
                            )
                            self._update_video_buffer(
                                camera_id=camera_id,
                                frame=frame,
                                buffer_size=video_buffer_size,
                                record_interval=1.0 / record_fps_local,
                                max_age_seconds=window_seconds,
                            )

                            if reader_delay > 0:
                                time.sleep(reader_delay)

                        except Exception as e:
                            logger.error(f"Reader loop error: {e}")
                            failures += 1
                            self._update_stream_stats(
                                camera_id,
                                failed_increment=1,
                                last_error=str(e),
                            )
                            time.sleep(0.5)
                finally:
                    if ffmpeg_proc is not None:
                        self._stop_ffmpeg_capture(ffmpeg_proc)
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:
                            pass

            reader_thread = threading.Thread(
                target=reader_loop,
                daemon=True,
                name=f"reader-{camera_id}",
            )
            reader_thread.start()
            
            while self.running and not stop_event.is_set():
                current_time = time.time()
                if current_time - last_config_refresh >= 30:
                    config = self.settings_service.load_config()
                    last_config_refresh = current_time
                    record_fps = float(getattr(config.event, "record_fps", config.detection.inference_fps))
                    record_fps = max(1.0, min(record_fps, 30.0))
                    reader_delay = 1.0 / record_fps
                
                # Dynamic FPS based on CPU load (aggressive throttling to reduce CPU)
                if current_time - last_cpu_check >= 5.0:
                    try:
                        cpu_percent = psutil.cpu_percent(interval=None)
                        base_fps = config.detection.inference_fps
                        if cpu_percent > 90:
                            target_fps = max(1, base_fps - 3)
                        elif cpu_percent > 80:
                            target_fps = max(2, base_fps - 2)
                        elif cpu_percent > 65:
                            target_fps = max(2, base_fps - 1)
                        elif cpu_percent < 40:
                            target_fps = min(5, base_fps + 1)  # Cap at 5 to avoid CPU spike
                        else:
                            target_fps = base_fps
                        frame_delay = 1.0 / max(target_fps, 1)
                        record_fps = float(getattr(config.event, "record_fps", target_fps))
                        record_fps = max(1.0, min(record_fps, 30.0))
                        reader_delay = 1.0 / record_fps
                        last_cpu_check = current_time
                        try:
                            self.metrics_service.set_fps(camera_id, float(target_fps))
                            self.metrics_service.set_cpu_usage(camera_id, cpu_percent)
                        except Exception:
                            pass
                    except Exception:
                        last_cpu_check = current_time

                # FPS throttling
                if current_time - last_inference_time < frame_delay:
                    time.sleep(0.01)
                    continue
                
                last_inference_time = current_time

                with frame_lock:
                    frame = latest_frame["frame"]
                    if frame is not None:
                        frame = frame.copy()
                if frame is None:
                    self._update_camera_status(camera_id, CameraStatus.RETRYING, None)
                    time.sleep(0.2)
                    continue
                
                self._update_camera_status(camera_id, CameraStatus.CONNECTED, _utc_now_naive())

                def _log_gate(reason: str) -> None:
                    last_gate = self.last_gate_log.get(camera_id, 0.0)
                    if current_time - last_gate >= 30:
                        info_reasons = (
                            reason.startswith("no_detections")
                            or reason.startswith("temporal_consistency_failed")
                            or reason == "thermal_static_guard"
                        )
                        level = (
                            logging.INFO
                            if detection_source == "thermal" and info_reasons
                            else logging.DEBUG
                        )
                        logger.log(level, "EVENT_GATE camera=%s reason=%s", camera_id, reason)
                        self.last_gate_log[camera_id] = current_time

                frame_age = self._get_last_frame_age(camera_id, current_time)
                stale_threshold = max(
                    2.0,
                    frame_delay * 2,
                    min(5.0, max(2.5, float(getattr(config.stream, "read_failure_timeout_seconds", 8.0)) * 0.35)),
                )
                if frame_age is not None and frame_age > stale_threshold:
                    self.stale_gate_hits[camera_id] = int(self.stale_gate_hits.get(camera_id, 0)) + 1
                    if self.stale_gate_hits[camera_id] < 3:
                        time.sleep(0.1)
                        continue
                    self._update_camera_status(camera_id, CameraStatus.RETRYING, None)
                    self.event_start_time[camera_id] = None
                    _log_gate(f"stream_stale age={frame_age:.1f}s")
                    time.sleep(0.2)
                    continue
                self.stale_gate_hits[camera_id] = 0

                prebuffer_seconds = float(getattr(config.event, "prebuffer_seconds", 0.0))
                postbuffer_seconds = float(getattr(config.event, "postbuffer_seconds", 0.0))
                frame_interval = max(int(config.event.frame_interval), 1)
                sample_rate = max(config.detection.inference_fps / frame_interval, 1.0)
                min_event_window = max(4.0, float(config.event.min_event_duration))
                window_seconds = prebuffer_seconds + postbuffer_seconds + min_event_window
                buffer_size = max(
                    config.event.frame_buffer_size,
                    int(math.ceil(window_seconds * sample_rate)),
                    10,
                )

                motion_active = self._is_motion_active(camera, frame, config)
                if not motion_active:
                    self._update_frame_buffer(
                        camera_id=camera_id,
                        frame=frame,
                        detections=[],
                        frame_interval=frame_interval,
                        buffer_size=buffer_size,
                    )
                    continue

                suppression_active = False
                suppression_wakeup_candidate = False
                suppression_candidate_area = 0
                suppression_candidate_prev = 0
                suppression_candidate_ratio = 0.0
                active_motion_cameras = self._count_recent_motion_cameras(window_seconds=6.0)
                thermal_suppression_streak = int(
                    getattr(config.motion, "thermal_suppression_streak", 15)
                )
                thermal_suppression_secs = int(
                    getattr(config.motion, "thermal_suppression_duration", 30)
                )
                if detection_source == "thermal" and getattr(
                    config.motion, "thermal_suppression_enabled", True
                ):
                    (
                        thermal_suppression_streak,
                        thermal_suppression_secs,
                    ) = self._thermal_suppression_policy(
                        base_streak=thermal_suppression_streak,
                        base_duration_secs=thermal_suppression_secs,
                        active_motion_cameras=active_motion_cameras,
                    )

                # Thermal inference suppression: if YOLO returned empty N times
                # in a row, skip inference until motion area increases significantly.
                if detection_source == "thermal" and getattr(config.motion, "thermal_suppression_enabled", True):
                    wakeup_ratio = float(getattr(config.motion, "thermal_suppression_wakeup_ratio", 2.5))
                    suppression_secs = thermal_suppression_secs
                    suppressed_ts = self.suppressed_until.get(camera_id, 0.0)
                    current_area = int(self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0))
                    prev_area = int(self.last_motion_area.get(camera_id, current_area))
                    self._update_thermal_motion_peak(
                        camera_id=camera_id,
                        current_area=current_area,
                        now_ts=current_time,
                    )
                    min_wakeup_area = max(1200, int(getattr(config.motion, "min_area", 0)) * 3)
                    probe_interval_secs = self._thermal_probe_interval_seconds(
                        suppression_secs=suppression_secs,
                        active_motion_cameras=active_motion_cameras,
                    )
                    rearm_until = float(self.suppression_rearm_until.get(camera_id, 0.0))
                    if current_time < rearm_until and current_time < float(suppressed_ts):
                        self.suppressed_until.pop(camera_id, None)
                        suppressed_ts = 0.0
                    suppression_active = current_time < suppressed_ts
                    if current_time < suppressed_ts:
                        last_probe = float(self.last_suppression_probe.get(camera_id, 0.0))
                        probe_due = (current_time - last_probe) >= probe_interval_secs
                        wakeup_candidate = self._should_wakeup_thermal_suppression(
                            current_area=current_area,
                            prev_area=prev_area,
                            wakeup_ratio=wakeup_ratio,
                            min_wakeup_area=min_wakeup_area,
                        )
                        # Run inference when wakeup_candidate (area jump) OR probe_due (periodic).
                        # Previously: wakeup_candidate required probe_due, so we skipped inference
                        # when a person entered during suppression if probe_due was false.
                        if wakeup_candidate:
                            suppression_wakeup_candidate = True
                            suppression_candidate_area = current_area
                            suppression_candidate_prev = prev_area
                            suppression_candidate_ratio = (
                                float(current_area) / float(max(prev_area, 1))
                            )
                            self.last_suppression_probe[camera_id] = current_time
                        elif probe_due:
                            self.last_suppression_probe[camera_id] = current_time
                            logger.debug(
                                "DETECT camera=%s suppression_probe area=%s prev=%s",
                                camera_id,
                                current_area,
                                prev_area,
                            )
                        else:
                            self.last_motion_area[camera_id] = current_area
                            self._update_frame_buffer(
                                camera_id=camera_id,
                                frame=frame,
                                detections=[],
                                frame_interval=frame_interval,
                                buffer_size=buffer_size,
                            )
                            continue
                    self.last_motion_area[camera_id] = current_area

                # Preprocess frame
                if detection_source == "thermal" and config.thermal.enable_enhancement:
                    adaptive_clip = self._get_adaptive_clahe_clip(frame, config)
                    preprocessed = self.inference_service.preprocess_thermal(
                        frame,
                        enable_enhancement=True,
                        clahe_clip_limit=adaptive_clip,
                        clahe_tile_size=tuple(config.thermal.clahe_tile_size),
                    )
                else:
                    preprocessed = self.inference_service.preprocess_color(frame)
                
                # Run inference (with metrics)
                confidence_threshold = float(config.detection.confidence_threshold)
                thermal_recovery_conf_override: Optional[float] = None
                thermal_allclass_fallback = False
                thermal_recovery_hold_applied = False
                if detection_source == "thermal":
                    thermal_conf = float(
                        getattr(config.detection, "thermal_confidence_threshold", confidence_threshold)
                    )
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    confidence_threshold = self._thermal_confidence_policy(
                        base_confidence=thermal_conf,
                        active_motion_cameras=active_motion_cameras,
                        motion_area_now=motion_area_now,
                        base_min_area=int(getattr(config.motion, "min_area", 0)),
                    )
                t0 = time.perf_counter()
                detections_raw = self.inference_service.infer(
                    preprocessed,
                    confidence_threshold=confidence_threshold,
                    inference_resolution=tuple(config.detection.inference_resolution),
                )
                # Relaxed retry for color cameras only.
                # Thermal cameras: no fallback — the configured threshold is final.
                # Thermal fallbacks produced too many false positives in production.
                if len(detections_raw) == 0 and detection_source != "thermal":
                    relaxed_threshold = max(0.35, confidence_threshold - 0.10)
                    last_relaxed = float(self.last_relaxed_infer_time.get(camera_id, 0.0))
                    if (
                        relaxed_threshold < confidence_threshold
                        and current_time - last_relaxed >= 1.0
                    ):
                        relaxed_detections = self.inference_service.infer(
                            preprocessed,
                            confidence_threshold=relaxed_threshold,
                            inference_resolution=tuple(config.detection.inference_resolution),
                        )
                        self.last_relaxed_infer_time[camera_id] = current_time
                        if relaxed_detections:
                            detections_raw = relaxed_detections
                            logger.debug(
                                "DETECT camera=%s relaxed_threshold=%.2f recovered=%s",
                                camera_id,
                                relaxed_threshold,
                                len(relaxed_detections),
                            )
                elif (
                    len(detections_raw) == 0
                    and detection_source == "thermal"
                    and active_motion_cameras >= 2
                ):
                    # Concurrent thermal motion: allow a small, gated retry to
                    # reduce "only one camera catches" misses under contention.
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    retry_motion_gate = max(900, int(getattr(config.motion, "min_area", 0)) * 2)
                    relaxed_threshold = max(0.25, confidence_threshold - 0.05)
                    last_relaxed = float(self.last_relaxed_infer_time.get(camera_id, 0.0))
                    if (
                        motion_area_now >= retry_motion_gate
                        and relaxed_threshold < confidence_threshold
                        and current_time - last_relaxed >= 1.0
                    ):
                        relaxed_detections = self.inference_service.infer(
                            preprocessed,
                            confidence_threshold=relaxed_threshold,
                            inference_resolution=tuple(config.detection.inference_resolution),
                        )
                        self.last_relaxed_infer_time[camera_id] = current_time
                        if relaxed_detections:
                            detections_raw = relaxed_detections
                            thermal_recovery_conf_override = float(relaxed_threshold)
                            logger.debug(
                                "DETECT camera=%s thermal_relaxed_threshold=%.2f recovered=%s area=%s",
                                camera_id,
                                relaxed_threshold,
                                len(relaxed_detections),
                                motion_area_now,
                            )
                if len(detections_raw) == 0 and detection_source == "thermal":
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    deep_threshold = self._thermal_deep_recovery_threshold(
                        base_confidence=confidence_threshold,
                        motion_area_now=motion_area_now,
                        base_min_area=int(getattr(config.motion, "min_area", 0)),
                        no_detection_streak=int(self.no_detection_streak.get(camera_id, 0)) + 1,
                        active_motion_cameras=active_motion_cameras,
                    )
                    last_relaxed = float(self.last_relaxed_infer_time.get(camera_id, 0.0))
                    if (
                        deep_threshold is not None
                        and current_time - last_relaxed >= 0.8
                    ):
                        deep_recovery = self.inference_service.infer(
                            preprocessed,
                            confidence_threshold=deep_threshold,
                            inference_resolution=tuple(config.detection.inference_resolution),
                        )
                        self.last_relaxed_infer_time[camera_id] = current_time
                        if deep_recovery:
                            detections_raw = deep_recovery
                            thermal_recovery_conf_override = max(0.20, float(deep_threshold))
                            logger.info(
                                "DETECT camera=%s thermal_deep_recovery threshold=%.2f recovered=%s area=%s streak=%s",
                                camera_id,
                                deep_threshold,
                                len(deep_recovery),
                                motion_area_now,
                                int(self.no_detection_streak.get(camera_id, 0)) + 1,
                            )
                if len(detections_raw) == 0 and detection_source == "thermal":
                    # Scrypted-like recovery path: if person-only head keeps
                    # returning empty under clear thermal motion, retry with
                    # pseudo-color + all-class inference and coerce to person.
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    base_min_area = int(getattr(config.motion, "min_area", 0))
                    allclass_motion_gate = max(
                        520,
                        int(base_min_area * (1.25 if active_motion_cameras >= 2 else 1.10)),
                    )
                    no_det_streak = int(self.no_detection_streak.get(camera_id, 0)) + 1
                    if no_det_streak >= 8:
                        allclass_motion_gate = min(allclass_motion_gate, 700)
                    if no_det_streak >= 24:
                        allclass_motion_gate = min(allclass_motion_gate, 480)
                    allclass_threshold = max(
                        0.10,
                        confidence_threshold - (0.30 if active_motion_cameras >= 2 else 0.34),
                    )
                    if motion_area_now >= max(2400, int(base_min_area) * 4):
                        allclass_threshold = min(allclass_threshold, 0.16)
                    last_allclass = float(self.last_thermal_allclass_infer_time.get(camera_id, 0.0))
                    allclass_cooldown = (
                        0.35 if motion_area_now >= max(2000, int(base_min_area) * 3) else 0.55
                    )
                    if (
                        motion_area_now >= allclass_motion_gate
                        and current_time - last_allclass >= allclass_cooldown
                    ):
                        pseudo = self.inference_service.preprocess_thermal_pseudocolor(frame)
                        allclass_detections = self.inference_service.infer_all_classes(
                            pseudo,
                            confidence_threshold=allclass_threshold,
                            inference_resolution=tuple(config.detection.inference_resolution),
                        )
                        self.last_thermal_allclass_infer_time[camera_id] = current_time
                        coerced = self._coerce_allclass_to_person(allclass_detections)
                        if coerced:
                            detections_raw = coerced
                            thermal_recovery_conf_override = max(
                                0.16,
                                min(0.26, float(allclass_threshold) + 0.01),
                            )
                            thermal_allclass_fallback = True
                            logger.info(
                                "DETECT camera=%s thermal_allclass_recovery threshold=%.2f recovered=%s area=%s streak=%s",
                                camera_id,
                                allclass_threshold,
                                len(coerced),
                                motion_area_now,
                                no_det_streak,
                            )
                if (
                    len(detections_raw) > 0
                    and detection_source == "thermal"
                    and thermal_recovery_conf_override is not None
                ):
                    hold_detections = self._clone_recovery_detections(
                        detections_raw,
                        confidence_decay=0.01,
                    )
                    if hold_detections:
                        self.thermal_recovery_hold_detections[camera_id] = hold_detections
                        self.thermal_recovery_hold_until[camera_id] = current_time + float(
                            self._thermal_recovery_hold_window_seconds(active_motion_cameras)
                        )
                elif len(detections_raw) == 0 and detection_source == "thermal":
                    # Recovery detections can be sparse (every few frames) and fail
                    # temporal consistency. Reuse very recent recovery candidates for
                    # a short window while motion is still clearly active.
                    hold_until = float(self.thermal_recovery_hold_until.get(camera_id, 0.0))
                    cached_hold = self.thermal_recovery_hold_detections.get(camera_id, [])
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    base_min_area = int(getattr(config.motion, "min_area", 0))
                    hold_motion_gate = max(
                        700,
                        int(base_min_area * (1.5 if active_motion_cameras >= 2 else 1.3)),
                    )
                    if (
                        current_time <= hold_until
                        and motion_area_now >= hold_motion_gate
                        and cached_hold
                    ):
                        held = self._clone_recovery_detections(cached_hold, confidence_decay=0.03)
                        if held:
                            detections_raw = held
                            thermal_recovery_hold_applied = True
                            best_hold_conf = max(
                                (float(det.get("confidence", 0.0)) for det in held),
                                default=0.20,
                            )
                            thermal_recovery_conf_override = max(
                                0.18,
                                min(0.32, best_hold_conf),
                            )
                            last_hold_log = float(self.last_fallback_log.get(camera_id, 0.0))
                            if current_time - last_hold_log >= 6.0:
                                logger.info(
                                    "DETECT camera=%s thermal_recovery_hold reused=%s area=%s hold_for=%.2fs",
                                    camera_id,
                                    len(held),
                                    motion_area_now,
                                    max(0.0, hold_until - current_time),
                                )
                                self.last_fallback_log[camera_id] = current_time
                inference_latency = time.perf_counter() - t0
                model_name = getattr(config.detection, "model", "yolov8n-person") or "yolov8n-person"
                try:
                    self.metrics_service.record_inference_latency(
                        camera_id, model_name.replace("-person", ""), inference_latency
                    )
                except Exception:
                    pass
                
                # Filter by aspect ratio (preset or custom)
                #
                # Thermal boxes can be "blob-like" and violate strict person AR presets.
                # Use a wider default for thermal and rely on subsequent quality+temporal
                # gates to prevent fake alarms.
                if detection_source == "thermal":
                    ar_min, ar_max = (0.08, 2.50)
                else:
                    ar_min, ar_max = config.detection.get_effective_aspect_ratio_bounds()
                detections_ar = self.inference_service.filter_by_aspect_ratio(
                    detections_raw,
                    min_ratio=ar_min,
                    max_ratio=ar_max,
                )
                detections = detections_ar
                detections_after_ar = len(detections_ar)
                thermal_drop_conf = 0
                thermal_drop_area = 0
                thermal_drop_height = 0
                thermal_conf_floor = (
                    float(thermal_recovery_conf_override)
                    if thermal_recovery_conf_override is not None
                    else confidence_threshold
                )
                if detection_source == "thermal" and thermal_recovery_conf_override is None:
                    conf_relax = 0.08 if active_motion_cameras >= 2 else 0.05
                    thermal_conf_floor = min(
                        thermal_conf_floor,
                        max(0.20, confidence_threshold - conf_relax),
                    )
                thermal_min_area_ratio = 0.0015
                thermal_min_height_ratio = 0.05
                if detection_source == "thermal" and active_motion_cameras >= 2:
                    # Concurrent thermal load: keep quality gates slightly looser
                    # to reduce misses on smaller/farther person boxes.
                    thermal_min_area_ratio = 0.0012
                    thermal_min_height_ratio = 0.045
                if detection_source == "thermal" and thermal_allclass_fallback:
                    thermal_min_area_ratio = min(thermal_min_area_ratio, 0.0010)
                    thermal_min_height_ratio = min(thermal_min_height_ratio, 0.042)
                    thermal_conf_floor = min(
                        thermal_conf_floor,
                        max(0.18, confidence_threshold - 0.10),
                    )
                if detection_source == "thermal" and detections_after_ar > 0:
                    frame_h, frame_w = frame.shape[:2]
                    frame_area = float(max(frame_h * frame_w, 1))
                    # Thermal confidence tends to be lower; keep floors aligned
                    # with the actual inference thresholds to avoid dropping
                    # fallback recoveries (e.g., 0.20-0.25 conf hits).
                    min_area_ratio = thermal_min_area_ratio
                    min_height_ratio = thermal_min_height_ratio
                    conf_floor = thermal_conf_floor
                    filtered_thermal: List[Dict] = []
                    for det in detections_ar:
                        x1, y1, x2, y2 = det["bbox"]
                        w = max(0, x2 - x1)
                        h = max(0, y2 - y1)
                        area_ratio = (w * h) / frame_area
                        height_ratio = h / float(max(frame_h, 1))
                        conf = float(det.get("confidence", 0.0))
                        if conf < conf_floor:
                            thermal_drop_conf += 1
                            continue
                        if area_ratio < min_area_ratio:
                            thermal_drop_area += 1
                            continue
                        if height_ratio < min_height_ratio:
                            thermal_drop_height += 1
                            continue
                        filtered_thermal.append(det)
                    detections = filtered_thermal
                
                # Update frame buffer for media generation
                self._update_frame_buffer(
                    camera_id=camera_id,
                    frame=frame,
                    detections=detections,
                    frame_interval=frame_interval,
                    buffer_size=buffer_size,
                )

                # Update detection history
                detections_after_qual = len(detections)
                detections = self._filter_detections_by_zones(camera, detections, frame.shape)
                last_pipe_log = self.last_detection_pipeline_log.get(camera_id, 0.0)
                if current_time - last_pipe_log >= 10.0:
                    raw_best_conf = max((d.get("confidence", 0.0) for d in detections_raw), default=0.0)
                    if detection_source == "thermal":
                        logger.debug(
                            "DETECT_PIPELINE camera=%s raw=%s ar=%s qual=%s zone=%s raw_best_conf=%.2f qual_drop=conf:%s area:%s h:%s qual_floor=%.2f qual_min_area=%.4f qual_min_h=%.2f",
                            camera_id,
                            len(detections_raw),
                            detections_after_ar,
                            detections_after_qual,
                            len(detections),
                            raw_best_conf,
                            thermal_drop_conf,
                            thermal_drop_area,
                            thermal_drop_height,
                            thermal_conf_floor,
                            thermal_min_area_ratio,
                            thermal_min_height_ratio,
                        )
                    else:
                        logger.debug(
                            "DETECT_PIPELINE camera=%s raw=%s ar=%s zone=%s raw_best_conf=%.2f",
                            camera_id,
                            len(detections_raw),
                            detections_after_ar,
                            len(detections),
                            raw_best_conf,
                        )
                    self.last_detection_pipeline_log[camera_id] = current_time
                self.detection_history[camera_id].append(detections)

                # If suppression was active, lift it only after probe sees actual detections.
                if suppression_active and len(detections) > 0:
                    self.suppressed_until.pop(camera_id, None)
                    self.empty_inference_streak[camera_id] = 0
                    self.last_suppression_probe.pop(camera_id, None)
                    self.suppression_rearm_until[camera_id] = current_time + float(
                        self._thermal_suppression_rearm_seconds(active_motion_cameras)
                    )
                    if suppression_wakeup_candidate:
                        logger.info(
                            "DETECT camera=%s suppression_wakeup_confirmed area=%s prev=%s growth=%.2f detections=%s",
                            camera_id,
                            suppression_candidate_area,
                            suppression_candidate_prev,
                            suppression_candidate_ratio,
                            len(detections),
                        )
                    else:
                        logger.info(
                            "DETECT camera=%s suppression_probe_confirmed detections=%s",
                            camera_id,
                            len(detections),
                        )

                # Detection log: when person found throttle to 10s; empty every 60s (reduces log noise)
                last_log = self.last_detection_log.get(camera_id, 0.0)
                interval = 10.0 if len(detections) > 0 else 60.0
                if current_time - last_log >= interval:
                    best_conf = max((d.get("confidence", 0.0) for d in detections), default=0.0)
                    logger.debug(
                        "DETECT camera=%s count=%s best_conf=%.2f",
                        camera_id,
                        len(detections),
                        best_conf,
                    )
                    self.last_detection_log[camera_id] = current_time

                # Check if person detected
                if len(detections) == 0:
                    self.no_detection_streak[camera_id] += 1
                    if self.no_detection_streak[camera_id] <= 2:
                        _log_gate(f"no_detections_grace streak={self.no_detection_streak[camera_id]}")
                        continue
                    self.event_start_time[camera_id] = None
                    if detection_source == "thermal" and getattr(config.motion, "thermal_suppression_enabled", True):
                        streak_limit = thermal_suppression_streak
                        suppression_secs = thermal_suppression_secs
                        motion_state_now = self.motion_state.get(camera_id, {})
                        current_area = int(motion_state_now.get("thermal_motion_area_raw", 0))
                        adaptive_min_area = int(
                            motion_state_now.get(
                                "thermal_auto_min_area",
                                int(getattr(config.motion, "min_area", 0)),
                            )
                            or int(getattr(config.motion, "min_area", 0))
                        )
                        rearm_until = float(self.suppression_rearm_until.get(camera_id, 0.0))
                        if current_time < rearm_until:
                            self.empty_inference_streak[camera_id] = 0
                        else:
                            effective_area = self._effective_thermal_motion_area(
                                camera_id=camera_id,
                                current_area=current_area,
                                now_ts=current_time,
                            )
                            if self._should_hold_thermal_suppression_for_motion(
                                current_area=effective_area,
                                adaptive_min_area=adaptive_min_area,
                                active_motion_cameras=active_motion_cameras,
                            ):
                                self.empty_inference_streak[camera_id] = max(
                                    0,
                                    self.empty_inference_streak.get(camera_id, 0) - 1,
                                )
                            else:
                                self.empty_inference_streak[camera_id] = (
                                    self.empty_inference_streak.get(camera_id, 0) + 1
                                )
                                if self.empty_inference_streak[camera_id] >= streak_limit:
                                    self.suppressed_until[camera_id] = current_time + float(suppression_secs)
                                    self.empty_inference_streak[camera_id] = 0
                                    self.last_suppression_probe[camera_id] = current_time
                                    self.last_motion_area[camera_id] = current_area
                                    logger.info(
                                        "DETECT camera=%s inference_suppressed for %ds (%d consecutive empty results)",
                                        camera_id, suppression_secs, streak_limit,
                                    )
                    if detection_source == "thermal":
                        motion_area_now = int(
                            self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                        )
                        _log_gate(
                            "no_detections "
                            f"raw={len(detections_raw)} ar={detections_after_ar} "
                            f"qual={detections_after_qual} zone={len(detections)} "
                            f"conf={confidence_threshold:.2f} qual_conf={thermal_conf_floor:.2f} area={motion_area_now}"
                        )
                    else:
                        _log_gate(
                            "no_detections "
                            f"raw={len(detections_raw)} ar={detections_after_ar} zone={len(detections)} "
                            f"conf={confidence_threshold:.2f}"
                        )
                    continue
                self.no_detection_streak[camera_id] = 0
                self.empty_inference_streak[camera_id] = 0
                self.last_suppression_probe.pop(camera_id, None)

                # Check temporal consistency (only when we have detections)
                thermal_recovery_conf = 0.0
                if detection_source == "thermal":
                    (
                        temporal_min_frames,
                        temporal_max_gap,
                        thermal_recovery_conf,
                    ) = self._thermal_temporal_policy(
                        confidence_threshold=confidence_threshold,
                        active_motion_cameras=active_motion_cameras,
                    )
                else:
                    temporal_min_frames = 2
                    temporal_max_gap = 2
                temporal_pass = self.inference_service.check_temporal_consistency(
                    detections,
                    list(self.detection_history[camera_id])[:-1],  # Exclude current
                    min_consecutive_frames=temporal_min_frames,
                    max_gap_frames=temporal_max_gap,
                )
                if not temporal_pass:
                    best_conf = max((d.get("confidence", 0.0) for d in detections), default=0.0)
                    if detection_source == "thermal":
                        motion_area_now = int(
                            self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                        )
                        min_motion_mult = 2 if active_motion_cameras >= 2 else 3
                        min_motion_floor = 1200 if active_motion_cameras >= 2 else 1400
                        base_min_area = int(getattr(config.motion, "min_area", 0))
                        guard_min_area = min(max(260, base_min_area), 700)
                        if thermal_recovery_conf_override is not None:
                            # Deep recovery already requires repeated misses +
                            # strong motion; keep temporal recovery reachable
                            # even when adaptive min_area is elevated.
                            min_motion_mult = 2 if active_motion_cameras >= 2 else 1
                            min_motion_floor = 1050 if active_motion_cameras >= 2 else 950
                        min_motion_area = max(
                            min_motion_floor,
                            guard_min_area * min_motion_mult,
                        )
                        recovery_conf_gate = thermal_recovery_conf
                        if thermal_recovery_conf_override is not None:
                            recovery_conf_gate = min(
                                recovery_conf_gate,
                                max(float(thermal_recovery_conf_override) + 0.02, 0.28),
                            )
                            if motion_area_now >= max(2200, guard_min_area * 3):
                                recovery_conf_gate = min(
                                    recovery_conf_gate,
                                    max(float(thermal_recovery_conf_override) + 0.00, 0.26),
                                )
                        if best_conf >= recovery_conf_gate and motion_area_now >= min_motion_area:
                            temporal_pass = True
                            logger.debug(
                                "EVENT_GATE camera=%s reason=thermal_temporal_recovered best_conf=%.2f area=%s conf_gate=%.2f",
                                camera_id,
                                best_conf,
                                motion_area_now,
                                recovery_conf_gate,
                            )
                    else:
                        # Recovery path: allow a confident single-frame person hit
                        # after brief no-detection streaks to reduce missed walk-throughs.
                        if best_conf >= max(confidence_threshold, 0.50):
                            temporal_pass = True
                            logger.debug(
                                "EVENT_GATE camera=%s reason=temporal_recovered best_conf=%.2f",
                                camera_id,
                                best_conf,
                            )
                if not temporal_pass:
                    self.event_start_time[camera_id] = None
                    _log_gate("temporal_consistency_failed")
                    continue

                if detection_source == "thermal":
                    motion_area_now = int(
                        self.motion_state.get(camera_id, {}).get("thermal_motion_area_raw", 0)
                    )
                    frame_h, frame_w = frame.shape[:2]
                    guard_conf_threshold = confidence_threshold
                    guard_deep_recovery_mode = False
                    if thermal_recovery_conf_override is not None:
                        guard_conf_threshold = float(thermal_recovery_conf_override)
                        guard_deep_recovery_mode = True
                    detection_frames_for_guard = list(self.detection_history[camera_id])
                    allow_recovery_static_bypass = False
                    if (
                        thermal_recovery_conf_override is not None
                        and (thermal_allclass_fallback or thermal_recovery_hold_applied)
                    ):
                        base_min_area = int(getattr(config.motion, "min_area", 0))
                        recovery_frames = detection_frames_for_guard[-4:] if detection_frames_for_guard else []
                        recovery_observed = sum(
                            1
                            for frame_dets in recovery_frames
                            if any(
                                isinstance(det, dict) and det.get("bbox")
                                for det in (frame_dets or [])
                            )
                        )
                        edge_touch_ratio = self._thermal_bbox_edge_touch_ratio(
                            detection_frames=detection_frames_for_guard,
                            frame_width=frame_w,
                            frame_height=frame_h,
                            sample_frames=5,
                        )
                        best_conf_now = max(
                            (float(det.get("confidence", 0.0)) for det in detections),
                            default=0.0,
                        )
                        allow_recovery_static_bypass = (
                            recovery_observed >= 2
                            and motion_area_now >= max(1600, int(base_min_area) * 2)
                            and best_conf_now >= max(guard_conf_threshold - 0.08, 0.18)
                            and edge_touch_ratio < 0.78
                        )
                    static_guard_pass = (
                        allow_recovery_static_bypass
                        or self._passes_thermal_static_event_guard(
                            detection_frames=detection_frames_for_guard,
                            motion_area_now=motion_area_now,
                            active_motion_cameras=active_motion_cameras,
                            confidence_threshold=guard_conf_threshold,
                            base_min_area=int(getattr(config.motion, "min_area", 0)),
                            frame_width=frame_w,
                            frame_height=frame_h,
                            deep_recovery_mode=guard_deep_recovery_mode,
                        )
                    )
                    if not static_guard_pass:
                        self.event_start_time[camera_id] = None
                        _log_gate("thermal_static_guard")
                        continue

                # Enforce minimum event duration
                start_time = self.event_start_time.get(camera_id)
                if start_time is None:
                    self.event_start_time[camera_id] = current_time
                    _log_gate("event_started_waiting_min_duration")
                    continue
                if current_time - start_time < config.event.min_event_duration:
                    _log_gate(
                        f"min_duration_wait elapsed={current_time - start_time:.1f}s "
                        f"required={config.event.min_event_duration:.1f}s"
                    )
                    continue
                
                # Check event cooldown
                last_event = self.last_event_time.get(camera_id, 0)
                if current_time - last_event < config.event.cooldown_seconds:
                    _log_gate(
                        f"cooldown_active remaining={config.event.cooldown_seconds - (current_time - last_event):.1f}s"
                    )
                    continue
                
                # Create event
                self._create_event(camera, detections, config)
                self.last_event_time[camera_id] = current_time
                self.event_start_time[camera_id] = None
                
        except Exception as e:
            logger.error(f"Detection loop error for camera {camera_id}: {e}")
            self._update_camera_status(camera_id, CameraStatus.DOWN, None)
        
        finally:
            stop_event.set()
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
                logger.info(f"Released camera {camera_id}")
                self._update_camera_status(camera_id, CameraStatus.DOWN, None)
            if reader_thread:
                reader_thread.join(timeout=5)
                if reader_thread.is_alive():
                    logger.warning("Reader thread did not stop cleanly for camera %s", camera_id)
            self._cleanup_camera_state(camera_id)

    def _update_camera_status(
        self,
        camera_id: str,
        status: CameraStatus,
        last_frame_ts: Optional[datetime],
        min_interval_seconds: float = 5.0,
    ) -> None:
        now = time.time()
        last_update = self.last_status_update.get(camera_id, 0.0)
        if now - last_update < min_interval_seconds:
            return

        try:
            with session_scope() as db:
                camera = db.query(Camera).filter(Camera.id == camera_id).first()
                if not camera:
                    return

                camera.status = status
                if last_frame_ts is not None:
                    camera.last_frame_ts = last_frame_ts
                db.commit()
                self.last_status_update[camera_id] = now

                try:
                    online = db.query(Camera).filter(Camera.status == CameraStatus.CONNECTED).count()
                    retrying = db.query(Camera).filter(Camera.status == CameraStatus.RETRYING).count()
                    down = db.query(Camera).filter(Camera.status == CameraStatus.DOWN).count()
                    self.websocket_manager.broadcast_status_sync({
                        "camera_id": camera_id,
                        "status": status.value,
                        "counts": {
                            "online": online,
                            "retrying": retrying,
                            "down": down,
                        },
                    })
                except Exception as e:
                    logger.debug("Status broadcast skipped: %s", e)
        except Exception as e:
            logger.error("Failed to update camera status for %s: %s", camera_id, e)
    
    def _create_event(self, camera: Camera, detections: List[Dict], config) -> None:
        """
        Create event in database.
        
        Args:
            camera: Camera model
            detections: List of detections
            config: Application config
        """
        try:
            # Get highest confidence detection
            best_detection = max(detections, key=lambda d: d["confidence"])
            
            # Get database session
            with session_scope() as db:
                # Enforce cooldown against persisted events (handles restarts/multi-process)
                if config.event.cooldown_seconds > 0:
                    latest = (
                        db.query(Event)
                        .filter(Event.camera_id == camera.id)
                        .order_by(Event.timestamp.desc())
                        .first()
                    )
                    if latest and latest.timestamp:
                        elapsed = (_utc_now_naive() - latest.timestamp).total_seconds()
                        if elapsed < config.event.cooldown_seconds:
                            logger.info(
                                "Event suppressed by cooldown (db) camera=%s remaining=%.1fs",
                                camera.id,
                                config.event.cooldown_seconds - elapsed,
                            )
                            return

                # Create event with person count
                person_count = len(detections)
                event = self.event_service.create_event(
                    db=db,
                    camera_id=camera.id,
                    timestamp=_utc_now_naive(),
                    confidence=best_detection["confidence"],
                    event_type="person",
                    person_count=person_count,
                    summary=None,  # AI summary will be added later
                    ai_enabled=config.ai.enabled,
                    ai_reason="not_configured" if not config.ai.enabled else None,
                )
                
                logger.info(
                    "EVENT camera=%s id=%s confidence=%.2f",
                    camera.id,
                    event.id,
                    best_detection["confidence"],
                )
                try:
                    self.metrics_service.record_event(camera.id, event.event_type or "person")
                except Exception:
                    pass
                try:
                    # Don't send media URLs via WebSocket (no Ingress prefix available here)
                    # Frontend will fetch URLs from /api/events endpoint
                    self.websocket_manager.broadcast_event_sync({
                        "id": event.id,
                        "camera_id": event.camera_id,
                        "timestamp": event.timestamp.isoformat() + "Z",
                        "confidence": event.confidence,
                        "event_type": event.event_type,
                        "summary": event.summary,
                        "collage_url": None,  # Will be fetched from API
                        "gif_url": None,
                        "mp4_url": None,
                    })
                except Exception as e:
                    logger.debug("Event broadcast skipped: %s", e)

                # MQTT Publish (skip person alarm if AI confirmation required)
                try:
                    if not self._ai_requires_confirmation(config):
                        self.mqtt_service.publish_event({
                            "id": event.id,
                            "camera_id": event.camera_id,
                            "timestamp": event.timestamp.isoformat() + "Z",
                            "confidence": event.confidence,
                            "event_type": event.event_type,
                            "summary": event.summary,
                            "person_count": person_count,
                            "ai_required": False,
                            "ai_confirmed": True,
                        })
                except Exception as e:
                    logger.error("MQTT publish failed: %s", e)

                self._start_media_generation(
                    camera,
                    event.id,
                    config,
                    event_timestamp=event.timestamp,
                )
                
        except Exception as e:
            logger.error(f"Failed to create event: {e}")

    def _open_capture(self, rtsp_url: str, config, camera_id: Optional[str] = None) -> Optional[cv2.VideoCapture]:
        """
        Open video capture with timeout protection and retry logic.
        """
        cap = None
        
        def target():
            nonlocal cap
            # Set timeout options for ffmpeg backend
            # stimeout: Socket timeout in microseconds
            # timeout: Maximum time to wait for connection (microseconds)
            transport = getattr(config.stream, "protocol", "tcp")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;{transport}|stimeout;10000000|timeout;15000000|"
                "fflags;discardcorrupt|flags;low_delay|max_delay;500000|err_detect;ignore_err"
            )
            
            codec_fallbacks = [None, "H264", "H265", "MJPG"]
            if camera_id:
                cached_codec = self.codec_cache.get(camera_id)
                if cached_codec and cached_codec != "AUTO":
                    codec_fallbacks = [cached_codec] + [c for c in codec_fallbacks if c != cached_codec]
            
            for codec in codec_fallbacks:
                try:
                    temp_cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                    temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, config.stream.buffer_size)
                    
                    # Set timeouts
                    if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                        temp_cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                    if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                        temp_cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
                    
                    if codec:
                        temp_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
                    
                    if temp_cap.isOpened():
                        # Try to read a frame to verify
                        ret, _ = temp_cap.read()
                        if ret:
                            if camera_id:
                                self.codec_cache[camera_id] = codec or "AUTO"
                            if codec:
                                logger.info(f"Opened camera {camera_id} with codec {codec}")
                            else:
                                logger.info(f"Opened camera {camera_id} with default codec")
                            cap = temp_cap
                            return
                    temp_cap.release()
                except Exception as e:
                    logger.debug(f"Codec {codec} attempt failed for {camera_id}: {e}")
            
            logger.warning(f"All codec attempts failed for {camera_id}")

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()
        t.join(timeout=15)  # Increased from 5 to 15 seconds
        
        if t.is_alive():
            logger.error("Camera connection timeout after 15s: %s", redact_rtsp_url(rtsp_url))
            return None
            
        if cap and cap.isOpened():
            return cap
        
        logger.error("Failed to open camera: %s", redact_rtsp_url(rtsp_url))
        return None

    def _open_capture_with_fallbacks(
        self,
        rtsp_urls: List[str],
        config,
        camera_id: Optional[str] = None,
    ) -> Tuple[Optional[cv2.VideoCapture], Optional[str]]:
        last_url = None
        for url in rtsp_urls:
            last_url = url
            cap = self._open_capture(url, config, camera_id)
            if cap and cap.isOpened():
                if len(rtsp_urls) > 1 and url != rtsp_urls[0]:
                    logger.info(
                        "Fallback stream selected for camera %s: %s",
                        camera_id,
                        redact_rtsp_url(url),
                    )
                return cap, url
        if last_url:
            logger.error("All RTSP sources failed for camera %s", camera_id)
        return None, None

    def _probe_stream_resolution(
        self,
        rtsp_url: str,
        config,
        camera_id: Optional[str] = None,
    ) -> Optional[Tuple[int, int]]:
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            transport = getattr(config.stream, "protocol", "tcp")
            cmd = [
                ffprobe,
                "-v",
                "error",
                "-rtsp_transport",
                transport,
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                rtsp_url,
            ]
            try:
                output = subprocess.check_output(
                    cmd,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                ).decode("utf-8", errors="ignore").strip()
                if output:
                    # ffprobe may include diagnostic lines mixed with CSV output.
                    # Parse robustly by scanning lines for a valid "w,h" pair.
                    for line in reversed(output.splitlines()):
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) < 2:
                            continue
                        if not (parts[0].isdigit() and parts[1].isdigit()):
                            continue
                        width = int(parts[0])
                        height = int(parts[1])
                        if width > 0 and height > 0:
                            return width, height
            except Exception as exc:
                logger.debug(
                    "ffprobe failed for camera %s: %s",
                    camera_id or "unknown",
                    exc,
                )

        cap = self._open_capture(rtsp_url, config, camera_id)
        if cap and cap.isOpened():
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    return frame.shape[1], frame.shape[0]
            finally:
                try:
                    cap.release()
                except Exception:
                    pass
        return None

    def _open_ffmpeg_capture(
        self,
        rtsp_url: str,
        config,
        camera_id: Optional[str],
        output_size: Tuple[int, int],
        scale_output: bool,
        is_reconnect: bool = False,
    ) -> Optional[subprocess.Popen]:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.warning("ffmpeg not found; skipping ffmpeg capture for camera %s", camera_id)
            return None

        transport = getattr(config.stream, "protocol", "tcp")
        loglevel = os.getenv("FFMPEG_LOGLEVEL", "error").strip() or "error"
        frame_size = output_size[0] * output_size[1] * 3
        # Too-short RTSP timeout can turn brief upstream jitter into ffmpeg EOF.
        timeout_secs = max(
            15.0,
            float(getattr(config.stream, "read_failure_timeout_seconds", 8.0)),
        )
        timeout_us = int(timeout_secs * 1_000_000)
        input_urls = [self._append_rtsp_timeout(rtsp_url, timeout_us), rtsp_url]

        for url_idx, input_url in enumerate(input_urls):
            cmd = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                loglevel,
                "-rtsp_transport",
                transport,
                "-i",
                input_url,
                "-an",
                "-sn",
                "-dn",
            ]
            if scale_output:
                cmd.extend(["-vf", f"scale={output_size[0]}:{output_size[1]}"])
            cmd.extend(
                [
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "bgr24",
                    "-",
                ]
            )

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=frame_size * 2,
                )
            except Exception as exc:
                logger.warning("Failed to start ffmpeg capture for camera %s: %s", camera_id, exc)
                return None

            time.sleep(0.2)
            if process.poll() is not None:
                detail = ""
                if process.stderr:
                    try:
                        detail = process.stderr.read(4096).decode(errors="ignore").strip()
                    except Exception:
                        detail = ""
                if detail and url_idx == 0 and self._ffmpeg_option_unsupported(detail, "timeout"):
                    self._stop_ffmpeg_capture(process)
                    continue
                if detail:
                    logger.warning(
                        "FFmpeg exited immediately for camera %s (url=%s): %s",
                        camera_id,
                        redact_rtsp_url(rtsp_url),
                        detail,
                    )
                else:
                    logger.warning(
                        "FFmpeg exited immediately for camera %s (url=%s)",
                        camera_id,
                        redact_rtsp_url(rtsp_url),
                    )
                self._stop_ffmpeg_capture(process)
                return None

            self._start_ffmpeg_stderr_reader(process, camera_id)
            if is_reconnect:
                if camera_id:
                    self.last_reconnect_ts[camera_id] = time.time()
                    self.suppression_rearm_until[camera_id] = time.time() + 20.0
                logger.info("Reconnected camera %s (ffmpeg backend)", camera_id)
            else:
                logger.info("Opened camera %s with ffmpeg backend", camera_id)
            return process

        return None

    def _append_rtsp_timeout(self, rtsp_url: str, timeout_us: int) -> str:
        if "timeout=" in rtsp_url:
            return rtsp_url
        separator = "&" if "?" in rtsp_url else "?"
        return f"{rtsp_url}{separator}timeout={int(timeout_us)}"

    def _ffmpeg_option_unsupported(self, detail: str, option: str) -> bool:
        if not detail:
            return False
        text = detail.lower()
        opt = option.lower()
        if f"unrecognized option '{opt}'" in text or f"unrecognized option \"{opt}\"" in text:
            return True
        if "option not found" in text and opt in text:
            return True
        return False

    def _start_ffmpeg_stderr_reader(
        self,
        process: subprocess.Popen,
        camera_id: Optional[str],
    ) -> None:
        if not process.stderr or not camera_id:
            return

        def _reader() -> None:
            try:
                for raw in iter(process.stderr.readline, b""):
                    if not raw:
                        break
                    text = raw.decode(errors="ignore").strip()
                    if not text:
                        continue
                    with self.ffmpeg_error_lock:
                        self.ffmpeg_last_errors[camera_id].append(text)
            except Exception:
                return

        threading.Thread(
            target=_reader,
            daemon=True,
            name=f"ffmpeg-stderr-{camera_id}",
        ).start()

    def _open_ffmpeg_with_fallbacks(
        self,
        rtsp_urls: List[str],
        config,
        camera_id: Optional[str] = None,
        is_reconnect: bool = False,
    ) -> Tuple[Optional[subprocess.Popen], Optional[str], Optional[Tuple[int, int]]]:
        if not shutil.which("ffmpeg"):
            return None, None, None

        for url in rtsp_urls:
            scale_output = False
            cached = self.ffmpeg_frame_shapes.get(camera_id)
            if cached:
                width, height = cached
            else:
                size = self._probe_stream_resolution(url, config, camera_id)
                if size:
                    width, height = size
                    if camera_id:
                        self.ffmpeg_frame_shapes[camera_id] = (width, height)
                else:
                    width = height = 0

            if width <= 0 or height <= 0:
                if getattr(config.stream, "capture_backend", "auto") == "ffmpeg":
                    width, height = config.detection.inference_resolution
                    scale_output = True
                    logger.warning(
                        "FFmpeg capture using inference resolution %sx%s for camera %s",
                        width,
                        height,
                        camera_id,
                    )
                else:
                    continue

            process = self._open_ffmpeg_capture(
                url,
                config,
                camera_id,
                (width, height),
                scale_output,
                is_reconnect=is_reconnect,
            )
            if process:
                if len(rtsp_urls) > 1 and url != rtsp_urls[0]:
                    logger.info(
                        "FFmpeg fallback stream selected for camera %s: %s",
                        camera_id,
                        redact_rtsp_url(url),
                    )
                return process, url, (height, width)

        if rtsp_urls:
            logger.error("All RTSP sources failed for ffmpeg capture camera %s", camera_id)
        return None, None, None

    def _read_ffmpeg_frame(
        self,
        process: Optional[subprocess.Popen],
        frame_size: Optional[int],
        frame_shape: Optional[Tuple[int, int]],
    ) -> Optional[np.ndarray]:
        if process is None or process.stdout is None or not frame_size or not frame_shape:
            return None
        try:
            raw = process.stdout.read(frame_size)
        except Exception:
            return None
        if not raw or len(raw) < frame_size:
            return None
        try:
            return np.frombuffer(raw, dtype=np.uint8).reshape((frame_shape[0], frame_shape[1], 3))
        except Exception:
            return None

    def _stop_ffmpeg_capture(self, process: Optional[subprocess.Popen]) -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        try:
            if process.stdout:
                process.stdout.close()
        except Exception:
            pass
        try:
            if process.stderr:
                process.stderr.close()
        except Exception:
            pass

    def _resolve_detection_stream(
        self,
        camera: Camera,
        detection_source: str,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        # Substream for detection when set (low CPU)
        if getattr(camera, "rtsp_url_detection", None):
            return "detect", "detect", camera.rtsp_url_detection
        if detection_source == "thermal":
            if camera.rtsp_url_thermal:
                return "thermal", "thermal", camera.rtsp_url_thermal
            if camera.rtsp_url:
                return "thermal", None, camera.rtsp_url
        if detection_source == "color":
            if camera.rtsp_url_color:
                return "color", "color", camera.rtsp_url_color
            if camera.rtsp_url:
                return "color", None, camera.rtsp_url

        if camera.rtsp_url_color:
            return "color", "color", camera.rtsp_url_color
        if camera.rtsp_url_thermal:
            return "thermal", "thermal", camera.rtsp_url_thermal
        if camera.rtsp_url:
            fallback_source = "thermal" if camera.type and camera.type.value == "thermal" else "color"
            return fallback_source, None, camera.rtsp_url

        return detection_source, None, None

    def _get_detection_rtsp_urls(
        self,
        camera_id: str,
        restream_source: Optional[str],
        primary_url: Optional[str],
    ) -> List[str]:
        """Scrypted-style: only go2rtc. Ya var ya yok."""
        restream_url = self._get_go2rtc_restream_url(camera_id, restream_source)
        return [restream_url] if restream_url else []

    def _get_go2rtc_restream_url(
        self,
        camera_id: str,
        source: Optional[str] = None,
    ) -> Optional[str]:
        if not self.go2rtc_service:
            self._log_go2rtc_unavailable(camera_id)
            return None
        if not self.go2rtc_service.ensure_enabled():
            self._log_go2rtc_unavailable(camera_id)
        return self.go2rtc_service.build_restream_url(camera_id, source)

    def _log_go2rtc_unavailable(self, camera_id: str, interval: float = 30.0) -> None:
        now = time.time()
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                self._init_stream_stats(camera_id)
                stats = self.stream_stats.get(camera_id)
            if not stats:
                return
            last_log = stats.get("last_go2rtc_log", 0.0)
            if now - last_log < interval:
                return
            stats["last_go2rtc_log"] = now
        logger.warning(
            "go2rtc not available for camera %s; will keep retrying restream URL",
            camera_id,
        )

    def _get_adaptive_clahe_clip(self, frame: np.ndarray, config) -> float:
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 60:
            return max(config.thermal.clahe_clip_limit, 3.0)
        return config.thermal.clahe_clip_limit

    def _init_stream_stats(self, camera_id: str) -> None:
        with self.stream_stats_lock:
            if camera_id in self.stream_stats:
                return
            self.stream_stats[camera_id] = {
                "frames_read": 0,
                "frames_failed": 0,
                "reconnects": 0,
                "reconnect_timestamps": deque(maxlen=20),
                "reconnect_events": deque(maxlen=40),
                "last_log": 0.0,
                "last_frames_read": 0,
                "last_frames_failed": 0,
                "last_error": None,
                "last_reconnect_reason": None,
                "last_frame_time": 0.0,
                "last_go2rtc_log": 0.0,
            }

    def _update_stream_stats(
        self,
        camera_id: str,
        read_increment: int = 0,
        failed_increment: int = 0,
        reconnect_increment: int = 0,
        last_error: Optional[str] = None,
        last_reconnect_reason: Optional[str] = None,
        last_frame_time: Optional[float] = None,
    ) -> None:
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                return
            stats["frames_read"] += read_increment
            stats["frames_failed"] += failed_increment
            stats["reconnects"] += reconnect_increment
            if reconnect_increment > 0:
                reconnect_times = stats.get("reconnect_timestamps")
                if not isinstance(reconnect_times, deque):
                    reconnect_times = deque(maxlen=20)
                    stats["reconnect_timestamps"] = reconnect_times
                reconnect_events = stats.get("reconnect_events")
                if not isinstance(reconnect_events, deque):
                    reconnect_events = deque(maxlen=40)
                    stats["reconnect_events"] = reconnect_events
                reason = str(last_reconnect_reason or "reconnect")
                for _ in range(max(0, int(reconnect_increment))):
                    ts = time.time()
                    reconnect_times.append(ts)
                    reconnect_events.append((ts, reason))
            if last_error:
                stats["last_error"] = last_error
            if last_reconnect_reason:
                stats["last_reconnect_reason"] = last_reconnect_reason
            if last_frame_time is not None:
                stats["last_frame_time"] = last_frame_time

    def _count_recent_reconnects(self, camera_id: str, window_seconds: float = 300.0) -> int:
        now = time.time()
        window = max(1.0, float(window_seconds))
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                return 0
            reconnect_times = list(stats.get("reconnect_timestamps", []))
        return sum(1 for ts in reconnect_times if (now - float(ts)) <= window)

    def _count_recent_reconnect_reasons(
        self,
        camera_id: str,
        reasons: Optional[set[str]] = None,
        window_seconds: float = 300.0,
    ) -> int:
        now = time.time()
        window = max(1.0, float(window_seconds))
        allowed = {str(r) for r in reasons} if reasons else None
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                return 0
            events = list(stats.get("reconnect_events", []))
        count = 0
        for ts, reason in events:
            if (now - float(ts)) > window:
                continue
            if allowed is not None and str(reason) not in allowed:
                continue
            count += 1
        return count

    def _latest_ffmpeg_error_hint(self, camera_id: str, max_chars: int = 200) -> Optional[str]:
        with self.ffmpeg_error_lock:
            errors = list(self.ffmpeg_last_errors.get(camera_id, []))
        if not errors:
            return None
        last = str(errors[-1]).strip()
        if not last:
            return None
        compact = " ".join(last.split())
        if len(compact) <= max_chars:
            return compact
        return compact[: max(40, int(max_chars) - 3)] + "..."

    def _log_stream_summary(self, camera_id: str, interval: float, protocol: str) -> None:
        now = time.time()
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                return
            last_log = stats.get("last_log", 0.0)
            if now - last_log < interval:
                return
            frames_read = stats.get("frames_read", 0)
            frames_failed = stats.get("frames_failed", 0)
            delta_read = frames_read - stats.get("last_frames_read", 0)
            delta_failed = frames_failed - stats.get("last_frames_failed", 0)
            elapsed = max(now - last_log, 1.0)
            stats["last_log"] = now
            stats["last_frames_read"] = frames_read
            stats["last_frames_failed"] = frames_failed

        fps = delta_read / elapsed
        fail_rate = (delta_failed / max(delta_read + delta_failed, 1)) * 100
        last_error = stats.get("last_error")
        last_reconnect_reason = stats.get("last_reconnect_reason")
        logger.debug(
            "STREAM camera=%s protocol=%s fps=%.1f fail=%.1f%% read=%s failed=%s reconnects=%s last_error=%s last_reconnect=%s",
            camera_id,
            protocol,
            fps,
            fail_rate,
            frames_read,
            frames_failed,
            stats.get("reconnects", 0),
            last_error or "-",
            last_reconnect_reason or "-",
        )

    def _get_last_frame_age(self, camera_id: str, now: float) -> Optional[float]:
        with self.stream_stats_lock:
            stats = self.stream_stats.get(camera_id)
            if not stats:
                return None
            last_frame_time = stats.get("last_frame_time")
        if not last_frame_time:
            return None
        return max(0.0, now - float(last_frame_time))

    def _ai_requires_confirmation(self, config) -> bool:
        try:
            has_key = bool(config.ai.api_key) and config.ai.api_key != "***REDACTED***"
            return bool(config.ai.enabled and has_key)
        except Exception:
            return False

    def _is_ai_confirmed(self, summary: Optional[str]) -> bool:
        if not summary:
            return False
        text = summary.lower()
        # Be conservative: if both positive and negative cues appear in the
        # same response, treat it as rejected to avoid false alarms.
        if any(marker in text for marker in AI_NEGATIVE_MARKERS):
            return False
        return any(marker in text for marker in AI_POSITIVE_MARKERS)

    def _event_is_ai_confirmed(self, event: Event, ai_required: bool) -> bool:
        """Single source of truth for downstream notify/publish gating."""
        if not ai_required:
            return True
        if getattr(event, "rejected_by_ai", False):
            return False
        return self._is_ai_confirmed(getattr(event, "summary", None))

    def _is_motion_active(self, camera: Camera, frame: np.ndarray, config) -> bool:
        base_motion = config.motion.model_dump()
        camera_motion = camera.motion_config or {}
        use_global_motion = camera_motion.get("use_global") is True

        def _is_legacy_motion_defaults(cfg: dict) -> bool:
            try:
                sensitivity = int(cfg.get("sensitivity", 7))
                min_area = int(cfg.get("min_area", cfg.get("threshold", 500)))
                cooldown = int(cfg.get("cooldown_seconds", cfg.get("cooldown", 5)))
            except Exception:
                return False
            return sensitivity == 7 and min_area == 500 and cooldown == 5

        if use_global_motion or _is_legacy_motion_defaults(camera_motion):
            motion_settings = dict(base_motion)
            if "enabled" in camera_motion:
                motion_settings["enabled"] = camera_motion["enabled"]
            if "roi" in camera_motion:
                motion_settings["roi"] = camera_motion["roi"]
        else:
            motion_settings = {**base_motion, **camera_motion}

        if str(base_motion.get("mode", "auto")).lower() == "auto":
            # In global auto mode, keep camera-level enable/roi only.
            motion_settings = dict(base_motion)
            if "enabled" in camera_motion:
                motion_settings["enabled"] = camera_motion["enabled"]
            if "roi" in camera_motion:
                motion_settings["roi"] = camera_motion["roi"]

        state = self.motion_state[camera.id]
        if motion_settings.get("enabled", True) is False:
            if not state.get("motion_disabled_logged"):
                logger.info(
                    "Motion filter disabled for camera %s; running inference on all frames",
                    camera.id,
                )
                state["motion_disabled_logged"] = True
            return True
        state.pop("motion_disabled_logged", None)

        algorithm = motion_settings.get("algorithm", "mog2")
        mode = str(motion_settings.get("mode", getattr(config.motion, "mode", "auto"))).lower()
        sensitivity = int(motion_settings.get("sensitivity", config.motion.sensitivity))
        min_area = int(
            motion_settings.get("min_area", motion_settings.get("threshold", config.motion.min_area))
        )
        cooldown_seconds = int(
            motion_settings.get(
                "cooldown_seconds",
                motion_settings.get("cooldown", config.motion.cooldown_seconds),
            )
        )

        if state.get("algorithm") != algorithm:
            state.clear()
            state["algorithm"] = algorithm
        motion_active = bool(state.get("motion_active"))
        previous_motion_active = motion_active
        last_motion = state.get("last_motion", 0.0)
        now = time.time()
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # Downscale for motion detection to reduce CPU (480px width = ~44% fewer pixels than 640)
        motion_width = 480
        original_h, original_w = gray.shape[:2]
        if original_w > motion_width:
            scale = motion_width / float(original_w)
            target_h = max(1, int(original_h * scale))
            gray = cv2.resize(gray, (motion_width, target_h))
            min_area = max(1, int(min_area * scale * scale))
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        camera_type = getattr(getattr(camera, "type", None), "value", getattr(camera, "type", None))
        is_thermal_motion = (
            camera_type == "thermal"
            or str(motion_settings.get("pipeline", "")).lower() == "thermal_iir"
        )
        active_motion_cameras = self._count_recent_motion_cameras(window_seconds=6.0) if is_thermal_motion else 0
        effective_algorithm = algorithm

        thermal_floor = int(motion_settings.get("thermal_min_area_floor", 260)) if is_thermal_motion else 0
        if is_thermal_motion:
            min_area = max(min_area, max(80, thermal_floor))
            gate_warmup_seconds = float(motion_settings.get("thermal_warmup_seconds", 25.0))
            state.setdefault("thermal_motion_gate_warmup_until", now + max(5.0, gate_warmup_seconds))
            motion_area = self._motion_area_thermal_iir(
                gray=gray,
                sensitivity=sensitivity,
                min_area=max(1, min_area),
                state=state,
                motion_settings=motion_settings,
                now=now,
            )
            effective_algorithm = "thermal_iir"
        elif algorithm in ("mog2", "knn"):
            motion_area = self._motion_area_background_subtractor(camera.id, gray, algorithm, sensitivity, state)
        else:
            motion_area = self._motion_area_frame_diff(gray, sensitivity, state)

        if mode == "auto":
            profile = str(motion_settings.get("auto_profile", getattr(config.motion, "auto_profile", "normal"))).lower()
            profile_map = {
                "low": {"multiplier": 1.25, "floor_boost": 1.20, "update_mul": 1.30},
                "normal": {"multiplier": 1.00, "floor_boost": 1.00, "update_mul": 1.00},
                "high": {"multiplier": 0.80, "floor_boost": 0.85, "update_mul": 0.80},
            }
            profile_cfg = profile_map.get(profile, profile_map["normal"])
            floor = int(motion_settings.get("auto_min_area_floor", getattr(config.motion, "auto_min_area_floor", 40)))
            ceiling = int(motion_settings.get("auto_min_area_ceiling", getattr(config.motion, "auto_min_area_ceiling", 2500)))
            multiplier = float(motion_settings.get("auto_multiplier", getattr(config.motion, "auto_multiplier", 1.6)))
            multiplier *= float(profile_cfg["multiplier"])
            warmup_seconds = int(motion_settings.get("auto_warmup_seconds", getattr(config.motion, "auto_warmup_seconds", 45)))
            update_seconds = int(motion_settings.get("auto_update_seconds", getattr(config.motion, "auto_update_seconds", 10)))
            floor = max(0, floor)
            ceiling = max(floor + 1, ceiling)
            if is_thermal_motion:
                thermal_cap_default = self._thermal_auto_min_area_cap(
                    configured_ceiling=ceiling,
                    active_motion_cameras=active_motion_cameras,
                )
                thermal_ceiling = int(
                    motion_settings.get("thermal_auto_min_area_ceiling", thermal_cap_default)
                )
                ceiling = max(floor + 1, min(ceiling, thermal_ceiling))
            multiplier = max(1.0, multiplier)
            floor = int(max(0, floor * float(profile_cfg["floor_boost"])))
            update_seconds = int(max(2, update_seconds * float(profile_cfg["update_mul"])))
            state.setdefault("auto_started_at", now)
            history = state.setdefault("auto_motion_history", deque(maxlen=600))
            history.append(float(motion_area))

            recalc = False
            last_calc = float(state.get("auto_last_calc", 0.0))
            if "auto_learned_min_area" not in state:
                recalc = True
            elif now - last_calc >= max(2, update_seconds):
                recalc = True

            if recalc and len(history) >= 30:
                percentile = max(85.0, min(98.0, 84.0 + (sensitivity * 1.4)))
                noise_p = float(np.percentile(np.array(history, dtype=np.float32), percentile))
                learned = int(noise_p * multiplier)
                learned = max(floor, min(ceiling, learned))
                if is_thermal_motion:
                    prev_learned = state.get("auto_learned_min_area")
                    down_step = int(motion_settings.get("thermal_auto_min_area_step_down", 40))
                    up_step = int(motion_settings.get("thermal_auto_min_area_step_up", 120))
                    learned = self._slew_limited_auto_min_area(
                        previous_learned=prev_learned if prev_learned is not None else None,
                        learned_target=learned,
                        max_down_step=down_step,
                        max_up_step=up_step,
                    )
                state["auto_learned_min_area"] = learned
                state["auto_last_calc"] = now

            if now - float(state.get("auto_started_at", now)) < max(5, warmup_seconds):
                min_area = max(min_area, floor)
            else:
                learned = int(state.get("auto_learned_min_area", min_area))
                min_area = max(floor, min(ceiling, learned))
            if is_thermal_motion:
                min_area = max(min_area, max(80, thermal_floor))

        prebuffer_seconds = float(getattr(config.event, "prebuffer_seconds", 0.0))
        if is_thermal_motion and now < float(state.get("thermal_motion_gate_warmup_until", 0.0)):
            warmup_gate = self._thermal_warmup_motion_gate(
                min_area=min_area,
                gate_floor=700,
                gate_multiplier=1.0,
            )
            if motion_area < warmup_gate:
                motion_area = 0
        if is_thermal_motion:
            reconnect_gate_seconds = float(motion_settings.get("thermal_reconnect_warmup_seconds", 6.0))
            reconnect_gate_seconds = max(0.0, reconnect_gate_seconds)
            last_reconnect_ts = float(self.last_reconnect_ts.get(camera.id, 0.0))
            if last_reconnect_ts > 0.0 and (now - last_reconnect_ts) < reconnect_gate_seconds:
                reconnect_gate = self._thermal_warmup_motion_gate(
                    min_area=min_area,
                    gate_floor=650,
                    gate_multiplier=0.95,
                )
                if motion_area < reconnect_gate:
                    motion_area = 0
        if is_thermal_motion:
            active_factor = float(motion_settings.get("thermal_active_hysteresis", 1.08))
            idle_factor = float(motion_settings.get("thermal_idle_hysteresis", 0.92))
            active_streak_required = int(motion_settings.get("thermal_active_streak_frames", 2))
            idle_streak_required = int(motion_settings.get("thermal_idle_streak_frames", 3))
            above_streak = int(state.get("thermal_motion_above_streak", 0))
            below_streak = int(state.get("thermal_motion_below_streak", 0))
            (
                motion_detected,
                above_streak,
                below_streak,
                _,
                _,
            ) = self._thermal_motion_hysteresis_decision(
                motion_area=motion_area,
                min_area=min_area,
                motion_active=motion_active,
                above_streak=above_streak,
                below_streak=below_streak,
                active_factor=active_factor,
                idle_factor=idle_factor,
                active_streak_required=active_streak_required,
                idle_streak_required=idle_streak_required,
            )
            state["thermal_motion_above_streak"] = above_streak
            state["thermal_motion_below_streak"] = below_streak
        else:
            motion_detected = motion_area >= min_area
        if motion_detected:
            if not motion_active:
                self._reset_motion_buffers(camera.id, prebuffer_seconds)
            state["last_motion"] = now
            motion_active = True
        elif not (cooldown_seconds and now - last_motion < cooldown_seconds):
            if is_thermal_motion and motion_active and self._should_hold_thermal_motion_active(
                active_since_ts=float(state.get("motion_active_since", 0.0)),
                now_ts=now,
                min_active_seconds=float(motion_settings.get("thermal_min_active_seconds", 3.0)),
            ):
                motion_active = True
            else:
                motion_active = False

        state["motion_active"] = motion_active
        if motion_active and not previous_motion_active:
            state["motion_active_since"] = now
        elif not motion_active:
            state.pop("motion_active_since", None)

        last_logged_state = state.get("last_motion_logged_state")
        last_motion_log = state.get("last_motion_log", 0.0)
        log_interval = float(motion_settings.get("log_interval", 30.0))
        if last_logged_state is None or motion_active != last_logged_state:
            logger.info(
                "Motion filter [%s]: %s (area=%d, min=%d, sensitivity=%d, algo=%s)",
                camera.id,
                "active" if motion_active else "idle",
                motion_area,
                min_area,
                sensitivity,
                effective_algorithm,
            )
            state["last_motion_logged_state"] = motion_active
            state["last_motion_log"] = now
        elif now - last_motion_log >= log_interval:
            logger.debug(
                "Motion filter [%s]: %s (area=%d, min=%d, sensitivity=%d, algo=%s)",
                camera.id,
                "active" if motion_active else "idle",
                motion_area,
                min_area,
                sensitivity,
                effective_algorithm,
            )
            state["last_motion_log"] = now

        return motion_active

    def _motion_area_frame_diff(self, gray: np.ndarray, sensitivity: int, state: Dict[str, Any]) -> int:
        """Frame-diff motion area (original method)."""
        prev = state.get("prev_frame")
        if prev is None:
            state["prev_frame"] = gray.copy()
            return 0
        diff = cv2.absdiff(prev, gray)
        threshold = max(10, 60 - (sensitivity * 5))
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        motion_area = int(cv2.countNonZero(thresh))
        state["prev_frame"] = gray.copy()
        return motion_area

    def _motion_area_background_subtractor(
        self, camera_id: str, gray: np.ndarray, algorithm: str, sensitivity: int, state: Dict[str, Any]
    ) -> int:
        """MOG2/KNN background subtractor motion area (stable, fewer shadow false alarms)."""
        if "subtractor" not in state:
            if algorithm == "knn":
                state["subtractor"] = cv2.createBackgroundSubtractorKNN(
                    history=500, dist2Threshold=400.0, detectShadows=True
                )
            else:
                state["subtractor"] = cv2.createBackgroundSubtractorMOG2(
                    history=500, varThreshold=max(8, 24 - sensitivity * 2), detectShadows=True
                )
            state["warmup_frames"] = 0
        subtractor = state["subtractor"]
        warmup = state.get("warmup_frames", 0)
        warmup_max = 30
        if warmup < warmup_max:
            state["warmup_frames"] = warmup + 1
            subtractor.apply(gray)
            return 0
        fg_mask = subtractor.apply(gray)
        # 0=background, 127=shadow (MOG2/KNN), 255=foreground; count only foreground
        motion_area = int(np.sum(fg_mask == 255))
        return motion_area

    def _motion_area_thermal_iir(
        self,
        gray: np.ndarray,
        sensitivity: int,
        min_area: int,
        state: Dict[str, Any],
        motion_settings: Dict[str, Any],
        now: float,
    ) -> int:
        """Thermal-specific motion: drift compensation + controlled IIR + adaptive threshold."""
        gray_f = gray.astype(np.float32)
        gray_mean = float(np.mean(gray_f))
        gray_centered = gray_f - gray_mean

        bg = state.get("thermal_bg")
        noise_var = state.get("thermal_noise_var")
        warmup_seconds = float(motion_settings.get("thermal_warmup_seconds", 25.0))
        warmup_until = float(state.get("thermal_warmup_until", 0.0))
        if bg is None or noise_var is None or bg.shape != gray_centered.shape:
            state["thermal_bg"] = gray_centered.copy()
            state["thermal_noise_var"] = np.full_like(gray_centered, 16.0, dtype=np.float32)
            state["thermal_prev_gray"] = gray.copy()
            persist_window = int(motion_settings.get("thermal_persistence_window", 4))
            state["thermal_persist"] = deque(maxlen=max(3, persist_window))
            state["thermal_hold_until"] = 0.0
            state["thermal_warmup_until"] = now + max(5.0, warmup_seconds)
            return 0

        prev_gray = state.get("thermal_prev_gray")
        nuc_hold_seconds = float(motion_settings.get("thermal_nuc_hold_seconds", 2.0))
        if prev_gray is not None and prev_gray.shape == gray.shape:
            frame_jump = cv2.absdiff(prev_gray, gray)
            jump_ratio = float(np.mean(frame_jump > int(motion_settings.get("thermal_nuc_jump_threshold", 18))))
            mean_shift = abs(float(np.mean(gray)) - float(np.mean(prev_gray)))
            if jump_ratio >= float(motion_settings.get("thermal_nuc_jump_ratio", 0.70)) and mean_shift >= float(
                motion_settings.get("thermal_nuc_mean_shift", 8.0)
            ):
                state["thermal_hold_until"] = now + max(0.5, nuc_hold_seconds)
        state["thermal_prev_gray"] = gray.copy()

        alpha = float(motion_settings.get("thermal_bg_alpha", 0.985))
        beta = float(motion_settings.get("thermal_noise_beta", 0.990))
        alpha = min(0.9995, max(0.90, alpha))
        beta = min(0.9995, max(0.90, beta))

        k1_default = max(1.6, 3.0 - (sensitivity * 0.12))
        k1 = float(motion_settings.get("thermal_k1", k1_default))
        k2 = float(motion_settings.get("thermal_k2", k1 + 1.0))
        if k2 <= k1:
            k2 = k1 + 0.5
        noise_floor = float(motion_settings.get("thermal_noise_floor", 2.5))

        residual = gray_centered - bg
        sigma = np.sqrt(np.maximum(noise_var, 1.0))
        update_thresh = k1 * sigma
        detect_thresh = (k2 * sigma) + noise_floor

        abs_residual = np.abs(residual)
        update_mask = abs_residual < update_thresh
        not_update = ~update_mask

        # Controlled IIR update: freeze foreground-like pixels.
        bg[update_mask] = (alpha * bg[update_mask]) + ((1.0 - alpha) * gray_centered[update_mask])
        noise_var[update_mask] = (beta * noise_var[update_mask]) + ((1.0 - beta) * (residual[update_mask] ** 2))
        # Gentle decay for frozen pixels to avoid stale over-estimation.
        noise_var[not_update] = np.minimum(noise_var[not_update] * 1.002, 1600.0)

        raw_mask = (abs_residual > detect_thresh).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        raw_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        raw_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(raw_mask, connectivity=8)
        min_blob = max(8, int(min_area * float(motion_settings.get("thermal_min_blob_ratio", 0.12))))
        motion_area = 0
        for idx in range(1, num_labels):
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if area >= min_blob:
                motion_area += area

        persist_window = int(motion_settings.get("thermal_persistence_window", 4))
        persist_required = int(motion_settings.get("thermal_persistence_required", 3))
        persist_required = max(2, min(persist_required, max(3, persist_window)))
        persist = state.setdefault("thermal_persist", deque(maxlen=max(3, persist_window)))
        persist.append(motion_area >= min_area)
        persisted_motion = sum(1 for flag in persist if flag) >= persist_required
        hold_until = float(state.get("thermal_hold_until", 0.0))
        if now < hold_until:
            persisted_motion = False
            motion_area = 0
        if warmup_until == 0.0:
            state["thermal_warmup_until"] = now + max(5.0, warmup_seconds)
            warmup_until = float(state.get("thermal_warmup_until", 0.0))
        if now < warmup_until:
            persisted_motion = False
            motion_area = 0

        state["thermal_bg"] = bg
        state["thermal_noise_var"] = noise_var
        state["thermal_motion_persisted"] = persisted_motion
        state["thermal_motion_area_raw"] = motion_area
        return motion_area if persisted_motion else 0

    def _filter_detections_by_zones(
        self,
        camera: Camera,
        detections: List[Dict],
        frame_shape: Tuple[int, int, int],
    ) -> List[Dict]:
        zones = self._get_camera_zones(camera)
        if not zones:
            return detections

        height, width = frame_shape[:2]
        filtered = []
        for det in detections:
            if self._detection_matches_zones(det, zones, width=max(width, 1), height=max(height, 1)):
                filtered.append(det)
        return filtered

    def _get_camera_zones(self, camera: Camera) -> List[Dict[str, Any]]:
        cache = self.zone_cache[camera.id]
        now = time.time()
        if cache and now - cache.get("loaded_at", 0.0) < 30.0:
            return cache.get("zones", [])

        with session_scope() as db:
            camera_db = db.query(Camera).filter(Camera.id == camera.id).first()
            if not camera_db or not camera_db.zones:
                zones = []
            else:
                zones = [
                    {
                        "mode": zone.mode.value,
                        "polygon": zone.polygon,
                    }
                    for zone in camera_db.zones
                    if zone.enabled
                    and zone.mode.value in ("person", "both")
                    and zone.polygon
                ]
            cache["zones"] = zones
            cache["loaded_at"] = now
            return zones

    def _is_point_in_any_zone(self, x: float, y: float, zones: List[Dict[str, Any]]) -> bool:
        for zone in zones:
            if self._point_in_polygon(x, y, zone["polygon"]):
                return True
        return False

    def _detection_matches_zones(
        self,
        detection: Dict[str, Any],
        zones: List[Dict[str, Any]],
        width: int,
        height: int,
    ) -> bool:
        """Match a person bbox to zones using foot-priority + sampled overlap."""
        x1, y1, x2, y2 = detection["bbox"]
        x1 = max(0.0, min(float(x1), float(width - 1)))
        y1 = max(0.0, min(float(y1), float(height - 1)))
        x2 = max(0.0, min(float(x2), float(width - 1)))
        y2 = max(0.0, min(float(y2), float(height - 1)))
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        # Person/contact points first: catches crossings at zone boundaries.
        primary_points = [
            ((x1 + x2) * 0.5, y2),                # foot center
            (x1 + (x2 - x1) * 0.25, y2),          # left foot
            (x1 + (x2 - x1) * 0.75, y2),          # right foot
            ((x1 + x2) * 0.5, (y1 + y2) * 0.5),   # bbox center
        ]
        for px, py in primary_points:
            if self._is_point_in_any_zone(px / width, py / height, zones):
                return True

        # Fallback: coarse overlap check using 3x3 sampled points.
        inside_count = 0
        for gx in (0.2, 0.5, 0.8):
            for gy in (0.2, 0.5, 0.8):
                px = x1 + (x2 - x1) * gx
                py = y1 + (y2 - y1) * gy
                if self._is_point_in_any_zone(px / width, py / height, zones):
                    inside_count += 1
                    if inside_count >= 2:
                        return True
        return False

    def _point_in_polygon(self, x: float, y: float, polygon: List[List[float]]) -> bool:
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    def _update_frame_buffer(
        self,
        camera_id: str,
        frame: np.ndarray,
        detections: List[Dict],
        frame_interval: int,
        buffer_size: int,
    ) -> None:
        lock = self.frame_buffer_locks[camera_id]
        with lock:
            buffer = self.frame_buffers[camera_id]
            if buffer.maxlen != buffer_size:
                buffer = deque(buffer, maxlen=buffer_size)
                self.frame_buffers[camera_id] = buffer

            self.frame_counters[camera_id] += 1
            has_detection = bool(detections)
            should_sample = has_detection or self.frame_counters[camera_id] % frame_interval == 0
            if not should_sample and len(buffer) == 0:
                should_sample = True
            if not should_sample:
                return

            best_detection = max(detections, key=lambda d: d["confidence"]) if detections else None
            if best_detection:
                best_detection = {
                    **best_detection,
                    "bbox": list(best_detection["bbox"]),
                }

            buffer.append((frame.copy(), best_detection, time.time()))

    def _update_video_buffer(
        self,
        camera_id: str,
        frame: np.ndarray,
        buffer_size: int,
        record_interval: float,
        max_age_seconds: Optional[float] = None,
    ) -> None:
        if record_interval <= 0:
            return
        now = time.time()
        last_sample = self.video_last_sample.get(camera_id, 0.0)
        if now - last_sample < record_interval:
            return
        self.video_last_sample[camera_id] = now
        lock = self.video_buffer_locks[camera_id]
        with lock:
            buffer = self.video_buffers[camera_id]
            if buffer.maxlen != buffer_size:
                buffer = deque(buffer, maxlen=buffer_size)
                self.video_buffers[camera_id] = buffer
            buffer.append((frame.copy(), now))
            if max_age_seconds and max_age_seconds > 0:
                cutoff = now - max_age_seconds
                while buffer and buffer[0][1] < cutoff:
                    buffer.popleft()

    def _align_detections_to_timestamps(
        self,
        detections: List[Optional[Dict]],
        detection_timestamps: List[float],
        target_timestamps: List[float],
        max_gap_seconds: float = 0.75,
    ) -> List[Optional[Dict]]:
        if not target_timestamps:
            return []
        if not detections or not detection_timestamps:
            return [None for _ in target_timestamps]
        if len(detections) != len(detection_timestamps):
            return [None for _ in target_timestamps]
        idx = 0
        aligned: List[Optional[Dict]] = []
        for ts in target_timestamps:
            while idx + 1 < len(detection_timestamps) and detection_timestamps[idx + 1] <= ts:
                idx += 1
            candidates = [idx]
            if idx + 1 < len(detection_timestamps):
                candidates.append(idx + 1)
            best = min(candidates, key=lambda i: abs(detection_timestamps[i] - ts))
            if abs(detection_timestamps[best] - ts) <= max_gap_seconds:
                aligned.append(detections[best])
            else:
                aligned.append(None)
        return aligned

    @staticmethod
    def _has_bbox_detections(detections: List[Optional[Dict]]) -> bool:
        return any(isinstance(det, dict) and det.get("bbox") for det in detections)

    def _estimate_frame_duplicate_ratio(
        self,
        frames: List[np.ndarray],
        sample_count: int = 18,
        duplicate_threshold: float = 1.3,
    ) -> float:
        """Estimate duplicate ratio from lightweight grayscale frame diffs."""
        if len(frames) < 2:
            return 0.0
        sample_count = max(2, min(sample_count, len(frames)))
        if sample_count == 2:
            indices = [0, len(frames) - 1]
        else:
            indices = [
                int(round(i * (len(frames) - 1) / (sample_count - 1)))
                for i in range(sample_count)
            ]

        duplicate_pairs = 0
        total_pairs = 0
        prev_gray: Optional[np.ndarray] = None
        for idx in indices:
            frame = frames[idx]
            if frame is None:
                continue
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            gray = cv2.resize(gray, (96, 72), interpolation=cv2.INTER_AREA)
            if prev_gray is not None:
                diff = float(cv2.absdiff(gray, prev_gray).mean())
                total_pairs += 1
                if diff <= duplicate_threshold:
                    duplicate_pairs += 1
            prev_gray = gray

        if total_pairs == 0:
            return 0.0
        return duplicate_pairs / float(total_pairs)

    def _detect_static_phantom_event(
        self,
        frames: List[np.ndarray],
        detections: List[Optional[Dict]],
    ) -> Optional[Dict[str, float]]:
        """
        Detect clearly static phantom thermal events before expensive media/AI steps.

        Conservative gate:
        - Many sampled frames are near-identical.
        - Bounding box center barely moves.
        - Confidence is not high.
        """
        if len(frames) < 12:
            return None

        dets_with_bbox = [det for det in detections if isinstance(det, dict) and det.get("bbox")]
        if len(dets_with_bbox) < 6:
            return None

        max_conf = max(float(det.get("confidence", 0.0)) for det in dets_with_bbox)
        # Keep medium/high-confidence hits for review; only drop clearly weak ghosts.
        if max_conf >= 0.58:
            return None

        centers_x: List[float] = []
        centers_y: List[float] = []
        for det in dets_with_bbox:
            x1, y1, x2, y2 = det["bbox"]
            centers_x.append((float(x1) + float(x2)) / 2.0)
            centers_y.append((float(y1) + float(y2)) / 2.0)

        x_spread = max(centers_x) - min(centers_x) if centers_x else 9999.0
        y_spread = max(centers_y) - min(centers_y) if centers_y else 9999.0
        # True walk-throughs usually travel more than a tiny jitter window.
        if max(x_spread, y_spread) > 6.0:
            return None

        dup_ratio = self._estimate_frame_duplicate_ratio(frames)
        if dup_ratio < 0.995:
            return None

        return {
            "duplicate_ratio": dup_ratio,
            "max_conf": max_conf,
            "x_spread": x_spread,
            "y_spread": y_spread,
            "sampled_frames": float(len(frames)),
        }

    def _start_media_generation(
        self,
        camera: Camera,
        event_id: str,
        config,
        event_timestamp: Optional[datetime] = None,
    ) -> None:
        prebuffer_seconds = float(getattr(config.event, "prebuffer_seconds", 5.0))
        postbuffer_seconds = float(getattr(config.event, "postbuffer_seconds", 0.0))
        ai_required = self._ai_requires_confirmation(config)
        event_epoch_ts: Optional[float] = None
        if event_timestamp is not None:
            if event_timestamp.tzinfo is None:
                event_epoch_ts = event_timestamp.replace(tzinfo=timezone.utc).timestamp()
            else:
                event_epoch_ts = event_timestamp.astimezone(timezone.utc).timestamp()

        def _run_media() -> None:
            if postbuffer_seconds > 0:
                time.sleep(postbuffer_seconds)
            window_start_ts: Optional[float] = None
            window_end_ts: Optional[float] = None
            if event_epoch_ts is not None:
                window_start_ts = event_epoch_ts - prebuffer_seconds
                window_end_ts = event_epoch_ts + postbuffer_seconds
            frames, detections, timestamps = self._get_event_media_data(
                camera.id,
                window_start_ts=window_start_ts,
                window_end_ts=window_end_ts,
            )
            video_frames, video_timestamps = self._get_event_video_data(
                camera.id,
                window_start_ts=window_start_ts,
                window_end_ts=window_end_ts,
            )
            if len(frames) == 0:
                logger.warning(
                    "Skipping media generation for event %s (no frames)",
                    event_id,
                )
                return
            with session_scope() as db:
                if not self._has_bbox_detections(detections):
                    event = db.query(Event).filter(Event.id == event_id).first()
                    if event:
                        db.delete(event)
                        db.commit()
                    logger.warning(
                        "Deleted phantom event %s (no bbox in media window — thermal ghost)",
                        event_id,
                    )
                    return

                phantom_metrics = self._detect_static_phantom_event(frames, detections)
                if phantom_metrics:
                    event = db.query(Event).filter(Event.id == event_id).first()
                    if event:
                        db.delete(event)
                        db.commit()
                    logger.info(
                        "Deleted phantom event %s early (dup=%.1f%% conf=%.2f spread=%.1fx%.1f)",
                        event_id,
                        phantom_metrics["duplicate_ratio"] * 100.0,
                        phantom_metrics["max_conf"],
                        phantom_metrics["x_spread"],
                        phantom_metrics["y_spread"],
                    )
                    return

                mp4_frames = video_frames if video_frames else frames
                mp4_timestamps = video_timestamps if video_frames else timestamps
                mp4_detections = (
                    self._align_detections_to_timestamps(detections, timestamps, mp4_timestamps)
                    if video_frames
                    else detections
                )

                if ai_required:
                    collage_path = self.media_service.generate_collage_for_ai(
                        db=db,
                        event_id=event_id,
                        frames=frames,
                        detections=detections,
                        timestamps=timestamps,
                        camera_name=camera.name or "Camera",
                    )
                    if not collage_path:
                        return
                    event = db.query(Event).filter(Event.id == event_id).first()
                    if not event:
                        return
                    summary = asyncio.run(self.ai_service.analyze_event(
                        {
                            "id": event.id,
                            "camera_id": event.camera_id,
                            "timestamp": event.timestamp.isoformat() + "Z",
                            "confidence": event.confidence,
                        },
                        collage_path=collage_path,
                        camera={
                            "id": camera.id,
                            "name": camera.name,
                            "type": camera.type.value if camera.type else None,
                            "detection_source": get_detection_source(camera.detection_source.value),
                        },
                    ))
                    if not self._is_ai_confirmed(summary):
                        logger.info("Event %s rejected by AI, keeping for review", event_id)
                        review_collage = self.media_service.generate_collage_for_review(
                            db=db,
                            event_id=event_id,
                            frames=frames,
                            detections=detections,
                            timestamps=timestamps,
                            camera_name=camera.name or "Camera",
                        )
                        event.rejected_by_ai = True
                        event.summary = summary
                        event.collage_url = (
                            f"/api/events/{event_id}/collage"
                            if review_collage
                            else None
                        )
                        db.commit()
                        return
                    event.summary = summary
                    event.ai_enabled = True
                    event.ai_reason = None
                    event.rejected_by_ai = False
                    db.commit()

                    # Publish immediately after AI-confirmed collage decision.
                    # Video generation can continue in background.
                    try:
                        self.mqtt_service.publish_event({
                            "id": event.id,
                            "camera_id": event.camera_id,
                            "timestamp": event.timestamp.isoformat() + "Z",
                            "confidence": event.confidence,
                            "event_type": event.event_type,
                            "summary": event.summary,
                            "ai_enabled": bool(event.ai_enabled),
                            "ai_required": True,
                            "ai_confirmed": True,
                            "ai_reason": event.ai_reason,
                        }, person_detected=True)
                    except Exception as e:
                        logger.error("MQTT immediate publish failed: %s", e)

                self.media_service.generate_event_media(
                    db=db,
                    event_id=event_id,
                    frames=frames,
                    detections=detections,
                    timestamps=timestamps,
                    camera_name=camera.name or "Camera",
                    include_gif=True,
                    mp4_frames=mp4_frames,
                    mp4_detections=mp4_detections,
                    mp4_timestamps=mp4_timestamps,
                    mp4_real_time=False,  # Enable 4x speedup
                )
                event = db.query(Event).filter(Event.id == event_id).first()
                if event:
                    collage_path = self.media_service.get_media_path(event_id, "collage")
                    mp4_path = self.media_service.get_media_path(event_id, "mp4")
                    gif_path = self.media_service.get_media_path(event_id, "gif")

                    if not ai_required:
                        summary = None
                        if collage_path and config.ai.enabled:
                            detection_source = get_detection_source(camera.detection_source.value)
                            summary = asyncio.run(self.ai_service.analyze_event(
                                {
                                    "id": event.id,
                                    "camera_id": event.camera_id,
                                    "timestamp": event.timestamp.isoformat() + "Z",
                                    "confidence": event.confidence,
                                },
                                collage_path=collage_path,
                                camera={
                                    "id": camera.id,
                                    "name": camera.name,
                                    "type": camera.type.value if camera.type else None,
                                    "detection_source": detection_source,
                                },
                            ))
                        has_key = bool(config.ai.api_key) and config.ai.api_key != "***REDACTED***"
                        if summary:
                            event.summary = summary
                            event.ai_enabled = True
                            event.ai_reason = None
                        elif config.ai.enabled:
                            event.ai_enabled = bool(has_key)
                            event.ai_reason = "no_api_key" if not has_key else "analysis_failed"
                        db.commit()

                    ai_confirmed = self._event_is_ai_confirmed(event, ai_required)

                    # Re-publish to MQTT with summary and AI confirmation gate
                    if not ai_required:
                        try:
                            self.mqtt_service.publish_event({
                                "id": event.id,
                                "camera_id": event.camera_id,
                                "timestamp": event.timestamp.isoformat() + "Z",
                                "confidence": event.confidence,
                                "event_type": event.event_type,
                                "summary": event.summary,
                                "ai_enabled": bool(event.ai_enabled),
                                "ai_required": ai_required,
                                "ai_confirmed": ai_confirmed,
                                "ai_reason": event.ai_reason,
                            }, person_detected=ai_confirmed)
                        except Exception as e:
                            logger.error("MQTT update failed: %s", e)

                    if ai_confirmed:
                        try:
                            asyncio.run(
                                self.telegram_service.send_event_notification(
                                    event={
                                        "id": event.id,
                                        "camera_id": event.camera_id,
                                        "timestamp": event.timestamp.isoformat() + "Z",
                                        "confidence": event.confidence,
                                        "summary": event.summary,
                                    },
                                    camera={"id": camera.id, "name": camera.name},
                                    collage_path=collage_path,
                                    mp4_path=mp4_path,
                                    gif_path=gif_path,
                                )
                            )
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(
                                self.telegram_service.send_event_notification(
                                    event={
                                        "id": event.id,
                                        "camera_id": event.camera_id,
                                        "timestamp": event.timestamp.isoformat() + "Z",
                                        "confidence": event.confidence,
                                        "summary": event.summary,
                                    },
                                    camera={"id": camera.id, "name": camera.name},
                                    collage_path=collage_path,
                                    mp4_path=mp4_path,
                                    gif_path=gif_path,
                                )
                            )
                            loop.close()
                    else:
                        logger.info(
                            "Event %s notification suppressed (ai_rejected=%s, ai_required=%s)",
                            event.id,
                            bool(getattr(event, "rejected_by_ai", False)),
                            ai_required,
                        )
        threading.Thread(
            target=_run_media,
            daemon=True,
            name=f"media-{event_id}",
        ).start()

    def _get_event_media_data(
        self,
        camera_id: str,
        window_start_ts: Optional[float] = None,
        window_end_ts: Optional[float] = None,
    ) -> Tuple[List[np.ndarray], List[Optional[Dict]], List[float]]:
        buffer = self.frame_buffers.get(camera_id)
        if not buffer or len(buffer) == 0:
            frame = self.get_latest_frame(camera_id)
            if frame is None:
                return [], [], []
            return [frame], [None], [time.time()]

        lock = self.frame_buffer_locks[camera_id]
        with lock:
            items = list(buffer)
            selected_items = items
            if (
                window_start_ts is not None
                and window_end_ts is not None
                and window_end_ts >= window_start_ts
            ):
                selected_items = [
                    item
                    for item in items
                    if len(item) > 2 and window_start_ts <= float(item[2]) <= window_end_ts
                ]
                if not selected_items:
                    # Window miss fallback: try one-window wider before tail fallback.
                    window_span = max(float(window_end_ts - window_start_ts), 1.0)
                    wider_start = float(window_start_ts) - window_span
                    wider_end = float(window_end_ts) + window_span
                    selected_items = [
                        item
                        for item in items
                        if len(item) > 2 and wider_start <= float(item[2]) <= wider_end
                    ]
                if not selected_items:
                    # Keep most recent frames only; avoid stale, historical detections.
                    selected_items = items[-min(len(items), 80):]
                    logger.debug(
                        "EVENT_MEDIA camera=%s window_miss fallback=tail items=%s",
                        camera_id,
                        len(selected_items),
                    )

            frames = [item[0] for item in selected_items]
            detections = [item[1] for item in selected_items]
            timestamps = [item[2] for item in selected_items if len(item) > 2]
        if len(timestamps) != len(frames):
            timestamps = []
        return frames, detections, timestamps

    def _get_event_video_data(
        self,
        camera_id: str,
        window_start_ts: Optional[float] = None,
        window_end_ts: Optional[float] = None,
    ) -> Tuple[List[np.ndarray], List[float]]:
        buffer = self.video_buffers.get(camera_id)
        if not buffer or len(buffer) == 0:
            return [], []
        lock = self.video_buffer_locks[camera_id]
        with lock:
            items = list(buffer)
            selected_items = items
            if (
                window_start_ts is not None
                and window_end_ts is not None
                and window_end_ts >= window_start_ts
            ):
                selected_items = [
                    item
                    for item in items
                    if len(item) > 1 and window_start_ts <= float(item[1]) <= window_end_ts
                ]
                if not selected_items:
                    window_span = max(float(window_end_ts - window_start_ts), 1.0)
                    wider_start = float(window_start_ts) - window_span
                    wider_end = float(window_end_ts) + window_span
                    selected_items = [
                        item
                        for item in items
                        if len(item) > 1 and wider_start <= float(item[1]) <= wider_end
                    ]
                if not selected_items:
                    selected_items = items[-min(len(items), 120):]
                    logger.debug(
                        "EVENT_VIDEO camera=%s window_miss fallback=tail items=%s",
                        camera_id,
                        len(selected_items),
                    )
        frames = [item[0] for item in selected_items]
        timestamps = [item[1] for item in selected_items]
        return frames, timestamps

    def get_latest_frame(self, camera_id: str) -> Optional[np.ndarray]:
        lock = self.latest_frame_locks[camera_id]
        with lock:
            frame = self.latest_frames.get(camera_id)
            if frame is None:
                return None
            return frame.copy()


# Global singleton instance
_detector_worker: Optional[DetectorWorker] = None


def get_detector_worker() -> DetectorWorker:
    """
    Get or create the global detector worker instance.
    
    Returns:
        DetectorWorker: Global detector worker instance
    """
    global _detector_worker
    if _detector_worker is None:
        _detector_worker = DetectorWorker()
    return _detector_worker
