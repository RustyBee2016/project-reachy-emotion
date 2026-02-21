"""Tests for API client retry logic and v1 endpoint usage."""

import pytest
import os
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
    def test_stage_to_train_routes_to_direct_promote(self, mock_post):
        """Test stage_to_train helper routes to canonical /api/v1/media/promote."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": "success", "promoted_ids": ["test1"]}
        )

        api_client.stage_to_train(["test1"], "happy")

        # Verify direct promotion endpoint was called
        call_args = mock_post.call_args
        assert "/api/v1/media/promote" in call_args[0][0]

    @patch('requests.post')
    def test_promote_falls_back_to_legacy_when_canonical_missing(self, mock_post):
        missing = Mock(status_code=404, json=lambda: {"detail": "Not Found"})
        missing.raise_for_status = Mock()
        legacy_ok = Mock(status_code=200, json=lambda: {"status": "ok"})
        legacy_ok.raise_for_status = Mock()
        mock_post.side_effect = [missing, legacy_ok]

        result = api_client.promote(video_id="vid-1", dest_split="train", label="happy", dry_run=True)

        assert result["status"] == "ok"
        assert mock_post.call_count == 2
        first_url = mock_post.call_args_list[0][0][0]
        second_url = mock_post.call_args_list[1][0][0]
        assert "/api/v1/media/promote" in first_url
        assert "/api/media/promote" in second_url

    @patch("requests.post")
    def test_rebuild_manifest_uses_v1_ingest_endpoint(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
        api_client.rebuild_manifest()
        call_args = mock_post.call_args
        assert "/api/v1/ingest/manifest/rebuild" in call_args[0][0]
        assert call_args[1]["json"]["splits"] == ["train", "test"]

    @patch("requests.post")
    def test_prepare_run_frames_uses_v1_ingest_endpoint(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "ok", "run_id": "run_0001"})
        api_client.prepare_run_frames(run_id="run_0001", train_fraction=0.8, seed=42, dry_run=True)
        call_args = mock_post.call_args
        assert "/api/v1/ingest/prepare-run-frames" in call_args[0][0]
        assert call_args[1]["json"]["run_id"] == "run_0001"
        assert call_args[1]["json"]["seed"] == 42
        assert call_args[1]["json"]["dry_run"] is True

    @patch("requests.get")
    def test_get_training_status_uses_gateway_status_endpoint(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "training"})
        api_client.get_training_status("run_0001")
        call_args = mock_get.call_args
        assert "/api/training/status/run_0001" in call_args[0][0]

    @patch("requests.post")
    def test_rebuild_manifest_uses_v1_ingest_endpoint(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
        api_client.rebuild_manifest()
        call_args = mock_post.call_args
        assert "/api/v1/ingest/manifest/rebuild" in call_args[0][0]
        assert call_args[1]["json"]["splits"] == ["train", "test"]

    @patch("requests.post")
    def test_prepare_run_frames_uses_v1_ingest_endpoint(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "ok", "run_id": "run_0001"})
        api_client.prepare_run_frames(run_id="run_0001", train_fraction=0.8, seed=42)
        call_args = mock_post.call_args
        assert "/api/v1/ingest/prepare-run-frames" in call_args[0][0]
        assert call_args[1]["json"]["run_id"] == "run_0001"
        assert call_args[1]["json"]["seed"] == 42

    @patch("requests.get")
    def test_get_training_status_uses_gateway_status_endpoint(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "training"})
        api_client.get_training_status("run_0001")
        call_args = mock_get.call_args
        assert "/api/training/status/run_0001" in call_args[0][0]


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


class TestSSLVerification:
    """Test SSL verification behavior for private gateway/media hosts."""

    def test_private_https_defaults_to_verify(self):
        with patch.dict(os.environ, {}, clear=True):
            verify = api_client._request_verify("https://10.0.4.140", "GATEWAY")
            assert verify is True

    def test_explicit_verify_flag_overrides_default(self):
        with patch.dict(os.environ, {"REACHY_GATEWAY_CA_BUNDLE": "/tmp/ca.pem"}, clear=True):
            verify = api_client._request_verify("https://10.0.4.140", "GATEWAY")
            assert verify == "/tmp/ca.pem"

    @patch("requests.post")
    def test_reject_video_passes_verify_argument(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})
        with patch.dict(os.environ, {"REACHY_GATEWAY_BASE": "https://10.0.4.140"}, clear=True):
            api_client.reject_video("luma_123", "corr-1", reason="incorrect")
        assert mock_post.call_args.kwargs["verify"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
