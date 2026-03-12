"""
Emotion-LLM-Gesture Pipeline

Main orchestrator that coordinates:
1. Receiving emotion events from Jetson edge device
2. Generating empathetic LLM responses based on detected emotions
3. Parsing gesture keywords from LLM responses
4. Dispatching gestures to Reachy robot

This is the central integration point for the emotion-driven interaction system.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from apps.llm.client import EmpatheticLLMClient, MockEmpatheticLLMClient, LLMResponse
from apps.llm.config import LLMConfig
from apps.reachy.config import ReachyConfig
from apps.reachy.gestures.gesture_controller import GestureController, GestureResult
from apps.reachy.gestures.emotion_gesture_map import (
    EmotionGestureMapper,
    KEYWORD_TO_GESTURE,
    GestureKeyword,
)
from apps.reachy.gestures.gesture_definitions import GESTURE_LIBRARY
from apps.reachy.gestures.gesture_modulator import GestureModulator

# Inference robustness utilities
from shared.utils.confidence_handler import ConfidenceHandler, ConfidenceResult
from shared.utils.emotion_smoother import EmotionSmoother, SmoothedResult, create_smoother_30fps

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    """Current state of the pipeline."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class PipelineConfig:
    """Configuration for the emotion-LLM-gesture pipeline."""
    
    llm_config: LLMConfig = field(default_factory=LLMConfig.from_env)
    reachy_config: ReachyConfig = field(default_factory=ReachyConfig.from_env)
    
    use_mock_llm: bool = False
    
    # Confidence threshold for abstention (returns "uncertain" if below)
    min_confidence_threshold: float = 0.6
    
    # Margin threshold between top-2 predictions
    confidence_margin_threshold: float = 0.15
    
    # Temporal smoothing settings
    enable_temporal_smoothing: bool = True
    smoothing_window_size: int = 15  # 0.5s at 30 FPS
    smoothing_min_consistency: float = 0.6  # 60% of window must agree
    
    emotion_debounce_seconds: float = 2.0
    
    enable_gestures: bool = True
    
    max_queue_size: int = 100
    
    response_timeout: float = 30.0


@dataclass
class EmotionEvent:
    """Emotion detection event from Jetson."""
    emotion: str
    confidence: float
    device_id: str
    timestamp: str
    frame_number: Optional[int] = None
    inference_ms: Optional[float] = None


@dataclass
class PipelineResult:
    """Result of processing an emotion event through the pipeline."""
    emotion_event: EmotionEvent
    llm_response: Optional[LLMResponse] = None
    gesture_results: List[GestureResult] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EmotionLLMGesturePipeline:
    """
    Main pipeline orchestrating emotion → LLM → gesture flow.
    
    This class:
    - Receives emotion events from the Jetson edge device
    - Generates context-aware LLM responses using GPT-5.2
    - Parses gesture keywords from LLM responses
    - Dispatches gestures to the Reachy robot
    - Manages conversation state and emotion transitions
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        
        self._state = PipelineState.STOPPED
        
        if self.config.use_mock_llm:
            self._llm_client: EmpatheticLLMClient = MockEmpatheticLLMClient(
                self.config.llm_config
            )
        else:
            self._llm_client = EmpatheticLLMClient(self.config.llm_config)
        
        self._gesture_controller = GestureController(self.config.reachy_config)
        self._gesture_mapper = EmotionGestureMapper()
        self._gesture_modulator = GestureModulator()
        
        # Initialize confidence handler for abstention
        self._confidence_handler = ConfidenceHandler(
            threshold=self.config.min_confidence_threshold,
            margin_threshold=self.config.confidence_margin_threshold,
        )
        
        # Initialize temporal smoother for flicker prevention
        self._emotion_smoother: Optional[EmotionSmoother] = None
        if self.config.enable_temporal_smoothing:
            self._emotion_smoother = EmotionSmoother(
                window_size=self.config.smoothing_window_size,
                min_consistency=self.config.smoothing_min_consistency,
            )
        
        self._event_queue: asyncio.Queue[EmotionEvent] = asyncio.Queue(
            maxsize=self.config.max_queue_size
        )
        
        self._current_emotion: Optional[str] = None
        self._last_emotion_time: Optional[datetime] = None
        self._emotion_history: List[EmotionEvent] = []
        
        self._on_response: Optional[Callable[[PipelineResult], Any]] = None
        self._on_gesture: Optional[Callable[[GestureResult], Any]] = None
        
        self._processing_task: Optional[asyncio.Task] = None
        
        logger.info("EmotionLLMGesturePipeline initialized")
    
    @property
    def state(self) -> PipelineState:
        """Get current pipeline state."""
        return self._state
    
    @property
    def current_emotion(self) -> Optional[str]:
        """Get the current detected emotion."""
        return self._current_emotion
    
    def set_response_callback(
        self,
        callback: Callable[[PipelineResult], Any]
    ) -> None:
        """Set callback for pipeline results."""
        self._on_response = callback
    
    def set_gesture_callback(
        self,
        callback: Callable[[GestureResult], Any]
    ) -> None:
        """Set callback for gesture completions."""
        self._on_gesture = callback
        self._gesture_controller.set_gesture_callback(callback)
    
    async def start(self) -> bool:
        """
        Start the pipeline.
        
        Returns:
            True if started successfully
        """
        if self._state == PipelineState.RUNNING:
            logger.warning("Pipeline already running")
            return True
        
        self._state = PipelineState.STARTING
        logger.info("Starting emotion-LLM-gesture pipeline...")
        
        try:
            if self.config.enable_gestures:
                connected = await self._gesture_controller.connect()
                if not connected:
                    logger.warning("Failed to connect to Reachy, continuing without gestures")
            
            self._processing_task = asyncio.create_task(self._process_events())
            
            self._state = PipelineState.RUNNING
            logger.info("Pipeline started successfully")
            return True
            
        except Exception as e:
            self._state = PipelineState.ERROR
            logger.error(f"Failed to start pipeline: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the pipeline."""
        logger.info("Stopping pipeline...")
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
        
        if self.config.enable_gestures:
            await self._gesture_controller.return_to_neutral()
            await self._gesture_controller.disconnect()
        
        await self._llm_client.close()
        
        self._state = PipelineState.STOPPED
        logger.info("Pipeline stopped")
    
    async def submit_emotion_event(self, event: EmotionEvent) -> bool:
        """
        Submit an emotion event for processing.
        
        Applies confidence thresholding and temporal smoothing before queuing.
        
        Args:
            event: Emotion detection event from Jetson
            
        Returns:
            True if event was queued successfully
        """
        if self._state != PipelineState.RUNNING:
            logger.warning(f"Cannot submit event, pipeline state: {self._state}")
            return False
        
        # Step 1: Check confidence threshold (abstention mechanism)
        confidence_result = self._confidence_handler.evaluate(
            emotion=event.emotion,
            confidence=event.confidence,
        )
        
        if not confidence_result.should_act:
            logger.debug(
                f"Abstaining from event: {event.emotion} ({event.confidence:.0%}) - "
                f"{confidence_result.reason}"
            )
            # Still feed to smoother for window tracking, but mark as uncertain
            if self._emotion_smoother:
                self._emotion_smoother.smooth("uncertain", 0.0)
            return False
        
        # Step 2: Apply temporal smoothing (flicker prevention)
        final_emotion = event.emotion
        final_confidence = event.confidence
        
        if self._emotion_smoother:
            smoothed = self._emotion_smoother.smooth(event.emotion, event.confidence)
            
            if not smoothed.is_stable:
                logger.debug(
                    f"Emotion not stable: {event.emotion} (consistency: {smoothed.consistency_ratio:.0%})"
                )
                # Don't queue unstable emotions - robot holds current gesture
                return False
            
            final_emotion = smoothed.emotion
            final_confidence = smoothed.confidence
            
            # If smoother returns uncertain, skip processing
            if final_emotion == "uncertain":
                logger.debug("Smoother returned uncertain, skipping")
                return False
        
        # Step 3: Queue the validated, smoothed event
        smoothed_event = EmotionEvent(
            emotion=final_emotion,
            confidence=final_confidence,
            device_id=event.device_id,
            timestamp=event.timestamp,
            frame_number=event.frame_number,
            inference_ms=event.inference_ms,
        )
        
        try:
            self._event_queue.put_nowait(smoothed_event)
            logger.debug(f"Queued smoothed emotion: {final_emotion} ({final_confidence:.0%})")
            return True
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
            return False
    
    async def process_emotion_with_message(
        self,
        event: EmotionEvent,
        user_message: str
    ) -> PipelineResult:
        """
        Process an emotion event with an explicit user message.
        
        This is the main entry point for interactive conversations where
        the user provides a message along with their detected emotion.
        
        Args:
            event: Emotion detection event
            user_message: User's spoken/typed message
            
        Returns:
            Pipeline result with LLM response and gesture results
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self._state = PipelineState.PROCESSING
            
            self._update_emotion_state(event)
            
            llm_response = await self._llm_client.generate_response(
                user_message=user_message,
                emotion=event.emotion,
                confidence=event.confidence
            )
            
            gesture_results = []
            if self.config.enable_gestures and llm_response.gesture_keywords:
                gesture_results = await self._execute_gestures_from_keywords(
                    llm_response.gesture_keywords
                )
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = PipelineResult(
                emotion_event=event,
                llm_response=llm_response,
                gesture_results=gesture_results,
                success=True,
                processing_time_ms=processing_time
            )
            
            if self._on_response:
                try:
                    self._on_response(result)
                except Exception as e:
                    logger.error(f"Response callback error: {e}")
            
            self._state = PipelineState.RUNNING
            return result
            
        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Pipeline processing error: {e}")
            
            self._state = PipelineState.RUNNING
            return PipelineResult(
                emotion_event=event,
                success=False,
                error=str(e),
                processing_time_ms=processing_time
            )
    
    async def _process_events(self) -> None:
        """Background task to process queued emotion events."""
        logger.info("Event processing loop started")
        
        while True:
            try:
                event = await self._event_queue.get()
                
                if self._should_process_emotion(event):
                    await self._handle_emotion_change(event)
                
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def _should_process_emotion(self, event: EmotionEvent) -> bool:
        """Check if emotion event should trigger processing."""
        if event.emotion != self._current_emotion:
            return True
        
        if self._last_emotion_time:
            elapsed = (datetime.utcnow() - self._last_emotion_time).total_seconds()
            if elapsed < self.config.emotion_debounce_seconds:
                return False
        
        return True
    
    def _update_emotion_state(self, event: EmotionEvent) -> None:
        """Update internal emotion state."""
        self._current_emotion = event.emotion
        self._last_emotion_time = datetime.utcnow()
        self._emotion_history.append(event)
        
        if len(self._emotion_history) > 100:
            self._emotion_history = self._emotion_history[-100:]
    
    async def _handle_emotion_change(self, event: EmotionEvent) -> None:
        """Handle a significant emotion change."""
        logger.info(f"Emotion change detected: {self._current_emotion} -> {event.emotion}")
        
        self._update_emotion_state(event)
        
        if self.config.enable_gestures:
            default_gesture = self._gesture_mapper.get_default_gesture(event.emotion)
            base_gesture = GESTURE_LIBRARY.get(default_gesture)
            if base_gesture:
                modulated = self._gesture_modulator.modulate(base_gesture, event.confidence)
                if modulated is not None:
                    await self._gesture_controller.execute_gesture(modulated)
                else:
                    logger.debug(
                        f"Emotion change gesture '{base_gesture.name}' suppressed "
                        f"(confidence {event.confidence:.2f} below abstain threshold)"
                    )
    
    async def _execute_gestures_from_keywords(
        self,
        keywords: List[str]
    ) -> List[GestureResult]:
        """Execute gestures based on parsed keywords."""
        results = []
        
        for keyword_str in keywords:
            try:
                keyword = GestureKeyword(keyword_str)
                gesture_type = KEYWORD_TO_GESTURE.get(keyword)
                
                if gesture_type:
                    base_gesture = GESTURE_LIBRARY.get(gesture_type)
                    if base_gesture:
                        confidence = getattr(
                            self._emotion_history[-1], "confidence", 1.0
                        ) if self._emotion_history else 1.0
                        gesture = self._gesture_modulator.modulate(base_gesture, confidence)
                        if gesture is None:
                            logger.debug(
                                f"Gesture '{base_gesture.name}' suppressed by modulator "
                                f"(confidence too low, abstaining)"
                            )
                            continue
                        result = await self._gesture_controller.execute_gesture(gesture)
                        results.append(result)
                        
                        await asyncio.sleep(0.3)
                        
            except (ValueError, KeyError) as e:
                logger.warning(f"Unknown gesture keyword: {keyword_str}")
        
        return results
    
    def get_conversation_history(self) -> List[dict]:
        """Get the current conversation history."""
        return [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in self._llm_client.get_history()
        ]
    
    def clear_conversation(self) -> None:
        """Clear conversation history and reset emotion state."""
        self._llm_client.clear_history()
        self._current_emotion = None
        self._last_emotion_time = None
        self._emotion_history.clear()
        logger.info("Conversation and emotion state cleared")
    
    def get_metrics(self) -> dict:
        """Get pipeline metrics."""
        metrics = {
            "state": self._state.value,
            "current_emotion": self._current_emotion,
            "queue_size": self._event_queue.qsize(),
            "emotion_history_length": len(self._emotion_history),
            "conversation_length": len(self._llm_client.get_history()),
            "gesture_controller_connected": self._gesture_controller.is_connected,
            "gesture_modulator_stats": self._gesture_modulator.stats,
            "gesture_modulator_last_expressiveness": (
                self._gesture_modulator.last_expressiveness.value
                if self._gesture_modulator.last_expressiveness else None
            ),
        }
        
        # Add smoother stats if enabled
        if self._emotion_smoother:
            smoother_stats = self._emotion_smoother.get_window_stats()
            metrics["smoother_window_size"] = smoother_stats.get("window_size", 0)
            metrics["smoother_last_stable"] = smoother_stats.get("last_stable_emotion")
            metrics["smoother_emotion_counts"] = smoother_stats.get("emotion_counts", {})
        
        return metrics


async def demo_pipeline():
    """Demo function to test the pipeline."""
    logging.basicConfig(level=logging.INFO)
    
    config = PipelineConfig(
        use_mock_llm=True,
        reachy_config=ReachyConfig(simulation_mode=True),
        enable_gestures=True,
    )
    
    pipeline = EmotionLLMGesturePipeline(config)
    
    def on_response(result: PipelineResult):
        print(f"\n--- Pipeline Result ---")
        print(f"Emotion: {result.emotion_event.emotion}")
        if result.llm_response:
            print(f"Response: {result.llm_response.clean_content}")
            print(f"Gestures: {result.llm_response.gesture_keywords}")
        print(f"Processing time: {result.processing_time_ms:.1f}ms")
    
    pipeline.set_response_callback(on_response)
    
    await pipeline.start()
    
    print("\n=== Emotion-LLM-Gesture Pipeline Demo ===\n")
    
    test_interactions = [
        (EmotionEvent(
            emotion="neutral",
            confidence=0.78,
            device_id="reachy-mini-01",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ), "Hi, I just wanted to check in and see how things are going."),
        
        (EmotionEvent(
            emotion="sad",
            confidence=0.92,
            device_id="reachy-mini-01",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ), "I've been feeling really down lately..."),
        
        (EmotionEvent(
            emotion="sad",
            confidence=0.85,
            device_id="reachy-mini-01",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ), "Work has been so stressful and I feel overwhelmed."),
        
        (EmotionEvent(
            emotion="happy",
            confidence=0.88,
            device_id="reachy-mini-01",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ), "Actually, I just remembered I got some good news today!"),
        
        (EmotionEvent(
            emotion="neutral",
            confidence=0.72,
            device_id="reachy-mini-01",
            timestamp=datetime.utcnow().isoformat() + "Z"
        ), "Thanks for listening. I feel a bit better now."),
    ]
    
    for event, message in test_interactions:
        print(f"\nUser ({event.emotion}): {message}")
        result = await pipeline.process_emotion_with_message(event, message)
        await asyncio.sleep(1)
    
    print("\n--- Pipeline Metrics ---")
    metrics = pipeline.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    await pipeline.stop()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_pipeline())
