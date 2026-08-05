"""Tests for the AI Image-to-Bill API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_without_file():
    """Test upload endpoint without file."""
    response = client.post("/api/upload-image")
    assert response.status_code == 422


def test_get_nonexistent_result():
    """Test getting result for non-existent job."""
    response = client.get("/api/result/nonexistent-id")
    assert response.status_code == 404


def test_extract_without_upload():
    """Test extraction without prior upload."""
    response = client.post("/api/extract-bill", json={
        "id": "nonexistent-id",
        "preprocess": True
    })
    assert response.status_code == 404


def test_validate_without_extraction():
    """Test validation without extraction."""
    response = client.post("/api/validate", json={
        "id": "nonexistent-id"
    })
    assert response.status_code == 404
