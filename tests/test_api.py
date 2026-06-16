from __future__ import annotations

from fastapi.testclient import TestClient
from src.api import app

def test_api_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "mock_mode" in data
