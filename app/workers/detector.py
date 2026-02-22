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
        self.last_detection_log: Dict[str, float] = {}
        self.last_gate_log: Dict[str, float] = {}
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
        self.last_reconnect_ts.clear()
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
        self.last_gate_log.pop(camera_id, None)
        self.stale_gate_hits.pop(camera_id, None)
        self.last_reconnect_ts.pop(camera_id, None)
        with self.stream_stats_lock:
            self.stream_stats.pop(camera_id, None)

    def _reset_motion_buffers(self, camera_id: str, prebuffer_seconds: float) -> None:
        lock = self.frame_buffer_locks[camera_id]
        with lock:
            buffer = self.frame_buffers.get(camera_id)
            if buffer is not None and prebuffer_seconds > 0:
                cutoff = time.time() - prebuffer_seconds
                trimmed = deque((item for item in buffer if item[2] >= cutoff), maxlen=buffer.maxlen)
                self.frame_buffers[camera_id] = trimmed
        video_lock = self.video_buffer_locks[camera_id]
        with video_lock:
            buffer = self.video_buffers.get(camera_id)
            if buffer is not None and prebuffer_seconds > 0:
                cutoff = time.time() - prebuffer_seconds
                trimmed = deque((item for item in buffer if item[1] >= cutoff), maxlen=buffer.maxlen)
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
                    if active_backend == "ffmpeg":
                        ffmpeg_proc, active_url, ffmpeg_frame_shape = self._open_ffmpeg_with_fallbacks(
                            rtsp_urls,
                            config,
                            camera_id,
                            is_reconnect=is_reconnect,
                        )
                        if ffmpeg_proc and ffmpeg_frame_shape:
                            ffmpeg_frame_size = ffmpeg_frame_shape[0] * ffmpeg_frame_shape[1] * 3
                            return True
                        if capture_backend == "auto":
                            active_backend = "opencv"
                    if active_backend == "opencv":
                        cap, active_url = self._open_capture_with_fallbacks(rtsp_urls, config, camera_id)
                        if cap is not None and cap.isOpened():
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
                                failure_threshold = max(1, int(getattr(config.stream, "read_failure_threshold", 3)))
                                failure_timeout = float(getattr(config.stream, "read_failure_timeout_seconds", 8.0))
                                if failures >= failure_threshold:
                                    now = time.time()
                                    last_frame_age = self._get_last_frame_age(camera_id, now)
                                    is_stale = last_frame_age is None or last_frame_age >= failure_timeout
                                    if is_stale:
                                        reconnect_cooldown = 8.0
                                        last_reconnect = float(self.last_reconnect_ts.get(camera_id, 0.0))
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
                        logger.debug("EVENT_GATE camera=%s reason=%s", camera_id, reason)
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
                thermal_floor = float(getattr(config.detection, "thermal_confidence_threshold", confidence_threshold))
                if detection_source == "thermal":
                    confidence_threshold = max(confidence_threshold, thermal_floor)
                t0 = time.perf_counter()
                detections = self.inference_service.infer(
                    preprocessed,
                    confidence_threshold=confidence_threshold,
                    inference_resolution=tuple(config.detection.inference_resolution),
                )
                inference_latency = time.perf_counter() - t0
                model_name = getattr(config.detection, "model", "yolov8n-person") or "yolov8n-person"
                try:
                    self.metrics_service.record_inference_latency(
                        camera_id, model_name.replace("-person", ""), inference_latency
                    )
                except Exception:
                    pass
                
                # Filter by aspect ratio (preset or custom)
                ar_min, ar_max = config.detection.get_effective_aspect_ratio_bounds()
                detections = self.inference_service.filter_by_aspect_ratio(
                    detections,
                    min_ratio=ar_min,
                    max_ratio=ar_max,
                )
                
                # Update frame buffer for media generation
                self._update_frame_buffer(
                    camera_id=camera_id,
                    frame=frame,
                    detections=detections,
                    frame_interval=frame_interval,
                    buffer_size=buffer_size,
                )

                # Update detection history
                detections = self._filter_detections_by_zones(camera, detections, frame.shape)
                self.detection_history[camera_id].append(detections)

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
                    self.event_start_time[camera_id] = None
                    _log_gate("no_detections")
                    continue

                # Check temporal consistency (only when we have detections)
                # Tuned for short walk-through scenarios:
                # - require fewer consecutive frames
                # - allow small gaps
                if not self.inference_service.check_temporal_consistency(
                    detections,
                    list(self.detection_history[camera_id])[:-1],  # Exclude current
                    min_consecutive_frames=2,
                    max_gap_frames=2,
                ):
                    self.event_start_time[camera_id] = None
                    _log_gate("temporal_consistency_failed")
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

                self._start_media_generation(camera, event.id, config)
                
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
            cmd = [
                ffprobe,
                "-v",
                "error",
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
                    parts = output.split(",")
                    if len(parts) >= 2:
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
        timeout_us = int(getattr(config.stream, "read_failure_timeout_seconds", 8.0) * 1_000_000)
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
            if last_error:
                stats["last_error"] = last_error
            if last_reconnect_reason:
                stats["last_reconnect_reason"] = last_reconnect_reason
            if last_frame_time is not None:
                stats["last_frame_time"] = last_frame_time

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
        if any(marker in text for marker in AI_NEGATIVE_MARKERS):
            return False
        return any(marker in text for marker in AI_POSITIVE_MARKERS)

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

        if algorithm in ("mog2", "knn"):
            motion_area = self._motion_area_background_subtractor(
                camera.id, gray, algorithm, sensitivity, state
            )
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
                state["auto_learned_min_area"] = learned
                state["auto_last_calc"] = now

            if now - float(state.get("auto_started_at", now)) < max(5, warmup_seconds):
                min_area = max(min_area, floor)
            else:
                learned = int(state.get("auto_learned_min_area", min_area))
                min_area = max(floor, min(ceiling, learned))

        prebuffer_seconds = float(getattr(config.event, "prebuffer_seconds", 0.0))
        motion_detected = motion_area >= min_area
        if motion_detected:
            if not motion_active:
                self._reset_motion_buffers(camera.id, prebuffer_seconds)
            state["last_motion"] = now
            motion_active = True
        elif not (cooldown_seconds and now - last_motion < cooldown_seconds):
            motion_active = False

        state["motion_active"] = motion_active

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
                algorithm,
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
                algorithm,
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

    def _start_media_generation(self, camera: Camera, event_id: str, config) -> None:
        postbuffer_seconds = float(getattr(config.event, "postbuffer_seconds", 0.0))
        ai_required = self._ai_requires_confirmation(config)

        def _run_media() -> None:
            if postbuffer_seconds > 0:
                time.sleep(postbuffer_seconds)
            frames, detections, timestamps = self._get_event_media_data(camera.id)
            video_frames, video_timestamps = self._get_event_video_data(camera.id)
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
                        event.rejected_by_ai = bool(ai_required)
                        event.summary = "No person detection in media window"
                        event.ai_enabled = bool(config.ai.enabled)
                        if not event.ai_reason:
                            event.ai_reason = "no_person_detections"
                        db.commit()
                    logger.warning(
                        "Skipping media generation for event %s (no person detection in media window)",
                        event_id,
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
                        event.rejected_by_ai = True
                        event.summary = summary
                        event.collage_url = f"/api/events/{event_id}/collage"
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

                    ai_confirmed = True if not ai_required else self._is_ai_confirmed(event.summary)

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

                    try:
                        if ai_confirmed:
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
                        if ai_confirmed:
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
        threading.Thread(
            target=_run_media,
            daemon=True,
            name=f"media-{event_id}",
        ).start()

    def _get_event_media_data(
        self, camera_id: str
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
            frames = [item[0] for item in items]
            detections = [item[1] for item in items]
            timestamps = [item[2] for item in items if len(item) > 2]
        if len(timestamps) != len(frames):
            timestamps = []
        return frames, detections, timestamps

    def _get_event_video_data(
        self, camera_id: str
    ) -> Tuple[List[np.ndarray], List[float]]:
        buffer = self.video_buffers.get(camera_id)
        if not buffer or len(buffer) == 0:
            return [], []
        lock = self.video_buffer_locks[camera_id]
        with lock:
            items = list(buffer)
        frames = [item[0] for item in items]
        timestamps = [item[1] for item in items]
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
