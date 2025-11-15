"""API schema exports for the Media Mover service."""

from .promote import (
    ResetManifestRequest,
    ResetManifestResponse,
    SampleRequest,
    SampleResponse,
    StageRequest,
    StageResponse,
)
from .responses import (
    ErrorDetail,
    ErrorResponse,
    HealthCheckData,
    HealthCheckResponse,
    ListVideosData,
    ListVideosResponse,
    PaginationMeta,
    ResponseMeta,
    SuccessResponse,
    ThumbnailData,
    ThumbnailResponse,
    VideoMetadata,
    VideoMetadataResponse,
    create_error_response,
    create_single_error_response,
    create_success_response,
)

__all__ = [
    # Promote schemas
    "StageRequest",
    "StageResponse",
    "SampleRequest",
    "SampleResponse",
    "ResetManifestRequest",
    "ResetManifestResponse",
    # Response schemas
    "ResponseMeta",
    "PaginationMeta",
    "ErrorDetail",
    "SuccessResponse",
    "ErrorResponse",
    "VideoMetadata",
    "ListVideosData",
    "ListVideosResponse",
    "VideoMetadataResponse",
    "ThumbnailData",
    "ThumbnailResponse",
    "HealthCheckData",
    "HealthCheckResponse",
    # Helper functions
    "create_success_response",
    "create_error_response",
    "create_single_error_response",
]
