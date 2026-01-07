"""Schemas for emotion-conditioned dialogue generation."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DialogueRequest(BaseModel):
    """Request for emotion-conditioned dialogue generation.
    
    Attributes:
        emotion: Detected emotion (happy, sad, angry, neutral, surprise, fearful)
        confidence: Confidence score (0.0-1.0)
        user_message: Optional user message to respond to
        conversation_history: Optional prior conversation turns
        device_id: Optional device identifier for context
    """
    
    emotion: str = Field(
        ...,
        description="Detected emotion type",
        pattern="^(happy|sad|angry|neutral|surprise|fearful)$"
    )
    
    confidence: float = Field(
        ...,
        description="Emotion detection confidence",
        ge=0.0,
        le=1.0
    )
    
    user_message: Optional[str] = Field(
        None,
        description="User message to respond to",
        max_length=500
    )
    
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Prior conversation turns (role, content pairs)",
        max_length=10
    )
    
    device_id: Optional[str] = Field(
        None,
        description="Device identifier for context tracking",
        max_length=100
    )
    
    @field_validator("conversation_history")
    @classmethod
    def validate_conversation_history(cls, v: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        """Validate conversation history format."""
        if v is None:
            return v
        
        for turn in v:
            if "role" not in turn or "content" not in turn:
                raise ValueError("Each conversation turn must have 'role' and 'content' fields")
            if turn["role"] not in {"user", "assistant", "system"}:
                raise ValueError(f"Invalid role: {turn['role']}")
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "emotion": "sad",
                    "confidence": 0.87,
                    "user_message": "I'm having a rough day.",
                    "device_id": "reachy-mini-01"
                },
                {
                    "emotion": "happy",
                    "confidence": 0.92,
                    "user_message": "I just got great news!",
                    "conversation_history": [
                        {"role": "user", "content": "Hi Reachy!"},
                        {"role": "assistant", "content": "Hello! How are you today?"}
                    ],
                    "device_id": "reachy-mini-01"
                }
            ]
        }
    }


class DialogueData(BaseModel):
    """Dialogue generation response data.
    
    Attributes:
        text: Generated dialogue text
        gesture: Gesture cue for robot SDK
        tone: Tone descriptor for TTS system
        emotion: Original emotion input
        confidence: Original confidence input
    """
    
    text: str = Field(
        ...,
        description="Generated dialogue text for the robot to speak"
    )
    
    gesture: str = Field(
        ...,
        description="Gesture identifier for robot SDK"
    )
    
    tone: str = Field(
        ...,
        description="Tone descriptor for TTS system"
    )
    
    emotion: str = Field(
        ...,
        description="Original detected emotion"
    )
    
    confidence: float = Field(
        ...,
        description="Original emotion confidence"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "I'm here with you. How's your day going? I noticed you might be feeling a little down. Want to talk about it?",
                    "gesture": "head_tilt_sympathetic",
                    "tone": "gentle_supportive",
                    "emotion": "sad",
                    "confidence": 0.87
                }
            ]
        }
    }


# Import SuccessResponse first to avoid NameError
from .responses import SuccessResponse

# Type alias for the full response
DialogueResponse = SuccessResponse[DialogueData]  # type: ignore
