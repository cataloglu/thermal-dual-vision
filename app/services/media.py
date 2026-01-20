"""
Media service for Smart Motion Detector v2.

This service handles event media generation and management.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Event
from app.workers.media import get_media_worker


logger = logging.getLogger(__name__)


class MediaService:
    """Service for event media operations."""
    
    MEDIA_DIR = Path("data/media")
    
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
        camera_name: str = "Camera",
    ) -> Dict[str, str]:
        """
        Generate all media files for an event (collage, GIF, MP4).
        
        Generates files in parallel for speed.
        
        Args:
            db: Database session
            event_id: Event ID
            frames: List of event frames
            detections: List of detections (one per frame)
            camera_name: Camera name for overlay
            
        Returns:
            Dict with media URLs (collage_url, gif_url, mp4_url)
            
        Raises:
            ValueError: If event not found or insufficient frames
        """
        # Get event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        if len(frames) < 10:
            raise ValueError(f"Need at least 10 frames, got {len(frames)}")
        
        # Create event media directory
        event_dir = self.MEDIA_DIR / event_id
        event_dir.mkdir(parents=True, exist_ok=True)
        
        # Output paths
        collage_path = str(event_dir / "collage.jpg")
        gif_path = str(event_dir / "preview.gif")
        mp4_path = str(event_dir / "timelapse.mp4")
        
        # Generate media in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks
            collage_future = executor.submit(
                self.media_worker.create_collage,
                frames,
                collage_path,
                camera_name,
                event.timestamp,
                event.confidence,
            )
            
            gif_future = executor.submit(
                self.media_worker.create_timeline_gif,
                frames,
                gif_path,
                camera_name,
                event.timestamp,
            )
            
            mp4_future = executor.submit(
                self.media_worker.create_timelapse_mp4,
                frames,
                detections,
                mp4_path,
                camera_name,
                event.timestamp,
            )
            
            # Wait for all to complete
            collage_future.result()
            gif_future.result()
            mp4_future.result()
        
        # Update event with media URLs
        event.collage_url = f"/api/events/{event_id}/collage"
        event.gif_url = f"/api/events/{event_id}/preview.gif"
        event.mp4_url = f"/api/events/{event_id}/timelapse.mp4"
        db.commit()
        
        logger.info(f"Event media generated: {event_id}")
        
        return {
            "collage_url": event.collage_url,
            "gif_url": event.gif_url,
            "mp4_url": event.mp4_url,
        }
    
    def get_media_path(self, event_id: str, media_type: str) -> Optional[Path]:
        """
        Get media file path for an event.
        
        Args:
            event_id: Event ID
            media_type: Media type (collage, gif, mp4)
            
        Returns:
            Path to media file if exists, None otherwise
        """
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
