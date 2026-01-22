"""
Integration tests for recordings API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_get_recordings_empty(client):
    response = client.get("/api/recordings")
    assert response.status_code == 200
    data = response.json()
    assert data["recordings"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_delete_recording_stub(client):
    response = client.delete("/api/recordings/test-recording-id")
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] is True
    assert data["id"] == "test-recording-id"
