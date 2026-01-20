"""
Retention worker for Smart Motion Detector v2.

This worker handles automatic cleanup of old events and media files
based on retention policy and disk usage limits.
"""
import logging
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import Event
from app.db.session import get_session
from app.services.settings import get_settings_service


logger = logging.getLogger(__name__)


class RetentionWorker:
    """
    Retention worker for automatic cleanup.
    
    Handles:
    - Age-based cleanup (retention_days)
    - Disk-based cleanup (disk_limit_percent)
    - Media deletion order (mp4 → gif → collage)
    """
    
    MEDIA_DIR = Path("data/media")
    
    def __init__(self):
        """Initialize retention worker."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.settings_service = get_settings_service()
        
        logger.info("RetentionWorker initialized")
    
    def start(self) -> None:
        """Start retention worker thread."""
        if self.running:
            logger.warning("RetentionWorker already running")
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="retention-worker"
        )
        self.thread.start()
        
        logger.info("RetentionWorker started")
    
    def stop(self) -> None:
        """Stop retention worker thread."""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("RetentionWorker stopped")
    
    def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while self.running:
            try:
                # Load settings
                config = self.settings_service.load_config()
                
                # Get database session
                db = next(get_session())
                
                try:
                    # Cleanup by retention days
                    deleted_by_age = self.cleanup_old_events(
                        db=db,
                        retention_days=config.media.retention_days
                    )
                    
                    if deleted_by_age > 0:
                        logger.info(f"Cleaned up {deleted_by_age} events by retention policy")
                    
                    # Cleanup by disk limit
                    deleted_by_disk = self.cleanup_by_disk_limit(
                        db=db,
                        disk_limit_percent=config.media.disk_limit_percent
                    )
                    
                    if deleted_by_disk > 0:
                        logger.info(f"Cleaned up {deleted_by_disk} events by disk limit")
                    
                finally:
                    db.close()
                
                # Sleep for cleanup interval
                sleep_hours = config.media.cleanup_interval_hours
                logger.debug(f"Sleeping for {sleep_hours} hours until next cleanup")
                time.sleep(sleep_hours * 3600)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                time.sleep(3600)  # Sleep 1 hour on error
    
    def cleanup_old_events(
        self,
        db: Session,
        retention_days: int
    ) -> int:
        """
        Cleanup events older than retention_days.
        
        Args:
            db: Database session
            retention_days: Days to keep events
            
        Returns:
            Number of events deleted
        """
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Query old events
        old_events = db.query(Event).filter(Event.timestamp < cutoff_date).all()
        
        deleted_count = 0
        
        for event in old_events:
            try:
                # Delete media files
                self.delete_event_media(event.id)
                
                # Delete database record
                db.delete(event)
                db.commit()
                
                deleted_count += 1
                logger.debug(f"Deleted old event: {event.id} (age: {(datetime.utcnow() - event.timestamp).days} days)")
                
            except Exception as e:
                logger.error(f"Failed to delete event {event.id}: {e}")
                db.rollback()
        
        return deleted_count
    
    def cleanup_by_disk_limit(
        self,
        db: Session,
        disk_limit_percent: int
    ) -> int:
        """
        Cleanup events if disk usage exceeds limit.
        
        Deletes oldest events first until disk usage is below limit.
        
        Args:
            db: Database session
            disk_limit_percent: Maximum disk usage percentage (50-95)
            
        Returns:
            Number of events deleted
        """
        # Check disk usage
        disk_usage = self._get_disk_usage_percent()
        
        if disk_usage < disk_limit_percent:
            logger.debug(f"Disk usage {disk_usage:.1f}% is below limit {disk_limit_percent}%")
            return 0
        
        logger.warning(f"Disk usage {disk_usage:.1f}% exceeds limit {disk_limit_percent}%")
        
        # Get oldest events
        old_events = db.query(Event).order_by(Event.timestamp.asc()).all()
        
        deleted_count = 0
        
        for event in old_events:
            try:
                # Delete media files
                self.delete_event_media(event.id)
                
                # Delete database record
                db.delete(event)
                db.commit()
                
                deleted_count += 1
                
                # Check disk usage again
                disk_usage = self._get_disk_usage_percent()
                
                if disk_usage < disk_limit_percent:
                    logger.info(f"Disk usage now {disk_usage:.1f}%, below limit")
                    break
                
            except Exception as e:
                logger.error(f"Failed to delete event {event.id}: {e}")
                db.rollback()
        
        return deleted_count
    
    def delete_event_media(self, event_id: str) -> None:
        """
        Delete all media files for an event.
        
        Deletion order: mp4 → gif → collage (largest first)
        
        Args:
            event_id: Event ID
        """
        event_dir = self.MEDIA_DIR / event_id
        
        if not event_dir.exists():
            return
        
        # Delete in order: mp4 (largest) → gif → collage
        delete_order = ["timelapse.mp4", "preview.gif", "collage.jpg"]
        
        for filename in delete_order:
            file_path = event_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted media file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
        
        # Delete event directory
        try:
            if event_dir.exists():
                event_dir.rmdir()
                logger.debug(f"Deleted event directory: {event_dir}")
        except Exception as e:
            logger.error(f"Failed to delete directory {event_dir}: {e}")
    
    def _get_disk_usage_percent(self) -> float:
        """
        Get disk usage percentage for media directory.
        
        Returns:
            Disk usage percentage (0-100)
        """
        try:
            # Get disk usage for media directory
            usage = shutil.disk_usage(self.MEDIA_DIR)
            
            # Calculate percentage
            percent = (usage.used / usage.total) * 100
            
            return percent
            
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            return 0.0
    
    def get_media_size_mb(self, event_id: str) -> float:
        """
        Get total media size for an event.
        
        Args:
            event_id: Event ID
            
        Returns:
            Total size in MB
        """
        event_dir = self.MEDIA_DIR / event_id
        
        if not event_dir.exists():
            return 0.0
        
        total_size = 0
        
        for file in event_dir.iterdir():
            if file.is_file():
                total_size += file.stat().st_size
        
        return total_size / 1024 / 1024  # Convert to MB


# Global singleton instance
_retention_worker: Optional[RetentionWorker] = None


def get_retention_worker() -> RetentionWorker:
    """
    Get or create the global retention worker instance.
    
    Returns:
        RetentionWorker: Global retention worker instance
    """
    global _retention_worker
    if _retention_worker is None:
        _retention_worker = RetentionWorker()
    return _retention_worker
