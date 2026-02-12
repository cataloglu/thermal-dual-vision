"""
Basic health endpoint test
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] == True

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert data["version"] == "2.5.7"
