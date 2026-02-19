"""Unit tests for video listing endpoints with pagination and filtering."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db import models


class TestVideoListing:
    """Test suite for GET /api/videos/list endpoint."""

    @pytest.mark.asyncio
    async def test_list_videos_empty_database(self, client: AsyncClient):
        """Test listing videos when database is empty."""
        # Act
        response = await client.get("/api/videos/list")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["videos"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_videos_basic(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test basic video listing without filters."""
        # Arrange - Create 5 videos
        for i in range(5):
            video = models.Video(
                file_path=f"temp/video_{i}.mp4",
                split="temp",
                size_bytes=1024 * (i + 1),
                sha256=f"sha_{i}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act
        response = await client.get("/api/videos/list")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 5
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_videos_with_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test video listing with pagination."""
        # Arrange - Create 100 videos
        for i in range(100):
            video = models.Video(
                file_path=f"temp/video_{i:03d}.mp4",
                split="temp",
                size_bytes=1024,
                sha256=f"sha_{i:03d}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act - Get first page
        response1 = await client.get("/api/videos/list?limit=20&offset=0")

        # Assert - First page
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["videos"]) == 20
        assert data1["pagination"]["limit"] == 20
        assert data1["pagination"]["offset"] == 0
        assert data1["pagination"]["total"] == 100
        assert data1["pagination"]["has_more"] is True

        # Act - Get second page
        response2 = await client.get("/api/videos/list?limit=20&offset=20")

        # Assert - Second page
        data2 = response2.json()
        assert len(data2["videos"]) == 20
        assert data2["pagination"]["offset"] == 20

        # Assert - Different videos on each page
        ids_page1 = {v["video_id"] for v in data1["videos"]}
        ids_page2 = {v["video_id"] for v in data2["videos"]}
        assert ids_page1.isdisjoint(ids_page2)

    @pytest.mark.asyncio
    async def test_list_videos_last_page(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test pagination on last page with partial results."""
        # Arrange - Create 45 videos
        for i in range(45):
            video = models.Video(
                file_path=f"temp/video_{i}.mp4",
                split="temp",
                size_bytes=1024,
                sha256=f"sha_{i}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act - Get last page (offset=40, limit=20)
        response = await client.get("/api/videos/list?limit=20&offset=40")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 5  # Only 5 remaining
        assert data["pagination"]["has_more"] is False


class TestVideoListingFilters:
    """Test filtering capabilities of video listing."""

    @pytest.mark.asyncio
    async def test_list_videos_filter_by_split(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test filtering videos by split."""
        # Arrange - Create videos in different splits
        splits_data = {
            "temp": 10,
            "purged": 20,
            "train": 15,
            "test": 5,
        }
        for split, count in splits_data.items():
            for i in range(count):
                video = models.Video(
                    file_path=f"{split}/video_{i}.mp4",
                    split=split,
                    label="happy" if split in ("train",) else None,
                    size_bytes=1024,
                    sha256=f"{split}_sha_{i}",
                )
                db_session.add(video)
        await db_session.commit()

        # Act - Filter by purged
        response = await client.get("/api/videos/list?split=purged")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 20
        assert all(v["split"] == "purged" for v in data["videos"])
        assert data["pagination"]["total"] == 20

    @pytest.mark.asyncio
    async def test_list_videos_filter_by_label(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test filtering videos by emotion label."""
        # Arrange - Create videos with different labels
        labels = ["happy", "sad", "neutral"]
        for label in labels:
            for i in range(5):
                video = models.Video(
                    file_path=f"train/{label}_{i}.mp4",
                    split="train",
                    label=label,
                    size_bytes=1024,
                    sha256=f"{label}_sha_{i}",
                )
                db_session.add(video)
        await db_session.commit()

        # Act - Filter by happy
        response = await client.get("/api/videos/list?label=happy")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 5
        assert all(v["label"] == "happy" for v in data["videos"])

    @pytest.mark.asyncio
    async def test_list_videos_filter_by_split_and_label(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test combining split and label filters."""
        # Arrange
        for label in ["happy", "sad"]:
            for i in range(3):
                video = models.Video(
                    file_path=f"train/{label}_{i}.mp4",
                    split="train",
                    label=label,
                    size_bytes=1024,
                    sha256=f"train_{label}_sha_{i}",
                )
                db_session.add(video)
        await db_session.commit()

        # Act - Filter by train split AND happy label
        response = await client.get("/api/videos/list?split=train&label=happy")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 3
        assert all(v["split"] == "train" for v in data["videos"])
        assert all(v["label"] == "happy" for v in data["videos"])

    @pytest.mark.asyncio
    async def test_list_videos_filter_no_matches(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test filtering with no matching results."""
        # Arrange - Create videos in temp
        for i in range(5):
            video = models.Video(
                file_path=f"temp/video_{i}.mp4",
                split="temp",
                size_bytes=1024,
                sha256=f"sha_{i}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act - Filter by non-existent split
        response = await client.get("/api/videos/list?split=purged")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 0
        assert data["pagination"]["total"] == 0


class TestVideoListingSorting:
    """Test sorting capabilities of video listing."""

    @pytest.mark.asyncio
    async def test_list_videos_default_sort_order(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test default sorting (created_at descending)."""
        # Arrange - Create videos with small delays to ensure different timestamps
        import asyncio

        for i in range(5):
            video = models.Video(
                file_path=f"temp/video_{i}.mp4",
                split="temp",
                size_bytes=1024,
                sha256=f"sha_{i}",
            )
            db_session.add(video)
            await db_session.flush()
            await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
        await db_session.commit()

        # Act
        response = await client.get("/api/videos/list")

        # Assert - Most recent first (created_at descending)
        assert response.status_code == 200
        data = response.json()
        
        # Verify we got all videos
        assert len(data["videos"]) == 5
        
        # Verify sort order: created_at timestamps should be in descending order
        returned_timestamps = [v.get("created_at") for v in data["videos"]]
        
        # All timestamps should be present
        assert all(ts is not None for ts in returned_timestamps), \
            "Some videos missing created_at timestamp"
        
        # Verify descending order (most recent first)
        # Timestamps are ISO format strings, so lexicographic comparison works
        for i in range(len(returned_timestamps) - 1):
            assert returned_timestamps[i] >= returned_timestamps[i + 1], \
                f"Timestamps not in descending order at index {i}: {returned_timestamps}"

    @pytest.mark.asyncio
    async def test_list_videos_sort_by_size(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test sorting by file size."""
        # Arrange - Create videos with different sizes
        sizes = [5000, 1000, 3000, 2000, 4000]
        for i, size in enumerate(sizes):
            video = models.Video(
                file_path=f"temp/video_{i}.mp4",
                split="temp",
                size_bytes=size,
                sha256=f"sha_{i}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act - Sort by size descending
        response = await client.get("/api/videos/list?order_by=size_bytes&order=desc")

        # Assert
        assert response.status_code == 200
        data = response.json()
        returned_sizes = [v["size_bytes"] for v in data["videos"]]
        assert returned_sizes == sorted(sizes, reverse=True)


class TestVideoListingValidation:
    """Test input validation for listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_videos_invalid_split(self, client: AsyncClient):
        """Test error handling for invalid split value."""
        # Act
        response = await client.get("/api/videos/list?split=invalid_split")

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_list_videos_invalid_label(self, client: AsyncClient):
        """Test error handling for invalid label value."""
        # Act
        response = await client.get("/api/videos/list?label=invalid_emotion")

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_videos_negative_limit(self, client: AsyncClient):
        """Test error handling for negative limit."""
        # Act
        response = await client.get("/api/videos/list?limit=-10")

        # Assert - FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_videos_negative_offset(self, client: AsyncClient):
        """Test error handling for negative offset."""
        # Act
        response = await client.get("/api/videos/list?offset=-5")

        # Assert - FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_videos_limit_exceeds_maximum(self, client: AsyncClient):
        """Test that limit exceeding maximum is rejected."""
        # Act
        response = await client.get("/api/videos/list?limit=10000")

        # Assert - FastAPI returns 422 for validation errors (limit > max)
        assert response.status_code == 422


class TestVideoListingPerformance:
    """Test performance characteristics of listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_videos_large_dataset_performance(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test listing performance with large dataset."""
        import time

        # Arrange - Create 1000 videos
        for i in range(1000):
            video = models.Video(
                file_path=f"temp/video_{i:04d}.mp4",
                split="temp",
                size_bytes=1024,
                sha256=f"sha_{i:04d}",
            )
            db_session.add(video)
            if i % 100 == 0:
                await db_session.flush()
        await db_session.commit()

        # Act
        start = time.time()
        response = await client.get("/api/videos/list?limit=50")
        duration_ms = (time.time() - start) * 1000

        # Assert
        assert response.status_code == 200
        assert duration_ms < 200, f"Query took {duration_ms}ms, expected < 200ms"

    @pytest.mark.asyncio
    async def test_list_videos_count_query_performance(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that count query doesn't cause full table scan."""
        # Arrange - Create videos with indexed columns
        for i in range(500):
            video = models.Video(
                file_path=f"train/video_{i}.mp4",
                split="train",
                label="happy",
                size_bytes=1024,
                sha256=f"sha_{i}",
            )
            db_session.add(video)
        await db_session.commit()

        # Act - Filter by indexed column
        import time

        start = time.time()
        response = await client.get("/api/videos/list?split=train&limit=10")
        duration_ms = (time.time() - start) * 1000

        # Assert - Should use index, be fast
        assert response.status_code == 200
        assert duration_ms < 100, f"Indexed query took {duration_ms}ms"


class TestVideoListingResponseFormat:
    """Test response format and schema compliance."""

    @pytest.mark.asyncio
    async def test_list_videos_response_schema(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that response matches expected schema."""
        # Arrange
        video = models.Video(
            file_path="temp/test.mp4",
            split="temp",
            size_bytes=1024,
            sha256="test_sha",
            duration_sec=5.0,
            fps=30.0,
            width=1920,
            height=1080,
        )
        db_session.add(video)
        await db_session.commit()

        # Act
        response = await client.get("/api/videos/list")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "status" in data
        assert "videos" in data
        assert "pagination" in data

        # Check video structure
        video_data = data["videos"][0]
        required_fields = [
            "video_id",
            "file_name",
            "file_path",
            "split",
            "size_bytes",
            "created_at",
        ]
        for field in required_fields:
            assert field in video_data, f"Missing field: {field}"

        # Check pagination structure
        pagination = data["pagination"]
        assert "limit" in pagination
        assert "offset" in pagination
        assert "total" in pagination
        assert "has_more" in pagination

    @pytest.mark.asyncio
    async def test_list_videos_includes_all_metadata(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test that all metadata fields are included in response."""
        # Arrange
        video = models.Video(
            file_path="train/complete.mp4",
            split="train",
            label="happy",
            size_bytes=2048,
            sha256="complete_sha",
            duration_sec=10.5,
            fps=60.0,
            width=3840,
            height=2160,
        )
        db_session.add(video)
        await db_session.commit()

        # Act
        response = await client.get("/api/videos/list?split=train")

        # Assert
        assert response.status_code == 200
        video_data = response.json()["videos"][0]
        assert video_data["label"] == "happy"
        assert video_data["duration_sec"] == 10.5
        assert video_data["fps"] == 60.0
        assert video_data["width"] == 3840
        assert video_data["height"] == 2160
        assert video_data["sha256"] == "complete_sha"
