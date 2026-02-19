"""
Event service for Smart Motion Detector v2.

This service handles event CRUD operations, pagination, and filtering.
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.models import Event, Camera


logger = logging.getLogger(__name__)


class EventService:
    """Service for event operations."""
    
    def create_event(
        self,
        db: Session,
        camera_id: str,
        timestamp: datetime,
        confidence: float,
        event_type: str = "person",
        summary: Optional[str] = None,
        collage_url: Optional[str] = None,
        gif_url: Optional[str] = None,
        mp4_url: Optional[str] = None,
        ai_enabled: bool = False,
        ai_reason: Optional[str] = None,
        person_count: int = 1,
    ) -> Event:
        """
        Create a new event.
        
        Args:
            db: Database session
            camera_id: Camera ID
            timestamp: Event timestamp
            confidence: Detection confidence (0.0-1.0)
            event_type: Event type (default: "person")
            summary: AI-generated summary (optional)
            collage_url: Collage image URL (optional)
            gif_url: GIF preview URL (optional)
            mp4_url: MP4 timelapse URL (optional)
            ai_enabled: Whether AI summary is enabled
            ai_reason: Reason if AI is disabled (optional)
            
        Returns:
            Event: Created event
            
        Raises:
            ValueError: If camera_id doesn't exist
        """
        # Verify camera exists
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise ValueError(f"Camera with id {camera_id} not found")
        
        # Create event
        event = Event(
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=confidence,
            event_type=event_type,
            person_count=person_count,
            summary=summary,
            collage_url=collage_url,
            gif_url=gif_url,
            mp4_url=mp4_url,
            ai_enabled=ai_enabled,
            ai_reason=ai_reason,
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        logger.info(f"Event created: {event.id} for camera {camera_id}")
        
        return event
    
    def get_events(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        camera_id: Optional[str] = None,
        date_filter: Optional[date] = None,
        min_confidence: Optional[float] = None,
        rejected_only: Optional[bool] = None,
    ) -> Dict:
        """
        Get events with pagination and filtering.
        
        Args:
            db: Database session
            page: Page number (1-indexed)
            page_size: Number of events per page
            camera_id: Filter by camera ID (optional)
            date_filter: Filter by date (optional)
            min_confidence: Minimum confidence threshold (optional)
            
        Returns:
            Dict containing:
                - page: Current page number
                - page_size: Events per page
                - total: Total number of events
                - events: List of events
        """
        # Build query
        query = db.query(Event)
        
        # Apply filters
        filters = []
        
        if camera_id:
            filters.append(Event.camera_id == camera_id)
        
        if date_filter:
            # Filter by date (timestamp between start and end of day)
            start_of_day = datetime.combine(date_filter, datetime.min.time())
            end_of_day = datetime.combine(date_filter, datetime.max.time())
            filters.append(and_(
                Event.timestamp >= start_of_day,
                Event.timestamp <= end_of_day
            ))
        
        if min_confidence is not None:
            filters.append(Event.confidence >= min_confidence)
        
        if rejected_only is True:
            filters.append(Event.rejected_by_ai == True)
        elif rejected_only is False or rejected_only is None:
            filters.append(Event.rejected_by_ai == False)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        events = (
            query
            .order_by(Event.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0
        logger.info(
            f"Retrieved {len(events)} events (page {page}/{total_pages}, total={total})"
        )
        
        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "events": events,
        }
    
    def get_event_by_id(
        self,
        db: Session,
        event_id: str,
    ) -> Optional[Event]:
        """
        Get event by ID.
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            Event if found, None otherwise
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if event:
            logger.info(f"Event retrieved: {event_id}")
        else:
            logger.warning(f"Event not found: {event_id}")
        
        return event
    
    def delete_event(
        self,
        db: Session,
        event_id: str,
    ) -> bool:
        """
        Delete event by ID.
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            True if deleted, False if not found
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        
        if not event:
            logger.warning(f"Event not found for deletion: {event_id}")
            return False
        
        db.delete(event)
        db.commit()
        
        logger.info(f"Event deleted: {event_id}")
        
        return True
    
    def get_event_count_by_camera(
        self,
        db: Session,
        camera_id: str,
    ) -> int:
        """
        Get event count for a specific camera.
        
        Args:
            db: Database session
            camera_id: Camera ID
            
        Returns:
            Number of events for the camera
        """
        count = db.query(func.count(Event.id)).filter(Event.camera_id == camera_id).scalar()
        return count or 0


# Global singleton instance
_event_service: Optional[EventService] = None


def get_event_service() -> EventService:
    """
    Get or create the global event service instance.
    
    Returns:
        EventService: Global event service instance
    """
    global _event_service
    if _event_service is None:
        _event_service = EventService()
    return _event_service
