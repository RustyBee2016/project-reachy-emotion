"""Tests for API client retry logic and v1 endpoint usage."""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import ConnectionError, HTTPError, Timeout

from apps.web import api_client


class TestRetryLogic:
    """Test retry decorator functionality."""
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    @patch('requests.get')
    def test_retry_on_connection_error(self, mock_get, mock_sleep):
        """Test that connection errors trigger retry."""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "items": [],
                        "pagination": {"total": 0, "limit": 50, "offset": 0, "has_more": False}
                    }
                }
            )
        ]
        
        result = api_client.list_videos("temp")
        
        # Should have retried 2 times before success
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2
        assert result["items"] == []
    
    @patch('time.sleep')
    @patch('requests.get')
    def test_retry_on_timeout(self, mock_get, mock_sleep):
        """Test that timeout errors trigger retry."""
        mock_get.side_effect = [
            Timeout("Request timed out"),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "items": [{"video_id": "test1"}],
                        "pagination": {"total": 1, "limit": 50, "offset": 0, "has_more": False}
                    }
                }
            )
        ]
        
        result = api_client.list_videos("temp")
        
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1
        assert len(result["items"]) == 1
    
    @patch('time.sleep')
    @patch('requests.get')
    def test_retry_on_500_error(self, mock_get, mock_sleep):
        """Test that 5xx server errors trigger retry."""
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = HTTPError(response=mock_response_500)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "status": "success",
            "data": {
                "items": [],
                "pagination": {"total": 0, "limit": 50, "offset": 0, "has_more": False}
            }
        }
        mock_response_success.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_response_500, mock_response_success]
        
        result = api_client.list_videos("temp")
        
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1
        assert result["items"] == []
    
    @patch('requests.get')
    def test_no_retry_on_400_error(self, mock_get):
        """Test that 4xx client errors don't trigger retry."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        with pytest.raises(HTTPError):
            api_client.list_videos("invalid")
        
        # Should only try once (no retry for 4xx)
        assert mock_get.call_count == 1
    
    @patch('time.sleep')
    @patch('requests.get')
    def test_exponential_backoff(self, mock_get, mock_sleep):
        """Test that retry uses exponential backoff."""
        mock_get.side_effect = [
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            ConnectionError("Failed"),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {
                        "items": [],
                        "pagination": {"total": 0, "limit": 50, "offset": 0, "has_more": False}
                    }
                }
            )
        ]
        
        api_client.list_videos("temp")
        
        # Check that sleep times increase exponentially
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 1.0  # First retry: 1s
        assert sleep_calls[1] == 2.0  # Second retry: 2s
        assert sleep_calls[2] == 4.0  # Third retry: 4s


class TestV1EndpointUsage:
    """Test that client uses v1 endpoints correctly."""
    
    @patch('requests.get')
    def test_list_videos_uses_v1_endpoint(self, mock_get):
        """Test that list_videos calls /api/v1/media/list."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": "success",
                "data": {
                    "items": [{"video_id": "test1"}],
                    "pagination": {"total": 1, "limit": 50, "offset": 0, "has_more": False}
                },
                "meta": {"correlation_id": "test", "timestamp": "2025-01-01", "version": "v1"}
            }
        )
        
        api_client.list_videos("temp")
        
        # Verify v1 endpoint was called
        call_args = mock_get.call_args
        assert "/api/v1/media/list" in call_args[0][0]
    
    @patch('requests.post')
    def test_stage_uses_v1_endpoint(self, mock_post):
        """Test that stage_to_dataset_all calls /api/v1/promote/stage."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": "success", "promoted_ids": ["test1"]}
        )
        
        api_client.stage_to_dataset_all(["test1"], "happy")
        
        # Verify v1 endpoint was called
        call_args = mock_post.call_args
        assert "/api/v1/promote/stage" in call_args[0][0]


class TestResponseParsing:
    """Test that client correctly parses v1 response format."""
    
    @patch('requests.get')
    def test_parse_success_response(self, mock_get):
        """Test parsing of standardized success response."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": "success",
                "data": {
                    "items": [
                        {"video_id": "vid1", "file_path": "temp/vid1.mp4", "size_bytes": 1024, "mtime": 1234567890, "split": "temp"},
                        {"video_id": "vid2", "file_path": "temp/vid2.mp4", "size_bytes": 2048, "mtime": 1234567891, "split": "temp"}
                    ],
                    "pagination": {
                        "total": 2,
                        "limit": 50,
                        "offset": 0,
                        "has_more": False
                    }
                },
                "meta": {
                    "correlation_id": "test-123",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "version": "v1"
                }
            }
        )
        
        result = api_client.list_videos("temp")
        
        # Verify unwrapped format
        assert "items" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert "has_more" in result
        
        # Verify data
        assert len(result["items"]) == 2
        assert result["total"] == 2
        assert result["has_more"] is False
        assert result["items"][0]["video_id"] == "vid1"
    
    @patch('requests.get')
    def test_parse_empty_response(self, mock_get):
        """Test parsing of empty results."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "status": "success",
                "data": {
                    "items": [],
                    "pagination": {"total": 0, "limit": 50, "offset": 0, "has_more": False}
                },
                "meta": {"correlation_id": "test", "timestamp": "2025-01-01", "version": "v1"}
            }
        )
        
        result = api_client.list_videos("temp")
        
        assert result["items"] == []
        assert result["total"] == 0
        assert result["has_more"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
