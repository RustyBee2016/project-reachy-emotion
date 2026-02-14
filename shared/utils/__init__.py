"""
Shared Utilities for Reachy Emotion Classification

This module provides common utilities used across the emotion classification pipeline:

- confidence_handler: Abstention mechanism for low-confidence predictions
- emotion_smoother: Temporal smoothing to prevent flicker/thrashing
- thumbnail_generator: Video thumbnail generation (existing)
"""

from shared.utils.confidence_handler import (
    ConfidenceHandler,
    ConfidenceResult,
    should_act,
    get_safe_emotion,
)

from shared.utils.emotion_smoother import (
    EmotionSmoother,
    SmoothedResult,
    SmoothingMode,
    create_smoother_30fps,
    create_smoother_15fps,
    create_smoother_10fps,
)

__all__ = [
    # Confidence handling
    "ConfidenceHandler",
    "ConfidenceResult",
    "should_act",
    "get_safe_emotion",
    # Emotion smoothing
    "EmotionSmoother",
    "SmoothedResult",
    "SmoothingMode",
    "create_smoother_30fps",
    "create_smoother_15fps",
    "create_smoother_10fps",
]
