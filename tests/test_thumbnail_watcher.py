"""Tests for thumbnail watcher service."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.api.app.services.thumbnail_watcher import ThumbnailWatcherService
from shared.utils.thumbnail_generator import ThumbnailGenerationError


class TestThumbnailWatcherService:
    """Test suite for ThumbnailWatcherService."""
    
    @pytest.fixture
    def videos_root(self, tmp_path):
        """Create a temporary videos root directory."""
        root = tmp_path / "videos"
        root.mkdir()
        
        # Create split directories
        (root / "temp").mkdir()
        (root / "thumbs").mkdir()
        
        return root
    
    @pytest.fixture
    def watcher(self, videos_root):
        """Create a ThumbnailWatcherService instance."""
        with patch("shared.utils.thumbnail_generator.ThumbnailGenerator._validate_ffmpeg"):
            return ThumbnailWatcherService(
                videos_root=videos_root,
                watch_splits=["temp"],
                poll_interval=0.1,  # Fast polling for tests
            )
    
    def test_initialization(self, watcher, videos_root):
        """Test watcher initializes correctly."""
        assert watcher.videos_root == videos_root
        assert watcher.watch_splits == ["temp"]
        assert watcher.poll_interval == 0.1
        assert watcher.thumbs_path == videos_root / "thumbs"
        assert not watcher._running
        assert len(watcher._processed_videos) == 0
    
    def test_thumbs_directory_created(self, tmp_path):
        """Test thumbs directory is created if it doesn't exist."""
        root = tmp_path / "videos"
        root.mkdir()
        (root / "temp").mkdir()
        
        with patch("shared.utils.thumbnail_generator.ThumbnailGenerator._validate_ffmpeg"):
            watcher = ThumbnailWatcherService(
                videos_root=root,
                watch_splits=["temp"],
            )
        
        assert (root / "thumbs").exists()
    
    def test_scan_for_new_videos_empty(self, watcher):
        """Test scanning returns empty list when no videos present."""
        videos = watcher._scan_for_new_videos()
        assert videos == []
    
    def test_scan_for_new_videos_finds_video(self, watcher, videos_root):
        """Test scanning finds video without thumbnail."""
        # Create a video file
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        videos = watcher._scan_for_new_videos()
        
        assert len(videos) == 1
        assert videos[0][0] == "test_video"
        assert videos[0][1] == video_file
    
    def test_scan_for_new_videos_skips_existing_thumbnail(self, watcher, videos_root):
        """Test scanning skips videos that already have thumbnails."""
        # Create a video file
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        # Create corresponding thumbnail
        thumb_file = videos_root / "thumbs" / "test_video.jpg"
        thumb_file.write_text("fake thumbnail")
        
        videos = watcher._scan_for_new_videos()
        
        assert videos == []
    
    def test_scan_for_new_videos_skips_non_video_files(self, watcher, videos_root):
        """Test scanning skips non-video files."""
        # Create non-video files
        (videos_root / "temp" / "readme.txt").write_text("text file")
        (videos_root / "temp" / "data.json").write_text("{}")
        
        videos = watcher._scan_for_new_videos()
        
        assert videos == []
    
    def test_scan_for_new_videos_multiple_extensions(self, watcher, videos_root):
        """Test scanning finds videos with different extensions."""
        # Create videos with different extensions
        (videos_root / "temp" / "video1.mp4").write_text("video")
        (videos_root / "temp" / "video2.avi").write_text("video")
        (videos_root / "temp" / "video3.mov").write_text("video")
        
        videos = watcher._scan_for_new_videos()
        
        assert len(videos) == 3
        video_ids = [v[0] for v in videos]
        assert "video1" in video_ids
        assert "video2" in video_ids
        assert "video3" in video_ids
    
    def test_scan_for_new_videos_skips_processed(self, watcher, videos_root):
        """Test scanning skips already processed videos."""
        # Create a video file
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        # Mark as processed
        watcher._processed_videos.add("test_video")
        
        videos = watcher._scan_for_new_videos()
        
        assert videos == []
    
    def test_generate_thumbnail_for_video_success(self, watcher, videos_root):
        """Test successful thumbnail generation for a video."""
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        with patch.object(watcher.generator, "generate_thumbnail") as mock_gen:
            result = watcher._generate_thumbnail_for_video(
                video_id="test_video",
                video_path=video_file,
            )
        
        assert result is True
        assert "test_video" in watcher._processed_videos
        mock_gen.assert_called_once()
    
    def test_generate_thumbnail_for_video_failure(self, watcher, videos_root):
        """Test thumbnail generation failure handling."""
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        with patch.object(
            watcher.generator,
            "generate_thumbnail",
            side_effect=ThumbnailGenerationError("FFmpeg failed"),
        ):
            result = watcher._generate_thumbnail_for_video(
                video_id="test_video",
                video_path=video_file,
            )
        
        assert result is False
        assert "test_video" not in watcher._processed_videos
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, watcher):
        """Test starting and stopping the watcher service."""
        assert not watcher._running
        
        await watcher.start()
        assert watcher._running
        assert watcher._task is not None
        
        await asyncio.sleep(0.05)  # Let it run briefly
        
        await watcher.stop()
        assert not watcher._running
        assert watcher._task is None
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, watcher):
        """Test starting watcher when already running does nothing."""
        await watcher.start()
        task1 = watcher._task
        
        await watcher.start()  # Try to start again
        task2 = watcher._task
        
        assert task1 is task2  # Same task
        
        await watcher.stop()
    
    @pytest.mark.asyncio
    async def test_stop_not_running(self, watcher):
        """Test stopping watcher when not running does nothing."""
        assert not watcher._running
        await watcher.stop()  # Should not raise
        assert not watcher._running
    
    @pytest.mark.asyncio
    async def test_watch_loop_processes_videos(self, watcher, videos_root):
        """Test watch loop processes new videos."""
        # Create a video file
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        with patch.object(
            watcher,
            "_generate_thumbnail_for_video",
            return_value=True,
        ) as mock_gen:
            await watcher.start()
            
            # Wait for at least one scan cycle
            await asyncio.sleep(0.2)
            
            await watcher.stop()
            
            # Verify thumbnail generation was called
            assert mock_gen.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_watch_loop_continues_on_error(self, watcher, videos_root):
        """Test watch loop continues after errors."""
        # Create a video file
        video_file = videos_root / "temp" / "test_video.mp4"
        video_file.write_text("fake video")
        
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated error")
            return True
        
        with patch.object(
            watcher,
            "_generate_thumbnail_for_video",
            side_effect=side_effect,
        ):
            await watcher.start()
            
            # Wait for multiple scan cycles
            await asyncio.sleep(0.3)
            
            await watcher.stop()
            
            # Should have recovered and tried again
            assert call_count >= 2
    
    def test_get_stats(self, watcher, videos_root):
        """Test getting service statistics."""
        watcher._processed_videos.add("video1")
        watcher._processed_videos.add("video2")
        
        stats = watcher.get_stats()
        
        assert stats["running"] is False
        assert stats["processed_count"] == 2
        assert stats["watch_splits"] == ["temp"]
        assert stats["poll_interval"] == 0.1
        assert stats["thumbs_path"] == str(videos_root / "thumbs")
    
    @pytest.mark.asyncio
    async def test_get_stats_while_running(self, watcher):
        """Test getting stats while service is running."""
        await watcher.start()
        
        stats = watcher.get_stats()
        assert stats["running"] is True
        
        await watcher.stop()
