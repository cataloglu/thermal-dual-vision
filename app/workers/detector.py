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
import threading
import time
import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np
import psutil
from sqlalchemy.orm import Session

from app.db.models import Camera, Event, CameraStatus
from app.db.session import get_session
from app.services.camera import CameraService
from app.services.events import get_event_service
from app.services.ai import get_ai_service
from app.services.inference import get_inference_service
from app.services.media import get_media_service
from app.services.settings import get_settings_service
from app.services.telegram import get_telegram_service
from app.services.time_utils import get_detection_source
from app.services.websocket import get_websocket_manager


logger = logging.getLogger(__name__)


class DetectorWorker:
    """
    Detection worker for person detection pipeline.
    
    Manages per-camera detection threads with YOLOv8 inference.
    """
    
    def __init__(self):
        """Initialize detector worker."""
        self.running = False
        self.threads: Dict[str, threading.Thread] = {}
        
        # Services
        self.camera_service = CameraService()
        self.inference_service = get_inference_service()
        self.event_service = get_event_service()
        self.ai_service = get_ai_service()
        self.settings_service = get_settings_service()
        self.media_service = get_media_service()
        self.websocket_manager = get_websocket_manager()
        self.telegram_service = get_telegram_service()
        
        # Per-camera state
        self.frame_buffers: Dict[str, deque] = defaultdict(deque)
        self.frame_counters: Dict[str, int] = defaultdict(int)
        self.frame_buffer_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.detection_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))
        self.zone_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=5)))
        self.last_event_time: Dict[str, float] = {}
        self.event_start_time: Dict[str, Optional[float]] = {}
        self.motion_state: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.zone_cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.last_status_update: Dict[str, float] = {}
        self.codec_cache: Dict[str, str] = {}
        
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

            # Start detection threads for enabled cameras with detect role
            db = next(get_session())
            try:
                cameras = db.query(Camera).filter(Camera.enabled.is_(True)).all()
                started = 0
                for camera in cameras:
                    if "detect" not in (camera.stream_roles or []):
                        continue
                    self.start_camera_detection(camera)
                    started += 1
                logger.info("DetectorWorker camera threads started: %s", started)
            finally:
                db.close()
            
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
        for camera_id, thread in self.threads.items():
            logger.info(f"Stopping detection thread for camera {camera_id}")
            thread.join(timeout=5)
        
        self.threads.clear()
        self.frame_buffers.clear()
        self.frame_counters.clear()
        self.frame_buffer_locks.clear()
        self.detection_history.clear()
        self.zone_history.clear()
        self.last_event_time.clear()
        self.event_start_time.clear()
        self.motion_state.clear()
        self.zone_cache.clear()
        self.last_status_update.clear()
        self.codec_cache.clear()
        logger.info("DetectorWorker stopped")
    
    def start_camera_detection(self, camera: Camera) -> None:
        """
        Start detection thread for a camera.
        
        Args:
            camera: Camera model instance
        """
        if camera.id in self.threads:
            logger.warning(f"Detection thread already running for camera {camera.id}")
            return
        
        thread = threading.Thread(
            target=self._detection_loop,
            args=(camera,),
            daemon=True,
            name=f"detector-{camera.id}"
        )
        thread.start()
        self.threads[camera.id] = thread
        
        logger.info(f"Started detection thread for camera {camera.id}")
    
    def _detection_loop(self, camera: Camera) -> None:
        """
        Main detection loop for a camera.
        
        Args:
            camera: Camera model instance
        """
        camera_id = camera.id
        cap = None
        reader_stop = threading.Event()
        latest_frame: Dict[str, Optional[np.ndarray]] = {"frame": None}
        frame_lock = threading.Lock()
        reader_thread: Optional[threading.Thread] = None
        
        try:
            # Get settings
            config = self.settings_service.load_config()
            
            # Determine detection source (auto mode support)
            detection_source = get_detection_source(camera.detection_source.value)
            
            # Get RTSP URL based on source
            if detection_source == "thermal":
                rtsp_url = camera.rtsp_url_thermal
            else:
                rtsp_url = camera.rtsp_url_color or camera.rtsp_url
            
            if not rtsp_url:
                logger.error(f"No RTSP URL for camera {camera_id}")
                return
            
            # Force TCP protocol
            rtsp_url = self.camera_service.force_tcp_protocol(rtsp_url)
            
            logger.info(f"Starting detection for camera {camera_id}: {rtsp_url}")
            
            # Open video capture with codec fallback
            cap = self._open_capture(rtsp_url, config, camera_id)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                self._update_camera_status(camera_id, CameraStatus.DOWN, None)
                return
            
            # FPS control
            target_fps = config.detection.inference_fps
            frame_delay = 1.0 / target_fps
            last_inference_time = 0
            buffer_size = max(config.event.frame_buffer_size, 10)
            last_cpu_check = 0.0

            def reader_loop() -> None:
                nonlocal cap
                failures = 0
                while self.running and not reader_stop.is_set():
                    if cap is None or not cap.isOpened():
                        cap = self._open_capture(rtsp_url, config, camera_id)
                        if cap is None or not cap.isOpened():
                            failures = 0
                            time.sleep(1)
                            continue

                    ret, frame = cap.read()
                    if not ret or frame is None:
                        failures += 1
                        if failures >= 3:
                            logger.warning("Reconnecting camera %s after read failures", camera_id)
                            try:
                                cap.release()
                            except Exception:
                                pass
                            cap = None
                            failures = 0
                        time.sleep(0.2)
                        continue

                    failures = 0
                    with frame_lock:
                        latest_frame["frame"] = frame

            reader_thread = threading.Thread(
                target=reader_loop,
                daemon=True,
                name=f"reader-{camera_id}",
            )
            reader_thread.start()
            
            while self.running:
                current_time = time.time()
                
                # Dynamic FPS based on CPU load
                if current_time - last_cpu_check >= 5.0:
                    try:
                        cpu_percent = psutil.cpu_percent(interval=None)
                        if cpu_percent > 80:
                            target_fps = max(3, config.detection.inference_fps - 2)
                        elif cpu_percent < 40:
                            target_fps = min(7, config.detection.inference_fps + 2)
                        frame_delay = 1.0 / max(target_fps, 1)
                        last_cpu_check = current_time
                    except Exception:
                        last_cpu_check = current_time

                # FPS throttling
                if current_time - last_inference_time < frame_delay:
                    time.sleep(0.01)
                    continue
                
                last_inference_time = current_time

                with frame_lock:
                    frame = latest_frame["frame"]
                if frame is None:
                    self._update_camera_status(camera_id, CameraStatus.RETRYING, None)
                    time.sleep(0.2)
                    continue
                
                self._update_camera_status(camera_id, CameraStatus.CONNECTED, datetime.utcnow())

                if not self._is_motion_active(camera, frame, config):
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
                
                # Run inference
                detections = self.inference_service.infer(
                    preprocessed,
                    confidence_threshold=config.detection.confidence_threshold,
                )
                
                # Filter by aspect ratio
                detections = self.inference_service.filter_by_aspect_ratio(
                    detections,
                    min_ratio=config.detection.aspect_ratio_min,
                    max_ratio=config.detection.aspect_ratio_max,
                )
                
                # Update frame buffer for media generation
                self._update_frame_buffer(
                    camera_id=camera_id,
                    frame=frame,
                    detections=detections,
                    frame_interval=config.event.frame_interval,
                    buffer_size=buffer_size,
                )

                # Update detection history
                detections = self._filter_detections_by_zones(camera, detections, frame.shape)
                self.detection_history[camera_id].append(detections)
                
                # Check temporal consistency
                if not self.inference_service.check_temporal_consistency(
                    detections,
                    list(self.detection_history[camera_id])[:-1],  # Exclude current
                    min_consecutive_frames=3,
                    max_gap_frames=1,
                ):
                    self.event_start_time[camera_id] = None
                    continue
                
                # Check if person detected
                if len(detections) == 0:
                    self.event_start_time[camera_id] = None
                    continue

                # Enforce minimum event duration
                start_time = self.event_start_time.get(camera_id)
                if start_time is None:
                    self.event_start_time[camera_id] = current_time
                    continue
                if current_time - start_time < config.event.min_event_duration:
                    continue
                
                # Check event cooldown
                last_event = self.last_event_time.get(camera_id, 0)
                if current_time - last_event < config.event.cooldown_seconds:
                    continue
                
                # Create event
                self._create_event(camera, detections, config)
                self.last_event_time[camera_id] = current_time
                self.event_start_time[camera_id] = None
                
        except Exception as e:
            logger.error(f"Detection loop error for camera {camera_id}: {e}")
            self._update_camera_status(camera_id, CameraStatus.DOWN, None)
        
        finally:
            reader_stop.set()
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

        db = next(get_session())
        try:
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
        finally:
            db.close()
    
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
            db = next(get_session())
            
            try:
                # Create event
                event = self.event_service.create_event(
                    db=db,
                    camera_id=camera.id,
                    timestamp=datetime.utcnow(),
                    confidence=best_detection["confidence"],
                    event_type="person",
                    summary=None,  # AI summary will be added later
                    ai_enabled=config.ai.enabled,
                    ai_reason="not_configured" if not config.ai.enabled else None,
                )
                
                logger.info(
                    f"Event created: {event.id} for camera {camera.id} "
                    f"(confidence: {best_detection['confidence']:.2f})"
                )
                try:
                    self.websocket_manager.broadcast_event_sync({
                        "id": event.id,
                        "camera_id": event.camera_id,
                        "timestamp": event.timestamp.isoformat() + "Z",
                        "confidence": event.confidence,
                        "event_type": event.event_type,
                        "summary": event.summary,
                        "collage_url": event.collage_url or f"/api/events/{event.id}/collage",
                        "gif_url": event.gif_url or f"/api/events/{event.id}/preview.gif",
                        "mp4_url": event.mp4_url or f"/api/events/{event.id}/timelapse.mp4",
                    })
                except Exception as e:
                    logger.debug("Event broadcast skipped: %s", e)
                self._start_media_generation(camera, event.id, config)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to create event: {e}")

    def _open_capture(self, rtsp_url: str, config, camera_id: Optional[str] = None) -> cv2.VideoCapture:
        codec_fallbacks = [None, "H264", "H265", "MJPG"]
        if camera_id:
            cached_codec = self.codec_cache.get(camera_id)
            if cached_codec and cached_codec != "AUTO":
                codec_fallbacks = [cached_codec] + [c for c in codec_fallbacks if c != cached_codec]
        for codec in codec_fallbacks:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, config.stream.buffer_size)
            if codec:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    if camera_id:
                        self.codec_cache[camera_id] = codec or "AUTO"
                    if codec:
                        logger.info("Opened camera with codec %s", codec)
                    else:
                        logger.info("Opened camera with default codec")
                    return cap
            cap.release()
        return cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    def _get_adaptive_clahe_clip(self, frame: np.ndarray, config) -> float:
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 60:
            return max(config.thermal.clahe_clip_limit, 3.0)
        return config.thermal.clahe_clip_limit

    def _is_motion_active(self, camera: Camera, frame: np.ndarray, config) -> bool:
        motion_settings = dict(config.motion.model_dump())
        if camera.motion_config:
            motion_settings.update(camera.motion_config)

        sensitivity = int(motion_settings.get("sensitivity", config.motion.sensitivity))
        min_area = int(motion_settings.get("min_area", config.motion.min_area))
        cooldown_seconds = int(
            motion_settings.get("cooldown_seconds", config.motion.cooldown_seconds)
        )

        state = self.motion_state[camera.id]
        last_motion = state.get("last_motion", 0.0)
        now = time.time()
        if cooldown_seconds and now - last_motion < cooldown_seconds:
            return True

        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        prev = state.get("prev_frame")
        if prev is None:
            state["prev_frame"] = gray
            return True

        diff = cv2.absdiff(prev, gray)
        threshold = max(10, 60 - (sensitivity * 5))
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        motion_area = cv2.countNonZero(thresh)
        state["prev_frame"] = gray

        if motion_area >= min_area:
            state["last_motion"] = now
            return True

        return False

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
            x1, y1, x2, y2 = det["bbox"]
            cx = (x1 + x2) / 2.0 / width
            cy = (y1 + y2) / 2.0 / height
            if self._is_point_in_any_zone(cx, cy, zones):
                filtered.append(det)
        return filtered

    def _get_camera_zones(self, camera: Camera) -> List[Dict[str, Any]]:
        cache = self.zone_cache[camera.id]
        now = time.time()
        if cache and now - cache.get("loaded_at", 0.0) < 5.0:
            return cache.get("zones", [])

        db = next(get_session())
        try:
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
        finally:
            db.close()

    def _is_point_in_any_zone(self, x: float, y: float, zones: List[Dict[str, Any]]) -> bool:
        for zone in zones:
            if self._point_in_polygon(x, y, zone["polygon"]):
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
            if self.frame_counters[camera_id] % frame_interval != 0:
                return

            best_detection = max(detections, key=lambda d: d["confidence"]) if detections else None
            if best_detection:
                best_detection = {
                    **best_detection,
                    "bbox": list(best_detection["bbox"]),
                }

            buffer.append((frame.copy(), best_detection))

    def _start_media_generation(self, camera: Camera, event_id: str, config) -> None:
        frames, detections = self._get_event_media_data(camera.id)
        if len(frames) < 10:
            logger.warning(
                "Skipping media generation for event %s (frames=%s)",
                event_id,
                len(frames),
            )
            return

        def _run_media() -> None:
            db = next(get_session())
            try:
                self.media_service.generate_event_media(
                    db=db,
                    event_id=event_id,
                    frames=frames,
                    detections=detections,
                    camera_name=camera.name or "Camera",
                )
                event = db.query(Event).filter(Event.id == event_id).first()
                if event:
                    collage_path = self.media_service.get_media_path(event_id, "collage")
                    gif_path = self.media_service.get_media_path(event_id, "gif")

                    summary = None
                    if collage_path:
                        summary = self.ai_service.analyze_event(
                            {
                                "id": event.id,
                                "camera_id": event.camera_id,
                                "timestamp": event.timestamp.isoformat() + "Z",
                                "confidence": event.confidence,
                            },
                            collage_path=collage_path,
                            camera={"id": camera.id, "name": camera.name},
                        )
                    if summary:
                        event.summary = summary
                        event.ai_enabled = True
                        event.ai_reason = None
                    elif config.ai.enabled:
                        has_key = bool(config.ai.api_key) and config.ai.api_key != "***REDACTED***"
                        event.ai_enabled = bool(has_key)
                        event.ai_reason = "no_api_key" if not has_key else "analysis_failed"
                    db.commit()

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
                                gif_path=gif_path,
                            )
                        )
                        loop.close()
            except Exception as e:
                logger.error("Failed to generate media for event %s: %s", event_id, e)
            finally:
                db.close()

        threading.Thread(
            target=_run_media,
            daemon=True,
            name=f"media-{event_id}",
        ).start()

    def _get_event_media_data(
        self, camera_id: str
    ) -> Tuple[List[np.ndarray], List[Optional[Dict]]]:
        buffer = self.frame_buffers.get(camera_id)
        if not buffer:
            return [], []

        lock = self.frame_buffer_locks[camera_id]
        with lock:
            frames = [item[0] for item in list(buffer)]
            detections = [item[1] for item in list(buffer)]
        return frames, detections


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
