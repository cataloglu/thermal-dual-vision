"""
Media service for Smart Motion Detector v2.

This service handles event media generation and management.
"""
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Delay before trying to replace event MP4 from recording (segment must be closed: 60s + margin)
RECORDING_MP4_DELAY_SEC = 65  # > 60s segment duration to ensure segment is fully written

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Event
from app.services.recorder import get_continuous_recorder
from app.services.settings import get_settings_service
from app.workers.media import get_media_worker
from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)

MEDIA_MAX_CONCURRENCY = max(1, int(os.getenv("MEDIA_MAX_CONCURRENCY", "2")))
_MEDIA_SEMAPHORE = threading.BoundedSemaphore(MEDIA_MAX_CONCURRENCY)


@contextmanager
def _media_slot(event_id: str):
    start_wait = time.time()
    if not _MEDIA_SEMAPHORE.acquire(blocking=False):
        logger.warning(
            "Media generation busy (%d). Waiting for slot (event=%s)",
            MEDIA_MAX_CONCURRENCY,
            event_id,
        )
        _MEDIA_SEMAPHORE.acquire()
    wait_time = time.time() - start_wait
    if wait_time >= 1.0:
        logger.info(
            "Media generation queued for %.1fs (event=%s)",
            wait_time,
            event_id,
        )
    try:
        yield
    finally:
        _MEDIA_SEMAPHORE.release()


def _replace_mp4_from_recording(
    camera_id: str,
    start_utc: datetime,
    end_utc: datetime,
    mp4_path: str,
    speed_factor: float,
) -> None:
    """Background callback: try to replace event MP4 with recording clip once segment is closed."""
    try:
        recorder = get_continuous_recorder()
        if recorder.extract_clip(camera_id, start_utc, end_utc, mp4_path, speed_factor=speed_factor):
            logger.info(
                "Event MP4 replaced from recording (delayed extract) camera=%s %s–%s",
                camera_id,
                start_utc,
                end_utc,
            )
        else:
            logger.debug(
                "Delayed recording extract had no segment for camera=%s %s–%s (keeping buffer MP4)",
                camera_id,
                start_utc,
                end_utc,
            )
    except Exception as e:
        logger.warning("Delayed recording replace failed: %s", e)


class MediaService:
    """Service for event media operations."""
    
    MEDIA_DIR = DATA_DIR / "media"
    
    def __init__(self):
        """Initialize media service."""
        self.media_worker = get_media_worker()
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    def generate_collage_for_ai(
        self,
        db: Session,
        event_id: str,
        frames: List[np.ndarray],
        detections: List[Optional[Dict]],
        timestamps: Optional[List[float]] = None,
        camera_name: str = "Camera",
    ) -> Optional[Path]:
        """Create collage for AI pre-check — no bounding boxes so AI judges independently."""
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event or len(frames) == 0:
            return None
        event_dir = self.MEDIA_DIR / event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        collage_path = str(event_dir / "collage.jpg")
        try:
            self.media_worker.create_collage(
                frames,
                None,        # No bounding boxes for AI: independent judgment
                timestamps,
                collage_path,
                camera_name,
                event.timestamp,
                event.confidence,
            )
            return Path(collage_path) if os.path.exists(collage_path) else None
        except Exception as e:
            logger.warning("Collage for AI failed: %s", e)
            return None

    def generate_event_media(
        self,
        db: Session,
        event_id: str,
        frames: List[np.ndarray],
        detections: List[Optional[Dict]],
        timestamps: Optional[List[float]] = None,
        camera_name: str = "Camera",
        include_gif: bool = False,
        mp4_frames: Optional[List[np.ndarray]] = None,
        mp4_detections: Optional[List[Optional[Dict]]] = None,
        mp4_timestamps: Optional[List[float]] = None,
        mp4_real_time: bool = False,
    ) -> Dict[str, str]:
        """
        Generate all media files for an event (collage, MP4, optional GIF).
        
        Generates files in parallel for speed.
        
        Args:
            db: Database session
            event_id: Event ID
            frames: List of event frames
            detections: List of detections (one per frame)
            timestamps: Optional list of frame timestamps (epoch seconds)
            camera_name: Camera name for overlay
            include_gif: Whether to generate preview GIF
            
        Returns:
            Dict with media URLs (collage_url, gif_url, mp4_url)
            
        Raises:
            ValueError: If event not found or insufficient frames
        """
        # Get event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        if len(frames) == 0:
            raise ValueError("Need at least 1 frame, got 0")
        
        # Create event media directory
        event_dir = self.MEDIA_DIR / event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        
        # Output paths
        collage_path = str(event_dir / "collage.jpg")
        gif_path = str(event_dir / "preview.gif")
        mp4_path = str(event_dir / "timelapse.mp4")
        
        with _media_slot(event_id):
            # MP4: prefer continuous recording, fallback to frames when recording unavailable
            mp4_from_recording = False
            speed_factor = 4.0
            prebuffer = 5.0
            postbuffer = 5.0
            # event.timestamp is naive UTC from detector
            utc_dt = event.timestamp.replace(tzinfo=timezone.utc) if event.timestamp.tzinfo is None else event.timestamp.astimezone(timezone.utc)
            event_utc = utc_dt.replace(tzinfo=None)
            start_utc = event_utc - timedelta(seconds=prebuffer)
            end_utc = event_utc + timedelta(seconds=postbuffer)
            try:
                config = get_settings_service().load_config()
                prebuffer = float(getattr(config.event, "prebuffer_seconds", 5.0))
                postbuffer = float(getattr(config.event, "postbuffer_seconds", 5.0))
                speed_factor = max(1.0, min(10.0, float(getattr(config.telegram, "video_speed", 2) or 2)))
                start_utc = event_utc - timedelta(seconds=prebuffer)
                end_utc = event_utc + timedelta(seconds=postbuffer)
                logger.debug(
                    "Event %s extract range (UTC): %s – %s (event_ts=%s)",
                    event_id, start_utc, end_utc, event.timestamp,
                )
                recorder = get_continuous_recorder()
                if recorder.extract_clip(event.camera_id, start_utc, end_utc, mp4_path, speed_factor=speed_factor):
                    mp4_from_recording = True
                    logger.info("Event %s MP4 from recording (%.1f sec @ %.1fx)", event_id, (end_utc - start_utc).total_seconds() / speed_factor, speed_factor)
                else:
                    # Recording segment may still be open; use buffer MP4, replace from recording in ~58s
                    logger.info(
                        "Event %s: segment not ready yet, using buffer MP4; will replace from recording in ~58s (range %s – %s UTC)",
                        event_id, start_utc, end_utc,
                    )
            except Exception as e:
                logger.warning("Clip from recording failed for %s (%s), using frame fallback", event_id, e)

            # When MP4 was from buffer, try to replace with recording clip once segment is closed (~60s)
            if not mp4_from_recording:
                timer = threading.Timer(
                    RECORDING_MP4_DELAY_SEC,
                    _replace_mp4_from_recording,
                    args=(event.camera_id, start_utc, end_utc, mp4_path, speed_factor),
                )
                timer.daemon = True
                timer.start()

            # Generate media in parallel (collage always; mp4 from frames if not from recording)
            mp4_source_frames = mp4_frames if mp4_frames else frames
            mp4_source_detections = mp4_detections if mp4_detections is not None else detections
            mp4_source_timestamps = mp4_timestamps if mp4_timestamps is not None else timestamps
            try:
                _config = get_settings_service().load_config()
                overlay_use_utc = getattr(_config.live, "overlay_timezone", "local") == "utc"
            except Exception:
                overlay_use_utc = False
            worker_count = 1 + (0 if mp4_from_recording else 1) + (1 if include_gif else 0)
            errors: List[Exception] = []
            with ThreadPoolExecutor(max_workers=max(1, worker_count)) as executor:
                tasks: List[tuple] = [
                    ("collage", executor.submit(
                        self.media_worker.create_collage,
                        frames,
                        detections,
                        timestamps,
                        collage_path,
                        camera_name,
                        event.timestamp,
                        event.confidence,
                    )),
                ]
                if not mp4_from_recording:
                    tasks.append((
                        "mp4",
                        executor.submit(
                            self.media_worker.create_timelapse_mp4,
                            mp4_source_frames,
                            mp4_source_detections,
                            mp4_path,
                            camera_name,
                            event.timestamp,
                            mp4_source_timestamps,
                            mp4_real_time,
                            speed_factor,
                            overlay_use_utc,
                        ),
                    ))
                if include_gif:
                    tasks.append((
                        "gif",
                        executor.submit(
                            self.media_worker.create_timeline_gif,
                            frames,
                            gif_path,
                            camera_name,
                            event.timestamp,
                        ),
                    ))
                for label, future in tasks:
                    try:
                        future.result()
                    except Exception as exc:
                        logger.warning("Failed to generate %s for event %s: %s", label, event_id, exc, exc_info=True)
                        if label == "collage":
                            errors.append(exc)
                        elif label == "mp4" and not mp4_from_recording:
                            # Fallback: create minimal MP4 from first frame (ensure video always exists)
                            try:
                                first = mp4_source_frames[0]
                                if first is not None and hasattr(first, "shape") and len(first.shape) >= 2:
                                    dup_count = 30  # ~3s at 10fps
                                    if mp4_source_timestamps and len(mp4_source_timestamps) > 1:
                                        span = mp4_source_timestamps[-1] - mp4_source_timestamps[0]
                                        dup_count = max(15, min(120, int(10 * span)))
                                    self.media_worker.create_minimal_mp4(
                                        [first] * dup_count,
                                        mp4_path,
                                        camera_name,
                                        event.timestamp,
                                    )
                                    logger.info("Event %s: MP4 fallback (minimal) created", event_id)
                            except Exception as fallback_exc:
                                logger.warning("MP4 fallback also failed for %s: %s", event_id, fallback_exc)
            if errors:
                raise errors[0]
            
            # Save URLs to database WITHOUT prefix (prefix added at runtime in main.py)
            event.collage_url = f"/api/events/{event_id}/collage" if os.path.exists(collage_path) else None
            event.gif_url = f"/api/events/{event_id}/preview.gif" if os.path.exists(gif_path) else None
            # MP4: dosya varsa URL ver (.legacy = OpenCV fallback kullanıldı, yine de oynatılabilir)
            mp4_ok = os.path.exists(mp4_path)
            event.mp4_url = f"/api/events/{event_id}/timelapse.mp4" if mp4_ok else None
            if not mp4_ok and event.collage_url:
                logger.warning("Event %s: collage exists but MP4 missing (create_timelapse_mp4 or fallback failed)", event_id)
            db.commit()
            
            logger.info(f"Event media generated: {event_id}")
            
            return {
                "collage_url": event.collage_url,
                "gif_url": event.gif_url,
                "mp4_url": event.mp4_url,
            }
    
    def validate_id(self, id_str: str) -> bool:
        """Validate ID to prevent path traversal."""
        # Allow alphanumeric and hyphens
        if not re.match(r'^[a-zA-Z0-9-]+$', id_str):
            return False
        # Path traversal check
        if ".." in id_str or "/" in id_str or "\\" in id_str:
            return False
        return True

    def get_media_path(self, event_id: str, media_type: str) -> Optional[Path]:
        """
        Get media file path for an event.
        
        Args:
            event_id: Event ID
            media_type: Media type (collage, gif, mp4)
            
        Returns:
            Path to media file if exists, None otherwise
        """
        if not self.validate_id(event_id):
            logger.warning(f"Invalid event_id detected: {event_id}")
            return None

        event_dir = self.MEDIA_DIR / event_id
        
        if media_type == "collage":
            path = event_dir / "collage.jpg"
        elif media_type == "gif":
            path = event_dir / "preview.gif"
        elif media_type == "mp4":
            path = event_dir / "timelapse.mp4"
        else:
            return None
        
        return path if path.exists() else None


# Global singleton instance
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """
    Get or create the global media service instance.
    
    Returns:
        MediaService: Global media service instance
    """
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
