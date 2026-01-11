#!/usr/bin/env python3
"""
Jetson Emotion WebSocket Client
Streams emotion detection events to Ubuntu 2 gateway with auto-reconnection.
Handles gesture cues from the gateway for Reachy robot control.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import socket
import socketio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CueType(Enum):
    """Types of cues that can be received from the gateway."""
    GESTURE = "gesture"
    TTS = "tts"
    EXPRESSION = "expression"
    AUDIO = "audio"


@dataclass
class GestureCue:
    """Gesture cue received from gateway."""
    gesture_type: str
    priority: int = 1
    duration: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


@dataclass 
class TTSCue:
    """Text-to-speech cue received from gateway."""
    text: str
    voice: str = "default"
    speed: float = 1.0
    correlation_id: Optional[str] = None


class EmotionClient:
    """WebSocket client for streaming emotion events from Jetson."""
    
    def __init__(
        self,
        gateway_url: str,
        device_id: str,
        heartbeat_interval: int = 30,
        reconnect_attempts: int = 0  # 0 = infinite
    ):
        """
        Initialize emotion client.
        
        Args:
            gateway_url: WebSocket gateway URL (e.g., http://10.0.4.140:8000)
            device_id: Unique device identifier
            heartbeat_interval: Heartbeat interval in seconds
            reconnect_attempts: Max reconnection attempts (0 = infinite)
        """
        self.gateway_url = gateway_url
        self.device_id = device_id
        self.heartbeat_interval = heartbeat_interval
        
        # Socket.IO client
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=reconnect_attempts,
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=False,
            engineio_logger=False
        )
        
        # Connection state
        self.connected = False
        self.connection_time = None
        
        # Metrics
        self.events_sent = 0
        self.errors_count = 0
        self.reconnection_count = 0
        self.cues_received = 0
        self.gestures_executed = 0
        
        # Heartbeat task
        self._heartbeat_task = None
        
        # Cue callbacks
        self._gesture_callback: Optional[Callable[[GestureCue], Any]] = None
        self._tts_callback: Optional[Callable[[TTSCue], Any]] = None
        self._cue_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._cue_processor_task: Optional[asyncio.Task] = None
        
        # Register event handlers
        self._register_handlers()
        
        logger.info(f"Emotion client initialized: {device_id} -> {gateway_url}")
    
    def _register_handlers(self):
        """Register WebSocket event handlers."""
        
        @self.sio.event
        async def connect():
            """Handle connection event."""
            logger.info(f"Connected to gateway: {self.gateway_url}")
            self.connected = True
            self.connection_time = datetime.now()
            
            # Send registration
            await self._register_device()
            
            # Start heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        @self.sio.event
        async def disconnect():
            """Handle disconnection event."""
            logger.warning("Disconnected from gateway")
            self.connected = False
            self.reconnection_count += 1
            
            # Cancel heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
        
        @self.sio.event
        async def cue(data: Dict[str, Any]):
            """Handle cue from gateway (gestures, TTS, etc.)."""
            logger.info(f"Received cue: {data}")
            self.cues_received += 1
            await self._cue_queue.put(data)
        
        @self.sio.event
        async def error(data: Dict[str, Any]):
            """Handle error from gateway."""
            logger.error(f"Gateway error: {data}")
            self.errors_count += 1
    
    async def _register_device(self):
        """Register device with gateway."""
        registration = {
            'device_id': self.device_id,
            'device_type': 'jetson',
            'hostname': socket.gethostname(),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        try:
            await self.sio.emit('register', registration)
            logger.info(f"Device registered: {self.device_id}")
        except Exception as e:
            logger.error(f"Registration failed: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to gateway."""
        while self.connected:
            try:
                await self.sio.emit('heartbeat', {
                    'device_id': self.device_id,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                })
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def connect(self):
        """Connect to WebSocket gateway."""
        try:
            await self.sio.connect(self.gateway_url, namespaces=['/'])
            logger.info("WebSocket connection established")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from gateway."""
        if self.connected:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            await self.sio.disconnect()
            logger.info("Disconnected from gateway")
    
    async def send_emotion_event(self, emotion_data: Dict[str, Any]):
        """
        Send emotion detection event to gateway.
        
        Args:
            emotion_data: Emotion event data
                - emotion: str (emotion label)
                - confidence: float (0-1)
                - inference_ms: float (inference time)
                - timestamp: str (ISO format)
                - frame_number: int (optional)
        """
        if not self.connected:
            logger.warning("Not connected, cannot send event")
            return
        
        try:
            # Add device ID
            event = {
                'device_id': self.device_id,
                **emotion_data
            }
            
            # Send event
            await self.sio.emit('emotion_event', event)
            self.events_sent += 1
            
            logger.debug(f"Emotion event sent: {emotion_data['emotion']} "
                        f"({emotion_data['confidence']:.2%})")
            
        except Exception as e:
            logger.error(f"Failed to send emotion event: {e}")
            self.errors_count += 1
    
    def set_gesture_callback(self, callback: Callable[[GestureCue], Any]) -> None:
        """
        Set callback for gesture cues.
        
        Args:
            callback: Function to call when gesture cue is received.
                      Can be sync or async.
        """
        self._gesture_callback = callback
        logger.info("Gesture callback registered")
    
    def set_tts_callback(self, callback: Callable[[TTSCue], Any]) -> None:
        """
        Set callback for TTS cues.
        
        Args:
            callback: Function to call when TTS cue is received.
        """
        self._tts_callback = callback
        logger.info("TTS callback registered")
    
    async def _process_cue_queue(self) -> None:
        """Process cues from the queue."""
        logger.info("Cue processor started")
        
        while True:
            try:
                cue_data = await self._cue_queue.get()
                await self._handle_cue(cue_data)
                self._cue_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Cue processor stopped")
                break
            except Exception as e:
                logger.error(f"Cue processing error: {e}")
    
    async def _handle_cue(self, cue_data: Dict[str, Any]) -> None:
        """
        Handle a single cue from the gateway.
        
        Args:
            cue_data: Raw cue data from gateway
        """
        cue_type = cue_data.get("type", "").lower()
        
        try:
            if cue_type == CueType.GESTURE.value:
                gesture_cue = GestureCue(
                    gesture_type=cue_data.get("gesture_type", ""),
                    priority=cue_data.get("priority", 1),
                    duration=cue_data.get("duration"),
                    parameters=cue_data.get("parameters"),
                    correlation_id=cue_data.get("correlation_id")
                )
                
                if self._gesture_callback:
                    result = self._gesture_callback(gesture_cue)
                    if asyncio.iscoroutine(result):
                        await result
                    self.gestures_executed += 1
                    logger.info(f"Gesture executed: {gesture_cue.gesture_type}")
                else:
                    logger.warning(f"No gesture callback registered for: {gesture_cue.gesture_type}")
                    
            elif cue_type == CueType.TTS.value:
                tts_cue = TTSCue(
                    text=cue_data.get("text", ""),
                    voice=cue_data.get("voice", "default"),
                    speed=cue_data.get("speed", 1.0),
                    correlation_id=cue_data.get("correlation_id")
                )
                
                if self._tts_callback:
                    result = self._tts_callback(tts_cue)
                    if asyncio.iscoroutine(result):
                        await result
                    logger.info(f"TTS executed: {tts_cue.text[:30]}...")
                else:
                    logger.warning("No TTS callback registered")
                    
            else:
                logger.warning(f"Unknown cue type: {cue_type}")
                
        except Exception as e:
            logger.error(f"Error handling cue {cue_type}: {e}")
    
    async def start_cue_processor(self) -> None:
        """Start the background cue processor."""
        if self._cue_processor_task is None:
            self._cue_processor_task = asyncio.create_task(self._process_cue_queue())
            logger.info("Cue processor task started")
    
    async def stop_cue_processor(self) -> None:
        """Stop the background cue processor."""
        if self._cue_processor_task:
            self._cue_processor_task.cancel()
            try:
                await self._cue_processor_task
            except asyncio.CancelledError:
                pass
            self._cue_processor_task = None
            logger.info("Cue processor task stopped")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get client metrics.
        
        Returns:
            Metrics dictionary
        """
        uptime = None
        if self.connection_time:
            uptime = (datetime.now() - self.connection_time).total_seconds()
        
        return {
            'connected': self.connected,
            'uptime_seconds': uptime,
            'events_sent': self.events_sent,
            'errors_count': self.errors_count,
            'reconnection_count': self.reconnection_count,
            'cues_received': self.cues_received,
            'gestures_executed': self.gestures_executed,
            'cue_queue_size': self._cue_queue.qsize()
        }


async def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Jetson Emotion WebSocket Client')
    parser.add_argument('--gateway', default='http://10.0.4.140:8000', help='Gateway URL')
    parser.add_argument('--device-id', default='reachy-mini-01', help='Device ID')
    parser.add_argument('--test-mode', action='store_true', help='Send test events')
    
    args = parser.parse_args()
    
    # Create client
    client = EmotionClient(
        gateway_url=args.gateway,
        device_id=args.device_id
    )
    
    # Connect
    await client.connect()
    
    # Test mode: send mock events
    if args.test_mode:
        logger.info("Test mode: sending mock emotion events")
        
        emotions = ['happy', 'sad']
        for i in range(10):
            emotion = emotions[i % 2]
            event = {
                'emotion': emotion,
                'confidence': 0.85 + (i * 0.01),
                'inference_ms': 45.2 + (i * 2),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'frame_number': i
            }
            
            await client.send_emotion_event(event)
            await asyncio.sleep(1)
        
        # Print metrics
        metrics = client.get_metrics()
        print(f"\nMetrics: {json.dumps(metrics, indent=2)}")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
