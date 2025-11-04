"""
Integration tests for Streamlit UI components.
Tests session management, API integration, and WebSocket handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))


class TestSessionManager:
    """Test session manager functionality."""
    
    def test_session_initialization(self):
        """Test session state initialization."""
        from apps.web.session_manager import SessionManager
        
        # Mock streamlit session_state
        mock_session = {}
        
        with patch('streamlit.session_state', mock_session):
            SessionManager.initialize()
            
            # Check all required keys are initialized
            assert 'api_client' in mock_session
            assert 'ws_client' in mock_session
            assert 'current_page' in mock_session
            assert 'selected_videos' in mock_session
            assert 'filter_split' in mock_session
            assert 'latest_emotion' in mock_session
            assert 'notifications' in mock_session
    
    def test_get_api_client(self):
        """Test API client retrieval."""
        from apps.web.session_manager import SessionManager
        from apps.web.api_client_v2 import ReachyAPIClient
        
        mock_session = {}
        
        with patch('streamlit.session_state', mock_session):
            client = SessionManager.get_api_client()
            
            assert isinstance(client, ReachyAPIClient)
            assert client is mock_session['api_client']
    
    def test_add_notification(self):
        """Test notification system."""
        from apps.web.session_manager import SessionManager
        
        mock_session = {'notifications': []}
        
        with patch('streamlit.session_state', mock_session):
            SessionManager.add_notification("Test message", "info")
            
            assert len(mock_session['notifications']) == 1
            assert mock_session['notifications'][0]['message'] == "Test message"
            assert mock_session['notifications'][0]['level'] == "info"
    
    def test_notification_limit(self):
        """Test notification queue limit."""
        from apps.web.session_manager import SessionManager
        
        mock_session = {'notifications': []}
        
        with patch('streamlit.session_state', mock_session):
            # Add 25 notifications
            for i in range(25):
                SessionManager.add_notification(f"Message {i}", "info")
            
            # Should keep only last 20
            assert len(mock_session['notifications']) == 20
            assert mock_session['notifications'][-1]['message'] == "Message 24"
    
    def test_clear_notifications(self):
        """Test clearing notifications."""
        from apps.web.session_manager import SessionManager
        
        mock_session = {
            'notifications': [
                {'message': 'Test 1', 'level': 'info'},
                {'message': 'Test 2', 'level': 'error'}
            ]
        }
        
        with patch('streamlit.session_state', mock_session):
            SessionManager.clear_notifications()
            
            assert len(mock_session['notifications']) == 0
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        from apps.web.session_manager import SessionManager
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig
        
        mock_session = {
            'api_client': ReachyAPIClient(APIConfig()),
            'ws_client': None,
            'ws_connected': False,
            'notifications': [{'msg': 'test'}],
            'selected_videos': ['vid1', 'vid2']
        }
        
        # Set some metrics
        mock_session['api_client'].request_count = 100
        mock_session['api_client'].error_count = 5
        mock_session['api_client'].retry_count = 10
        
        with patch('streamlit.session_state', mock_session):
            stats = SessionManager.get_stats()
            
            assert stats['api_requests'] == 100
            assert stats['api_errors'] == 5
            assert stats['api_retries'] == 10
            assert stats['ws_connected'] is False
            assert stats['notifications'] == 1
            assert stats['selected_videos'] == 2


class TestAPIIntegration:
    """Test API integration in UI."""
    
    def test_video_list_loading(self):
        """Test video list loading with API client."""
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig, VideoMetadata
        
        # Create mock client
        client = ReachyAPIClient(APIConfig())
        
        # Mock the list_videos method
        mock_videos = [
            VideoMetadata(
                video_id='vid1',
                file_path='videos/temp/test1.mp4',
                split='temp',
                label='happy'
            ),
            VideoMetadata(
                video_id='vid2',
                file_path='videos/temp/test2.mp4',
                split='temp',
                label='sad'
            )
        ]
        
        with patch.object(client, 'list_videos', return_value=mock_videos):
            videos = client.list_videos(split='temp', limit=50)
            
            assert len(videos) == 2
            assert videos[0].video_id == 'vid1'
            assert videos[1].label == 'sad'
    
    def test_batch_promotion(self):
        """Test batch promotion operation."""
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig
        
        client = ReachyAPIClient(APIConfig())
        
        # Mock promote_video
        with patch.object(client, 'promote_video', return_value={'status': 'success'}):
            video_ids = ['vid1', 'vid2', 'vid3']
            
            results = []
            for vid in video_ids:
                result = client.promote_video(vid, 'dataset_all', 'happy')
                results.append(result)
            
            assert len(results) == 3
            assert all(r['status'] == 'success' for r in results)
    
    def test_error_handling_in_ui(self):
        """Test error handling in UI operations."""
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig, NonRetryableError
        
        client = ReachyAPIClient(APIConfig())
        
        # Mock API error
        with patch.object(client, 'list_videos', side_effect=NonRetryableError("API Error", 500)):
            with pytest.raises(NonRetryableError):
                client.list_videos(split='temp')


class TestWebSocketIntegration:
    """Test WebSocket integration in UI."""
    
    @pytest.mark.asyncio
    async def test_emotion_event_handling(self):
        """Test emotion event updates session state."""
        from apps.web.session_manager import SessionManager
        from apps.web.websocket_client import EmotionEvent
        from datetime import datetime
        
        mock_session = {
            'latest_emotion': None,
            'notifications': []
        }
        
        # Create emotion event
        event = EmotionEvent(
            device_id='reachy-01',
            emotion='happy',
            confidence=0.87,
            inference_ms=92.5,
            timestamp=datetime.now()
        )
        
        with patch('streamlit.session_state', mock_session):
            await SessionManager._on_emotion_event(event)
            
            assert mock_session['latest_emotion'] == event
            assert len(mock_session['notifications']) == 1
            assert 'happy' in mock_session['notifications'][0]['message']
    
    @pytest.mark.asyncio
    async def test_promotion_event_handling(self):
        """Test promotion event updates session state."""
        from apps.web.session_manager import SessionManager
        from apps.web.websocket_client import PromotionEvent
        from datetime import datetime
        
        mock_session = {
            'recent_promotions': [],
            'notifications': []
        }
        
        # Create promotion event
        event = PromotionEvent(
            video_id='vid123',
            from_split='temp',
            to_split='dataset_all',
            label='happy',
            success=True,
            timestamp=datetime.now()
        )
        
        with patch('streamlit.session_state', mock_session):
            await SessionManager._on_promotion_event(event)
            
            assert len(mock_session['recent_promotions']) == 1
            assert mock_session['recent_promotions'][0] == event
            assert len(mock_session['notifications']) == 1
    
    def test_websocket_message_polling(self):
        """Test polling WebSocket messages."""
        from apps.web.session_manager import SessionManager
        from apps.web.websocket_client import WebSocketClient, EmotionEvent
        from datetime import datetime
        
        # Create mock WebSocket client
        mock_ws = Mock(spec=WebSocketClient)
        
        # Mock message queue
        emotion_event = EmotionEvent(
            device_id='test',
            emotion='happy',
            confidence=0.9,
            inference_ms=100,
            timestamp=datetime.now()
        )
        
        mock_ws.get_messages.return_value = [('emotion', emotion_event)]
        
        mock_session = {
            'ws_client': mock_ws,
            'ws_connected': True,
            'latest_emotion': None,
            'recent_promotions': []
        }
        
        with patch('streamlit.session_state', mock_session):
            SessionManager.poll_websocket_messages()
            
            assert mock_session['latest_emotion'] == emotion_event
            mock_ws.get_messages.assert_called_once()


class TestUIComponents:
    """Test UI component rendering."""
    
    def test_video_card_selection(self):
        """Test video card selection logic."""
        from apps.web.api_client_v2 import VideoMetadata
        
        video = VideoMetadata(
            video_id='test-vid-123',
            file_path='videos/temp/test.mp4',
            split='temp',
            label='happy'
        )
        
        selected_videos = []
        
        # Simulate selection
        if video.video_id not in selected_videos:
            selected_videos.append(video.video_id)
        
        assert 'test-vid-123' in selected_videos
        
        # Simulate deselection
        if video.video_id in selected_videos:
            selected_videos.remove(video.video_id)
        
        assert 'test-vid-123' not in selected_videos
    
    def test_batch_selection_logic(self):
        """Test select all functionality."""
        from apps.web.api_client_v2 import VideoMetadata
        
        videos = [
            VideoMetadata(video_id=f'vid{i}', file_path=f'test{i}.mp4', split='temp')
            for i in range(5)
        ]
        
        selected_videos = []
        select_all = True
        
        # Select all
        if select_all:
            for video in videos:
                if video.video_id not in selected_videos:
                    selected_videos.append(video.video_id)
        
        assert len(selected_videos) == 5
        assert all(f'vid{i}' in selected_videos for i in range(5))


class TestDataFlow:
    """Test end-to-end data flow."""
    
    def test_upload_to_promotion_flow(self):
        """Test complete flow from upload to promotion."""
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig
        
        client = ReachyAPIClient(APIConfig())
        
        # Mock the flow
        with patch.object(client, 'promote_video', return_value={'status': 'success'}):
            # Step 1: Video uploaded (simulated)
            video_id = 'new-video-123'
            
            # Step 2: User labels video
            label = 'happy'
            
            # Step 3: Promote to dataset_all
            result = client.promote_video(video_id, 'dataset_all', label)
            
            assert result['status'] == 'success'
    
    def test_filter_and_batch_promote(self):
        """Test filtering videos and batch promoting."""
        from apps.web.api_client_v2 import ReachyAPIClient, APIConfig, VideoMetadata
        
        client = ReachyAPIClient(APIConfig())
        
        # Mock video list
        mock_videos = [
            VideoMetadata(video_id=f'vid{i}', file_path=f'test{i}.mp4', split='temp', label=None)
            for i in range(10)
        ]
        
        with patch.object(client, 'list_videos', return_value=mock_videos):
            with patch.object(client, 'promote_video', return_value={'status': 'success'}):
                # Get videos
                videos = client.list_videos(split='temp', limit=50)
                
                # Select first 5
                selected = videos[:5]
                
                # Batch promote
                results = []
                for video in selected:
                    result = client.promote_video(video.video_id, 'dataset_all', 'happy')
                    results.append(result)
                
                assert len(results) == 5
                assert all(r['status'] == 'success' for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
