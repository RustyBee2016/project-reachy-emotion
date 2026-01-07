"""Tests for emotion-conditioned dialogue generation endpoints."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response

from apps.api.app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_lm_studio_response():
    """Mock LM Studio API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": "I'm here with you. How's your day going? I noticed you might be feeling a little down. Want to talk about it?"
                }
            }
        ]
    }


class TestDialogueGeneration:
    """Tests for /api/v1/dialogue/generate endpoint."""
    
    def test_generate_dialogue_sad_emotion(self, client, mock_lm_studio_response):
        """Test dialogue generation for sad emotion."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock LM Studio response
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "sad",
                "confidence": 0.87,
                "user_message": "I'm having a rough day."
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "status" in data
            assert data["status"] == "success"
            assert "data" in data
            
            # Verify dialogue data
            dialogue = data["data"]
            assert "text" in dialogue
            assert "gesture" in dialogue
            assert "tone" in dialogue
            assert "emotion" in dialogue
            assert "confidence" in dialogue
            
            # Verify emotion-specific cues
            assert dialogue["emotion"] == "sad"
            assert dialogue["confidence"] == 0.87
            assert dialogue["gesture"] == "head_tilt_sympathetic"
            assert dialogue["tone"] == "gentle_supportive"
            assert len(dialogue["text"]) > 0
    
    def test_generate_dialogue_happy_emotion(self, client, mock_lm_studio_response):
        """Test dialogue generation for happy emotion."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "That's wonderful! I'm so happy for you!"}}]
            }
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "happy",
                "confidence": 0.92,
                "user_message": "I just got great news!"
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            dialogue = data["data"]
            
            assert dialogue["emotion"] == "happy"
            assert dialogue["gesture"] == "wave_enthusiastic"
            assert dialogue["tone"] == "warm_upbeat"
    
    def test_generate_dialogue_with_conversation_history(self, client, mock_lm_studio_response):
        """Test dialogue generation with conversation history."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "neutral",
                "confidence": 0.75,
                "user_message": "Tell me more.",
                "conversation_history": [
                    {"role": "user", "content": "Hi Reachy!"},
                    {"role": "assistant", "content": "Hello! How are you today?"}
                ]
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            
            # Verify LM Studio was called with history
            call_args = mock_post.call_args
            lm_payload = call_args[1]["json"]
            assert "messages" in lm_payload
            assert len(lm_payload["messages"]) >= 4  # system + emotion + history + current
    
    def test_generate_dialogue_low_confidence(self, client, mock_lm_studio_response):
        """Test dialogue generation with low confidence emotion."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "angry",
                "confidence": 0.55,  # Low confidence
                "user_message": "This is frustrating."
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            dialogue = data["data"]
            
            # Low confidence should result in neutral fallback
            assert dialogue["gesture"] == "neutral_stance"
            assert dialogue["tone"] == "neutral"
    
    def test_generate_dialogue_invalid_emotion(self, client):
        """Test dialogue generation with invalid emotion."""
        payload = {
            "emotion": "invalid_emotion",
            "confidence": 0.85,
            "user_message": "Hello"
        }
        
        response = client.post("/api/v1/dialogue/generate", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_dialogue_invalid_confidence(self, client):
        """Test dialogue generation with invalid confidence."""
        payload = {
            "emotion": "happy",
            "confidence": 1.5,  # Out of range
            "user_message": "Hello"
        }
        
        response = client.post("/api/v1/dialogue/generate", json=payload)
        
        assert response.status_code == 422
    
    def test_generate_dialogue_lm_studio_timeout(self, client):
        """Test handling of LM Studio timeout."""
        with patch("httpx.AsyncClient.post") as mock_post:
            from httpx import TimeoutException
            mock_post.side_effect = TimeoutException("Request timed out")
            
            payload = {
                "emotion": "sad",
                "confidence": 0.87,
                "user_message": "Hello"
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 504  # Gateway timeout
            data = response.json()
            assert "error" in data["detail"]
            assert data["detail"]["error"] == "lm_studio_timeout"
    
    def test_generate_dialogue_lm_studio_error(self, client):
        """Test handling of LM Studio error response."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 500
            mock_response.is_error = True
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "happy",
                "confidence": 0.90,
                "user_message": "Hello"
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 502  # Bad gateway
            data = response.json()
            assert "error" in data["detail"]
    
    def test_generate_dialogue_correlation_id_header(self, client, mock_lm_studio_response):
        """Test that correlation ID is returned in response header."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "neutral",
                "confidence": 0.80,
            }
            
            correlation_id = "test-correlation-123"
            response = client.post(
                "/api/v1/dialogue/generate",
                json=payload,
                headers={"X-Correlation-ID": correlation_id}
            )
            
            assert response.status_code == 200
            assert "X-Correlation-ID" in response.headers
            assert response.headers["X-Correlation-ID"] == correlation_id
    
    def test_generate_dialogue_all_emotion_types(self, client, mock_lm_studio_response):
        """Test dialogue generation for all supported emotion types."""
        emotions = ["happy", "sad", "angry", "neutral", "surprise", "fearful"]
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            for emotion in emotions:
                payload = {
                    "emotion": emotion,
                    "confidence": 0.85,
                    "user_message": "Test message"
                }
                
                response = client.post("/api/v1/dialogue/generate", json=payload)
                
                assert response.status_code == 200, f"Failed for emotion: {emotion}"
                data = response.json()
                assert data["data"]["emotion"] == emotion
    
    def test_dialogue_health_check(self, client):
        """Test dialogue service health check."""
        response = client.get("/api/v1/dialogue/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "dialogue"
        assert "correlation_id" in data


class TestDialoguePromptBuilding:
    """Tests for LM Studio prompt construction logic."""
    
    def test_prompt_includes_emotion_context(self, client, mock_lm_studio_response):
        """Test that prompts include emotion-specific guidance."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "sad",
                "confidence": 0.90,
                "user_message": "I'm feeling down."
            }
            
            client.post("/api/v1/dialogue/generate", json=payload)
            
            # Verify LM Studio was called
            call_args = mock_post.call_args
            lm_payload = call_args[1]["json"]
            messages = lm_payload["messages"]
            
            # Check that emotion context is in system messages
            system_messages = [m for m in messages if m["role"] == "system"]
            assert len(system_messages) >= 2
            
            # Verify emotion is mentioned
            emotion_context = " ".join([m["content"] for m in system_messages])
            assert "sad" in emotion_context.lower()
            assert "0.90" in emotion_context or "90" in emotion_context


class TestDialogueEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_generate_dialogue_without_user_message(self, client, mock_lm_studio_response):
        """Test dialogue generation without explicit user message."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lm_studio_response
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "happy",
                "confidence": 0.85,
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            # Should use default greeting
    
    def test_generate_dialogue_malformed_lm_response(self, client):
        """Test handling of malformed LM Studio response."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "structure"}
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "neutral",
                "confidence": 0.80,
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 502
            data = response.json()
            assert "lm_studio_response_error" in data["detail"]["error"]
    
    def test_generate_dialogue_empty_text_response(self, client):
        """Test handling of empty text from LM Studio."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "   "}}]  # Whitespace only
            }
            mock_post.return_value = mock_response
            
            payload = {
                "emotion": "neutral",
                "confidence": 0.80,
            }
            
            response = client.post("/api/v1/dialogue/generate", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            # Should strip whitespace
            assert len(data["data"]["text"]) == 0
