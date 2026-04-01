"""WebSocket endpoint for streaming robot cues (text, gesture, tone) to Jetson devices.

This router implements the /ws/cues/{device_id} WebSocket channel that allows
the server to push dialogue responses and behavioral cues to connected Reachy robots.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for robot devices."""
    
    def __init__(self):
        """Initialize connection manager with empty connections dict."""
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.
        
        Args:
            device_id: Unique device identifier
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"Device connected: {device_id}")
    
    def disconnect(self, device_id: str) -> None:
        """Remove a device from active connections.
        
        Args:
            device_id: Device identifier to disconnect
        """
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Device disconnected: {device_id}")
    
    async def send_cue(self, device_id: str, cue: Dict[str, Any]) -> bool:
        """Send a cue message to a specific device.
        
        Args:
            device_id: Target device identifier
            cue: Cue message dictionary
            
        Returns:
            True if sent successfully, False if device not connected
        """
        if device_id not in self.active_connections:
            logger.warning(f"Cannot send cue: device {device_id} not connected")
            return False
        
        try:
            await self.active_connections[device_id].send_json(cue)
            logger.debug(f"Cue sent to {device_id}: {cue.get('type', 'unknown')}")
            return True
        except Exception as exc:
            logger.error(f"Failed to send cue to {device_id}: {exc}")
            self.disconnect(device_id)
            return False
    
    async def broadcast(self, cue: Dict[str, Any]) -> int:
        """Broadcast a cue to all connected devices.
        
        Args:
            cue: Cue message dictionary
            
        Returns:
            Number of devices that received the cue
        """
        sent_count = 0
        disconnected = []
        
        for device_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(cue)
                sent_count += 1
            except Exception as exc:
                logger.error(f"Failed to broadcast to {device_id}: {exc}")
                disconnected.append(device_id)
        
        # Clean up disconnected devices
        for device_id in disconnected:
            self.disconnect(device_id)
        
        return sent_count
    
    def is_connected(self, device_id: str) -> bool:
        """Check if a device is currently connected.
        
        Args:
            device_id: Device identifier to check
            
        Returns:
            True if connected, False otherwise
        """
        return device_id in self.active_connections
    
    def get_connected_devices(self) -> list[str]:
        """Get list of all connected device IDs.
        
        Returns:
            List of device identifiers
        """
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


def create_cue_message(
    cue_type: str,
    text: Optional[str] = None,
    gesture_id: Optional[str] = None,
    tone: Optional[str] = None,
    correlation_id: Optional[str] = None,
    expires_in_seconds: int = 30,
) -> Dict[str, Any]:
    """Create a standardized cue message.
    
    Args:
        cue_type: Type of cue (tts, gesture, combined)
        text: Text to speak (for tts cues)
        gesture_id: Gesture identifier (for gesture cues)
        tone: Tone descriptor (for tts cues)
        correlation_id: Optional correlation ID for tracking
        expires_in_seconds: Seconds until cue expires
        
    Returns:
        Cue message dictionary
    """
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
    
    cue = {
        "type": cue_type,
        "correlation_id": correlation_id or str(uuid4()),
        "expires_at": expires_at,
        "timestamp": now.isoformat(),
    }
    
    if text is not None:
        cue["text"] = text
    if gesture_id is not None:
        cue["gesture_id"] = gesture_id
    if tone is not None:
        cue["tone"] = tone
    
    return cue


@router.websocket("/ws/cues/{device_id}")
async def websocket_cues_endpoint(websocket: WebSocket, device_id: str):
    """WebSocket endpoint for streaming cues to robot devices.
    
    This endpoint maintains a persistent connection with Reachy robots and
    allows the server to push dialogue responses, gestures, and behavioral
    cues in real-time.
    
    Protocol:
        - Server → Client: JSON cue messages with type, text, gesture_id, tone
        - Client → Server: JSON acknowledgments with correlation_id
        - Heartbeat: Client should send ping every 30s, server responds with pong
    
    Args:
        websocket: WebSocket connection
        device_id: Unique device identifier
        
    Raises:
        WebSocketException: If device_id is invalid or connection fails
    """
    # Validate device_id format
    if not device_id or len(device_id) > 100:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid device_id"
        )
    
    # Check if device already connected
    if manager.is_connected(device_id):
        logger.warning(f"Device {device_id} already connected, closing existing connection")
        # Could optionally close the existing connection here
    
    await manager.connect(device_id, websocket)
    
    try:
        # Send welcome message
        welcome = {
            "type": "connection_established",
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_version": "0.08.4.3",
        }
        await websocket.send_json(welcome)
        
        # Main message loop
        while True:
            try:
                # Receive messages from client (acknowledgments, pings, etc.)
                data = await websocket.receive_json()
                
                # Handle different message types
                msg_type = data.get("type", "unknown")
                
                if msg_type == "ping":
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                elif msg_type == "ack":
                    # Log acknowledgment
                    correlation_id = data.get("correlation_id")
                    logger.info(
                        f"Cue acknowledged by {device_id}",
                        extra={"correlation_id": correlation_id}
                    )
                
                elif msg_type == "cue_result":
                    # Gesture/TTS execution feedback from Jetson
                    correlation_id = data.get("correlation_id")
                    success = data.get("success", False)
                    duration_ms = data.get("duration_ms", 0.0)
                    error_msg = data.get("error")
                    if success:
                        logger.info(
                            "Cue executed on %s: correlation=%s duration=%.1fms",
                            device_id,
                            correlation_id,
                            duration_ms,
                        )
                    else:
                        logger.warning(
                            "Cue failed on %s: correlation=%s error=%s",
                            device_id,
                            correlation_id,
                            error_msg,
                        )

                elif msg_type == "error":
                    # Log client-side error
                    error_msg = data.get("message", "Unknown error")
                    logger.error(
                        f"Client error from {device_id}: {error_msg}",
                        extra={"device_id": device_id, "error": error_msg}
                    )

                else:
                    logger.warning(
                        f"Unknown message type from {device_id}: {msg_type}"
                    )
            
            except asyncio.TimeoutError:
                # No message received in timeout period, continue
                continue
    
    except WebSocketDisconnect:
        logger.info(f"Device {device_id} disconnected normally")
        manager.disconnect(device_id)
    
    except Exception as exc:
        logger.error(f"WebSocket error for {device_id}: {exc}", exc_info=True)
        manager.disconnect(device_id)
        raise


# Helper function to send cues from other parts of the application
async def send_dialogue_cue(
    device_id: str,
    text: str,
    gesture: str,
    tone: str,
    correlation_id: Optional[str] = None,
) -> bool:
    """Send a dialogue cue to a specific device.
    
    This is a convenience function that can be called from the dialogue
    router to push generated responses to the robot.
    
    Args:
        device_id: Target device identifier
        text: Dialogue text to speak
        gesture: Gesture identifier
        tone: Tone descriptor
        correlation_id: Optional correlation ID
        
    Returns:
        True if sent successfully, False otherwise
    """
    cue = create_cue_message(
        cue_type="combined",
        text=text,
        gesture_id=gesture,
        tone=tone,
        correlation_id=correlation_id,
    )
    
    return await manager.send_cue(device_id, cue)
