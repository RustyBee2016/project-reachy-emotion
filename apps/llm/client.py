"""
Empathetic LLM Client

Async client for OpenAI GPT-5.2 API with emotion-aware prompting
and gesture keyword extraction.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import json

import httpx

from apps.llm.config import LLMConfig
from apps.llm.prompts.emotion_prompts import EmotionPromptBuilder, EmotionContext
from apps.reachy.gestures.emotion_gesture_map import EmotionGestureMapper

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from the LLM with parsed gesture keywords."""
    content: str
    clean_content: str
    gesture_keywords: List[str]
    model: str
    usage: Dict[str, int]
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class ConversationMessage:
    """A message in the conversation history."""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EmpatheticLLMClient:
    """
    Async client for emotion-aware LLM interactions.
    
    Uses GPT-5.2 to generate empathetic responses based on detected emotions,
    with embedded gesture keywords for Reachy robot control.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize the LLM client.
        
        Args:
            config: LLM configuration. Uses defaults if not provided.
        """
        self.config = config or LLMConfig.from_env()
        self.prompt_builder = EmotionPromptBuilder(
            include_gestures=self.config.enable_gesture_keywords
        )
        self.gesture_mapper = EmotionGestureMapper()
        
        self._conversation_history: List[ConversationMessage] = []
        self._current_emotion: Optional[str] = None
        self._current_system_prompt: Optional[str] = None
        
        base_url = self.config.base_url or "https://api.openai.com/v1"
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout,
        )
        
        logger.info(f"EmpatheticLLMClient initialized with model: {self.config.model}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self) -> "EmpatheticLLMClient":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    def update_emotion_context(
        self,
        emotion: str,
        confidence: float = 1.0
    ) -> None:
        """
        Update the current emotion context.
        
        This will rebuild the system prompt if the emotion has changed.
        
        Args:
            emotion: Detected emotion label
            confidence: Confidence score (0-1)
        """
        if emotion != self._current_emotion:
            logger.info(f"Emotion context updated: {self._current_emotion} -> {emotion}")
            
            if self._current_emotion:
                self._current_system_prompt = self.prompt_builder.build_emotion_transition_prompt(
                    previous_emotion=self._current_emotion,
                    current_emotion=emotion,
                    confidence=confidence
                )
            else:
                self._current_system_prompt = self.prompt_builder.build_system_prompt(
                    emotion=emotion,
                    confidence=confidence
                )
            
            self._current_emotion = emotion
    
    async def generate_response(
        self,
        user_message: str,
        emotion: Optional[str] = None,
        confidence: float = 1.0,
        include_history: bool = True,
        max_history: int = 10
    ) -> LLMResponse:
        """
        Generate an empathetic response to the user message.
        
        Args:
            user_message: The user's message
            emotion: Detected emotion (updates context if provided)
            confidence: Emotion confidence score
            include_history: Whether to include conversation history
            max_history: Maximum history messages to include
            
        Returns:
            LLMResponse with content and gesture keywords
        """
        if emotion:
            self.update_emotion_context(emotion, confidence)
        
        messages = self._build_messages(
            user_message,
            include_history=include_history,
            max_history=max_history
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self._call_api(messages)
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            content = response["choices"][0]["message"]["content"]
            
            gesture_keywords = [
                kw.value for kw in 
                self.gesture_mapper.parse_keywords_from_response(content)
            ]
            clean_content = self.gesture_mapper.strip_keywords_from_response(content)
            
            self._conversation_history.append(
                ConversationMessage(role="user", content=user_message)
            )
            self._conversation_history.append(
                ConversationMessage(role="assistant", content=content)
            )
            
            llm_response = LLMResponse(
                content=content,
                clean_content=clean_content,
                gesture_keywords=gesture_keywords,
                model=response.get("model", self.config.model),
                usage=response.get("usage", {}),
                latency_ms=latency_ms
            )
            
            logger.info(
                f"LLM response generated in {latency_ms:.1f}ms, "
                f"gestures: {gesture_keywords}"
            )
            
            return llm_response
            
        except Exception as e:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"LLM API error after {latency_ms:.1f}ms: {e}")
            raise
    
    async def generate_response_stream(
        self,
        user_message: str,
        emotion: Optional[str] = None,
        confidence: float = 1.0
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response.
        
        Args:
            user_message: The user's message
            emotion: Detected emotion
            confidence: Emotion confidence score
            
        Yields:
            Response content chunks
        """
        if emotion:
            self.update_emotion_context(emotion, confidence)
        
        messages = self._build_messages(user_message)
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }
        
        full_content = ""
        
        async with self._client.stream(
            "POST",
            "/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                            yield content
                    except json.JSONDecodeError:
                        continue
        
        self._conversation_history.append(
            ConversationMessage(role="user", content=user_message)
        )
        self._conversation_history.append(
            ConversationMessage(role="assistant", content=full_content)
        )
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[ConversationMessage]:
        """Get conversation history."""
        return self._conversation_history.copy()
    
    def _build_messages(
        self,
        user_message: str,
        include_history: bool = True,
        max_history: int = 10
    ) -> List[Dict[str, str]]:
        """Build the messages array for the API call."""
        messages = []
        
        if self._current_system_prompt:
            messages.append({
                "role": "system",
                "content": self._current_system_prompt
            })
        else:
            default_prompt = self.prompt_builder.build_system_prompt("neutral")
            messages.append({
                "role": "system",
                "content": default_prompt
            })
        
        if include_history and self._conversation_history:
            history_slice = self._conversation_history[-max_history * 2:]
            for msg in history_slice:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make the API call with retry logic."""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        
        try:
            response = await self._client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and retry_count < self.config.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(f"Rate limited, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._call_api(messages, retry_count + 1)
            raise
            
        except httpx.TimeoutException:
            if retry_count < self.config.max_retries:
                logger.warning(f"Timeout, retrying ({retry_count + 1}/{self.config.max_retries})...")
                return await self._call_api(messages, retry_count + 1)
            raise


class MockEmpatheticLLMClient(EmpatheticLLMClient):
    """
    Mock LLM client for testing without API calls.
    
    Generates realistic mock responses with appropriate gesture keywords.
    """
    
    MOCK_RESPONSES = {
        "happy": [
            "That's wonderful to hear! [THUMBS_UP] I'm so glad things are going well for you. What's been the highlight of your day? [EXCITED]",
            "Your happiness is contagious! [CELEBRATE] Tell me more about what's making you feel so good today.",
            "I love seeing you in such great spirits! [NOD] Keep that positive energy going!",
        ],
        "sad": [
            "I hear you, and I'm here with you [LISTEN]. It's okay to feel this way [EMPATHY]. Would you like to talk about what's on your mind?",
            "That sounds really difficult [SAD_ACK]. I want you to know that your feelings are valid [COMFORT]. I'm here for you.",
            "I'm sorry you're going through this [EMPATHY]. Sometimes life can be really hard [HUG]. Take all the time you need.",
        ],
        "neutral": [
            "I'm here and listening [LISTEN]. How can I help you today? [NOD]",
            "Thanks for sharing that with me [NOD]. What else is on your mind?",
            "I appreciate you talking with me [WAVE]. Let me know how I can support you.",
        ],
        "anger": [
            "I can hear that you're really frustrated right now [LISTEN]. That makes complete sense. I'm not going anywhere — take all the time you need. [NOD]",
            "It sounds like things have been really difficult [LISTEN]. I want to understand. Can you tell me more about what's been happening? [NOD]",
            "Your frustration is completely valid [NOD]. I'm here to listen, not to judge. What would feel most helpful right now?",
        ],
        "fear": [
            "You are safe, and I am right here with you [COMFORT]. Take a slow breath — I'm not going anywhere. [EMPATHY]",
            "That sounds really frightening [EMPATHY]. It's okay to feel this way. I'm here as a steady presence for you. [COMFORT]",
            "I hear you, and I want you to know you're not alone [COMFORT]. We can take this one step at a time together. [NOD]",
        ],
        "disgust": [
            "That sounds like a really unpleasant experience [NOD]. I can understand why you'd feel that way. Can I ask what happened?",
            "I hear you — that's a strong reaction, and it makes sense [SHRUG]. Let's talk about what might help you move forward. [NOD]",
            "That sounds genuinely uncomfortable [LISTEN]. It's okay to name that feeling. What would feel better right now?",
        ],
        "contempt": [
            "I'm curious about what's behind that feeling [NOD]. It sounds like something really let you down. I'd like to understand more.",
            "I hear a lot of disappointment in what you're saying [LISTEN]. What happened that brought you to this point? [NOD]",
            "I want to make sure I understand what you're feeling [NOD]. Can you help me see it from your perspective?",
        ],
        "surprise": [
            "Oh wow, that does sound unexpected! [EXCITED] Tell me more — was this a good surprise or a difficult one? [NOD]",
            "That's quite something! [OPEN_ARMS] I'd love to hear all about it. How are you feeling now that the dust has settled?",
            "I can see why that caught you off guard [NOD]. How are you doing with it? [EXCITED]",
        ],
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize mock client without HTTP client."""
        self.config = config or LLMConfig()
        self.prompt_builder = EmotionPromptBuilder(
            include_gestures=self.config.enable_gesture_keywords
        )
        self.gesture_mapper = EmotionGestureMapper()
        
        self._conversation_history: List[ConversationMessage] = []
        self._current_emotion: Optional[str] = None
        self._current_system_prompt: Optional[str] = None
        self._response_index = 0
        
        logger.info("MockEmpatheticLLMClient initialized")
    
    async def close(self) -> None:
        """No-op for mock client."""
        pass
    
    async def generate_response(
        self,
        user_message: str,
        emotion: Optional[str] = None,
        confidence: float = 1.0,
        include_history: bool = True,
        max_history: int = 10
    ) -> LLMResponse:
        """Generate a mock response."""
        if emotion:
            self.update_emotion_context(emotion, confidence)
        
        emotion_key = (self._current_emotion or "neutral").lower()
        responses = self.MOCK_RESPONSES.get(emotion_key, self.MOCK_RESPONSES["neutral"])
        
        content = responses[self._response_index % len(responses)]
        self._response_index += 1
        
        await asyncio.sleep(0.1)
        
        gesture_keywords = [
            kw.value for kw in 
            self.gesture_mapper.parse_keywords_from_response(content)
        ]
        clean_content = self.gesture_mapper.strip_keywords_from_response(content)
        
        self._conversation_history.append(
            ConversationMessage(role="user", content=user_message)
        )
        self._conversation_history.append(
            ConversationMessage(role="assistant", content=content)
        )
        
        return LLMResponse(
            content=content,
            clean_content=clean_content,
            gesture_keywords=gesture_keywords,
            model="mock-gpt-5.2",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency_ms=100.0
        )


async def demo_llm_client():
    """Demo function to test the LLM client."""
    logging.basicConfig(level=logging.INFO)
    
    client = MockEmpatheticLLMClient()
    
    print("\n=== Empathetic LLM Client Demo ===\n")
    
    test_cases = [
        ("I'm feeling really down today...", "sad", 0.9),
        ("I just got promoted at work!", "happy", 0.95),
        ("Just checking in", "neutral", 0.6),
    ]
    
    for message, emotion, confidence in test_cases:
        print(f"User ({emotion}): {message}")
        
        response = await client.generate_response(
            user_message=message,
            emotion=emotion,
            confidence=confidence
        )
        
        print(f"Reachy: {response.clean_content}")
        print(f"  Gestures: {response.gesture_keywords}")
        print(f"  Latency: {response.latency_ms:.1f}ms")
        print()
    
    await client.close()
    print("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_llm_client())
