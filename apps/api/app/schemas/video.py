"""Pydantic schemas for video API responses."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EnhancedVideoMetadataPayload(BaseModel):
    """Enhanced video metadata with database fields."""
    
    schema_version: str = Field(default="v1")
    video_id: str  # UUID from database
    file_name: str
    file_path: str
    split: str
    label: Optional[str] = None
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: Optional[str] = None
    mtime: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    lookup_method: str = Field(
        default="filesystem",
        description="How video was found: uuid, file_path, or filesystem"
    )


class VideoSummary(BaseModel):
    """Summary of video metadata for list responses."""
    
    video_id: str
    file_name: str
    file_path: str
    split: str
    label: Optional[str] = None
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: str
    created_at: str
    updated_at: Optional[str] = None


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    
    limit: int
    offset: int
    total: int
    has_more: bool


class VideoListResponse(BaseModel):
    """Response for video listing endpoint."""
    
    status: str = "ok"
    videos: List[VideoSummary]
    pagination: PaginationInfo


class VideoUrlResponse(BaseModel):
    """Response for video URL generation endpoint."""
    
    status: str = "ok"
    video_id: str
    stream_url: str
    thumbnail_url: str
    expires_at: Optional[str] = None
