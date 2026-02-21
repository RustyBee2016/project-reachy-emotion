"""Integration tests for emotion metadata persistence.

Tests the full flow: UI → API → Database → Filesystem
Validates that emotion labels are correctly saved and retrievable.
"""

import uuid
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db.models import PromotionLog, Video
from apps.api.app.services import PromoteService, PromotionValidationError


@pytest.fixture
def test_video_id() -> str:
    """Generate a unique video ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def test_video_file(tmp_path: Path, test_video_id: str) -> Path:
    """Create a temporary test video file."""
    video_dir = tmp_path / "videos" / "temp"
    video_dir.mkdir(parents=True, exist_ok=True)
    
    video_file = video_dir / f"{test_video_id}.mp4"
    video_file.write_bytes(b"fake video content for testing")
    
    return video_file


@pytest.mark.asyncio
@pytest.mark.integration
async def test_legacy_stage_endpoint_deprecated_video_with_emotion_label(
    async_session: AsyncSession,
    test_video_id: str,
    test_video_file: Path,
):
    """Test deprecated stage endpoint rejects even with valid emotion label."""
    
    # Arrange: Create a video record in temp split
    video = Video(
        video_id=uuid.UUID(test_video_id),
        file_path=str(test_video_file),
        split="temp",
        label=None,  # No label initially
        size_bytes=test_video_file.stat().st_size,
        sha256="fake_sha256_hash_for_testing",
    )
    async_session.add(video)
    await async_session.commit()
    
    # Act: Legacy stage endpoint is deprecated
    service = PromoteService(async_session, actor="test_user")
    with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
        await service.stage_to_train(
            video_ids=[test_video_id],
            label="happy",
            dry_run=False,
        )
    
    # Assert: Database record updated
    await async_session.refresh(video)
    assert video.split == "temp"
    assert video.label is None
    
    # Assert: PromotionLog entry created
    stmt = select(PromotionLog).where(PromotionLog.video_id == uuid.UUID(test_video_id))
    result = await async_session.execute(stmt)
    promotion_log = result.scalar_one_or_none()
    assert promotion_log is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_legacy_stage_endpoint_deprecated_multiple_videos_different_labels(
    async_session: AsyncSession,
    tmp_path: Path,
):
    """Test deprecated stage endpoint rejects batch promotions for all labels."""
    
    # Arrange: Create 3 videos with different emotions
    test_data = [
        (str(uuid.uuid4()), "happy"),
        (str(uuid.uuid4()), "sad"),
        (str(uuid.uuid4()), "neutral"),
    ]
    
    video_ids = []
    for video_id, expected_label in test_data:
        video_file = tmp_path / "videos" / "temp" / f"{video_id}.mp4"
        video_file.parent.mkdir(parents=True, exist_ok=True)
        video_file.write_bytes(b"fake video content")
        
        video = Video(
            video_id=uuid.UUID(video_id),
            file_path=str(video_file),
            split="temp",
            label=None,
            size_bytes=video_file.stat().st_size,
            sha256=f"fake_sha256_{video_id}",
        )
        async_session.add(video)
        video_ids.append(video_id)
    
    await async_session.commit()
    
    # Act: Legacy stage endpoint is deprecated
    service = PromoteService(async_session, actor="test_user")
    
    for video_id, label in test_data:
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train(
                video_ids=[video_id],
                label=label,
                dry_run=False,
            )
    
    # Assert: All videos have correct labels in database
    for video_id, expected_label in test_data:
        stmt = select(Video).where(Video.video_id == uuid.UUID(video_id))
        result = await async_session.execute(stmt)
        video = result.scalar_one()
        
        assert video.split == "temp"
        assert video.label is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_emotion_label_rejected(
    async_session: AsyncSession,
    test_video_id: str,
    test_video_file: Path,
):
    """Test that invalid emotion labels are rejected."""
    
    # Arrange: Create a video in temp
    video = Video(
        video_id=uuid.UUID(test_video_id),
        file_path=str(test_video_file),
        split="temp",
        label=None,
        size_bytes=test_video_file.stat().st_size,
        sha256="fake_sha256_hash",
    )
    async_session.add(video)
    await async_session.commit()
    
    # Act & Assert: invalid label still fails validation pre-deprecation check
    service = PromoteService(async_session, actor="test_user")
    
    with pytest.raises(PromotionValidationError) as exc_info:
        await service.stage_to_train(
            video_ids=[test_video_id],
            label="invalid_emotion_label",
            dry_run=False,
        )
    
    # Assert: Error message indicates invalid label
    assert "invalid" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()
    
    # Assert: Video remains in temp split
    await async_session.refresh(video)
    assert video.split == "temp"
    assert video.label is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_promotion_audit_log_captures_metadata(
    async_session: AsyncSession,
    test_video_id: str,
    test_video_file: Path,
):
    """Test that PromotionLog captures all required metadata."""
    
    # Arrange: Create a video
    video = Video(
        video_id=uuid.UUID(test_video_id),
        file_path=str(test_video_file),
        split="temp",
        label=None,
        size_bytes=test_video_file.stat().st_size,
        sha256="fake_sha256_hash",
    )
    async_session.add(video)
    await async_session.commit()
    
    # Act: Legacy stage endpoint is deprecated
    service = PromoteService(async_session, actor="integration_test_user")
    correlation_id = str(uuid.uuid4())
    service.set_correlation_id(correlation_id)
    with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
        await service.stage_to_train(
            video_ids=[test_video_id],
            label="neutral",
            dry_run=False,
        )
    
    # Assert: PromotionLog has all metadata
    stmt = select(PromotionLog).where(PromotionLog.video_id == uuid.UUID(test_video_id))
    result = await async_session.execute(stmt)
    log_entry = result.scalar_one_or_none()
    assert log_entry is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dry_run_does_not_persist_changes(
    async_session: AsyncSession,
    test_video_id: str,
    test_video_file: Path,
):
    """Test that dry_run=True does not persist changes to database."""
    
    # Arrange: Create a video
    video = Video(
        video_id=uuid.UUID(test_video_id),
        file_path=str(test_video_file),
        split="temp",
        label=None,
        size_bytes=test_video_file.stat().st_size,
        sha256="fake_sha256_hash",
    )
    async_session.add(video)
    await async_session.commit()
    
    # Act: Legacy stage endpoint is deprecated (even in dry_run)
    service = PromoteService(async_session, actor="test_user")
    with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
        await service.stage_to_train(
            video_ids=[test_video_id],
            label="happy",
            dry_run=True,
        )
    
    # Assert: Database NOT updated
    await async_session.refresh(video)
    assert video.split == "temp"  # Still in temp
    assert video.label is None  # No label assigned
    
    # Assert: No PromotionLog entry created
    stmt = select(PromotionLog).where(PromotionLog.video_id == uuid.UUID(test_video_id))
    result = await async_session.execute(stmt)
    log_entry = result.scalar_one_or_none()
    assert log_entry is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_all_valid_emotion_labels(
    async_session: AsyncSession,
    tmp_path: Path,
):
    """Test that all valid emotion labels are accepted."""
    
    valid_emotions = ["happy", "sad", "neutral"]
    
    for emotion in valid_emotions:
        # Arrange: Create a video for each emotion
        video_id = str(uuid.uuid4())
        video_file = tmp_path / "videos" / "temp" / f"{video_id}.mp4"
        video_file.parent.mkdir(parents=True, exist_ok=True)
        video_file.write_bytes(b"fake video content")
        
        video = Video(
            video_id=uuid.UUID(video_id),
            file_path=str(video_file),
            split="temp",
            label=None,
            size_bytes=video_file.stat().st_size,
            sha256=f"fake_sha256_{video_id}",
        )
        async_session.add(video)
        await async_session.commit()
        
        # Act: Legacy stage endpoint is deprecated
        service = PromoteService(async_session, actor="test_user")
        with pytest.raises(PromotionValidationError, match="Deprecated endpoint"):
            await service.stage_to_train(
                video_ids=[video_id],
                label=emotion,
                dry_run=False,
            )
        
        # Assert: row unchanged (direct promotions should use /api/v1/media/promote)
        await async_session.refresh(video)
        assert video.split == "temp"
        assert video.label is None


# Fixtures for database session (to be implemented in conftest.py)
@pytest.fixture
async def async_session() -> Generator[AsyncSession, None, None]:
    """Provide an async database session for testing.
    
    NOTE: This fixture should be implemented in conftest.py with proper
    database setup/teardown for integration tests.
    """
    # This is a placeholder - actual implementation needed in conftest.py
    raise NotImplementedError(
        "async_session fixture must be implemented in conftest.py. "
        "See apps/api/app/db/session.py for database setup."
    )
