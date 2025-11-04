"""
Test suite for WebSocket client with auto-reconnection and event handling.
Run with: pytest tests/test_websocket_client.py -v
"""

import pytest
import asyncio
import queue
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))


class TestWebSocketConnection:
    """Test WebSocket connection and reconnection logic."""
    
    @pytest.mark.asyncio
    async def test_initial_connection(self):
        """Test initial WebSocket connection."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient') as mock_sio:
            mock_sio_instance = AsyncMock()
            mock_sio.return_value = mock_sio_instance
            
            client = WebSocketClient('http://10.0.4.140:8000', 'test-device')
            await client.connect()
            
            mock_sio_instance.connect.assert_called_once_with('http://10.0.4.140:8000', namespaces=['/'])
            assert client.device_id == 'test-device'
    
    @pytest.mark.asyncio
    async def test_auto_reconnection(self):
        """Test automatic reconnection with exponential backoff."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient') as mock_sio:
            mock_sio_instance = Mock()
            mock_sio.return_value = mock_sio_instance
            
            # Verify reconnection settings
            client = WebSocketClient('http://10.0.4.140:8000')
            
            assert mock_sio.call_args[1]['reconnection'] is True
            assert mock_sio.call_args[1]['reconnection_delay'] == 1
            assert mock_sio.call_args[1]['reconnection_delay_max'] == 30
    
    @pytest.mark.asyncio
    async def test_registration_on_connect(self):
        """Test device registration sent on connection."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient') as mock_sio:
            mock_sio_instance = AsyncMock()
            mock_sio.return_value = mock_sio_instance
            
            client = WebSocketClient('http://10.0.4.140:8000', 'web-ui-01')
            
            # Simulate connection event
            connect_handler = None
            def on_event(event):
                def decorator(func):
                    nonlocal connect_handler
                    if event == 'connect':
                        connect_handler = func
                    return func
                return decorator
            
            mock_sio_instance.on = on_event
            mock_sio_instance.event = on_event
            
            # Trigger connect event
            await client.connect()
            if connect_handler:
                await connect_handler()
            
            # Verify registration message
            mock_sio_instance.emit.assert_called()
            call_args = mock_sio_instance.emit.call_args
            assert call_args[0][0] == 'register'
            assert call_args[0][1]['device_id'] == 'web-ui-01'
            assert call_args[0][1]['device_type'] == 'ui'


class TestEventHandling:
    """Test event subscription and handling."""
    
    def test_event_subscription(self):
        """Test subscribing to events with callbacks."""
        from apps.web.websocket_client import WebSocketClient, EventType
        
        client = WebSocketClient('http://10.0.4.140:8000')
        
        callback_called = False
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
        
        client.subscribe(EventType.EMOTION, test_callback)
        
        assert EventType.EMOTION in client.subscriptions
        assert test_callback in client.subscriptions[EventType.EMOTION]
    
    @pytest.mark.asyncio
    async def test_emotion_event_handling(self):
        """Test emotion event parsing and queuing."""
        from apps.web.websocket_client import WebSocketClient, EmotionEvent
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            # Simulate emotion event
            event_data = {
                'device_id': 'reachy-mini-01',
                'emotion': 'happy',
                'confidence': 0.87,
                'inference_ms': 92.5,
                'timestamp': '2025-11-03T21:30:00Z'
            }
            
            # Process event
            await client._handle_emotion_event(event_data)
            
            # Check message was queued
            assert not client.message_queue.empty()
            event_type, event = client.message_queue.get_nowait()
            assert event_type == 'emotion'
            assert isinstance(event, EmotionEvent)
            assert event.emotion == 'happy'
            assert event.confidence == 0.87
    
    @pytest.mark.asyncio
    async def test_promotion_event_handling(self):
        """Test promotion completion event handling."""
        from apps.web.websocket_client import WebSocketClient, PromotionEvent
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            event_data = {
                'video_id': 'abc123',
                'from_split': 'temp',
                'to_split': 'dataset_all',
                'label': 'happy',
                'success': True,
                'timestamp': '2025-11-03T21:30:00Z'
            }
            
            await client._handle_promotion_event(event_data)
            
            event_type, event = client.message_queue.get_nowait()
            assert event_type == 'promotion'
            assert isinstance(event, PromotionEvent)
            assert event.video_id == 'abc123'
            assert event.success is True
    
    @pytest.mark.asyncio
    async def test_training_event_handling(self):
        """Test training status event handling."""
        from apps.web.websocket_client import WebSocketClient, TrainingEvent
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            event_data = {
                'run_id': 'run_001',
                'status': 'training',
                'epoch': 10,
                'loss': 0.234,
                'accuracy': 0.856,
                'f1_score': 0.842,
                'timestamp': '2025-11-03T21:30:00Z'
            }
            
            await client._handle_training_event(event_data)
            
            event_type, event = client.message_queue.get_nowait()
            assert event_type == 'training'
            assert isinstance(event, TrainingEvent)
            assert event.run_id == 'run_001'
            assert event.accuracy == 0.856


class TestMessageQueue:
    """Test thread-safe message queuing."""
    
    def test_message_queue_operations(self):
        """Test basic queue operations."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            # Queue should start empty
            assert client.message_queue.empty()
            
            # Add messages
            client.message_queue.put(('test', {'data': 'value'}))
            assert not client.message_queue.empty()
            
            # Retrieve message
            msg_type, msg_data = client.message_queue.get_nowait()
            assert msg_type == 'test'
            assert msg_data['data'] == 'value'
            assert client.message_queue.empty()
    
    def test_get_messages_batch(self):
        """Test batch message retrieval."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            # Add multiple messages
            for i in range(5):
                client.message_queue.put(('test', {'id': i}))
            
            # Get all messages
            messages = client.get_messages(max_count=10)
            assert len(messages) == 5
            assert all(msg[0] == 'test' for msg in messages)
            assert client.message_queue.empty()


class TestHeartbeat:
    """Test heartbeat mechanism."""
    
    @pytest.mark.asyncio
    async def test_heartbeat_sending(self):
        """Test periodic heartbeat sending."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient') as mock_sio:
            mock_sio_instance = AsyncMock()
            mock_sio.return_value = mock_sio_instance
            
            client = WebSocketClient('http://10.0.4.140:8000', heartbeat_interval=1)
            client.connected = True
            
            # Start heartbeat
            heartbeat_task = asyncio.create_task(client._heartbeat_loop())
            
            # Wait for heartbeats
            await asyncio.sleep(2.5)
            
            # Cancel task
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            
            # Should have sent at least 2 heartbeats
            assert mock_sio_instance.emit.call_count >= 2
            
            # Check heartbeat format
            heartbeat_calls = [
                call for call in mock_sio_instance.emit.call_args_list
                if call[0][0] == 'heartbeat'
            ]
            assert len(heartbeat_calls) >= 2
    
    def test_heartbeat_timeout_detection(self):
        """Test detection of missed heartbeats."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000', heartbeat_interval=30)
            client.connected = True
            client.last_heartbeat = datetime.now()
            
            # Check healthy
            assert client.is_healthy()
            
            # Simulate timeout
            import datetime as dt
            client.last_heartbeat = datetime.now() - dt.timedelta(seconds=100)
            assert not client.is_healthy()


class TestMetrics:
    """Test metrics tracking."""
    
    def test_metrics_collection(self):
        """Test that client tracks metrics."""
        from apps.web.websocket_client import WebSocketClient
        
        with patch('socketio.AsyncClient'):
            client = WebSocketClient('http://10.0.4.140:8000')
            
            # Initial metrics
            assert client.events_received == 0
            assert client.errors_count == 0
            assert client.reconnection_count == 0
            
            # Simulate events
            client.events_received += 1
            client.errors_count += 1
            
            metrics = client.get_metrics()
            assert metrics['events_received'] == 1
            assert metrics['errors_count'] == 1
            assert metrics['reconnection_count'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--color=yes'])
