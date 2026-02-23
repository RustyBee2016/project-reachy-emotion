"""Standard response schemas for consistent API responses.

All v1 API endpoints should use these response schemas to ensure
consistent structure across the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field


# Generic type for response data
T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata included in all API responses."""
    
    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for request tracing"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp in UTC"
    )
    version: str = Field(
        default="v1",
        description="API version"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""
    
    total: int = Field(description="Total number of items available")
    limit: int = Field(description="Maximum number of items per page")
    offset: int = Field(description="Current offset in the result set")
    has_more: bool = Field(description="Whether more items are available")
    
    @classmethod
    def from_params(cls, total: int, limit: int, offset: int) -> PaginationMeta:
        """Create pagination metadata from query parameters."""
        return cls(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )


class ErrorDetail(BaseModel):
    """Details about a specific error."""
    
    code: str = Field(description="Error code (e.g., NOT_FOUND, VALIDATION_ERROR)")
    message: str = Field(description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error (if applicable)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope.
    
    All successful API responses should use this structure.
    """
    
    status: str = Field(default="success", description="Response status")
    data: T = Field(description="Response payload")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")


class ErrorResponse(BaseModel):
    """Standard error response envelope.
    
    All error responses should use this structure.
    """
    
    status: str = Field(default="error", description="Response status")
    errors: List[ErrorDetail] = Field(description="List of errors")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Response metadata")


# ============================================================================
# Media API Response Models
# ============================================================================

class VideoMetadata(BaseModel):
    """Metadata for a single video file."""
    
    video_id: str = Field(description="Video identifier (filename without extension)")
    file_path: str = Field(description="Relative path from videos root")
    size_bytes: int = Field(description="File size in bytes")
    mtime: float = Field(description="Last modification time (Unix timestamp)")
    split: str = Field(description="Video split (temp, train, test, purged)")
    label: Optional[str] = Field(
        default=None,
        description="Emotion label when available (happy, sad, neutral).",
    )


class ListVideosData(BaseModel):
    """Data payload for list videos response."""
    
    items: List[VideoMetadata] = Field(description="List of video metadata")
    pagination: PaginationMeta = Field(description="Pagination information")


class ThumbnailData(BaseModel):
    """Data payload for thumbnail response."""
    
    video_id: str = Field(description="Video identifier")
    thumbnail_url: str = Field(description="URL to thumbnail image")


# Type aliases for cleaner code
ListVideosResponse = SuccessResponse[ListVideosData]
VideoMetadataResponse = SuccessResponse[VideoMetadata]
ThumbnailResponse = SuccessResponse[ThumbnailData]


# ============================================================================
# Health Check Response Models
# ============================================================================

class HealthCheckData(BaseModel):
    """Data payload for health check response."""
    
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    status: str = Field(description="Overall health status (healthy, degraded, unhealthy)")
    checks: Dict[str, Any] = Field(description="Individual health check results")


# Type alias for health check response
HealthCheckResponse = SuccessResponse[HealthCheckData]


# ============================================================================
# Helper Functions
# ============================================================================

def create_success_response(
    data: T,
    correlation_id: Optional[str] = None
) -> SuccessResponse[T]:
    """Create a standard success response.
    
    Args:
        data: Response payload
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Standardized success response
    """
    meta = ResponseMeta()
    if correlation_id:
        meta.correlation_id = correlation_id
    
    return SuccessResponse(data=data, meta=meta)


def create_error_response(
    errors: List[ErrorDetail],
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create a standard error response.
    
    Args:
        errors: List of error details
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Standardized error response
    """
    meta = ResponseMeta()
    if correlation_id:
        meta.correlation_id = correlation_id
    
    return ErrorResponse(errors=errors, meta=meta)


def create_single_error_response(
    code: str,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> ErrorResponse:
    """Create an error response with a single error.
    
    Args:
        code: Error code
        message: Error message
        field: Optional field that caused the error
        details: Optional additional details
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Standardized error response
    """
    error = ErrorDetail(
        code=code,
        message=message,
        field=field,
        details=details
    )
    return create_error_response([error], correlation_id)
