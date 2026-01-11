"""
WebSocket Cue Handler for Reachy Gesture Routing

Handles incoming cues from the gateway and routes gesture commands
to the Reachy gesture controller.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from apps.reachy.config import ReachyConfig
from apps.reachy.gestures.gesture_controller import GestureController, GestureResult
from apps.reachy.gestures.gesture_definitions import GestureType, GESTURE_LIBRARY
from apps.reachy.gestures.emotion_gesture_map import GestureKeyword, KEYWORD_TO_GESTURE

logger = logging.getLogger(__name__)


@dataclass
class CueResult:
    """Result of processing a cue."""
    success: bool
    cue_type: str
    gesture_name: Optional[str] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class ReachyCueHandler:
    """
    Handles WebSocket cues and routes them to appropriate Reachy actions.
    
    Supports:
    - Gesture cues: Execute physical gestures on Reachy
    - TTS cues: Text-to-speech (future)
    - Expression cues: Facial expressions (future)
    """
    
    def __init__(
        self,
        config: Optional[ReachyConfig] = None,
        gesture_controller: Optional[GestureController] = None
    ):
        """
        Initialize the cue handler.
        
        Args:
            config: Reachy configuration
            gesture_controller: Optional pre-configured gesture controller
        """
        self.config = config or ReachyConfig.from_env()
        
        if gesture_controller:
            self._gesture_controller = gesture_controller
        else:
            self._gesture_controller = GestureController(self.config)
        
        self._connected = False
        self._cues_processed = 0
        self._cues_failed = 0
        
        self._on_cue_complete: Optional[Callable[[CueResult], Any]] = None
        
        logger.info("ReachyCueHandler initialized")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Reachy."""
        return self._connected and self._gesture_controller.is_connected
    
    async def connect(self) -> bool:
        """
        Connect to Reachy robot.
        
        Returns:
            True if connection successful
        """
        try:
            self._connected = await self._gesture_controller.connect()
            logger.info(f"Cue handler connected: {self._connected}")
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect cue handler: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Reachy robot."""
        await self._gesture_controller.disconnect()
        self._connected = False
        logger.info("Cue handler disconnected")
    
    def set_completion_callback(
        self,
        callback: Callable[[CueResult], Any]
    ) -> None:
        """Set callback for cue completion."""
        self._on_cue_complete = callback
    
    async def handle_cue(self, cue_data: Dict[str, Any]) -> CueResult:
        """
        Handle an incoming cue from the gateway.
        
        Args:
            cue_data: Cue data dictionary with:
                - type: str ("gesture", "tts", "expression")
                - gesture_type: str (for gesture cues)
                - correlation_id: str (optional)
                - Additional type-specific fields
        
        Returns:
            CueResult with success status and details
        """
        cue_type = cue_data.get("type", "unknown").lower()
        correlation_id = cue_data.get("correlation_id")
        
        logger.info(f"Handling cue: type={cue_type}, correlation_id={correlation_id}")
        
        try:
            if cue_type == "gesture":
                result = await self._handle_gesture_cue(cue_data)
            elif cue_type == "tts":
                result = await self._handle_tts_cue(cue_data)
            elif cue_type == "expression":
                result = await self._handle_expression_cue(cue_data)
            else:
                result = CueResult(
                    success=False,
                    cue_type=cue_type,
                    error=f"Unknown cue type: {cue_type}",
                    correlation_id=correlation_id
                )
            
            if result.success:
                self._cues_processed += 1
            else:
                self._cues_failed += 1
            
            if self._on_cue_complete:
                try:
                    callback_result = self._on_cue_complete(result)
                    if asyncio.iscoroutine(callback_result):
                        await callback_result
                except Exception as e:
                    logger.error(f"Cue completion callback error: {e}")
            
            return result
            
        except Exception as e:
            self._cues_failed += 1
            logger.error(f"Error handling cue: {e}")
            return CueResult(
                success=False,
                cue_type=cue_type,
                error=str(e),
                correlation_id=correlation_id
            )
    
    async def _handle_gesture_cue(self, cue_data: Dict[str, Any]) -> CueResult:
        """Handle a gesture cue."""
        gesture_type_str = cue_data.get("gesture_type", "").upper()
        correlation_id = cue_data.get("correlation_id")
        
        gesture_type = self._resolve_gesture_type(gesture_type_str)
        
        if gesture_type is None:
            return CueResult(
                success=False,
                cue_type="gesture",
                error=f"Unknown gesture type: {gesture_type_str}",
                correlation_id=correlation_id
            )
        
        gesture = GESTURE_LIBRARY.get(gesture_type)
        if gesture is None:
            return CueResult(
                success=False,
                cue_type="gesture",
                error=f"Gesture not in library: {gesture_type.name}",
                correlation_id=correlation_id
            )
        
        gesture_result = await self._gesture_controller.execute_gesture(gesture)
        
        return CueResult(
            success=gesture_result.success,
            cue_type="gesture",
            gesture_name=gesture_result.gesture_name,
            duration_ms=gesture_result.duration_ms,
            error=gesture_result.error,
            correlation_id=correlation_id
        )
    
    async def _handle_tts_cue(self, cue_data: Dict[str, Any]) -> CueResult:
        """Handle a TTS cue (placeholder for future implementation)."""
        text = cue_data.get("text", "")
        correlation_id = cue_data.get("correlation_id")
        
        logger.info(f"TTS cue received (not implemented): {text[:50]}...")
        
        return CueResult(
            success=True,
            cue_type="tts",
            correlation_id=correlation_id
        )
    
    async def _handle_expression_cue(self, cue_data: Dict[str, Any]) -> CueResult:
        """Handle an expression cue (placeholder for future implementation)."""
        expression = cue_data.get("expression", "")
        correlation_id = cue_data.get("correlation_id")
        
        logger.info(f"Expression cue received (not implemented): {expression}")
        
        return CueResult(
            success=True,
            cue_type="expression",
            correlation_id=correlation_id
        )
    
    def _resolve_gesture_type(self, gesture_str: str) -> Optional[GestureType]:
        """
        Resolve a gesture string to a GestureType.
        
        Supports both GestureType names and GestureKeyword names.
        
        Args:
            gesture_str: Gesture type string (e.g., "WAVE", "NOD", "EMPATHY")
        
        Returns:
            GestureType or None if not found
        """
        gesture_str_upper = gesture_str.upper()
        
        try:
            return GestureType[gesture_str_upper]
        except KeyError:
            pass
        
        try:
            keyword = GestureKeyword[gesture_str_upper]
            return KEYWORD_TO_GESTURE.get(keyword)
        except KeyError:
            pass
        
        return None
    
    async def execute_gesture_by_name(self, gesture_name: str) -> CueResult:
        """
        Execute a gesture by name (convenience method).
        
        Args:
            gesture_name: Name of the gesture to execute
        
        Returns:
            CueResult with execution details
        """
        return await self.handle_cue({
            "type": "gesture",
            "gesture_type": gesture_name
        })
    
    async def execute_gestures_from_keywords(
        self,
        keywords: list[str],
        delay_between: float = 0.3
    ) -> list[CueResult]:
        """
        Execute a sequence of gestures from keyword strings.
        
        Args:
            keywords: List of gesture keyword strings
            delay_between: Delay in seconds between gestures
        
        Returns:
            List of CueResults for each gesture
        """
        results = []
        
        for keyword in keywords:
            result = await self.execute_gesture_by_name(keyword)
            results.append(result)
            
            if result.success and len(keywords) > 1:
                await asyncio.sleep(delay_between)
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cue handler metrics."""
        return {
            "connected": self.is_connected,
            "cues_processed": self._cues_processed,
            "cues_failed": self._cues_failed,
            "gesture_controller_state": self._gesture_controller.state.value,
        }


async def demo_cue_handler():
    """Demo function to test the cue handler."""
    logging.basicConfig(level=logging.INFO)
    
    config = ReachyConfig(simulation_mode=True)
    handler = ReachyCueHandler(config)
    
    await handler.connect()
    
    print("\n=== Cue Handler Demo ===\n")
    
    test_cues = [
        {"type": "gesture", "gesture_type": "WAVE", "correlation_id": "test-1"},
        {"type": "gesture", "gesture_type": "NOD", "correlation_id": "test-2"},
        {"type": "gesture", "gesture_type": "EMPATHY", "correlation_id": "test-3"},
        {"type": "gesture", "gesture_type": "INVALID", "correlation_id": "test-4"},
        {"type": "tts", "text": "Hello, I am Reachy!", "correlation_id": "test-5"},
    ]
    
    for cue in test_cues:
        print(f"\nProcessing cue: {cue}")
        result = await handler.handle_cue(cue)
        print(f"Result: success={result.success}, gesture={result.gesture_name}, "
              f"duration={result.duration_ms:.1f}ms, error={result.error}")
    
    print("\n--- Metrics ---")
    metrics = handler.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    await handler.disconnect()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_cue_handler())
