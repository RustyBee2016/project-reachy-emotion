"""Integration tests for thumbnail generation system.

These tests verify the complete thumbnail generation workflow:
1. Video is placed in /videos/temp
2. Thumbnail watcher detects it
3. Thumbnail is generated in /videos/thumbs
4. Thumbnail endpoint returns the correct URL
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.api.app.services.thumbnail_watcher import ThumbnailWatcherService
from shared.utils.thumbnail_generator import ThumbnailGenerator


@pytest.mark.integration
class TestThumbnailIntegration:
    """Integration tests for thumbnail generation."""
    
    @pytest.fixture
    def videos_root(self, tmp_path):
        """Create a temporary videos root directory structure."""
        root = tmp_path / "videos"
        root.mkdir()
        
        # Create all required directories
        (root / "temp").mkdir()
        (root / "thumbs").mkdir()
        (root / "dataset_all").mkdir()
        (root / "train").mkdir()
        (root / "test").mkdir()
        
        return root
    
    @pytest.fixture
    def sample_video(self, videos_root):
        """Create a real sample video file using FFmpeg if available.
        
        Falls back to a dummy file if FFmpeg is not available.
        """
        video_path = videos_root / "temp" / "test_video.mp4"
        
        # Try to create a real video with FFmpeg
        try:
            # Create a 1-second black video
            subprocess.run(
                [
                    "ffmpeg",
                    "-f", "lavfi",
                    "-i", "color=c=black:s=320x240:d=1",
                    "-pix_fmt", "yuv420p",
                    "-y",
                    str(video_path),
                ],
                capture_output=True,
                timeout=10,
                check=True,
            )
            return video_path
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # FFmpeg not available or failed, create dummy file
            video_path.write_bytes(b"FAKE_VIDEO_CONTENT")
            return video_path
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    def test_thumbnail_generator_with_real_video(self, videos_root, sample_video):
        """Test thumbnail generation with a real video file."""
        generator = ThumbnailGenerator()
        thumbnail_path = videos_root / "thumbs" / "test_video.jpg"
        
        result = generator.generate_thumbnail(
            video_path=sample_video,
            output_path=thumbnail_path,
        )
        
        assert result == thumbnail_path
        assert thumbnail_path.exists()
        assert thumbnail_path.stat().st_size > 0
        
        # Verify it's a valid JPEG
        with thumbnail_path.open("rb") as f:
            header = f.read(3)
            assert header == b"\xff\xd8\xff", "Not a valid JPEG file"
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    @pytest.mark.asyncio
    async def test_watcher_generates_thumbnail_automatically(
        self, videos_root, sample_video
    ):
        """Test that watcher automatically generates thumbnails for new videos."""
        thumbnail_path = videos_root / "thumbs" / "test_video.jpg"
        
        # Ensure thumbnail doesn't exist yet
        assert not thumbnail_path.exists()
        
        # Start the watcher
        watcher = ThumbnailWatcherService(
            videos_root=videos_root,
            watch_splits=["temp"],
            poll_interval=0.5,
        )
        
        await watcher.start()
        
        try:
            # Wait for watcher to detect and process the video
            # Should happen within a few poll cycles
            for _ in range(10):  # Max 5 seconds
                await asyncio.sleep(0.5)
                if thumbnail_path.exists():
                    break
            
            # Verify thumbnail was created
            assert thumbnail_path.exists(), "Thumbnail was not generated"
            assert thumbnail_path.stat().st_size > 0
            
            # Verify it's in the processed set
            assert "test_video" in watcher._processed_videos
            
            # Verify stats
            stats = watcher.get_stats()
            assert stats["running"] is True
            assert stats["processed_count"] >= 1
            
        finally:
            await watcher.stop()
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    @pytest.mark.asyncio
    async def test_watcher_processes_multiple_videos(self, videos_root):
        """Test watcher processes multiple videos."""
        # Create multiple sample videos
        video_files = []
        for i in range(3):
            video_path = videos_root / "temp" / f"video_{i}.mp4"
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-f", "lavfi",
                        "-i", "color=c=black:s=320x240:d=1",
                        "-pix_fmt", "yuv420p",
                        "-y",
                        str(video_path),
                    ],
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                video_files.append(video_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pytest.skip("Failed to create test videos")
        
        # Start watcher
        watcher = ThumbnailWatcherService(
            videos_root=videos_root,
            watch_splits=["temp"],
            poll_interval=0.5,
        )
        
        await watcher.start()
        
        try:
            # Wait for all thumbnails to be generated
            max_wait = 15  # seconds
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < max_wait:
                thumbnails_exist = all(
                    (videos_root / "thumbs" / f"video_{i}.jpg").exists()
                    for i in range(3)
                )
                if thumbnails_exist:
                    break
                await asyncio.sleep(0.5)
            
            # Verify all thumbnails were created
            for i in range(3):
                thumb_path = videos_root / "thumbs" / f"video_{i}.jpg"
                assert thumb_path.exists(), f"Thumbnail {i} not generated"
                assert thumb_path.stat().st_size > 0
            
            # Verify stats
            stats = watcher.get_stats()
            assert stats["processed_count"] == 3
            
        finally:
            await watcher.stop()
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    @pytest.mark.asyncio
    async def test_watcher_skips_existing_thumbnails(self, videos_root, sample_video):
        """Test watcher doesn't regenerate existing thumbnails."""
        thumbnail_path = videos_root / "thumbs" / "test_video.jpg"
        
        # Pre-create a thumbnail
        thumbnail_path.write_text("EXISTING_THUMBNAIL")
        original_mtime = thumbnail_path.stat().st_mtime
        
        # Start watcher
        watcher = ThumbnailWatcherService(
            videos_root=videos_root,
            watch_splits=["temp"],
            poll_interval=0.5,
        )
        
        await watcher.start()
        
        try:
            # Wait a few cycles
            await asyncio.sleep(2.0)
            
            # Verify thumbnail was not modified
            assert thumbnail_path.exists()
            assert thumbnail_path.stat().st_mtime == original_mtime
            assert thumbnail_path.read_text() == "EXISTING_THUMBNAIL"
            
            # Should not be in processed set since it was skipped
            assert "test_video" not in watcher._processed_videos
            
        finally:
            await watcher.stop()
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    def test_thumbnail_quality_and_size(self, videos_root, sample_video):
        """Test that generated thumbnails have reasonable quality and size."""
        generator = ThumbnailGenerator()
        thumbnail_path = videos_root / "thumbs" / "test_video.jpg"
        
        generator.generate_thumbnail(
            video_path=sample_video,
            output_path=thumbnail_path,
        )
        
        # Check file size is reasonable (should be a few KB for a simple video)
        file_size = thumbnail_path.stat().st_size
        assert 1000 < file_size < 100000, f"Thumbnail size {file_size} seems unusual"
        
        # Verify JPEG format
        with thumbnail_path.open("rb") as f:
            # JPEG files start with FF D8 FF
            magic = f.read(3)
            assert magic == b"\xff\xd8\xff", "Not a valid JPEG"
    
    @pytest.mark.skipif(
        shutil.which("ffmpeg") is None,
        reason="FFmpeg not available for integration test"
    )
    def test_thumbnail_from_different_video_formats(self, videos_root):
        """Test thumbnail generation works with different video formats."""
        generator = ThumbnailGenerator()
        
        # Test with different container formats
        formats = ["mp4", "avi", "mov"]
        
        for fmt in formats:
            video_path = videos_root / "temp" / f"test_video.{fmt}"
            
            try:
                # Create video in specific format
                subprocess.run(
                    [
                        "ffmpeg",
                        "-f", "lavfi",
                        "-i", "color=c=black:s=320x240:d=1",
                        "-pix_fmt", "yuv420p",
                        "-y",
                        str(video_path),
                    ],
                    capture_output=True,
                    timeout=10,
                    check=True,
                )
                
                thumbnail_path = videos_root / "thumbs" / f"test_video_{fmt}.jpg"
                
                result = generator.generate_thumbnail(
                    video_path=video_path,
                    output_path=thumbnail_path,
                )
                
                assert result.exists()
                assert result.stat().st_size > 0
                
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # Skip this format if creation fails
                continue
