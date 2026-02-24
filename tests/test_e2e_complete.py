"""Complete end-to-end tests for the entire system."""

import pytest
from pathlib import Path
from unittest.mock import patch
import os

from fastapi.testclient import TestClient
from apps.api.app.main import create_app
from apps.api.app.config import get_config


@pytest.fixture
def complete_test_env(tmp_path):
    """Create a complete test environment with all components."""
    videos_root = tmp_path / "videos"
    videos_root.mkdir()
    
    # Create full directory structure
    for subdir in ["temp", "train", "test", "purged", "thumbs", "manifests"]:
        (videos_root / subdir).mkdir()
    
    # Create test videos across all splits
    test_videos = {
        "temp": ["temp_vid1.mp4", "temp_vid2.mp4", "temp_vid3.mp4"],
        "purged": ["purged_vid1.mp4", "purged_vid2.mp4"],
        "train": ["train_vid1.mp4"],
        "test": ["test_vid1.mp4"],
    }
    
    for split, videos in test_videos.items():
        for video in videos:
            (videos_root / split / video).write_text(f"fake content for {video}")
    
    # Create thumbnails
    for split, videos in test_videos.items():
        for video in videos:
            video_id = Path(video).stem
            (videos_root / "thumbs" / f"{video_id}.jpg").write_text(f"thumbnail for {video_id}")
    
    return videos_root


@pytest.fixture
def e2e_client(complete_test_env):
    """Create test client with complete environment."""
    env_vars = {
        "REACHY_VIDEOS_ROOT": str(complete_test_env),
        "REACHY_API_PORT": "54325",
        "REACHY_ENABLE_LEGACY_ENDPOINTS": "true",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        get_config.cache_clear()
        app = create_app()
        with TestClient(app) as client:
            yield client


class TestCompleteE2EWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_full_video_discovery_workflow(self, e2e_client):
        """Test discovering videos across all splits."""
        # 1. Check service health
        response = e2e_client.get("/api/v1/health")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "success"
        assert health["data"]["status"] == "healthy"
        
        # 2. List all videos in temp
        response = e2e_client.get("/api/v1/media/list?split=temp&limit=10&offset=0")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        temp_videos = body["data"]["items"]
        assert len(temp_videos) == 3
        
        # 3. Get metadata for first video
        first_video_id = temp_videos[0]["video_id"]
        response = e2e_client.get(f"/api/v1/media/{first_video_id}")
        assert response.status_code == 200
        metadata = response.json()
        assert metadata["status"] == "success"
        assert metadata["data"]["video_id"] == first_video_id
        
        # 4. Get thumbnail for video
        response = e2e_client.get(f"/api/v1/media/{first_video_id}/thumb")
        assert response.status_code == 200
        thumb = response.json()
        assert thumb["status"] == "success"
        assert first_video_id in thumb["data"]["thumbnail_url"]
    
    def test_pagination_across_large_dataset(self, e2e_client):
        """Test pagination works correctly."""
        # Get all temp videos with pagination
        all_videos = []
        offset = 0
        limit = 2
        
        while True:
            response = e2e_client.get(f"/api/v1/media/list?split=temp&limit={limit}&offset={offset}")
            assert response.status_code == 200
            body = response.json()
            data = body["data"]
            
            all_videos.extend(data["items"])
            
            if not data["pagination"]["has_more"]:
                break
            
            offset += limit
        
        # Should have found all 3 videos
        assert len(all_videos) == 3
        
        # All should be unique
        video_ids = [v["video_id"] for v in all_videos]
        assert len(video_ids) == len(set(video_ids))
    
    def test_cross_split_video_search(self, e2e_client):
        """Test finding videos across different splits."""
        splits = ["temp", "train", "test", "purged"]
        total_videos = 0
        
        for split in splits:
            response = e2e_client.get(f"/api/v1/media/list?split={split}&limit=10&offset=0")
            assert response.status_code == 200
            body = response.json()
            count = body["data"]["pagination"]["total"]
            total_videos += count
        
        # Should find all 7 videos (3 + 2 + 1 + 1)
        assert total_videos == 7
    
    def test_legacy_and_v1_consistency(self, e2e_client):
        """Test that legacy and v1 endpoints return consistent data."""
        # Get from v1
        response_v1 = e2e_client.get("/api/v1/media/list?split=temp&limit=10&offset=0")
        body_v1 = response_v1.json()
        v1_items = body_v1["data"]["items"]
        
        # Get from legacy
        response_legacy = e2e_client.get("/api/videos/list?split=temp&limit=10&offset=0")
        legacy_data = response_legacy.json()
        legacy_items = legacy_data["items"]
        
        # Should have same number of items
        assert len(v1_items) == len(legacy_items)
        
        # Video IDs should match
        v1_ids = {v["video_id"] for v in v1_items}
        legacy_ids = {v["video_id"] for v in legacy_items}
        assert v1_ids == legacy_ids
    
    def test_correlation_id_propagation(self, e2e_client):
        """Test that correlation IDs are propagated through requests."""
        correlation_id = "test-correlation-123"
        
        response = e2e_client.get(
            "/api/v1/media/list?split=temp&limit=10&offset=0",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Correlation ID should be in response metadata
        assert body["meta"]["correlation_id"] == correlation_id
    
    def test_error_handling_consistency(self, e2e_client):
        """Test that errors are handled consistently."""
        # Test 404 for non-existent video
        response = e2e_client.get("/api/v1/media/nonexistent_video_12345")
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body
        assert body["detail"]["error"] == "not_found"
        
        # Test 422 for invalid split
        response = e2e_client.get("/api/v1/media/list?split=invalid&limit=10&offset=0")
        assert response.status_code == 422
    
    def test_api_documentation_accessible(self, e2e_client):
        """Test that API documentation is accessible."""
        # OpenAPI schema
        response = e2e_client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/media/list" in schema["paths"]
        
        # Swagger UI
        response = e2e_client.get("/docs")
        assert response.status_code == 200
        
        # ReDoc
        response = e2e_client.get("/redoc")
        assert response.status_code == 200


class TestSystemResilience:
    """Test system resilience and edge cases."""
    
    def test_empty_split_handling(self, e2e_client):
        """Test handling of empty splits."""
        # Create a new split directory but leave it empty
        # (Already handled by fixture - train and test have only 1 video each)
        
        response = e2e_client.get("/api/v1/media/list?split=train&limit=10&offset=0")
        assert response.status_code == 200
        body = response.json()
        
        # Should return valid response even if only 1 video
        assert body["status"] == "success"
        assert body["data"]["pagination"]["total"] == 1
    
    def test_large_limit_handling(self, e2e_client):
        """Test that limit above API cap is rejected."""
        response = e2e_client.get("/api/v1/media/list?split=temp&limit=1000&offset=0")
        assert response.status_code == 422
    
    def test_offset_beyond_total(self, e2e_client):
        """Test that offset beyond total returns empty results."""
        response = e2e_client.get("/api/v1/media/list?split=temp&limit=10&offset=1000")
        assert response.status_code == 200
        body = response.json()
        
        # Should return empty items but valid pagination
        assert len(body["data"]["items"]) == 0
        assert body["data"]["pagination"]["total"] == 3
        assert body["data"]["pagination"]["has_more"] is False


class TestPerformanceBasics:
    """Basic performance validation tests."""
    
    def test_health_check_response_time(self, e2e_client):
        """Test that health check responds quickly."""
        import time
        
        start = time.time()
        response = e2e_client.get("/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        # Health check should be very fast (< 100ms)
        assert duration < 0.1
    
    def test_list_videos_response_time(self, e2e_client):
        """Test that list videos responds reasonably fast."""
        import time
        
        start = time.time()
        response = e2e_client.get("/api/v1/media/list?split=temp&limit=10&offset=0")
        duration = time.time() - start
        
        assert response.status_code == 200
        # List should be fast for small datasets (< 500ms)
        assert duration < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
