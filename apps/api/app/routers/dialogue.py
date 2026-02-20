"""Dialogue generation endpoints for emotion-conditioned LM Studio interaction.

This router provides the emotion-aware dialogue generation system that bridges
EmotionNet classifications with LM Studio's conversational AI to produce
empathetic, context-appropriate responses for the Reachy robot.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..config import AppConfig, get_config
from ..schemas import (
    DialogueData,
    DialogueRequest,
    create_single_error_response,
    create_success_response,
)
from ..schemas.responses import SuccessResponse

router = APIRouter(prefix="/api/v1/dialogue", tags=["dialogue"])

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


def _resolve_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID from request headers."""
    header_value = request.headers.get(CORRELATION_ID_HEADER)
    if header_value:
        return header_value.strip()
    return str(uuid4())


def _build_lm_studio_prompt(
    emotion: str,
    confidence: float,
    user_message: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """Build emotion-conditioned prompt for LM Studio.
    
    Args:
        emotion: Detected emotion (happy, sad, neutral)
        confidence: Confidence score (0.0-1.0)
        user_message: Optional user message to respond to
        conversation_history: Optional prior conversation turns
        
    Returns:
        Messages array for LM Studio chat completion
    """
    messages = [
        {
            "role": "system",
            "content": "You are Reachy, a friendly and empathetic robot assistant."
        }
    ]
    
    # Add emotion context to system prompt
    emotion_guidance = {
        "happy": "The user appears happy and upbeat. Respond with enthusiasm and positive energy. Use encouraging language.",
        "sad": "The user appears sad or down. Respond with empathy, warmth, and supportive tone. Avoid jokes or overly cheerful language. Offer comfort.",
        "neutral": "The user appears calm and neutral. Respond in a balanced, friendly tone.",
    }
    
    guidance = emotion_guidance.get(emotion, emotion_guidance["neutral"])
    confidence_note = ""
    if confidence < 0.7:
        confidence_note = " (Note: emotion detection confidence is moderate, so maintain a neutral backup tone.)"
    
    messages.append({
        "role": "system",
        "content": f"User emotion: {emotion} (confidence: {confidence:.2f}). {guidance}{confidence_note}"
    })
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add current user message
    if user_message:
        messages.append({"role": "user", "content": user_message})
    else:
        # Default greeting if no message
        messages.append({"role": "user", "content": "Hi Reachy."})
    
    return messages


def _extract_gesture_cue(emotion: str, confidence: float) -> str:
    """Determine appropriate gesture based on emotion.
    
    Args:
        emotion: Detected emotion
        confidence: Confidence score
        
    Returns:
        Gesture identifier for robot SDK
    """
    if confidence < 0.6:
        return "neutral_stance"
    
    gesture_map = {
        "happy": "wave_enthusiastic",
        "sad": "head_tilt_sympathetic",
        "neutral": "neutral_stance",
    }
    
    return gesture_map.get(emotion, "neutral_stance")


def _extract_tone_cue(emotion: str, confidence: float) -> str:
    """Determine appropriate speech tone based on emotion.
    
    Args:
        emotion: Detected emotion
        confidence: Confidence score
        
    Returns:
        Tone descriptor for TTS system
    """
    if confidence < 0.6:
        return "neutral"
    
    tone_map = {
        "happy": "warm_upbeat",
        "sad": "gentle_supportive",
        "neutral": "neutral",
    }
    
    return tone_map.get(emotion, "neutral")


@router.post("/generate", response_model=SuccessResponse[DialogueData])
async def generate_dialogue(
    payload: DialogueRequest,
    request_ctx: Request,
    response: Response,
    config: AppConfig = Depends(get_config),
) -> SuccessResponse[DialogueData]:
    """Generate emotion-conditioned dialogue via LM Studio.
    
    This endpoint receives emotion classification data and optional conversation
    context, then calls LM Studio to generate an appropriate empathetic response
    with accompanying gesture and tone cues for the robot.
    
    Args:
        payload: Dialogue generation request with emotion and context
        request_ctx: FastAPI request object
        response: FastAPI response object
        config: Application configuration
        
    Returns:
        Dialogue response with text, gesture, and tone cues
        
    Raises:
        HTTPException: 400 for validation errors, 502 for LM Studio failures
    """
    correlation_id = _resolve_correlation_id(request_ctx)
    
    # Build LM Studio prompt
    messages = _build_lm_studio_prompt(
        emotion=payload.emotion,
        confidence=payload.confidence,
        user_message=payload.user_message,
        conversation_history=payload.conversation_history,
    )
    
    # Prepare LM Studio request
    lm_studio_url = f"http://{config.lm_studio_host}:{config.lm_studio_port}/v1/chat/completions"
    lm_studio_payload = {
        "model": "local-model",  # LM Studio uses this as default
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 150,
    }
    
    # Call LM Studio
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            lm_response = await client.post(
                lm_studio_url,
                json=lm_studio_payload,
                headers={"Content-Type": "application/json"},
            )
            
            if lm_response.status_code != 200:
                logger.error(
                    "lm_studio_error",
                    extra={
                        "status_code": lm_response.status_code,
                        "correlation_id": correlation_id,
                        "emotion": payload.emotion,
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "error": "lm_studio_error",
                        "message": "Failed to generate dialogue from LM Studio",
                        "correlation_id": correlation_id,
                    }
                )
            
            lm_data = lm_response.json()
            
    except httpx.TimeoutException:
        logger.error(
            "lm_studio_timeout",
            extra={"correlation_id": correlation_id, "emotion": payload.emotion}
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "lm_studio_timeout",
                "message": "LM Studio request timed out",
                "correlation_id": correlation_id,
            }
        )
    except httpx.RequestError as exc:
        logger.error(
            "lm_studio_connection_error",
            extra={
                "correlation_id": correlation_id,
                "emotion": payload.emotion,
                "error": str(exc),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "lm_studio_connection_error",
                "message": "Could not connect to LM Studio",
                "correlation_id": correlation_id,
            }
        )
    
    # Extract generated text
    try:
        generated_text = lm_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error(
            "lm_studio_response_parse_error",
            extra={
                "correlation_id": correlation_id,
                "response": lm_data,
                "error": str(exc),
            }
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "lm_studio_response_error",
                "message": "Invalid response format from LM Studio",
                "correlation_id": correlation_id,
            }
        )
    
    # Generate gesture and tone cues
    gesture = _extract_gesture_cue(payload.emotion, payload.confidence)
    tone = _extract_tone_cue(payload.emotion, payload.confidence)
    
    # Build response
    dialogue_data = DialogueData(
        text=generated_text.strip(),
        gesture=gesture,
        tone=tone,
        emotion=payload.emotion,
        confidence=payload.confidence,
    )
    
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    
    logger.info(
        "dialogue_generated",
        extra={
            "correlation_id": correlation_id,
            "emotion": payload.emotion,
            "confidence": payload.confidence,
            "gesture": gesture,
            "tone": tone,
        }
    )
    
    return create_success_response(dialogue_data, correlation_id)


@router.get("/health")
async def dialogue_health_check(request: Request) -> Dict[str, Any]:
    """Health check for dialogue service.
    
    Returns:
        Health status dictionary
    """
    return {
        "status": "ok",
        "service": "dialogue",
        "correlation_id": _resolve_correlation_id(request),
    }
