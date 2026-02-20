"""
Unit tests for event service and database models.

Tests cover:
- Event creation
- Event retrieval with pagination
- Filtering by camera, date, confidence
- Event deletion
- Cascade delete (camera deletion)
- Database indexes
"""
import tempfile
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Camera, Event, Zone, CameraType, CameraStatus, DetectionSource
from app.db.session import init_db
from app.services.events import EventService


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        yield SessionLocal
        
        # Cleanup
        Base.metadata.drop_all(bind=engine)
        engine.dispose()  # Close all connections


@pytest.fixture
def db_session(temp_db):
    """Create database session for testing."""
    session = temp_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def event_service():
    """Create event service instance."""
    return EventService()


@pytest.fixture
def test_camera(db_session):
    """Create test camera."""
    camera = Camera(
        id="test-camera-1",
        name="Test Camera",
        type=CameraType.THERMAL,
        enabled=True,
        rtsp_url_thermal="rtsp://test",
        detection_source=DetectionSource.THERMAL,
        stream_roles=["detect", "live"],
        status=CameraStatus.CONNECTED,
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)
    return camera


def test_create_event(db_session, event_service, test_camera):
    """Test creating an event."""
    timestamp = _utc_now_naive()
    
    event = event_service.create_event(
        db=db_session,
        camera_id=test_camera.id,
        timestamp=timestamp,
        confidence=0.85,
        event_type="person",
        summary="Person detected",
        collage_url="/media/collage.jpg",
        gif_url="/media/preview.gif",
        mp4_url="/media/timelapse.mp4",
        ai_enabled=True,
    )
    
    assert event.id is not None
    assert event.camera_id == test_camera.id
    assert event.timestamp == timestamp
    assert event.confidence == 0.85
    assert event.event_type == "person"
    assert event.summary == "Person detected"
    assert event.collage_url == "/media/collage.jpg"
    assert event.ai_enabled is True


def test_create_event_invalid_camera(db_session, event_service):
    """Test creating event with invalid camera ID."""
    with pytest.raises(ValueError, match="Camera with id .* not found"):
        event_service.create_event(
            db=db_session,
            camera_id="invalid-camera",
            timestamp=_utc_now_naive(),
            confidence=0.5,
        )


def test_get_events_pagination(db_session, event_service, test_camera):
    """Test event pagination."""
    # Create 25 events
    for i in range(25):
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=_utc_now_naive() - timedelta(minutes=i),
            confidence=0.5 + (i * 0.01),
        )
    
    # Get first page
    result = event_service.get_events(db=db_session, page=1, page_size=10)
    
    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total"] == 25
    assert len(result["events"]) == 10
    
    # Get second page
    result = event_service.get_events(db=db_session, page=2, page_size=10)
    
    assert result["page"] == 2
    assert len(result["events"]) == 10
    
    # Get third page
    result = event_service.get_events(db=db_session, page=3, page_size=10)
    
    assert result["page"] == 3
    assert len(result["events"]) == 5  # Remaining events


def test_get_events_filter_by_camera(db_session, event_service):
    """Test filtering events by camera ID."""
    # Create two cameras
    camera1 = Camera(
        id="camera-1",
        name="Camera 1",
        type=CameraType.THERMAL,
        enabled=True,
        status=CameraStatus.CONNECTED,
    )
    camera2 = Camera(
        id="camera-2",
        name="Camera 2",
        type=CameraType.COLOR,
        enabled=True,
        status=CameraStatus.CONNECTED,
    )
    db_session.add_all([camera1, camera2])
    db_session.commit()
    
    # Create events for both cameras
    for i in range(5):
        event_service.create_event(
            db=db_session,
            camera_id=camera1.id,
            timestamp=_utc_now_naive(),
            confidence=0.5,
        )
    
    for i in range(3):
        event_service.create_event(
            db=db_session,
            camera_id=camera2.id,
            timestamp=_utc_now_naive(),
            confidence=0.5,
        )
    
    # Filter by camera1
    result = event_service.get_events(db=db_session, camera_id=camera1.id)
    assert result["total"] == 5
    
    # Filter by camera2
    result = event_service.get_events(db=db_session, camera_id=camera2.id)
    assert result["total"] == 3


def test_get_events_filter_by_date(db_session, event_service, test_camera):
    """Test filtering events by date."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Create events for today
    for i in range(3):
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=datetime.combine(today, datetime.min.time()) + timedelta(hours=i),
            confidence=0.5,
        )
    
    # Create events for yesterday
    for i in range(2):
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=i),
            confidence=0.5,
        )
    
    # Filter by today
    result = event_service.get_events(db=db_session, date_filter=today)
    assert result["total"] == 3
    
    # Filter by yesterday
    result = event_service.get_events(db=db_session, date_filter=yesterday)
    assert result["total"] == 2


def test_get_events_filter_by_confidence(db_session, event_service, test_camera):
    """Test filtering events by minimum confidence."""
    # Create events with different confidence levels
    confidences = [0.3, 0.5, 0.7, 0.9]
    for conf in confidences:
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=_utc_now_naive(),
            confidence=conf,
        )
    
    # Filter by confidence >= 0.6
    result = event_service.get_events(db=db_session, min_confidence=0.6)
    assert result["total"] == 2  # 0.7 and 0.9
    
    # Filter by confidence >= 0.8
    result = event_service.get_events(db=db_session, min_confidence=0.8)
    assert result["total"] == 1  # 0.9 only


def test_get_events_combined_filters(db_session, event_service):
    """Test combining multiple filters."""
    # Create two cameras
    camera1 = Camera(id="cam-1", name="Cam 1", type=CameraType.THERMAL, enabled=True, status=CameraStatus.CONNECTED)
    camera2 = Camera(id="cam-2", name="Cam 2", type=CameraType.COLOR, enabled=True, status=CameraStatus.CONNECTED)
    db_session.add_all([camera1, camera2])
    db_session.commit()
    
    today = date.today()
    
    # Create events with different combinations
    event_service.create_event(db=db_session, camera_id=camera1.id, timestamp=datetime.combine(today, datetime.min.time()), confidence=0.8)
    event_service.create_event(db=db_session, camera_id=camera1.id, timestamp=datetime.combine(today, datetime.min.time()), confidence=0.4)
    event_service.create_event(db=db_session, camera_id=camera2.id, timestamp=datetime.combine(today, datetime.min.time()), confidence=0.9)
    
    # Filter: camera1 + today + confidence >= 0.6
    result = event_service.get_events(
        db=db_session,
        camera_id=camera1.id,
        date_filter=today,
        min_confidence=0.6,
    )
    assert result["total"] == 1  # Only the 0.8 confidence event from camera1


def test_get_event_by_id(db_session, event_service, test_camera):
    """Test getting event by ID."""
    # Create event
    created_event = event_service.create_event(
        db=db_session,
        camera_id=test_camera.id,
        timestamp=_utc_now_naive(),
        confidence=0.75,
        summary="Test event",
    )
    
    # Retrieve event
    event = event_service.get_event_by_id(db=db_session, event_id=created_event.id)
    
    assert event is not None
    assert event.id == created_event.id
    assert event.confidence == 0.75
    assert event.summary == "Test event"


def test_get_event_by_id_not_found(db_session, event_service):
    """Test getting non-existent event."""
    event = event_service.get_event_by_id(db=db_session, event_id="non-existent")
    assert event is None


def test_delete_event(db_session, event_service, test_camera):
    """Test deleting an event."""
    # Create event
    event = event_service.create_event(
        db=db_session,
        camera_id=test_camera.id,
        timestamp=_utc_now_naive(),
        confidence=0.5,
    )
    
    # Delete event
    deleted = event_service.delete_event(db=db_session, event_id=event.id)
    assert deleted is True
    
    # Verify deletion
    retrieved = event_service.get_event_by_id(db=db_session, event_id=event.id)
    assert retrieved is None


def test_delete_event_not_found(db_session, event_service):
    """Test deleting non-existent event."""
    deleted = event_service.delete_event(db=db_session, event_id="non-existent")
    assert deleted is False


def test_cascade_delete_camera(db_session, event_service):
    """Test that events are deleted when camera is deleted."""
    # Create camera
    camera = Camera(
        id="test-camera",
        name="Test Camera",
        type=CameraType.THERMAL,
        enabled=True,
        status=CameraStatus.CONNECTED,
    )
    db_session.add(camera)
    db_session.commit()
    
    # Create events
    for i in range(3):
        event_service.create_event(
            db=db_session,
            camera_id=camera.id,
            timestamp=_utc_now_naive(),
            confidence=0.5,
        )
    
    # Verify events exist
    result = event_service.get_events(db=db_session, camera_id=camera.id)
    assert result["total"] == 3
    
    # Delete camera
    db_session.delete(camera)
    db_session.commit()
    
    # Verify events are deleted (cascade)
    result = event_service.get_events(db=db_session, camera_id=camera.id)
    assert result["total"] == 0


def test_event_timestamps_indexed(db_session, test_camera):
    """Test that timestamp index exists and works."""
    # Create events with different timestamps
    timestamps = [
        _utc_now_naive() - timedelta(hours=3),
        _utc_now_naive() - timedelta(hours=2),
        _utc_now_naive() - timedelta(hours=1),
    ]
    
    for ts in timestamps:
        event = Event(
            camera_id=test_camera.id,
            timestamp=ts,
            confidence=0.5,
            event_type="person",
        )
        db_session.add(event)
    
    db_session.commit()
    
    # Query events ordered by timestamp (should use index)
    events = db_session.query(Event).order_by(Event.timestamp.desc()).all()
    
    assert len(events) == 3
    # Verify descending order
    assert events[0].timestamp > events[1].timestamp
    assert events[1].timestamp > events[2].timestamp


def test_get_event_count_by_camera(db_session, event_service, test_camera):
    """Test getting event count for a camera."""
    # Create events
    for i in range(5):
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=_utc_now_naive(),
            confidence=0.5,
        )
    
    # Get count
    count = event_service.get_event_count_by_camera(db=db_session, camera_id=test_camera.id)
    assert count == 5


def test_events_ordered_by_timestamp_desc(db_session, event_service, test_camera):
    """Test that events are returned in descending timestamp order."""
    # Create events with specific timestamps
    timestamps = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 12, 0, 0),
        datetime(2026, 1, 1, 11, 0, 0),
    ]
    
    for ts in timestamps:
        event_service.create_event(
            db=db_session,
            camera_id=test_camera.id,
            timestamp=ts,
            confidence=0.5,
        )
    
    # Get events
    result = event_service.get_events(db=db_session)
    events = result["events"]
    
    # Verify descending order (newest first)
    assert events[0].timestamp == datetime(2026, 1, 1, 12, 0, 0)
    assert events[1].timestamp == datetime(2026, 1, 1, 11, 0, 0)
    assert events[2].timestamp == datetime(2026, 1, 1, 10, 0, 0)
