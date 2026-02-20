"""
Tests for enhanced API client with retry logic and idempotency.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError
import time
from datetime import datetime

from apps.web.api_client_v2 import (
    ReachyAPIClient,
    APIConfig,
    APIError,
    RetryableError,
    NonRetryableError,
    VideoMetadata
)


@pytest.fixture
def api_client():
    """Create API client with test configuration."""
    config = APIConfig(
        base_url='http://test.local/api',
        timeout=5,
        max_retries=3,
        api_token='test-token'
    )
    return ReachyAPIClient(config)


@pytest.fixture
def mock_response():
    """Create mock response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {'status': 'success'}
    response.text = '{"status": "success"}'
    return response


class TestRetryLogic:
    """Test exponential backoff retry logic."""
    
    def test_success_no_retry(self, api_client, mock_response):
        """Test successful request without retry."""
        with patch.object(api_client.session, 'request', return_value=mock_response):
            result = api_client._make_request('GET', '/test')
            
            assert result == {'status': 'success'}
            assert api_client.request_count == 1
            assert api_client.retry_count == 0
    
    def test_retry_on_500_error(self, api_client):
        """Test retry on 500 server error."""
        # First two calls fail with 500, third succeeds
        responses = [
            Mock(status_code=500),
            Mock(status_code=500),
            Mock(status_code=200, json=lambda: {'status': 'success'}, text='{}')
        ]
        
        with patch.object(api_client.session, 'request', side_effect=responses):
            with patch('time.sleep'):  # Skip actual sleep
                result = api_client._make_request('GET', '/test')
                
                assert result == {'status': 'success'}
                assert api_client.request_count == 3
                assert api_client.retry_count == 2
    
    def test_retry_on_timeout(self, api_client, mock_response):
        """Test retry on timeout error."""
        # First call times out, second succeeds
        with patch.object(api_client.session, 'request', side_effect=[
            Timeout("Request timed out"),
            mock_response
        ]):
            with patch('time.sleep'):
                result = api_client._make_request('GET', '/test')
                
                assert result == {'status': 'success'}
                assert api_client.retry_count == 1
    
    def test_retry_on_connection_error(self, api_client, mock_response):
        """Test retry on connection error."""
        with patch.object(api_client.session, 'request', side_effect=[
            ConnectionError("Connection refused"),
            mock_response
        ]):
            with patch('time.sleep'):
                result = api_client._make_request('GET', '/test')
                
                assert result == {'status': 'success'}
                assert api_client.retry_count == 1
    
    def test_no_retry_on_400_error(self, api_client):
        """Test no retry on 400 client error."""
        response = Mock(status_code=400, json=lambda: {'error': 'Bad request'}, text='{}')
        
        with patch.object(api_client.session, 'request', return_value=response):
            with pytest.raises(NonRetryableError) as exc_info:
                api_client._make_request('GET', '/test')
            
            assert exc_info.value.status_code == 400
            assert api_client.request_count == 1
            assert api_client.retry_count == 0
    
    def test_max_retries_exhausted(self, api_client):
        """Test failure after max retries exhausted."""
        response = Mock(status_code=500)
        
        with patch.object(api_client.session, 'request', return_value=response):
            with patch('time.sleep'):
                with pytest.raises(RetryableError):
                    api_client._make_request('GET', '/test')
                
                assert api_client.request_count == 3  # max_retries
                assert api_client.retry_count == 3
    
    def test_exponential_backoff_timing(self, api_client):
        """Test exponential backoff delay calculation."""
        response = Mock(status_code=500)
        sleep_times = []
        
        def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch.object(api_client.session, 'request', return_value=response):
            with patch('time.sleep', side_effect=mock_sleep):
                with pytest.raises(RetryableError):
                    api_client._make_request('GET', '/test')
        
        # Check delays are increasing (exponential)
        assert len(sleep_times) == 2  # 2 retries after first attempt
        assert sleep_times[1] > sleep_times[0]
        # With jitter, delays should be roughly: 1s, 2s (with variance)
        assert 0.5 <= sleep_times[0] <= 1.5
        assert 1.0 <= sleep_times[1] <= 3.0


class TestIdempotency:
    """Test idempotency key generation and usage."""
    
    def test_idempotency_key_generation(self, api_client):
        """Test idempotency key is deterministic within time window."""
        key1 = api_client._generate_idempotency_key('video1', 'train', 'happy')
        key2 = api_client._generate_idempotency_key('video1', 'train', 'happy')
        
        # Should be same within same minute
        assert key1 == key2
        assert len(key1) == 32  # SHA256 truncated
    
    def test_idempotency_key_different_args(self, api_client):
        """Test different arguments produce different keys."""
        key1 = api_client._generate_idempotency_key('video1', 'train', 'happy')
        key2 = api_client._generate_idempotency_key('video2', 'train', 'happy')
        
        assert key1 != key2
    
    def test_promote_video_includes_idempotency_key(self, api_client):
        """Test promotion includes idempotency key in headers."""
        mock_response = Mock(status_code=200, json=lambda: {'status': 'success'}, text='{}')
        
        with patch.object(api_client.session, 'request', return_value=mock_response) as mock_request:
            api_client.promote_video('video123', 'train', 'happy')
            
            # Check idempotency key was included
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            assert 'Idempotency-Key' in headers
            assert len(headers['Idempotency-Key']) == 32


class TestVideoManagement:
    """Test video management API methods."""
    
    def test_list_videos_basic(self, api_client):
        """Test basic video listing."""
        mock_response = Mock(
            status_code=200,
            json=lambda: {
                'videos': [
                    {
                        'video_id': 'vid1',
                        'file_path': 'videos/temp/test1.mp4',
                        'split': 'temp',
                        'label': 'happy',
                        'duration_sec': 5.0,
                        'width': 1920,
                        'height': 1080,
                        'fps': 30.0,
                        'size_bytes': 1000000,
                        'sha256': 'a' * 64,
                        'created_at': '2025-01-01T00:00:00',
                        'updated_at': '2025-01-01T00:00:00'
                    }
                ]
            },
            text='{}'
        )
        
        with patch.object(api_client.session, 'request', return_value=mock_response):
            videos = api_client.list_videos(split='temp', limit=10)
            
            assert len(videos) == 1
            assert isinstance(videos[0], VideoMetadata)
            assert videos[0].video_id == 'vid1'
            assert videos[0].split == 'temp'
            assert videos[0].label == 'happy'
    
    def test_list_videos_with_filters(self, api_client):
        """Test video listing with filters."""
        mock_response = Mock(
            status_code=200,
            json=lambda: {'videos': []},
            text='{}'
        )
        
        with patch.object(api_client.session, 'request', return_value=mock_response) as mock_request:
            api_client.list_videos(
                split='train',
                limit=50,
                offset=10,
                label='happy',
                after_date=datetime(2025, 1, 1)
            )
            
            # Check query parameters
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['split'] == 'train'
            assert params['limit'] == 50
            assert params['offset'] == 10
            assert params['label'] == 'happy'
            assert 'after' in params
    
    def test_promote_video_basic(self, api_client):
        """Test basic video promotion."""
        mock_response = Mock(
            status_code=200,
            json=lambda: {'status': 'success', 'video_id': 'vid1'},
            text='{}'
        )
        
        with patch.object(api_client.session, 'request', return_value=mock_response):
            result = api_client.promote_video('vid1', 'train', 'happy')
            
            assert result['status'] == 'success'
            assert result['video_id'] == 'vid1'
    
    def test_promote_video_requires_label_for_train(self, api_client):
        """Test label requirement for train promotion."""
        with pytest.raises(ValueError) as exc_info:
            api_client.promote_video('vid1', 'train', label=None)
        
        assert 'label required' in str(exc_info.value).lower()
    
    def test_promote_video_dry_run(self, api_client):
        """Test dry run promotion."""
        mock_response = Mock(
            status_code=200,
            json=lambda: {'status': 'success', 'dry_run': True},
            text='{}'
        )
        
        with patch.object(api_client.session, 'request', return_value=mock_response) as mock_request:
            result = api_client.promote_video('vid1', 'train', 'happy', dry_run=True)
            
            # Check dry_run flag in payload
            call_args = mock_request.call_args
            payload = call_args[1]['json']
            assert payload['dry_run'] is True
            assert result['dry_run'] is True
    
    @pytest.mark.asyncio
    async def test_batch_promote_async(self, api_client):
        """Test async batch promotion."""
        promotions = [
            ('vid1', 'train', 'happy'),
            ('vid2', 'train', 'sad'),
            ('vid3', 'train', 'happy')
        ]
        
        results = await api_client.batch_promote_async(promotions)
        
        # Should return results for all promotions
        assert len(results) == 3
        for result in results:
            assert result['status'] == 'success'


class TestHealthAndMetrics:
    """Test health check and metrics."""
    
    def test_health_check_healthy(self, api_client):
        """Test health check when API is healthy."""
        mock_response = Mock(
            status_code=200,
            json=lambda: {'status': 'healthy'},
            text='{}'
        )
        
        with patch.object(api_client.session, 'request', return_value=mock_response):
            assert api_client.health_check() is True
    
    def test_health_check_unhealthy(self, api_client):
        """Test health check when API is down."""
        with patch.object(api_client.session, 'request', side_effect=ConnectionError()):
            assert api_client.health_check() is False
    
    def test_get_stats(self, api_client):
        """Test client statistics."""
        # Simulate some requests
        api_client.request_count = 100
        api_client.error_count = 5
        api_client.retry_count = 10
        
        stats = api_client.get_stats()
        
        assert stats['request_count'] == 100
        assert stats['error_count'] == 5
        assert stats['retry_count'] == 10
        assert stats['error_rate'] == 0.05
        assert stats['retry_rate'] == 0.10


class TestErrorHandling:
    """Test error handling and classification."""
    
    def test_4xx_raises_non_retryable_error(self, api_client):
        """Test 4xx errors raise NonRetryableError."""
        for status_code in [400, 401, 403, 404, 422]:
            response = Mock(status_code=status_code, json=lambda: {}, text='{}')
            
            with patch.object(api_client.session, 'request', return_value=response):
                with pytest.raises(NonRetryableError) as exc_info:
                    api_client._make_request('GET', '/test')
                
                assert exc_info.value.status_code == status_code
    
    def test_5xx_triggers_retry(self, api_client):
        """Test 5xx errors trigger retry."""
        for status_code in [500, 502, 503, 504]:
            response = Mock(status_code=status_code)
            
            with patch.object(api_client.session, 'request', return_value=response):
                with patch('time.sleep'):
                    with pytest.raises(RetryableError):
                        api_client._make_request('GET', '/test', max_retries=2)
    
    def test_invalid_json_raises_non_retryable(self, api_client):
        """Test invalid JSON response raises NonRetryableError."""
        response = Mock(status_code=200, text='invalid json')
        response.json.side_effect = ValueError("Invalid JSON")
        
        with patch.object(api_client.session, 'request', return_value=response):
            with pytest.raises(NonRetryableError):
                api_client._make_request('GET', '/test')


class TestConfiguration:
    """Test API configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        client = ReachyAPIClient()
        
        assert client.config.timeout == 30
        assert client.config.max_retries == 3
        assert client.config.verify_ssl is True
    
    def test_custom_configuration(self):
        """Test custom configuration."""
        config = APIConfig(
            base_url='http://custom.local',
            timeout=60,
            max_retries=5,
            api_token='custom-token'
        )
        client = ReachyAPIClient(config)
        
        assert client.config.base_url == 'http://custom.local'
        assert client.config.timeout == 60
        assert client.config.max_retries == 5
        assert client.config.api_token == 'custom-token'
    
    def test_headers_include_auth_token(self):
        """Test authorization header is included when token is set."""
        config = APIConfig(api_token='test-token-123')
        client = ReachyAPIClient(config)
        
        headers = client._default_headers()
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-token-123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
