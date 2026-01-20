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
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Camera, Event
from app.db.session import get_session
from app.services.camera import CameraService
from app.services.events import get_event_service
from app.services.inference import get_inference_service
from app.services.settings import get_settings_service
from app.services.time_utils import get_detection_source


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
        self.settings_service = get_settings_service()
        
        # Per-camera state
        self.frame_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.detection_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))
        self.zone_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=5)))
        self.last_event_time: Dict[str, float] = {}
        
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
            
        except Exception as e:
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
            masked_url = self.camera_service.mask_rtsp_credentials(rtsp_url)
            
            logger.info(f"Starting detection for camera {camera_id}: {masked_url}")
            
            # Open video capture
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, config.stream.buffer_size)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return
            
            # FPS control
            target_fps = config.detection.inference_fps
            frame_delay = 1.0 / target_fps
            last_inference_time = 0
            
            while self.running:
                current_time = time.time()
                
                # FPS throttling
                if current_time - last_inference_time < frame_delay:
                    time.sleep(0.01)
                    continue
                
                last_inference_time = current_time
                
                # Read frame
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from camera {camera_id}")
                    time.sleep(1)
                    continue
                
                # Preprocess frame
                if detection_source == "thermal" and config.thermal.enable_enhancement:
                    preprocessed = self.inference_service.preprocess_thermal(
                        frame,
                        enable_enhancement=True,
                        clahe_clip_limit=config.thermal.clahe_clip_limit,
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
                detections = self.inference_service.filter_by_aspect_ratio(detections)
                
                # Update detection history
                self.detection_history[camera_id].append(detections)
                
                # Check temporal consistency
                if not self.inference_service.check_temporal_consistency(
                    detections,
                    list(self.detection_history[camera_id])[:-1],  # Exclude current
                    min_consecutive_frames=3,
                    max_gap_frames=1,
                ):
                    continue
                
                # Check if person detected
                if len(detections) == 0:
                    continue
                
                # Check event cooldown
                last_event = self.last_event_time.get(camera_id, 0)
                if current_time - last_event < config.event.cooldown_seconds:
                    continue
                
                # Create event
                self._create_event(camera, detections, config)
                self.last_event_time[camera_id] = current_time
                
        except Exception as e:
            logger.error(f"Detection loop error for camera {camera_id}: {e}")
        
        finally:
            if cap is not None:
                cap.release()
                logger.info(f"Released camera {camera_id}")
    
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
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to create event: {e}")


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
