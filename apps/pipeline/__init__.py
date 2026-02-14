"""
Emotion-LLM-Gesture Pipeline Module

Orchestrates the flow from emotion detection on Jetson to LLM response
generation and Reachy gesture execution.
"""

from apps.pipeline.emotion_llm_gesture import (
    EmotionLLMGesturePipeline,
    PipelineConfig,
    EmotionEvent,
    PipelineResult,
)

__all__ = [
    "EmotionLLMGesturePipeline",
    "PipelineConfig",
    "EmotionEvent",
    "PipelineResult",
]
__version__ = "0.1.0"
