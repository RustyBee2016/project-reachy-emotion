"""
Integration tests for the Emotion-LLM-Gesture Pipeline.

Tests the full pipeline from emotion events through LLM response to gesture execution.
"""

import pytest
import asyncio
from datetime import datetime

from apps.pipeline.emotion_llm_gesture import (
    EmotionLLMGesturePipeline,
    PipelineConfig,
    PipelineState,
    EmotionEvent,
    PipelineResult,
)
from apps.llm.config import LLMConfig
from apps.reachy.config import ReachyConfig
from apps.reachy.gestures.gesture_controller import GestureResult


class TestPipelineConfig:
    """Tests for PipelineConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()
        
        assert config.use_mock_llm is False
        assert config.min_confidence_threshold == 0.6
        assert config.emotion_debounce_seconds == 2.0
        assert config.enable_gestures is True
        assert config.max_queue_size == 100
        assert config.response_timeout == 30.0
    
    def test_config_with_mock_llm(self):
        """Test configuration with mock LLM enabled."""
        config = PipelineConfig(use_mock_llm=True)
        
        assert config.use_mock_llm is True
    
    def test_config_with_simulation_reachy(self):
        """Test configuration with Reachy simulation mode."""
        reachy_config = ReachyConfig(simulation_mode=True)
        config = PipelineConfig(reachy_config=reachy_config)
        
        assert config.reachy_config.simulation_mode is True


class TestEmotionEvent:
    """Tests for EmotionEvent dataclass."""
    
    def test_event_creation(self):
        """Test creating an emotion event."""
        event = EmotionEvent(
            emotion="happy",
            confidence=0.92,
            device_id="reachy-mini-01",
            timestamp="2026-01-11T15:00:00Z"
        )
        
        assert event.emotion == "happy"
        assert event.confidence == 0.92
        assert event.device_id == "reachy-mini-01"
    
    def test_event_with_optional_fields(self):
        """Test event with optional fields."""
        event = EmotionEvent(
            emotion="sad",
            confidence=0.85,
            device_id="reachy-mini-01",
            timestamp="2026-01-11T15:00:00Z",
            frame_number=1234,
            inference_ms=45.2
        )
        
        assert event.frame_number == 1234
        assert event.inference_ms == 45.2


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a pipeline result."""
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp="2026-01-11T15:00:00Z"
        )
        
        result = PipelineResult(
            emotion_event=event,
            success=True,
            processing_time_ms=150.0
        )
        
        assert result.success is True
        assert result.processing_time_ms == 150.0
        assert result.error is None
    
    def test_result_with_error(self):
        """Test result with error."""
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp="2026-01-11T15:00:00Z"
        )
        
        result = PipelineResult(
            emotion_event=event,
            success=False,
            error="Connection failed"
        )
        
        assert result.success is False
        assert result.error == "Connection failed"


class TestEmotionLLMGesturePipeline:
    """Tests for EmotionLLMGesturePipeline."""
    
    @pytest.fixture
    def pipeline_config(self):
        """Create test pipeline configuration."""
        return PipelineConfig(
            use_mock_llm=True,
            reachy_config=ReachyConfig(simulation_mode=True),
            enable_gestures=True,
            min_confidence_threshold=0.6,
        )
    
    @pytest.fixture
    def pipeline(self, pipeline_config):
        """Create a pipeline instance for testing."""
        return EmotionLLMGesturePipeline(pipeline_config)
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.state == PipelineState.STOPPED
        assert pipeline.current_emotion is None
    
    @pytest.mark.asyncio
    async def test_pipeline_start_stop(self, pipeline):
        """Test starting and stopping the pipeline."""
        started = await pipeline.start()
        
        assert started is True
        assert pipeline.state == PipelineState.RUNNING
        
        await pipeline.stop()
        
        assert pipeline.state == PipelineState.STOPPED
    
    @pytest.mark.asyncio
    async def test_submit_emotion_event(self, pipeline):
        """Test submitting an emotion event."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        submitted = await pipeline.submit_emotion_event(event)
        
        assert submitted is True
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_reject_low_confidence_event(self, pipeline):
        """Test low confidence events are rejected."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.3,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        submitted = await pipeline.submit_emotion_event(event)
        
        assert submitted is False
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_reject_event_when_stopped(self, pipeline):
        """Test events are rejected when pipeline is stopped."""
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        submitted = await pipeline.submit_emotion_event(event)
        
        assert submitted is False
    
    @pytest.mark.asyncio
    async def test_process_emotion_with_message(self, pipeline):
        """Test processing emotion with user message."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="sad",
            confidence=0.88,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        result = await pipeline.process_emotion_with_message(
            event=event,
            user_message="I'm feeling down today."
        )
        
        assert result.success is True
        assert result.llm_response is not None
        assert len(result.llm_response.content) > 0
        assert result.processing_time_ms > 0
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_process_happy_emotion(self, pipeline):
        """Test processing happy emotion generates appropriate response."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.92,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        result = await pipeline.process_emotion_with_message(
            event=event,
            user_message="I got promoted today!"
        )
        
        assert result.success is True
        assert result.llm_response is not None
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_gestures_executed_from_response(self, pipeline):
        """Test gestures are executed from LLM response keywords."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="sad",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        result = await pipeline.process_emotion_with_message(
            event=event,
            user_message="I'm really struggling."
        )
        
        assert result.success is True
        
        if result.llm_response and result.llm_response.gesture_keywords:
            assert len(result.gesture_results) > 0
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_emotion_state_updated(self, pipeline):
        """Test emotion state is updated after processing."""
        await pipeline.start()
        
        assert pipeline.current_emotion is None
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(event, "Hello!")
        
        assert pipeline.current_emotion == "happy"
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_conversation_history_maintained(self, pipeline):
        """Test conversation history is maintained."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="neutral",
            confidence=0.8,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(event, "Hello!")
        await pipeline.process_emotion_with_message(event, "How are you?")
        
        history = pipeline.get_conversation_history()
        
        assert len(history) == 4
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_clear_conversation(self, pipeline):
        """Test clearing conversation history."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="neutral",
            confidence=0.8,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(event, "Hello!")
        
        assert len(pipeline.get_conversation_history()) > 0
        
        pipeline.clear_conversation()
        
        assert len(pipeline.get_conversation_history()) == 0
        assert pipeline.current_emotion is None
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, pipeline):
        """Test getting pipeline metrics."""
        await pipeline.start()
        
        metrics = pipeline.get_metrics()
        
        assert "state" in metrics
        assert "current_emotion" in metrics
        assert "queue_size" in metrics
        assert "gesture_controller_connected" in metrics
        
        assert metrics["state"] == "running"
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_response_callback(self, pipeline):
        """Test response callback is invoked."""
        callback_results = []
        
        def on_response(result: PipelineResult):
            callback_results.append(result)
        
        pipeline.set_response_callback(on_response)
        
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(event, "Great day!")
        
        assert len(callback_results) == 1
        assert callback_results[0].success is True
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_gesture_callback(self, pipeline):
        """Test gesture callback is set."""
        callback_invoked = []
        
        def on_gesture(result: GestureResult):
            callback_invoked.append(result)
        
        pipeline.set_gesture_callback(on_gesture)
        
        await pipeline.start()
        await pipeline.stop()


class TestPipelineEmotionTransitions:
    """Tests for emotion transition handling."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline for testing."""
        config = PipelineConfig(
            use_mock_llm=True,
            reachy_config=ReachyConfig(simulation_mode=True),
            emotion_debounce_seconds=0.1,
        )
        return EmotionLLMGesturePipeline(config)
    
    @pytest.mark.asyncio
    async def test_emotion_transition_sad_to_happy(self, pipeline):
        """Test transitioning from sad to happy emotion."""
        await pipeline.start()
        
        sad_event = EmotionEvent(
            emotion="sad",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(sad_event, "I'm sad.")
        assert pipeline.current_emotion == "sad"
        
        happy_event = EmotionEvent(
            emotion="happy",
            confidence=0.85,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(happy_event, "Actually, I feel better!")
        assert pipeline.current_emotion == "happy"
        
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_same_emotion_debounced(self, pipeline):
        """Test same emotion events are debounced."""
        await pipeline.start()
        
        event1 = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        await pipeline.process_emotion_with_message(event1, "Hello!")
        
        await pipeline.stop()


class TestPipelineWithoutGestures:
    """Tests for pipeline with gestures disabled."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline without gestures."""
        config = PipelineConfig(
            use_mock_llm=True,
            enable_gestures=False,
        )
        return EmotionLLMGesturePipeline(config)
    
    @pytest.mark.asyncio
    async def test_pipeline_works_without_gestures(self, pipeline):
        """Test pipeline works with gestures disabled."""
        await pipeline.start()
        
        event = EmotionEvent(
            emotion="happy",
            confidence=0.9,
            device_id="test",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        result = await pipeline.process_emotion_with_message(event, "Hello!")
        
        assert result.success is True
        assert result.llm_response is not None
        assert len(result.gesture_results) == 0
        
        await pipeline.stop()
