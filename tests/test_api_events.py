"""
Integration tests for events API endpoints.
"""
from datetime import datetime
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_session, init_db
from app.db.models import Camera, Event, CameraType, CameraStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def _seed_events():
    init_db()
    camera_id = f"bulk-test-{uuid.uuid4()}"
    event_ids = []

    db = next(get_session())
    try:
        camera = Camera(
            id=camera_id,
            name="Bulk Test Camera",
            type=CameraType.THERMAL,
            enabled=True,
            status=CameraStatus.CONNECTED,
        )
        db.add(camera)
        db.commit()

        for _ in range(2):
            event = Event(
                camera_id=camera_id,
                timestamp=datetime.utcnow(),
                confidence=0.9,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            event_ids.append(event.id)
    finally:
        db.close()

    return camera_id, event_ids


def _cleanup_camera(camera_id: str, event_ids: list[str]) -> None:
    db = next(get_session())
    try:
        if event_ids:
            db.query(Event).filter(Event.id.in_(event_ids)).delete(synchronize_session=False)
        db.query(Camera).filter(Camera.id == camera_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_post_events_bulk_delete_success(client):
    camera_id, event_ids = _seed_events()
    try:
        response = client.post("/api/events/bulk-delete", json={"event_ids": event_ids})
        assert response.status_code == 200
        payload = response.json()
        assert payload["deleted_count"] == len(event_ids)
        assert payload["failed_ids"] == []

        db = next(get_session())
        try:
            remaining = db.query(Event).filter(Event.id.in_(event_ids)).count()
            assert remaining == 0
        finally:
            db.close()
    finally:
        _cleanup_camera(camera_id, event_ids)


def test_post_events_bulk_delete_validation_error(client):
    response = client.post("/api/events/bulk-delete", json={"event_ids": []})
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("code") == "VALIDATION_ERROR"
