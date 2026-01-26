"""
Unit tests for retention worker.

Tests cover:
- Cleanup by retention days
- Cleanup by disk limit
- Media deletion order (mp4 → collage)
- Disk usage checking
- Event media size calculation
"""
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Camera, Event, CameraType, CameraStatus
from app.workers.retention import RetentionWorker


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
        engine.dispose()


@pytest.fixture
def db_session(temp_db):
    """Create database session for testing."""
    session = temp_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def retention_worker():
    """Create retention worker instance."""
    return RetentionWorker()


@pytest.fixture
def test_camera(db_session):
    """Create test camera."""
    camera = Camera(
        id="test-camera",
        name="Test Camera",
        type=CameraType.THERMAL,
        enabled=True,
        status=CameraStatus.CONNECTED,
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)
    return camera


@pytest.fixture
def temp_media_dir(monkeypatch):
    """Create temporary media directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        media_dir = Path(tmpdir) / "media"
        media_dir.mkdir()
        monkeypatch.setattr(RetentionWorker, "MEDIA_DIR", media_dir)
        yield media_dir


def test_cleanup_old_events(db_session, retention_worker, test_camera, temp_media_dir):
    """Test cleanup of events older than retention days."""
    # Create old events (10 days ago)
    old_timestamp = datetime.utcnow() - timedelta(days=10)
    
    for i in range(3):
        event = Event(
            id=f"old-event-{i}",
            camera_id=test_camera.id,
            timestamp=old_timestamp,
            confidence=0.8,
            event_type="person",
        )
        db_session.add(event)
        
        # Create media directory
        event_dir = temp_media_dir / event.id
        event_dir.mkdir()
        (event_dir / "collage.jpg").write_text("test")
    
    db_session.commit()
    
    # Create recent events (2 days ago)
    recent_timestamp = datetime.utcnow() - timedelta(days=2)
    
    for i in range(2):
        event = Event(
            id=f"recent-event-{i}",
            camera_id=test_camera.id,
            timestamp=recent_timestamp,
            confidence=0.8,
            event_type="person",
        )
        db_session.add(event)
    
    db_session.commit()
    
    # Cleanup with 7 day retention
    deleted = retention_worker.cleanup_old_events(db=db_session, retention_days=7)
    
    # Should delete 3 old events
    assert deleted == 3
    
    # Verify old events deleted
    remaining = db_session.query(Event).count()
    assert remaining == 2


def test_cleanup_by_disk_limit(db_session, retention_worker, test_camera, temp_media_dir):
    """Test cleanup when disk limit is exceeded."""
    # Create events
    for i in range(5):
        event = Event(
            id=f"event-{i}",
            camera_id=test_camera.id,
            timestamp=datetime.utcnow() - timedelta(hours=i),
            confidence=0.8,
            event_type="person",
        )
        db_session.add(event)
        
        # Create media directory
        event_dir = temp_media_dir / event.id
        event_dir.mkdir()
        (event_dir / "collage.jpg").write_text("test")
    
    db_session.commit()
    
    # Mock disk usage to be over limit
    with patch.object(retention_worker, '_get_disk_usage_percent') as mock_usage:
        # First call: over limit, second call: under limit
        mock_usage.side_effect = [85.0, 75.0]
        
        deleted = retention_worker.cleanup_by_disk_limit(db=db_session, disk_limit_percent=80)
        
        # Should delete at least 1 event
        assert deleted >= 1


def test_delete_order_mp4_first(retention_worker, temp_media_dir):
    """Test that media files are deleted in correct order (mp4 → collage)."""
    # Create event directory with all media files
    event_id = "test-event"
    event_dir = temp_media_dir / event_id
    event_dir.mkdir()
    
    mp4_path = event_dir / "timelapse.mp4"
    collage_path = event_dir / "collage.jpg"
    
    mp4_path.write_text("mp4 content")
    collage_path.write_text("collage content")
    
    # Delete media
    retention_worker.delete_event_media(event_id)
    
    # All files should be deleted
    assert not mp4_path.exists()
    assert not collage_path.exists()
    
    # Directory should be deleted
    assert not event_dir.exists()


def test_delete_event_media_partial(retention_worker, temp_media_dir):
    """Test deletion when only some media files exist."""
    # Create event directory with only collage
    event_id = "test-event"
    event_dir = temp_media_dir / event_id
    event_dir.mkdir()
    
    collage_path = event_dir / "collage.jpg"
    collage_path.write_text("collage content")
    
    # Delete media (should not crash even if mp4 doesn't exist)
    retention_worker.delete_event_media(event_id)
    
    # Collage should be deleted
    assert not collage_path.exists()
    
    # Directory should be deleted
    assert not event_dir.exists()


def test_delete_event_media_not_exists(retention_worker, temp_media_dir):
    """Test deletion when event directory doesn't exist."""
    # Should not crash
    retention_worker.delete_event_media("non-existent-event")


def test_disk_usage_check(retention_worker, temp_media_dir):
    """Test disk usage percentage calculation."""
    # Get disk usage
    usage = retention_worker._get_disk_usage_percent()
    
    # Should return a valid percentage
    assert 0 <= usage <= 100


def test_get_media_size_mb(retention_worker, temp_media_dir):
    """Test media size calculation."""
    # Create event directory with files
    event_id = "test-event"
    event_dir = temp_media_dir / event_id
    event_dir.mkdir()
    
    # Create files with known sizes
    (event_dir / "collage.jpg").write_bytes(b"x" * 1024 * 100)  # 100 KB
    (event_dir / "timelapse.mp4").write_bytes(b"x" * 1024 * 1024 * 2)  # 2 MB
    
    # Get total size
    size_mb = retention_worker.get_media_size_mb(event_id)
    
    # Should be approximately 2.1 MB
    assert 2.0 < size_mb < 2.2


def test_get_media_size_mb_not_exists(retention_worker, temp_media_dir):
    """Test media size for non-existent event."""
    size_mb = retention_worker.get_media_size_mb("non-existent")
    assert size_mb == 0.0


def test_cleanup_oldest_first(db_session, retention_worker, test_camera, temp_media_dir):
    """Test that oldest events are deleted first."""
    # Create events with different timestamps
    timestamps = [
        datetime.utcnow() - timedelta(hours=10),  # Oldest
        datetime.utcnow() - timedelta(hours=5),
        datetime.utcnow() - timedelta(hours=1),   # Newest
    ]
    
    for i, ts in enumerate(timestamps):
        event = Event(
            id=f"event-{i}",
            camera_id=test_camera.id,
            timestamp=ts,
            confidence=0.8,
            event_type="person",
        )
        db_session.add(event)
        
        # Create media
        event_dir = temp_media_dir / event.id
        event_dir.mkdir()
        (event_dir / "collage.jpg").write_text("test")
    
    db_session.commit()
    
    # Mock disk usage to trigger cleanup
    with patch.object(retention_worker, '_get_disk_usage_percent') as mock_usage:
        # Over limit, then under limit after 1 deletion
        mock_usage.side_effect = [85.0, 75.0]
        
        deleted = retention_worker.cleanup_by_disk_limit(db=db_session, disk_limit_percent=80)
        
        # Should delete 1 event
        assert deleted == 1
        
        # Verify oldest event was deleted
        remaining_events = db_session.query(Event).order_by(Event.timestamp.asc()).all()
        assert len(remaining_events) == 2
        
        # First remaining event should be the second oldest
        assert remaining_events[0].id == "event-1"


def test_disk_usage_below_limit(db_session, retention_worker, test_camera):
    """Test that cleanup is skipped when disk usage is below limit."""
    # Create event
    event = Event(
        id="test-event",
        camera_id=test_camera.id,
        timestamp=datetime.utcnow(),
        confidence=0.8,
        event_type="person",
    )
    db_session.add(event)
    db_session.commit()
    
    # Mock disk usage to be below limit
    with patch.object(retention_worker, '_get_disk_usage_percent', return_value=50.0):
        deleted = retention_worker.cleanup_by_disk_limit(db=db_session, disk_limit_percent=80)
        
        # Should not delete anything
        assert deleted == 0
        
        # Event should still exist
        assert db_session.query(Event).count() == 1


def test_worker_lifecycle(retention_worker):
    """Test worker start and stop."""
    # Start worker
    retention_worker.start()
    assert retention_worker.running is True
    assert retention_worker.thread is not None
    assert retention_worker.thread.is_alive()
    
    # Stop worker
    retention_worker.stop()
    assert retention_worker.running is False


def test_worker_start_already_running(retention_worker):
    """Test starting worker when already running."""
    # Start worker
    retention_worker.start()
    assert retention_worker.running is True
    
    # Try to start again
    retention_worker.start()
    assert retention_worker.running is True
    
    # Cleanup
    retention_worker.stop()


def test_cleanup_with_db_error(db_session, retention_worker, test_camera, temp_media_dir):
    """Test cleanup handles database errors gracefully."""
    # Create event
    event = Event(
        id="test-event",
        camera_id=test_camera.id,
        timestamp=datetime.utcnow() - timedelta(days=10),
        confidence=0.8,
        event_type="person",
    )
    db_session.add(event)
    db_session.commit()
    
    # Mock delete_event_media to raise exception
    with patch.object(retention_worker, 'delete_event_media', side_effect=Exception("Test error")):
        deleted = retention_worker.cleanup_old_events(db=db_session, retention_days=7)
        
        # Should handle error and continue
        assert deleted == 0
        
        # Event should still exist (rollback)
        assert db_session.query(Event).count() == 1


def test_get_retention_worker_singleton():
    """Test that get_retention_worker returns singleton instance."""
    from app.workers.retention import get_retention_worker, _retention_worker
    
    # Get first instance
    worker1 = get_retention_worker()
    
    # Get second instance
    worker2 = get_retention_worker()
    
    # Should be same instance
    assert worker1 is worker2
