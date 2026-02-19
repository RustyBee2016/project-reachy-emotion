"""Comprehensive integration tests for the endpoint system."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from apps.api.app.config import get_config


@pytest.fixture
def test_videos_root(tmp_path):
    """Create a complete test videos directory structure."""
    videos_root = tmp_path / "videos"
    videos_root.mkdir()
    
    # Create all required subdirectories
    for subdir in ["temp", "train", "test", "purged", "thumbs", "manifests"]:
        (videos_root / subdir).mkdir()
    
    # Create test videos in different splits
    (videos_root / "temp" / "video_temp1.mp4").write_text("temp video 1")
    (videos_root / "temp" / "video_temp2.mp4").write_text("temp video 2")
    (videos_root / "purged" / "video_purged1.mp4").write_text("purged video 1")
    (videos_root / "train" / "video_train1.mp4").write_text("train video 1")
    (videos_root / "test" / "video_test1.mp4").write_text("test video 1")
    
    # Create thumbnails
    (videos_root / "thumbs" / "video_temp1.jpg").write_text("thumbnail 1")
    (videos_root / "thumbs" / "video_purged1.jpg").write_text("thumbnail 2")
    
    return videos_root


@pytest.fixture
def app_client(test_videos_root):
    """Create a test client with full configuration."""
    env_vars = {
        "REACHY_VIDEOS_ROOT": str(test_videos_root),
        "REACHY_API_PORT": "54324",
        "REACHY_ENABLE_LEGACY_ENDPOINTS": "true",
        "REACHY_ENABLE_CORS": "true",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        get_config.cache_clear()
        app = create_app()
        with TestClient(app) as client:
            yield client


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_health_check_workflow(self, app_client):
        """Test health check and readiness endpoints."""
        # Check health
        response = app_client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
        
        # Check readiness
        response = app_client.get("/api/v1/ready")
        assert response.status_code == 200
    
    def test_list_videos_all_splits(self, app_client):
        """Test listing videos from all splits."""
        splits = ["temp", "train", "test", "purged"]
        expected_counts = {
            "temp": 2,
            "train": 1,
            "test": 1,
            "purged": 1,
        }
        
        for split in splits:
            response = app_client.get(f"/api/v1/media/list?split={split}&limit=100&offset=0")
            assert response.status_code == 200
            
            body = response.json()
            assert body["status"] == "success"
            data = body["data"]
            assert data["pagination"]["total"] == expected_counts[split]
            assert len(data["items"]) == expected_counts[split]
            
            # Verify all items have correct split
            for item in data["items"]:
                assert item["split"] == split
    
    def test_video_metadata_retrieval(self, app_client):
        """Test retrieving metadata for specific videos."""
        # Get video from temp
        response = app_client.get("/api/v1/media/video_temp1")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["video_id"] == "video_temp1"
        assert data["split"] == "temp"
        assert "file_path" in data
        assert "size_bytes" in data
        
        # Get video from purged
        response = app_client.get("/api/v1/media/video_purged1")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["video_id"] == "video_purged1"
        assert data["split"] == "purged"
    
    def test_thumbnail_retrieval(self, app_client):
        """Test thumbnail URL generation."""
        response = app_client.get("/api/v1/media/video_temp1/thumb")
        assert response.status_code == 200
        
        body = response.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["video_id"] == "video_temp1"
        assert "thumbnail_url" in data
        assert "video_temp1.jpg" in data["thumbnail_url"]
    
    def test_pagination_workflow(self, app_client):
        """Test pagination across multiple requests."""
        # Get first video
        response = app_client.get("/api/v1/media/list?split=temp&limit=1&offset=0")
        assert response.status_code == 200
        body1 = response.json()
        data1 = body1["data"]
        assert len(data1["items"]) == 1
        video1_id = data1["items"][0]["video_id"]
        
        # Get second video
        response = app_client.get("/api/v1/media/list?split=temp&limit=1&offset=1")
        assert response.status_code == 200
        body2 = response.json()
        data2 = body2["data"]
        assert len(data2["items"]) == 1
        video2_id = data2["items"][0]["video_id"]
        
        # Verify they're different
        assert video1_id != video2_id
        
        # Get both at once
        response = app_client.get("/api/v1/media/list?split=temp&limit=2&offset=0")
        assert response.status_code == 200
        body_all = response.json()
        data_all = body_all["data"]
        assert len(data_all["items"]) == 2
        all_ids = {item["video_id"] for item in data_all["items"]}
        assert video1_id in all_ids
        assert video2_id in all_ids


class TestLegacyCompatibility:
    """Test backward compatibility with legacy endpoints."""
    
    def test_legacy_endpoints_work(self, app_client):
        """Test that all legacy endpoints still function."""
        # Legacy list endpoint
        response = app_client.get("/api/videos/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        assert "X-API-Deprecated" in response.headers
        
        # Legacy compat list endpoint
        response = app_client.get("/api/media/videos/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        assert "X-API-Deprecated" in response.headers
        
        # Legacy health endpoint
        response = app_client.get("/media/health")
        assert response.status_code == 200
        assert "X-API-Deprecated" in response.headers
        
        # Legacy media root
        response = app_client.get("/api/media")
        assert response.status_code == 200
        assert "X-API-Deprecated" in response.headers
    
    def test_legacy_response_format_matches_v1(self, app_client):
        """Test that legacy endpoints return unwrapped format for backward compatibility."""
        # Get from v1 (wrapped format)
        response_v1 = app_client.get("/api/v1/media/list?split=temp&limit=10&offset=0")
        body_v1 = response_v1.json()
        assert body_v1["status"] == "success"
        data_v1 = body_v1["data"]
        
        # Get from legacy (unwrapped format for backward compatibility)
        response_legacy = app_client.get("/api/videos/list?split=temp&limit=10&offset=0")
        data_legacy = response_legacy.json()
        
        # Legacy returns unwrapped format
        assert "items" in data_legacy
        assert "total" in data_legacy
        assert "limit" in data_legacy
        assert "offset" in data_legacy
        
        # Data should match
        assert data_v1["pagination"]["total"] == data_legacy["total"]
        assert len(data_v1["items"]) == len(data_legacy["items"])


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_split_returns_422(self, app_client):
        """Test that invalid split parameter returns validation error."""
        response = app_client.get("/api/v1/media/list?split=invalid&limit=10&offset=0")
        assert response.status_code == 422
    
    def test_nonexistent_video_returns_404(self, app_client):
        """Test that non-existent video returns 404."""
        response = app_client.get("/api/v1/media/nonexistent_video")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_nonexistent_thumbnail_returns_404(self, app_client):
        """Test that non-existent thumbnail returns 404."""
        response = app_client.get("/api/v1/media/video_temp2/thumb")
        assert response.status_code == 404
    
    def test_limit_validation(self, app_client):
        """Test that limit parameter is validated."""
        # Too high
        response = app_client.get("/api/v1/media/list?split=temp&limit=2000&offset=0")
        assert response.status_code == 422
        
        # Too low
        response = app_client.get("/api/v1/media/list?split=temp&limit=0&offset=0")
        assert response.status_code == 422
        
        # Valid
        response = app_client.get("/api/v1/media/list?split=temp&limit=50&offset=0")
        assert response.status_code == 200
    
    def test_negative_offset_rejected(self, app_client):
        """Test that negative offset is rejected."""
        response = app_client.get("/api/v1/media/list?split=temp&limit=10&offset=-1")
        assert response.status_code == 422


class TestCORSConfiguration:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_present(self, app_client):
        """Test that CORS headers are present when enabled."""
        response = app_client.options(
            "/api/v1/media/list",
            headers={
                "Origin": "http://localhost:8501",
                "Access-Control-Request-Method": "GET",
            }
        )
        # CORS should be configured
        assert response.status_code in [200, 204]


class TestConfigurationValidation:
    """Test configuration validation."""
    
    def test_invalid_videos_root_fails(self):
        """Test that invalid videos root causes startup failure."""
        env_vars = {
            "REACHY_VIDEOS_ROOT": "/nonexistent/path",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            
            # Should raise ConfigurationError during validation
            from apps.api.app.config import ConfigurationError, load_and_validate_config
            with pytest.raises(ConfigurationError):
                load_and_validate_config(check_port=False)


class TestAPIDocumentation:
    """Test that API documentation is accessible."""
    
    def test_openapi_schema_accessible(self, app_client):
        """Test that OpenAPI schema is available."""
        response = app_client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check that v1 endpoints are documented
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/media/list" in schema["paths"]
    
    def test_swagger_ui_accessible(self, app_client):
        """Test that Swagger UI is accessible."""
        response = app_client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_accessible(self, app_client):
        """Test that ReDoc is accessible."""
        response = app_client.get("/redoc")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
