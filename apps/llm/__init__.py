"""
LLM Integration Module

Provides empathetic LLM interaction using OpenAI GPT-5.2 for emotion-aware
responses that drive Reachy robot gestures.
"""

from apps.llm.config import LLMConfig
from apps.llm.client import EmpatheticLLMClient

__all__ = ["LLMConfig", "EmpatheticLLMClient"]
__version__ = "0.1.0"
