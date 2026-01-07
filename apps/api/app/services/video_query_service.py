"""Service for querying video metadata from database and filesystem."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import models
from ..config import AppConfig


class VideoQueryService:
    """Handles video metadata queries with DB-first, filesystem-fallback strategy."""

    def __init__(self, session: AsyncSession, config: AppConfig):
        self._session = session
        self._config = config

    async def get_video_by_identifier(
        self, identifier: str
    ) -> tuple[models.Video | None, str]:
        """
        Get video by UUID or filename.
        
        Args:
            identifier: Video UUID or filename/path
        
        Returns:
            Tuple of (video_model, lookup_method)
            lookup_method is one of: "uuid", "file_path", "not_found"
        """
        # Try as UUID first
        if self._is_valid_uuid(identifier):
            video = await self._get_by_uuid(identifier)
            if video:
                return video, "uuid"
        
        # Try as file path (exact match)
        video = await self._get_by_file_path(identifier)
        if video:
            return video, "file_path"
        
        # Try with common variations
        video = await self._get_by_file_path_variations(identifier)
        if video:
            return video, "file_path"
        
        return None, "not_found"

    async def _get_by_uuid(self, video_id: str) -> models.Video | None:
        """Get video by UUID."""
        stmt = select(models.Video).where(models.Video.video_id == video_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_file_path(self, file_path: str) -> models.Video | None:
        """Get video by exact file path match."""
        stmt = select(models.Video).where(models.Video.file_path == file_path)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_file_path_variations(self, identifier: str) -> models.Video | None:
        """Try common file path variations."""
        # Remove leading slash if present
        identifier = identifier.lstrip("/")
        
        # Try with different split prefixes
        for split in ["temp", "dataset_all", "train", "test"]:
            # Try as-is
            path = f"{split}/{identifier}"
            video = await self._get_by_file_path(path)
            if video:
                return video
            
            # Try with .mp4 extension if not present
            if not identifier.endswith(".mp4"):
                path_with_ext = f"{split}/{identifier}.mp4"
                video = await self._get_by_file_path(path_with_ext)
                if video:
                    return video
        
        # Try searching by filename only (last component of path)
        filename = Path(identifier).name
        if filename != identifier:
            stmt = select(models.Video).where(
                models.Video.file_path.like(f"%/{filename}")
            )
            result = await self._session.execute(stmt)
            video = result.scalar_one_or_none()
            if video:
                return video
        
        return None

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
