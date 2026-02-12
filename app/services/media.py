"""
Media service for Smart Motion Detector v2.

This service handles event media generation and management.
"""
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Event
from app.services.recorder import get_continuous_recorder
from app.services.settings import get_settings_service
from app.workers.media import get_media_worker
from app.utils.paths import DATA_DIR


logger = logging.getLogger(__name__)


class MediaService:
    """Service for event media operations."""
    
    MEDIA_DIR = DATA_DIR / "media"
    
    def __init__(self):
        """Initialize media service."""
        self.media_worker = get_media_worker()
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    
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
        
        # MP4: prefer continuous recording, fallback to frames when recording unavailable
        mp4_from_recording = False
        try:
            config = get_settings_service().load_config()
            prebuffer = float(getattr(config.event, "prebuffer_seconds", 5.0))
            postbuffer = float(getattr(config.event, "postbuffer_seconds", 15.0))
            start_time = event.timestamp - timedelta(seconds=prebuffer)
            end_time = event.timestamp + timedelta(seconds=postbuffer)
            recorder = get_continuous_recorder()
            if recorder.extract_clip(event.camera_id, start_time, end_time, mp4_path):
                mp4_from_recording = True
                logger.debug("Event %s MP4 from continuous recording", event_id)
            else:
                logger.info(
                    "Event %s: recording unavailable, using frame-based MP4 fallback",
                    event_id,
                )
        except Exception as e:
            logger.info("Clip from recording failed for %s (%s), using frame fallback", event_id, e)

        # Generate media in parallel (collage always; mp4 from frames if not from recording)
        mp4_source_frames = mp4_frames if mp4_frames else frames
        mp4_source_detections = mp4_detections if mp4_detections is not None else detections
        mp4_source_timestamps = mp4_timestamps if mp4_timestamps is not None else timestamps
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
                    logger.warning("Failed to generate %s for event %s: %s", label, event_id, exc)
                    if label == "collage":
                        errors.append(exc)
        if errors:
            raise errors[0]
        
        # Save URLs to database WITHOUT prefix (prefix added at runtime in main.py)
        event.collage_url = f"/api/events/{event_id}/collage" if os.path.exists(collage_path) else None
        event.gif_url = f"/api/events/{event_id}/preview.gif" if os.path.exists(gif_path) else None
        mp4_legacy_marker = f"{mp4_path}.legacy"
        mp4_ok = os.path.exists(mp4_path) and not os.path.exists(mp4_legacy_marker)
        event.mp4_url = f"/api/events/{event_id}/timelapse.mp4" if mp4_ok else None
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
