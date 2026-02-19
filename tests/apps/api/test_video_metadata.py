"""Unit tests for video metadata endpoints with database integration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db import models


class TestVideoMetadataByUUID:
    """Test suite for getting video metadata using UUID."""

    @pytest.mark.asyncio
    async def test_get_video_metadata_by_uuid_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test successful retrieval of video metadata using UUID."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/test_video.mp4"
        
        # Create physical file
        create_test_video_file(file_path)
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=1048576,
            sha256="abc123def456",
            duration_sec=5.2,
            fps=30.0,
            width=1920,
            height=1080,
        )
        db_session.add(video)
        await db_session.commit()

        # Act
        response = await client.get(f"/api/videos/{video_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["video"]["video_id"] == video_id
        assert data["video"]["file_name"] == "test_video.mp4"
        assert data["video"]["file_path"] == "temp/test_video.mp4"
        assert data["video"]["split"] == "temp"
        assert data["video"]["size_bytes"] == 1048576
        assert data["video"]["duration_sec"] == 5.2
        assert data["video"]["fps"] == 30.0
        assert data["video"]["width"] == 1920
        assert data["video"]["height"] == 1080
        assert data["video"]["sha256"] == "abc123def456"

    @pytest.mark.asyncio
    async def test_get_video_metadata_with_label(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test video metadata includes label when present."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "train/happy_video.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="train",
            label="happy",
            size_bytes=2097152,
            sha256="happy123",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act
        response = await client.get(f"/api/videos/{video_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["video"]["label"] == "happy"
        assert data["video"]["split"] == "train"

    @pytest.mark.asyncio
    async def test_get_video_metadata_uuid_not_found(self, client: AsyncClient):
        """Test 404 when video UUID doesn't exist."""
        # Arrange
        nonexistent_uuid = str(uuid.uuid4())

        # Act
        response = await client.get(f"/api/videos/{nonexistent_uuid}")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]["message"].lower()
        assert data["detail"]["error"] == "not_found"


class TestVideoMetadataByFilename:
    """Test suite for backward compatibility with filename-based lookups."""

    @pytest.mark.asyncio
    async def test_get_video_metadata_by_filename(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test getting video metadata using filename (legacy support)."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/luma_1.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=1048576,
            sha256="luma_sha",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act - Use filename instead of UUID
        response = await client.get("/api/videos/luma_1.mp4")

        # Assert - Should return UUID from database
        assert response.status_code == 200
        data = response.json()
        assert data["video"]["video_id"] == video_id
        assert data["video"]["file_name"] == "luma_1.mp4"

    @pytest.mark.asyncio
    async def test_get_video_metadata_by_stem(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test getting video metadata using filename stem (no extension)."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/my_video.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=512000,
            sha256="stem_sha",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act - Use stem without extension
        response = await client.get("/api/videos/my_video")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["video"]["video_id"] == video_id

    @pytest.mark.asyncio
    async def test_get_video_metadata_filename_not_found(self, client: AsyncClient):
        """Test 404 when filename doesn't exist in database or filesystem."""
        # Act
        response = await client.get("/api/videos/nonexistent_video.mp4")

        # Assert
        assert response.status_code == 404


class TestVideoMetadataEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_get_video_metadata_invalid_uuid_format(self, client: AsyncClient):
        """Test handling of malformed UUID."""
        # Act
        response = await client.get("/api/videos/not-a-valid-uuid")

        # Assert
        # Should try as filename first, then return 404
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_video_metadata_null_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test video with minimal metadata (null optional fields)."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/minimal.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=1024,
            sha256="minimal_sha",
            # duration_sec, fps, width, height are None
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act
        response = await client.get(f"/api/videos/{video_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["video"]["duration_sec"] is None
        assert data["video"]["fps"] is None
        assert data["video"]["width"] is None
        assert data["video"]["height"] is None

    @pytest.mark.asyncio
    async def test_get_video_metadata_special_characters_in_path(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test video with special characters in file path."""
        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/video with spaces & special-chars_123.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=2048,
            sha256="special_sha",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act
        response = await client.get(f"/api/videos/{video_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "video with spaces & special-chars_123.mp4" in data["video"]["file_path"]


class TestVideoMetadataPerformance:
    """Test performance characteristics of metadata endpoint."""

    @pytest.mark.asyncio
    async def test_get_video_metadata_response_time(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test that metadata retrieval is fast (< 100ms)."""
        import time

        # Arrange
        video_id = str(uuid.uuid4())
        file_path = "temp/perf_test.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path,
            split="temp",
            size_bytes=1048576,
            sha256="perf_sha",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path)

        # Act
        start = time.time()
        response = await client.get(f"/api/videos/{video_id}")
        duration_ms = (time.time() - start) * 1000

        # Assert
        assert response.status_code == 200
        assert duration_ms < 100, f"Response took {duration_ms}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_get_video_metadata_concurrent_requests(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test handling of concurrent metadata requests."""
        import asyncio

        # Arrange
        video_ids = []
        for i in range(10):
            video_id = str(uuid.uuid4())
            file_path = f"temp/concurrent_{i}.mp4"
            
            video = models.Video(
                video_id=video_id,
                file_path=file_path,
                split="temp",
                size_bytes=1024 * i,
                sha256=f"concurrent_sha_{i}",
            )
            db_session.add(video)
            video_ids.append(video_id)
            
            # Create physical file for each video
            create_test_video_file(file_path)
            
        await db_session.commit()

        # Act - Make 10 concurrent requests
        tasks = [client.get(f"/api/videos/{vid}") for vid in video_ids]
        responses = await asyncio.gather(*tasks)

        # Assert - All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 10


class TestVideoMetadataIntegration:
    """Integration tests combining database and filesystem operations."""

    @pytest.mark.asyncio
    async def test_video_metadata_after_promotion(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        create_test_video_file,
    ):
        """Test that metadata reflects changes after video promotion."""
        # Arrange - Create video in temp
        video_id = str(uuid.uuid4())
        file_path_temp = "temp/to_promote.mp4"
        
        video = models.Video(
            video_id=video_id,
            file_path=file_path_temp,
            split="temp",
            size_bytes=1048576,
            sha256="promote_sha",
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(file_path_temp)

        # Act 1 - Get initial metadata
        response1 = await client.get(f"/api/videos/{video_id}")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["video"]["split"] == "temp"
        assert data1["video"]["label"] is None

        # Act 2 - Simulate promotion (update DB directly for test)
        video.split = "train"
        video.label = "happy"
        file_path_promoted = "train/to_promote.mp4"
        video.file_path = file_path_promoted
        await db_session.commit()
        
        # Create physical file in new location
        create_test_video_file(file_path_promoted)

        # Act 3 - Get updated metadata
        response2 = await client.get(f"/api/videos/{video_id}")

        # Assert - Metadata should reflect promotion
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["video"]["split"] == "train"
        assert data2["video"]["label"] == "happy"
        assert "train" in data2["video"]["file_path"]


# Pytest fixtures would be defined in conftest.py
# Example fixture signatures:
"""
@pytest.fixture
async def client() -> AsyncClient:
    # Return test client
    pass

@pytest.fixture
async def db_session() -> AsyncSession:
    # Return test database session
    pass
"""
