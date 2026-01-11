"""
Unit tests for the Empathetic LLM Client.

Tests the LLM client, prompt building, and response processing.
"""

import pytest
import asyncio

from apps.llm.client import (
    EmpatheticLLMClient,
    MockEmpatheticLLMClient,
    LLMResponse,
    ConversationMessage,
)
from apps.llm.config import LLMConfig
from apps.llm.prompts.emotion_prompts import (
    EmotionPromptBuilder,
    EmotionContext,
    EMOTION_SYSTEM_PROMPTS,
    GESTURE_INSTRUCTION_PROMPT,
)
from apps.llm.prompts.gesture_keywords import (
    GESTURE_KEYWORDS,
    KEYWORD_DESCRIPTIONS,
    get_keyword_list_for_prompt,
    get_keywords_for_emotion,
)


class TestLLMConfig:
    """Tests for LLMConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LLMConfig()
        
        assert config.max_tokens == 500
        assert config.temperature == 0.7
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.enable_gesture_keywords is True
    
    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.2-pro")
        monkeypatch.setenv("OPENAI_MAX_TOKENS", "1000")
        
        config = LLMConfig.from_env()
        
        assert config.api_key == "test-key-123"
        assert config.model == "gpt-5.2-pro"
        assert config.max_tokens == 1000
    
    def test_config_validate_with_key(self):
        """Test validation passes with API key."""
        config = LLMConfig(api_key="test-key")
        assert config.validate() is True
    
    def test_config_validate_without_key(self):
        """Test validation fails without API key."""
        config = LLMConfig(api_key="")
        assert config.validate() is False


class TestGestureKeywords:
    """Tests for gesture keyword definitions."""
    
    def test_all_keywords_have_descriptions(self):
        """Verify all keywords have descriptions."""
        for keyword in GESTURE_KEYWORDS:
            assert keyword in KEYWORD_DESCRIPTIONS, f"Missing description for {keyword}"
    
    def test_keyword_list_for_prompt(self):
        """Test generating keyword list for prompts."""
        keyword_list = get_keyword_list_for_prompt()
        
        assert "Available gesture keywords" in keyword_list
        assert "[WAVE]" in keyword_list
        assert "[HUG]" in keyword_list
        assert "[EMPATHY]" in keyword_list
    
    def test_keywords_for_happy_emotion(self):
        """Test getting keywords for happy emotion."""
        keywords = get_keywords_for_emotion("happy")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "THUMBS_UP" in keywords or "CELEBRATE" in keywords
    
    def test_keywords_for_sad_emotion(self):
        """Test getting keywords for sad emotion."""
        keywords = get_keywords_for_emotion("sad")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "EMPATHY" in keywords or "COMFORT" in keywords
    
    def test_keywords_for_unknown_emotion(self):
        """Test getting keywords for unknown emotion."""
        keywords = get_keywords_for_emotion("confused")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0


class TestEmotionPromptBuilder:
    """Tests for EmotionPromptBuilder."""
    
    @pytest.fixture
    def builder(self):
        """Create a prompt builder for testing."""
        return EmotionPromptBuilder(include_gestures=True)
    
    @pytest.fixture
    def builder_no_gestures(self):
        """Create a prompt builder without gestures."""
        return EmotionPromptBuilder(include_gestures=False)
    
    def test_build_happy_prompt(self, builder):
        """Test building prompt for happy emotion."""
        prompt = builder.build_system_prompt("happy")
        
        assert "happy" in prompt.lower() or "positive" in prompt.lower()
        assert "Reachy" in prompt
    
    def test_build_sad_prompt(self, builder):
        """Test building prompt for sad emotion."""
        prompt = builder.build_system_prompt("sad")
        
        assert "sad" in prompt.lower() or "support" in prompt.lower()
        assert "Reachy" in prompt
    
    def test_build_neutral_prompt(self, builder):
        """Test building prompt for neutral emotion."""
        prompt = builder.build_system_prompt("neutral")
        
        assert "Reachy" in prompt
    
    def test_unknown_emotion_uses_neutral(self, builder):
        """Test unknown emotion falls back to neutral."""
        prompt = builder.build_system_prompt("confused")
        neutral_prompt = builder.build_system_prompt("neutral")
        
        assert "Reachy" in prompt
    
    def test_prompt_includes_gestures(self, builder):
        """Test prompt includes gesture instructions."""
        prompt = builder.build_system_prompt("happy")
        
        assert "[" in prompt and "]" in prompt
        assert "gesture" in prompt.lower()
    
    def test_prompt_without_gestures(self, builder_no_gestures):
        """Test prompt without gesture instructions."""
        prompt = builder_no_gestures.build_system_prompt("happy")
        
        assert "Available gesture keywords" not in prompt
    
    def test_low_confidence_adds_note(self, builder):
        """Test low confidence adds uncertainty note."""
        prompt = builder.build_system_prompt("happy", confidence=0.5)
        
        assert "confidence" in prompt.lower() or "moderate" in prompt.lower()
    
    def test_high_confidence_no_note(self, builder):
        """Test high confidence doesn't add uncertainty note."""
        prompt = builder.build_system_prompt("happy", confidence=0.95)
        
        lines = prompt.split("\n")
        confidence_notes = [l for l in lines if "confidence is moderate" in l.lower()]
        assert len(confidence_notes) == 0
    
    def test_custom_context_included(self, builder):
        """Test custom context is included in prompt."""
        custom = "User prefers formal language."
        prompt = builder.build_system_prompt("happy", custom_context=custom)
        
        assert custom in prompt
    
    def test_emotion_transition_prompt(self, builder):
        """Test building emotion transition prompt."""
        prompt = builder.build_emotion_transition_prompt(
            previous_emotion="sad",
            current_emotion="happy",
            confidence=0.9
        )
        
        assert "sad" in prompt.lower()
        assert "happy" in prompt.lower()
        assert "transition" in prompt.lower() or "shifted" in prompt.lower()
    
    def test_user_message_with_context(self, builder):
        """Test building user message with emotion context."""
        context = EmotionContext(
            emotion="happy",
            confidence=0.85
        )
        
        message = builder.build_user_message_with_context(
            user_message="Hello!",
            emotion_context=context
        )
        
        assert "Hello!" in message
        assert "happy" in message.lower()
        assert "85%" in message or "0.85" in message
    
    def test_get_recommended_gestures(self, builder):
        """Test getting recommended gestures for emotion."""
        gestures = builder.get_recommended_gestures("sad")
        
        assert isinstance(gestures, list)
        assert len(gestures) > 0


class TestEmotionSystemPrompts:
    """Tests for emotion system prompts."""
    
    def test_happy_prompt_exists(self):
        """Verify happy system prompt exists."""
        assert "happy" in EMOTION_SYSTEM_PROMPTS
        assert len(EMOTION_SYSTEM_PROMPTS["happy"]) > 100
    
    def test_sad_prompt_exists(self):
        """Verify sad system prompt exists."""
        assert "sad" in EMOTION_SYSTEM_PROMPTS
        assert len(EMOTION_SYSTEM_PROMPTS["sad"]) > 100
    
    def test_neutral_prompt_exists(self):
        """Verify neutral system prompt exists."""
        assert "neutral" in EMOTION_SYSTEM_PROMPTS
    
    def test_prompts_mention_reachy(self):
        """Verify all prompts mention Reachy."""
        for emotion, prompt in EMOTION_SYSTEM_PROMPTS.items():
            assert "Reachy" in prompt, f"Prompt for {emotion} doesn't mention Reachy"
    
    def test_prompts_include_gesture_recommendations(self):
        """Verify prompts include gesture recommendations."""
        for emotion, prompt in EMOTION_SYSTEM_PROMPTS.items():
            assert "[" in prompt and "]" in prompt, \
                f"Prompt for {emotion} missing gesture keywords"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""
    
    def test_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Hello [WAVE]!",
            clean_content="Hello !",
            gesture_keywords=["WAVE"],
            model="gpt-5.2",
            usage={"total_tokens": 100},
            latency_ms=150.0
        )
        
        assert response.content == "Hello [WAVE]!"
        assert response.clean_content == "Hello !"
        assert "WAVE" in response.gesture_keywords
        assert response.model == "gpt-5.2"
        assert response.latency_ms == 150.0
    
    def test_response_has_timestamp(self):
        """Test response has automatic timestamp."""
        response = LLMResponse(
            content="Test",
            clean_content="Test",
            gesture_keywords=[],
            model="test",
            usage={},
            latency_ms=0
        )
        
        assert response.timestamp is not None
        assert "T" in response.timestamp


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""
    
    def test_message_creation(self):
        """Test creating a conversation message."""
        msg = ConversationMessage(
            role="user",
            content="Hello!"
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.timestamp is not None


class TestMockEmpatheticLLMClient:
    """Tests for MockEmpatheticLLMClient."""
    
    @pytest.fixture
    def client(self):
        """Create a mock client for testing."""
        return MockEmpatheticLLMClient()
    
    @pytest.mark.asyncio
    async def test_generate_response_happy(self, client):
        """Test generating response for happy emotion."""
        response = await client.generate_response(
            user_message="I'm feeling great!",
            emotion="happy",
            confidence=0.9
        )
        
        assert isinstance(response, LLMResponse)
        assert len(response.content) > 0
        assert len(response.gesture_keywords) > 0
    
    @pytest.mark.asyncio
    async def test_generate_response_sad(self, client):
        """Test generating response for sad emotion."""
        response = await client.generate_response(
            user_message="I'm feeling down...",
            emotion="sad",
            confidence=0.85
        )
        
        assert isinstance(response, LLMResponse)
        assert len(response.content) > 0
        
        sad_keywords = {"EMPATHY", "COMFORT", "HUG", "SAD_ACK", "LISTEN"}
        assert any(kw in sad_keywords for kw in response.gesture_keywords)
    
    @pytest.mark.asyncio
    async def test_generate_response_neutral(self, client):
        """Test generating response for neutral emotion."""
        response = await client.generate_response(
            user_message="Just checking in.",
            emotion="neutral",
            confidence=0.7
        )
        
        assert isinstance(response, LLMResponse)
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_clean_content_has_no_keywords(self, client):
        """Test clean content has keywords removed."""
        response = await client.generate_response(
            user_message="Hello!",
            emotion="happy"
        )
        
        assert "[" not in response.clean_content
        assert "]" not in response.clean_content
    
    @pytest.mark.asyncio
    async def test_conversation_history_updated(self, client):
        """Test conversation history is updated after response."""
        await client.generate_response(
            user_message="Hello!",
            emotion="neutral"
        )
        
        history = client.get_history()
        
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
    
    @pytest.mark.asyncio
    async def test_clear_history(self, client):
        """Test clearing conversation history."""
        await client.generate_response("Hello!", emotion="neutral")
        
        assert len(client.get_history()) > 0
        
        client.clear_history()
        
        assert len(client.get_history()) == 0
    
    @pytest.mark.asyncio
    async def test_emotion_context_update(self, client):
        """Test emotion context is updated."""
        client.update_emotion_context("happy", 0.9)
        
        assert client._current_emotion == "happy"
        assert client._current_system_prompt is not None
    
    @pytest.mark.asyncio
    async def test_emotion_transition(self, client):
        """Test emotion transition updates prompt."""
        client.update_emotion_context("happy", 0.9)
        first_prompt = client._current_system_prompt
        
        client.update_emotion_context("sad", 0.85)
        second_prompt = client._current_system_prompt
        
        assert first_prompt != second_prompt
        assert client._current_emotion == "sad"
    
    @pytest.mark.asyncio
    async def test_multiple_responses_vary(self, client):
        """Test multiple responses are not identical."""
        responses = []
        for _ in range(3):
            response = await client.generate_response(
                user_message="Hello!",
                emotion="happy"
            )
            responses.append(response.content)
        
        unique_responses = set(responses)
        assert len(unique_responses) >= 1
    
    @pytest.mark.asyncio
    async def test_close_is_noop(self, client):
        """Test close method doesn't raise."""
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client works as async context manager."""
        async with MockEmpatheticLLMClient() as client:
            response = await client.generate_response(
                user_message="Test",
                emotion="neutral"
            )
            assert response is not None
