"""Tests for WebSocket robot cue streaming endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from apps.api.app.routers.websocket_cues import ConnectionManager, create_cue_message


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def connection_manager():
    """Create fresh connection manager for each test."""
    return ConnectionManager()


class TestWebSocketConnection:
    """Tests for WebSocket connection establishment and management."""
    
    def test_websocket_connection_established(self, client):
        """Test successful WebSocket connection."""
        device_id = "reachy-mini-test-01"
        
        with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            
            assert data["type"] == "connection_established"
            assert data["device_id"] == device_id
            assert "timestamp" in data
            assert "server_version" in data
    
    def test_websocket_invalid_device_id(self, client):
        """Test WebSocket connection with invalid device ID."""
        # Empty device_id should be rejected
        with pytest.raises(Exception):  # WebSocket exception
            with client.websocket_connect("/ws/cues/") as websocket:
                pass
    
    def test_websocket_ping_pong(self, client):
        """Test WebSocket heartbeat mechanism."""
        device_id = "reachy-mini-test-02"
        
        with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response
    
    def test_websocket_acknowledgment(self, client):
        """Test client acknowledgment of cues."""
        device_id = "reachy-mini-test-03"
        
        with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Send acknowledgment
            correlation_id = "test-correlation-123"
            websocket.send_json({
                "type": "ack",
                "correlation_id": correlation_id
            })
            
            # Should not raise error (ack is logged server-side)
    
    def test_websocket_client_error_reporting(self, client):
        """Test client error message handling."""
        device_id = "reachy-mini-test-04"
        
        with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Send error message
            websocket.send_json({
                "type": "error",
                "message": "Failed to execute gesture"
            })
            
            # Should not raise error (logged server-side)


class TestConnectionManager:
    """Tests for ConnectionManager class."""
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self, connection_manager):
        """Test adding a connection to manager."""
        from unittest.mock import AsyncMock, MagicMock
        
        device_id = "test-device-01"
        mock_websocket = AsyncMock()
        
        await connection_manager.connect(device_id, mock_websocket)
        
        assert connection_manager.is_connected(device_id)
        assert device_id in connection_manager.get_connected_devices()
    
    def test_connection_manager_disconnect(self, connection_manager):
        """Test removing a connection from manager."""
        from unittest.mock import MagicMock
        
        device_id = "test-device-02"
        mock_websocket = MagicMock()
        
        connection_manager.active_connections[device_id] = mock_websocket
        connection_manager.disconnect(device_id)
        
        assert not connection_manager.is_connected(device_id)
        assert device_id not in connection_manager.get_connected_devices()
    
    @pytest.mark.asyncio
    async def test_connection_manager_send_cue(self, connection_manager):
        """Test sending cue to specific device."""
        from unittest.mock import AsyncMock
        
        device_id = "test-device-03"
        mock_websocket = AsyncMock()
        connection_manager.active_connections[device_id] = mock_websocket
        
        cue = {"type": "tts", "text": "Hello"}
        result = await connection_manager.send_cue(device_id, cue)
        
        assert result is True
        mock_websocket.send_json.assert_called_once_with(cue)
    
    @pytest.mark.asyncio
    async def test_connection_manager_send_cue_not_connected(self, connection_manager):
        """Test sending cue to non-connected device."""
        device_id = "non-existent-device"
        cue = {"type": "tts", "text": "Hello"}
        
        result = await connection_manager.send_cue(device_id, cue)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self, connection_manager):
        """Test broadcasting cue to all devices."""
        from unittest.mock import AsyncMock
        
        # Add multiple devices
        devices = ["device-01", "device-02", "device-03"]
        for device_id in devices:
            mock_websocket = AsyncMock()
            connection_manager.active_connections[device_id] = mock_websocket
        
        cue = {"type": "gesture", "gesture_id": "wave"}
        sent_count = await connection_manager.broadcast(cue)
        
        assert sent_count == len(devices)
    
    @pytest.mark.asyncio
    async def test_connection_manager_broadcast_with_failures(self, connection_manager):
        """Test broadcast with some device failures."""
        from unittest.mock import AsyncMock
        
        # Add devices, one will fail
        device_ok = "device-ok"
        device_fail = "device-fail"
        
        mock_websocket_ok = AsyncMock()
        mock_websocket_fail = AsyncMock()
        mock_websocket_fail.send_json.side_effect = Exception("Connection lost")
        
        connection_manager.active_connections[device_ok] = mock_websocket_ok
        connection_manager.active_connections[device_fail] = mock_websocket_fail
        
        cue = {"type": "tts", "text": "Test"}
        sent_count = await connection_manager.broadcast(cue)
        
        assert sent_count == 1  # Only one succeeded
        assert not connection_manager.is_connected(device_fail)  # Failed device removed
        assert connection_manager.is_connected(device_ok)  # OK device still connected


class TestCueMessageCreation:
    """Tests for cue message creation helper."""
    
    def test_create_tts_cue(self):
        """Test creating TTS cue message."""
        cue = create_cue_message(
            cue_type="tts",
            text="Hello, how are you?",
            tone="warm_upbeat",
            correlation_id="test-123"
        )
        
        assert cue["type"] == "tts"
        assert cue["text"] == "Hello, how are you?"
        assert cue["tone"] == "warm_upbeat"
        assert cue["correlation_id"] == "test-123"
        assert "expires_at" in cue
        assert "timestamp" in cue
    
    def test_create_gesture_cue(self):
        """Test creating gesture cue message."""
        cue = create_cue_message(
            cue_type="gesture",
            gesture_id="wave_enthusiastic"
        )
        
        assert cue["type"] == "gesture"
        assert cue["gesture_id"] == "wave_enthusiastic"
        assert "correlation_id" in cue  # Auto-generated
    
    def test_create_combined_cue(self):
        """Test creating combined TTS + gesture cue."""
        cue = create_cue_message(
            cue_type="combined",
            text="I'm here to help!",
            gesture_id="open_hands_reassuring",
            tone="reassuring_calm"
        )
        
        assert cue["type"] == "combined"
        assert cue["text"] == "I'm here to help!"
        assert cue["gesture_id"] == "open_hands_reassuring"
        assert cue["tone"] == "reassuring_calm"
    
    def test_create_cue_with_custom_expiration(self):
        """Test creating cue with custom expiration time."""
        cue = create_cue_message(
            cue_type="tts",
            text="Urgent message",
            expires_in_seconds=10
        )
        
        assert "expires_at" in cue
        # Verify it's a valid ISO timestamp
        expires_at = datetime.fromisoformat(cue["expires_at"].replace("Z", "+00:00"))
        assert expires_at > datetime.utcnow()
    
    def test_create_cue_auto_correlation_id(self):
        """Test that correlation ID is auto-generated if not provided."""
        cue = create_cue_message(cue_type="tts", text="Test")
        
        assert "correlation_id" in cue
        assert len(cue["correlation_id"]) > 0


class TestDialogueCueIntegration:
    """Tests for sending dialogue cues via WebSocket."""
    
    @pytest.mark.asyncio
    async def test_send_dialogue_cue(self):
        """Test sending dialogue cue to device."""
        from unittest.mock import AsyncMock
        from apps.api.app.routers.websocket_cues import manager, send_dialogue_cue
        
        device_id = "reachy-mini-integration-01"
        mock_websocket = AsyncMock()
        manager.active_connections[device_id] = mock_websocket
        
        result = await send_dialogue_cue(
            device_id=device_id,
            text="I'm here with you.",
            gesture="head_tilt_sympathetic",
            tone="gentle_supportive",
            correlation_id="dialogue-123"
        )
        
        assert result is True
        mock_websocket.send_json.assert_called_once()
        
        # Verify cue structure
        call_args = mock_websocket.send_json.call_args
        cue = call_args[0][0]
        assert cue["type"] == "combined"
        assert cue["text"] == "I'm here with you."
        assert cue["gesture_id"] == "head_tilt_sympathetic"
        assert cue["tone"] == "gentle_supportive"
        assert cue["correlation_id"] == "dialogue-123"
        
        # Cleanup
        manager.disconnect(device_id)
    
    @pytest.mark.asyncio
    async def test_send_dialogue_cue_device_not_connected(self):
        """Test sending dialogue cue to non-connected device."""
        from apps.api.app.routers.websocket_cues import send_dialogue_cue
        
        result = await send_dialogue_cue(
            device_id="non-existent-device",
            text="Test",
            gesture="neutral_stance",
            tone="neutral"
        )
        
        assert result is False


class TestWebSocketEdgeCases:
    """Tests for WebSocket edge cases and error conditions."""
    
    def test_websocket_very_long_device_id(self, client):
        """Test WebSocket connection with excessively long device ID."""
        device_id = "x" * 200  # Exceeds 100 char limit
        
        with pytest.raises(Exception):  # Should reject
            with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
                pass
    
    def test_websocket_unknown_message_type(self, client):
        """Test handling of unknown message types."""
        device_id = "reachy-mini-test-unknown"
        
        with client.websocket_connect(f"/ws/cues/{device_id}") as websocket:
            # Receive welcome
            websocket.receive_json()
            
            # Send unknown message type
            websocket.send_json({
                "type": "unknown_type",
                "data": "some data"
            })
            
            # Should not crash (logged as warning)
    
    @pytest.mark.asyncio
    async def test_connection_manager_handles_send_failure(self, connection_manager):
        """Test that connection manager handles send failures gracefully."""
        from unittest.mock import AsyncMock
        
        device_id = "failing-device"
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("Send failed")
        
        connection_manager.active_connections[device_id] = mock_websocket
        
        cue = {"type": "tts", "text": "Test"}
        result = await connection_manager.send_cue(device_id, cue)
        
        assert result is False
        assert not connection_manager.is_connected(device_id)  # Should be removed


class TestWebSocketMultipleConnections:
    """Tests for handling multiple simultaneous connections."""
    
    def test_multiple_devices_connected(self, client):
        """Test multiple devices connecting simultaneously."""
        devices = ["device-01", "device-02", "device-03"]
        websockets = []
        
        # Connect all devices
        for device_id in devices:
            ws = client.websocket_connect(f"/ws/cues/{device_id}")
            ws.__enter__()
            websockets.append(ws)
            
            # Receive welcome
            ws.receive_json()
        
        # All should be connected
        # (In real implementation, would check manager.get_connected_devices())
        
        # Cleanup
        for ws in websockets:
            ws.__exit__(None, None, None)
