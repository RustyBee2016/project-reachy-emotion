"""
WebSocket client with auto-reconnection and event handling for real-time updates.
"""

import asyncio
import inspect
import json
import logging
import queue
import threading
import time
import sys
import types
from typing import Callable, Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import socketio
except ImportError:  # pragma: no cover - optional dependency fallback
    socketio = types.ModuleType("socketio")

    class _StubAsyncClient:  # minimal interface for tests and non-realtime environments
        def __init__(self, *args, **kwargs):
            self._handlers = {}

        def event(self, func):
            self._handlers[func.__name__] = func
            return func

        async def connect(self, *args, **kwargs):
            return None

        async def disconnect(self):
            return None

        async def emit(self, *args, **kwargs):
            return None

    socketio.AsyncClient = _StubAsyncClient  # type: ignore[attr-defined]
    sys.modules["socketio"] = socketio

logger = logging.getLogger(__name__)

class EventType(Enum):
    """WebSocket event types."""
    EMOTION = "emotion_event"
    PROMOTION = "promotion_complete"
    TRAINING = "training_status"
    GENERATION = "generation_complete"
    DEVICE = "device_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

@dataclass
class EmotionEvent:
    """Emotion detection event."""
    device_id: str
    emotion: str
    confidence: float
    inference_ms: float
    timestamp: datetime
    window: Optional[Dict] = None

@dataclass
class PromotionEvent:
    """Video promotion completion event."""
    video_id: str
    from_split: str
    to_split: str
    label: str
    success: bool
    timestamp: datetime
    error: Optional[str] = None

@dataclass
class TrainingEvent:
    """Training status update event."""
    run_id: str
    status: str  # pending, sampling, training, evaluating, completed, failed
    epoch: Optional[int] = None
    loss: Optional[float] = None
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    timestamp: Optional[datetime] = None

class WebSocketClient:
    """
    Complete WebSocket client for real-time system events.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Event subscription with callbacks
    - Thread-safe message queuing
    - Heartbeat monitoring
    - Metrics tracking
    """
    
    def __init__(
        self, 
        server_url: str,
        device_id: str = "web-ui",
        reconnect_attempts: int = 0,  # 0 = infinite
        heartbeat_interval: int = 30
    ):
        """Initialize WebSocket client."""
        self.server_url = server_url
        self.device_id = device_id
        self.reconnect_attempts = reconnect_attempts
        self.heartbeat_interval = heartbeat_interval
        
        # Socket.IO client with async support
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=reconnect_attempts,
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=True,
            engineio_logger=False
        )
        
        # Message queue for Streamlit (thread-safe)
        self.message_queue = queue.Queue()
        
        # Subscription callbacks
        self.subscriptions: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        
        # Connection state
        self.connected = False
        self.connection_time = None
        self.last_heartbeat = None
        
        # Metrics
        self.events_received = 0
        self.errors_count = 0
        self.reconnection_count = 0
        
        # Register handlers lazily at connect-time so test/mocked clients can
        # replace .on/.event after construction.
        self._handlers_registered = False
        
        # Heartbeat task
        self._heartbeat_task = None
    
    def _bind_event(self, event_name: str, handler: Callable[..., Any]) -> None:
        """Bind an event handler across real and mocked socket clients."""
        on_method = getattr(self.sio, "on", None)
        if callable(on_method) and not inspect.iscoroutinefunction(on_method):
            try:
                on_method(event_name, handler)
                return
            except TypeError:
                decorator = on_method(event_name)
                if callable(decorator):
                    decorator(handler)
                    return

        event_method = getattr(self.sio, "event", None)
        if callable(event_method) and not inspect.iscoroutinefunction(event_method):
            event_method(handler)

    def _register_handlers(self):
        """Register WebSocket event handlers."""
        if self._handlers_registered:
            return
        
        async def connect():
            """Handle connection event."""
            logger.info(f"WebSocket connected to {self.server_url}")
            self.connected = True
            self.connection_time = datetime.now()
            
            # Send registration message
            await self.sio.emit('register', {
                'device_id': self.device_id,
                'device_type': 'ui',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Start heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        async def disconnect():
            """Handle disconnection event."""
            logger.warning("WebSocket disconnected")
            self.connected = False
            self.reconnection_count += 1
            
            # Cancel heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
        
        async def emotion_event(data: Dict[str, Any]):
            """Handle emotion detection event from Jetson."""
            await self._handle_emotion_event(data)
        
        async def promotion_complete(data: Dict[str, Any]):
            """Handle video promotion completion event."""
            await self._handle_promotion_event(data)
        
        async def training_status(data: Dict[str, Any]):
            """Handle training status update event."""
            await self._handle_training_event(data)
        
        async def error(data: Dict[str, Any]):
            """Handle error event from server."""
            logger.error(f"Server error: {data}")
            self.errors_count += 1
            self.message_queue.put(('error', data))
            
            # Call error callbacks
            for callback in self.subscriptions[EventType.ERROR]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")

        self._bind_event("connect", connect)
        self._bind_event("disconnect", disconnect)
        self._bind_event(EventType.EMOTION.value, emotion_event)
        self._bind_event(EventType.PROMOTION.value, promotion_complete)
        self._bind_event(EventType.TRAINING.value, training_status)
        self._bind_event(EventType.ERROR.value, error)
        self._handlers_registered = True
    
    async def _handle_emotion_event(self, data: Dict[str, Any]):
        """Process emotion event."""
        self.events_received += 1
        
        # Parse event
        event = EmotionEvent(
            device_id=data['device_id'],
            emotion=data['emotion'],
            confidence=data['confidence'],
            inference_ms=data['inference_ms'],
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp'],
            window=data.get('window')
        )
        
        # Queue for Streamlit
        self.message_queue.put(('emotion', event))
        
        # Call subscribed callbacks
        for callback in self.subscriptions[EventType.EMOTION]:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in emotion callback: {e}")
    
    async def _handle_promotion_event(self, data: Dict[str, Any]):
        """Process promotion event."""
        self.events_received += 1
        
        # Parse event
        event = PromotionEvent(
            video_id=data['video_id'],
            from_split=data['from_split'],
            to_split=data['to_split'],
            label=data['label'],
            success=data['success'],
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp'],
            error=data.get('error')
        )
        
        # Queue for Streamlit
        self.message_queue.put(('promotion', event))
        
        # Call subscribed callbacks
        for callback in self.subscriptions[EventType.PROMOTION]:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in promotion callback: {e}")
    
    async def _handle_training_event(self, data: Dict[str, Any]):
        """Process training event."""
        self.events_received += 1
        
        # Parse event
        event = TrainingEvent(
            run_id=data['run_id'],
            status=data['status'],
            epoch=data.get('epoch'),
            loss=data.get('loss'),
            accuracy=data.get('accuracy'),
            f1_score=data.get('f1_score'),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') and isinstance(data['timestamp'], str) else data.get('timestamp')
        )
        
        # Queue for Streamlit
        self.message_queue.put(('training', event))
        
        # Call subscribed callbacks
        for callback in self.subscriptions[EventType.TRAINING]:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in training callback: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self.connected:
            try:
                await self.sio.emit('heartbeat', {
                    'device_id': self.device_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                self.last_heartbeat = datetime.now()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def connect(self):
        """Connect to WebSocket server."""
        try:
            if not self._handlers_registered:
                self._register_handlers()
            await self.sio.connect(self.server_url, namespaces=['/'])
            logger.info("WebSocket connection established")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.connected:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            await self.sio.disconnect()
            logger.info("WebSocket disconnected")
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """
        Subscribe to an event type with a callback.
        
        Args:
            event_type: Event type to subscribe to
            callback: Async function to call when event is received
        """
        if callback not in self.subscriptions[event_type]:
            self.subscriptions[event_type].append(callback)
            logger.info(f"Subscribed to {event_type} events")
    
    def get_messages(self, max_count: int = 100) -> List[Tuple[str, Any]]:
        """
        Get messages from queue (non-blocking).
        
        Args:
            max_count: Maximum number of messages to retrieve
        
        Returns:
            List of (event_type, data) tuples
        """
        messages = []
        while not self.message_queue.empty() and len(messages) < max_count:
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages
    
    def is_healthy(self) -> bool:
        """
        Check if client is healthy.
        
        Returns:
            True if connected and heartbeat is recent
        """
        if not self.connected:
            return False
        
        if self.last_heartbeat is None:
            return True  # Just connected
        
        # Check if heartbeat is stale (more than 2x interval)
        time_since_heartbeat = datetime.now() - self.last_heartbeat
        return time_since_heartbeat < timedelta(seconds=self.heartbeat_interval * 2)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get client metrics.
        
        Returns:
            Dictionary of metrics
        """
        uptime = None
        if self.connection_time:
            uptime = (datetime.now() - self.connection_time).total_seconds()
        
        return {
            'connected': self.connected,
            'uptime_seconds': uptime,
            'events_received': self.events_received,
            'errors_count': self.errors_count,
            'reconnection_count': self.reconnection_count,
            'queue_size': self.message_queue.qsize(),
            'is_healthy': self.is_healthy()
        }
