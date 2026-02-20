"""API schema exports for the Media Mover service."""

from .dialogue import (
    DialogueData,
    DialogueRequest,
    DialogueResponse,
)
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
from .train import (
    ExtractFramesRequest,
    ExtractFramesResponse,
    InitiateRunRequest,
    InitiateRunResponse,
    TrainingRunStatus,
)

__all__ = [
    # Dialogue schemas
    "DialogueRequest",
    "DialogueResponse",
    "DialogueData",
    # Promote schemas
    "StageRequest",
    "StageResponse",
    "SampleRequest",
    "SampleResponse",
    "ResetManifestRequest",
    "ResetManifestResponse",
    # Training schemas
    "ExtractFramesRequest",
    "ExtractFramesResponse",
    "InitiateRunRequest",
    "InitiateRunResponse",
    "TrainingRunStatus",
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
