"""Tests for v1 API endpoints."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from unittest.mock import patch
import os

from apps.api.app.main import create_app
from apps.api.app.config import get_config


@pytest.fixture
def test_videos_root(tmp_path):
    """Create a temporary videos root directory with test structure."""
    videos_root = tmp_path / "videos"
    videos_root.mkdir()
    
    # Create subdirectories
    (videos_root / "temp").mkdir()
    (videos_root / "train").mkdir()
    (videos_root / "test").mkdir()
    (videos_root / "purged").mkdir()
    (videos_root / "thumbs").mkdir()
    (videos_root / "manifests").mkdir()
    
    # Create some test video files
    (videos_root / "temp" / "video1.mp4").write_text("fake video 1")
    (videos_root / "temp" / "video2.mp4").write_text("fake video 2")
    (videos_root / "purged" / "video3.mp4").write_text("fake video 3")
    
    # Create a test thumbnail
    (videos_root / "thumbs" / "video1.jpg").write_text("fake thumbnail")
    
    return videos_root


@pytest.fixture
def client(test_videos_root):
    """Create a test client with temporary videos root."""
    env_vars = {
        "REACHY_VIDEOS_ROOT": str(test_videos_root),
        "REACHY_API_PORT": "54323",
        "REACHY_ENABLE_LEGACY_ENDPOINTS": "true",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        # Clear config cache to pick up new environment
        get_config.cache_clear()
        
        app = create_app()
        with TestClient(app) as test_client:
            yield test_client


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test that health check endpoint returns 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        assert "data" in body
        assert "meta" in body
        
        data = body["data"]
        assert data["service"] == "media-mover"
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
    
    def test_readiness_check(self, client):
        """Test that readiness check endpoint returns 200."""
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["service"] == "media-mover"


class TestMediaV1Endpoints:
    """Test v1 media endpoints."""
    
    def test_list_videos_temp(self, client):
        """Test listing videos from temp split."""
        response = client.get("/api/v1/media/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        assert "data" in body
        assert "meta" in body
        
        data = body["data"]
        assert "items" in data
        assert "pagination" in data
        
        # Check pagination
        pagination = data["pagination"]
        assert pagination["total"] == 2
        assert pagination["limit"] == 10
        assert pagination["offset"] == 0
        assert pagination["has_more"] is False
        
        # Should have 2 videos in temp
        assert len(data["items"]) == 2
        
        # Check video structure
        video = data["items"][0]
        assert "video_id" in video
        assert "file_path" in video
        assert "size_bytes" in video
        assert "mtime" in video
        assert "split" in video
        assert video["split"] == "temp"
    
    def test_list_videos_purged(self, client):
        """Test listing videos from purged split."""
        response = client.get("/api/v1/media/list?split=purged&limit=10&offset=0")
        assert response.status_code == 200
        
        body = response.json()
        data = body["data"]
        assert data["pagination"]["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["split"] == "purged"
    
    def test_list_videos_empty_split(self, client):
        """Test listing videos from empty split."""
        response = client.get("/api/v1/media/list?split=train&limit=10&offset=0")
        assert response.status_code == 200
        
        body = response.json()
        data = body["data"]
        assert data["pagination"]["total"] == 0
        assert len(data["items"]) == 0
    
    def test_list_videos_invalid_split(self, client):
        """Test that invalid split returns 400."""
        response = client.get("/api/v1/media/list?split=invalid&limit=10&offset=0")
        assert response.status_code == 422  # FastAPI validation error
    
    def test_list_videos_pagination(self, client):
        """Test pagination parameters."""
        # Get first video
        response = client.get("/api/v1/media/list?split=temp&limit=1&offset=0")
        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert len(data["items"]) == 1
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["offset"] == 0
        
        # Get second video
        response = client.get("/api/v1/media/list?split=temp&limit=1&offset=1")
        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert len(data["items"]) == 1
        assert data["pagination"]["offset"] == 1
    
    def test_get_video_metadata(self, client):
        """Test getting metadata for a specific video."""
        response = client.get("/api/v1/media/video1")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["video_id"] == "video1"
        assert data["split"] == "temp"
        assert "file_path" in data
        assert "size_bytes" in data
    
    def test_get_video_metadata_not_found(self, client):
        """Test that non-existent video returns 404."""
        response = client.get("/api/v1/media/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "not_found"
    
    def test_get_video_thumbnail(self, client):
        """Test getting thumbnail URL for a video."""
        response = client.get("/api/v1/media/video1/thumb")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["video_id"] == "video1"
        assert "thumbnail_url" in data
        assert "video1.jpg" in data["thumbnail_url"]
    
    def test_get_video_thumbnail_not_found(self, client):
        """Test that non-existent thumbnail returns 404."""
        response = client.get("/api/v1/media/video2/thumb")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "not_found"


class TestLegacyEndpoints:
    """Test legacy endpoint compatibility."""
    
    def test_legacy_list_videos(self, client):
        """Test that legacy list endpoint works and includes deprecation headers."""
        response = client.get("/api/videos/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        
        # Check deprecation headers
        assert "X-API-Deprecated" in response.headers
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Deprecation-Message" in response.headers
        
        # Check response format is same as v1
        data = response.json()
        assert "items" in data
        assert data["total"] == 2
    
    def test_legacy_list_videos_compat(self, client):
        """Test that legacy compatibility endpoint works."""
        response = client.get("/api/media/videos/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        
        # Check deprecation headers
        assert "X-API-Deprecated" in response.headers
        
        # Check response
        data = response.json()
        assert "items" in data
        assert data["total"] == 2
    
    def test_legacy_promote_is_real_handler(self, client):
        """Test that legacy promote path is wired to real handler, not deprecated stub."""
        response = client.post(
            "/api/media/promote",
            json={
                "video_id": "test",
                "label": "happy"
            }
        )
        # Missing dest_split should trigger real validation, not stub success.
        assert response.status_code == 400

        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("error") == "validation_error"
        assert "Missing fields: dest_split" in detail.get("message", "")
        assert "deprecated" not in data
        assert "new_endpoint" not in data

    def test_canonical_promote_validation_path(self, client):
        """Canonical /api/v1/media/promote should be available and enforce same validation."""
        response = client.post(
            "/api/v1/media/promote",
            json={
                "video_id": "test",
                "label": "happy"
            }
        )
        assert response.status_code == 400
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("error") == "validation_error"
        assert "Missing fields: dest_split" in detail.get("message", "")
    
    def test_legacy_health(self, client):
        """Test that legacy health endpoint works."""
        response = client.get("/media/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["deprecated"] is True
        
        # Check deprecation headers
        assert "X-API-Deprecated" in response.headers


class TestPromoteV1Endpoints:
    """Test v1 promote endpoints."""

    def test_legacy_stage_endpoint_deprecated_exists(self, client):
        """Test deprecated v1 stage endpoint remains registered."""
        # This will fail with 422 (validation error) but proves endpoint exists
        response = client.post("/api/v1/promote/stage", json={})
        assert response.status_code in [422, 400]  # Validation error, not 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
