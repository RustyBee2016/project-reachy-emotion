"""
Test suite for enhanced API client with retry logic and idempotency.
Run with: pytest tests/test_api_client.py -v
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))


class TestAPIClientRetryLogic:
    """Test exponential backoff retry logic."""
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_exponential_backoff_on_500_error(self, mock_request, mock_sleep):
        """Test that 500 errors trigger exponential backoff."""
        # Import will fail until implementation exists
        from apps.web.api_client_v2 import ReachyAPIClient
        
        # Setup mock to fail twice, then succeed
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.json.return_value = {'error': 'server error'}
        mock_response_500.raise_for_status.side_effect = HTTPError(response=mock_response_500)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {'status': 'ok'}
        
        mock_request.side_effect = [
            mock_response_500,
            mock_response_500,
            mock_response_success
        ]
        
        client = ReachyAPIClient()
        result = client.list_videos('temp')
        
        # Verify retries happened
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2
        
        # Verify exponential delays (with jitter, approximate)
        first_delay = mock_sleep.call_args_list[0][0][0]
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert 0.5 <= first_delay <= 1.5  # ~1s with jitter
        assert 1.0 <= second_delay <= 3.0  # ~2s with jitter
    
    @patch('requests.Session.request')
    def test_no_retry_on_400_error(self, mock_request):
        """Test that 400 errors don't trigger retry."""
        from apps.web.api_client_v2 import ReachyAPIClient, NonRetryableError
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'bad request'}
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        client = ReachyAPIClient()
        
        with pytest.raises(NonRetryableError) as exc_info:
            client.list_videos('invalid_split')
        
        assert exc_info.value.status_code == 400
        assert mock_request.call_count == 1  # No retry
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_retry_on_connection_error(self, mock_request, mock_sleep):
        """Test retry on connection errors."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        mock_request.side_effect = [
            ConnectionError("Connection failed"),
            Mock(status_code=200, json=lambda: {'videos': []})
        ]
        
        client = ReachyAPIClient()
        result = client.list_videos('temp')
        
        assert mock_request.call_count == 2
        assert mock_sleep.call_count == 1


class TestIdempotencyKeys:
    """Test idempotency key generation and usage."""
    
    def test_idempotency_key_generation(self):
        """Test that idempotency keys are unique but deterministic."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        client = ReachyAPIClient()
        
        # Same inputs within same minute should generate same key
        key1 = client._generate_idempotency_key('video1', 'train', 'happy')
        time.sleep(0.1)
        key2 = client._generate_idempotency_key('video1', 'train', 'happy')
        assert key1 == key2
        
        # Different inputs should generate different keys
        key3 = client._generate_idempotency_key('video2', 'train', 'happy')
        assert key1 != key3
    
    @patch('requests.Session.request')
    def test_idempotency_header_included(self, mock_request):
        """Test that idempotency key is included in headers."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {'status': 'success'}
        )
        
        client = ReachyAPIClient()
        client.promote_video('vid123', 'train', 'happy')
        
        # Check headers included idempotency key
        call_kwargs = mock_request.call_args[1]
        assert 'headers' in call_kwargs
        assert 'Idempotency-Key' in call_kwargs['headers']
        assert len(call_kwargs['headers']['Idempotency-Key']) == 32


class TestAsyncBatchOperations:
    """Test async batch operations."""
    
    @pytest.mark.asyncio
    async def test_batch_promote_async(self):
        """Test batch promotion of multiple videos."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        client = ReachyAPIClient()
        
        # Mock the async promotion
        with patch.object(client, '_promote_async') as mock_promote:
            mock_promote.return_value = {'status': 'success'}
            
            promotions = [
                ('vid1', 'train', 'happy'),
                ('vid2', 'train', 'sad'),
                ('vid3', 'train', 'neutral')
            ]
            
            results = await client.batch_promote_async(promotions)
            
            assert len(results) == 3
            assert all(r['status'] == 'success' for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_promote_with_failures(self):
        """Test batch promotion handles partial failures."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        client = ReachyAPIClient()
        
        # Mock with one failure
        async def mock_promote(session, vid, split, label):
            if vid == 'vid2':
                raise Exception("Promotion failed")
            return {'status': 'success', 'video_id': vid}
        
        with patch.object(client, '_promote_async', side_effect=mock_promote):
            promotions = [
                ('vid1', 'train', 'happy'),
                ('vid2', 'train', 'sad'),
                ('vid3', 'train', 'neutral')
            ]
            
            results = await client.batch_promote_async(promotions)
            
            # Should get 2 successes despite 1 failure
            assert len(results) == 2
            assert results[0]['video_id'] == 'vid1'
            assert results[1]['video_id'] == 'vid3'


class TestConnectionPooling:
    """Test connection pooling and session management."""
    
    def test_session_reuse(self):
        """Test that HTTP session is reused across requests."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        client = ReachyAPIClient()
        session1 = client.session
        
        # Make multiple requests
        with patch.object(client.session, 'request', return_value=Mock(status_code=200, json=lambda: {})):
            client.list_videos('temp')
            client.list_videos('train')
        
        # Session should be the same
        assert client.session is session1
    
    def test_health_check(self):
        """Test health check endpoint."""
        from apps.web.api_client_v2 import ReachyAPIClient
        
        client = ReachyAPIClient()
        
        with patch.object(client, '_make_request', return_value={'status': 'healthy'}):
            assert client.health_check() is True
        
        with patch.object(client, '_make_request', side_effect=Exception("Connection failed")):
            assert client.health_check() is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--color=yes'])
