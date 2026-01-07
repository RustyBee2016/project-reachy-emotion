"""Tests for thumbnail generation utility."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.utils.thumbnail_generator import (
    ThumbnailGenerationError,
    ThumbnailGenerator,
)


class TestThumbnailGenerator:
    """Test suite for ThumbnailGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a ThumbnailGenerator instance."""
        with patch.object(ThumbnailGenerator, "_validate_ffmpeg"):
            return ThumbnailGenerator()
    
    @pytest.fixture
    def temp_video(self, tmp_path):
        """Create a temporary video file for testing."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video content")
        return video_path
    
    @pytest.fixture
    def output_path(self, tmp_path):
        """Create output path for thumbnail."""
        return tmp_path / "thumbs" / "test_video.jpg"
    
    def test_validate_ffmpeg_success(self):
        """Test FFmpeg validation succeeds when ffmpeg is available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            generator = ThumbnailGenerator()
            assert generator.ffmpeg_path == "ffmpeg"
    
    def test_validate_ffmpeg_not_found(self):
        """Test FFmpeg validation fails when ffmpeg is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(ThumbnailGenerationError, match="FFmpeg not found"):
                ThumbnailGenerator()
    
    def test_validate_ffmpeg_failed(self):
        """Test FFmpeg validation fails when ffmpeg returns error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"
        
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(ThumbnailGenerationError, match="FFmpeg validation failed"):
                ThumbnailGenerator()
    
    def test_generate_thumbnail_success(self, generator, temp_video, output_path):
        """Test successful thumbnail generation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result):
            # Mock the output file creation
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda: True
                
                result = generator.generate_thumbnail(
                    video_path=temp_video,
                    output_path=output_path,
                )
                
                assert result == output_path
    
    def test_generate_thumbnail_video_not_found(self, generator, output_path):
        """Test thumbnail generation fails when video doesn't exist."""
        non_existent = Path("/nonexistent/video.mp4")
        
        with pytest.raises(FileNotFoundError, match="Video file not found"):
            generator.generate_thumbnail(
                video_path=non_existent,
                output_path=output_path,
            )
    
    def test_generate_thumbnail_existing_no_overwrite(
        self, generator, temp_video, output_path
    ):
        """Test thumbnail generation skips existing file when overwrite=False."""
        # Create the output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("existing thumbnail")
        
        result = generator.generate_thumbnail(
            video_path=temp_video,
            output_path=output_path,
            overwrite=False,
        )
        
        assert result == output_path
        assert output_path.read_text() == "existing thumbnail"
    
    def test_generate_thumbnail_ffmpeg_failure(self, generator, temp_video, output_path):
        """Test thumbnail generation fails when FFmpeg returns error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg error"
        
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(ThumbnailGenerationError, match="FFmpeg failed"):
                generator.generate_thumbnail(
                    video_path=temp_video,
                    output_path=output_path,
                )
    
    def test_generate_thumbnail_timeout(self, generator, temp_video, output_path):
        """Test thumbnail generation fails on timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            with pytest.raises(ThumbnailGenerationError, match="timed out"):
                generator.generate_thumbnail(
                    video_path=temp_video,
                    output_path=output_path,
                )
    
    def test_generate_thumbnail_creates_output_directory(
        self, generator, temp_video, output_path
    ):
        """Test thumbnail generation creates output directory if needed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda: True
                
                generator.generate_thumbnail(
                    video_path=temp_video,
                    output_path=output_path,
                )
                
                # Verify parent directory would be created
                assert output_path.parent.name == "thumbs"
    
    def test_generate_thumbnail_for_video_id_success(self, generator, tmp_path):
        """Test generating thumbnail by video ID."""
        videos_root = tmp_path / "videos"
        temp_dir = videos_root / "temp"
        thumbs_dir = videos_root / "thumbs"
        
        temp_dir.mkdir(parents=True)
        thumbs_dir.mkdir(parents=True)
        
        # Create test video
        video_file = temp_dir / "test_video.mp4"
        video_file.write_text("fake video")
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda: True
                
                result = generator.generate_thumbnail_for_video_id(
                    video_id="test_video",
                    videos_root=videos_root,
                    split="temp",
                )
                
                assert result == thumbs_dir / "test_video.jpg"
    
    def test_generate_thumbnail_for_video_id_not_found(self, generator, tmp_path):
        """Test generating thumbnail returns None when video not found."""
        videos_root = tmp_path / "videos"
        temp_dir = videos_root / "temp"
        temp_dir.mkdir(parents=True)
        
        result = generator.generate_thumbnail_for_video_id(
            video_id="nonexistent",
            videos_root=videos_root,
            split="temp",
        )
        
        assert result is None
    
    def test_generate_thumbnail_for_video_id_multiple_extensions(
        self, generator, tmp_path
    ):
        """Test video ID lookup works with different extensions."""
        videos_root = tmp_path / "videos"
        temp_dir = videos_root / "temp"
        thumbs_dir = videos_root / "thumbs"
        
        temp_dir.mkdir(parents=True)
        thumbs_dir.mkdir(parents=True)
        
        # Create video with .avi extension
        video_file = temp_dir / "test_video.avi"
        video_file.write_text("fake video")
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists") as mock_exists:
                mock_exists.side_effect = lambda: True
                
                result = generator.generate_thumbnail_for_video_id(
                    video_id="test_video",
                    videos_root=videos_root,
                    split="temp",
                )
                
                assert result == thumbs_dir / "test_video.jpg"
