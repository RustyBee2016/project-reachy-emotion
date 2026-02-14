"""
LLM Prompts Module

Contains emotion-aware system prompts and gesture keyword definitions
for empathetic robot interaction.
"""

from apps.llm.prompts.emotion_prompts import (
    EmotionPromptBuilder,
    EMOTION_SYSTEM_PROMPTS,
    GESTURE_INSTRUCTION_PROMPT,
)
from apps.llm.prompts.gesture_keywords import (
    GESTURE_KEYWORDS,
    KEYWORD_DESCRIPTIONS,
)

__all__ = [
    "EmotionPromptBuilder",
    "EMOTION_SYSTEM_PROMPTS",
    "GESTURE_INSTRUCTION_PROMPT",
    "GESTURE_KEYWORDS",
    "KEYWORD_DESCRIPTIONS",
]
