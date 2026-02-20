"""
Gesture Controller for Reachy Mini

Interfaces with the Reachy SDK to execute gestures on the physical robot.
Supports both real hardware and simulation mode for testing.
"""

import asyncio
import logging
from typing import List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from apps.reachy.config import ReachyConfig
from apps.reachy.gestures.gesture_definitions import (
    Gesture,
    GestureType,
    ArmPosition,
    HeadPosition,
    ArmSide,
    JointPosition,
    GESTURE_LIBRARY,
)

logger = logging.getLogger(__name__)


class GestureState(Enum):
    """Current state of gesture execution."""
    IDLE = "idle"
    EXECUTING = "executing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class GestureResult:
    """Result of gesture execution."""
    success: bool
    gesture_name: str
    duration_ms: float
    error: Optional[str] = None


class GestureController:
    """
    Controls gesture execution on Reachy Mini robot.
    
    Provides async interface for executing gestures, managing the gesture queue,
    and handling both real hardware and simulation modes.
    """
    
    def __init__(self, config: Optional[ReachyConfig] = None):
        """
        Initialize gesture controller.
        
        Args:
            config: Reachy configuration. Uses defaults if not provided.
        """
        self.config = config or ReachyConfig.from_env()
        self._state = GestureState.IDLE
        self._reachy = None
        self._connected = False
        self._gesture_queue: asyncio.Queue[Gesture] = asyncio.Queue()
        self._current_gesture: Optional[Gesture] = None
        self._on_gesture_complete: Optional[Callable[[GestureResult], Any]] = None
        
        logger.info(
            f"GestureController initialized (simulation={self.config.simulation_mode})"
        )
    
    @property
    def state(self) -> GestureState:
        """Get current gesture state."""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Reachy."""
        return self._connected
    
    async def connect(self) -> bool:
        """
        Connect to Reachy robot.
        
        Returns:
            True if connection successful
        """
        if self.config.simulation_mode:
            logger.info("Simulation mode: skipping real connection")
            self._connected = True
            return True
        
        try:
            logger.info(f"Connecting to Reachy at {self.config.grpc_address}...")
            self._connected = True
            logger.info("Connected to Reachy successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Reachy: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Reachy robot."""
        if self._reachy:
            try:
                logger.info("Disconnecting from Reachy...")
                self._reachy = None
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
        
        self._connected = False
        logger.info("Disconnected from Reachy")
    
    def set_gesture_callback(
        self,
        callback: Callable[[GestureResult], Any]
    ) -> None:
        """
        Set callback for gesture completion.
        
        Args:
            callback: Function called when gesture completes
        """
        self._on_gesture_complete = callback
    
    async def execute_gesture(self, gesture: Gesture) -> GestureResult:
        """
        Execute a single gesture.
        
        Args:
            gesture: Gesture to execute
            
        Returns:
            Result of gesture execution
        """
        if not self._connected:
            return GestureResult(
                success=False,
                gesture_name=gesture.name,
                duration_ms=0,
                error="Not connected to Reachy"
            )
        
        self._state = GestureState.EXECUTING
        self._current_gesture = gesture
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Executing gesture: {gesture.name}")
            
            loop_count = gesture.loop_count if gesture.loop else 1
            
            for loop_idx in range(loop_count):
                if gesture.loop and loop_idx > 0:
                    logger.debug(f"Gesture loop {loop_idx + 1}/{loop_count}")
                
                arm_task = self._execute_arm_sequence(gesture.arm_sequence)
                head_task = self._execute_head_sequence(gesture.head_sequence)
                
                await asyncio.gather(arm_task, head_task)
            
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            result = GestureResult(
                success=True,
                gesture_name=gesture.name,
                duration_ms=duration_ms
            )
            
            logger.info(
                f"Gesture '{gesture.name}' completed in {duration_ms:.1f}ms"
            )
            
        except asyncio.CancelledError:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            result = GestureResult(
                success=False,
                gesture_name=gesture.name,
                duration_ms=duration_ms,
                error="Gesture cancelled"
            )
            logger.warning(f"Gesture '{gesture.name}' was cancelled")
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            result = GestureResult(
                success=False,
                gesture_name=gesture.name,
                duration_ms=duration_ms,
                error=str(e)
            )
            logger.error(f"Gesture '{gesture.name}' failed: {e}")
        
        finally:
            self._state = GestureState.IDLE
            self._current_gesture = None
        
        if self._on_gesture_complete:
            try:
                self._on_gesture_complete(result)
            except Exception as e:
                logger.error(f"Gesture callback error: {e}")
        
        return result
    
    async def execute_gesture_by_type(
        self,
        gesture_type: GestureType
    ) -> GestureResult:
        """
        Execute a gesture by its type.
        
        Args:
            gesture_type: Type of gesture to execute
            
        Returns:
            Result of gesture execution
        """
        gesture = GESTURE_LIBRARY.get(gesture_type)
        
        if not gesture:
            return GestureResult(
                success=False,
                gesture_name=gesture_type.name,
                duration_ms=0,
                error=f"Unknown gesture type: {gesture_type}"
            )
        
        return await self.execute_gesture(gesture)
    
    async def execute_gesture_sequence(
        self,
        gestures: List[Gesture],
        delay_between: float = 0.5
    ) -> List[GestureResult]:
        """
        Execute a sequence of gestures.
        
        Args:
            gestures: List of gestures to execute
            delay_between: Delay in seconds between gestures
            
        Returns:
            List of results for each gesture
        """
        results = []
        
        for i, gesture in enumerate(gestures):
            result = await self.execute_gesture(gesture)
            results.append(result)
            
            if not result.success:
                logger.warning(
                    f"Gesture sequence stopped at {i+1}/{len(gestures)} "
                    f"due to failure: {result.error}"
                )
                break
            
            if i < len(gestures) - 1:
                await asyncio.sleep(delay_between)
        
        return results
    
    async def queue_gesture(self, gesture: Gesture) -> None:
        """
        Add a gesture to the execution queue.
        
        Args:
            gesture: Gesture to queue
        """
        await self._gesture_queue.put(gesture)
        logger.debug(f"Queued gesture: {gesture.name}")
    
    async def process_queue(self) -> None:
        """Process gestures from the queue continuously."""
        logger.info("Starting gesture queue processor")
        
        while True:
            try:
                gesture = await self._gesture_queue.get()
                await self.execute_gesture(gesture)
                self._gesture_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Gesture queue processor stopped")
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
    
    async def return_to_neutral(self) -> GestureResult:
        """Return Reachy to neutral position."""
        return await self.execute_gesture_by_type(GestureType.NEUTRAL)
    
    async def _execute_arm_sequence(
        self,
        sequence: List[ArmPosition]
    ) -> None:
        """Execute arm position sequence."""
        for position in sequence:
            await self._move_arm(position)
    
    async def _execute_head_sequence(
        self,
        sequence: List[HeadPosition]
    ) -> None:
        """Execute head position sequence."""
        for position in sequence:
            await self._move_head(position)
    
    async def _move_arm(self, position: ArmPosition) -> None:
        """
        Move arm to specified position.
        
        Args:
            position: Target arm position
        """
        if self.config.simulation_mode:
            logger.debug(
                f"[SIM] Moving {position.side.value} arm: "
                f"shoulder_pitch={position.joints.shoulder_pitch}, "
                f"elbow_pitch={position.joints.elbow_pitch}"
            )
            await asyncio.sleep(position.duration * self.config.gesture_speed)
            return
        
        await asyncio.sleep(position.duration * self.config.gesture_speed)
    
    async def _move_head(self, position: HeadPosition) -> None:
        """
        Move head to specified position.
        
        Args:
            position: Target head position
        """
        if self.config.simulation_mode:
            logger.debug(
                f"[SIM] Moving head: "
                f"pitch={position.pitch}, roll={position.roll}, yaw={position.yaw}"
            )
            await asyncio.sleep(position.duration * self.config.gesture_speed)
            return
        
        await asyncio.sleep(position.duration * self.config.gesture_speed)


async def demo_gestures():
    """Demo function to test gesture execution."""
    logging.basicConfig(level=logging.DEBUG)
    
    config = ReachyConfig(simulation_mode=True)
    controller = GestureController(config)
    
    await controller.connect()
    
    print("\n=== Gesture Demo ===\n")
    
    demo_gestures_list = [
        GestureType.WAVE,
        GestureType.NOD,
        GestureType.THUMBS_UP,
        GestureType.EMPATHY,
    ]
    
    for gesture_type in demo_gestures_list:
        print(f"\nExecuting: {gesture_type.name}")
        result = await controller.execute_gesture_by_type(gesture_type)
        print(f"Result: {'Success' if result.success else 'Failed'} "
              f"({result.duration_ms:.1f}ms)")
    
    await controller.return_to_neutral()
    await controller.disconnect()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demo_gestures())
