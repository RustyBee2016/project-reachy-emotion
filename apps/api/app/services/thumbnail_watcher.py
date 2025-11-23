"""Background service to watch for new videos and generate thumbnails.

This service monitors the videos/temp directory for new video files and
automatically generates thumbnails for them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Set

from shared.utils.thumbnail_generator import ThumbnailGenerator, ThumbnailGenerationError

logger = logging.getLogger(__name__)


class ThumbnailWatcherService:
    """Background service that watches for new videos and generates thumbnails."""
    
    def __init__(
        self,
        videos_root: Path,
        watch_splits: list[str] | None = None,
        poll_interval: float = 5.0,
        ffmpeg_path: str = "ffmpeg",
    ) -> None:
        """Initialize the thumbnail watcher service.
        
        Args:
            videos_root: Root directory containing video splits
            watch_splits: List of splits to watch (default: ["temp"])
            poll_interval: Seconds between directory scans (default: 5.0)
            ffmpeg_path: Path to ffmpeg binary
        """
        self.videos_root = Path(videos_root)
        self.watch_splits = watch_splits or ["temp"]
        self.poll_interval = poll_interval
        self.generator = ThumbnailGenerator(ffmpeg_path=ffmpeg_path)
        self.thumbs_path = self.videos_root / "thumbs"
        
        # Track processed videos to avoid regeneration
        self._processed_videos: Set[str] = set()
        self._running = False
        self._task: asyncio.Task | None = None
        
        # Ensure thumbs directory exists
        self.thumbs_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"ThumbnailWatcher initialized: watching {self.watch_splits}, "
            f"poll_interval={poll_interval}s"
        )
    
    def _scan_for_new_videos(self) -> list[tuple[str, Path]]:
        """Scan watch directories for videos without thumbnails.
        
        Returns:
            List of (video_id, video_path) tuples for videos needing thumbnails
        """
        videos_needing_thumbs = []
        
        for split in self.watch_splits:
            split_path = self.videos_root / split
            if not split_path.exists():
                logger.debug(f"Split directory does not exist: {split_path}")
                continue
            
            try:
                for video_file in split_path.iterdir():
                    if not video_file.is_file():
                        continue
                    
                    # Check if it's a video file
                    if video_file.suffix.lower() not in [
                        ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"
                    ]:
                        continue
                    
                    video_id = video_file.stem
                    thumbnail_path = self.thumbs_path / f"{video_id}.jpg"
                    
                    # Skip if thumbnail exists or already processed
                    if thumbnail_path.exists():
                        continue
                    
                    if video_id in self._processed_videos:
                        continue
                    
                    videos_needing_thumbs.append((video_id, video_file))
                    
            except Exception as exc:
                logger.error(f"Error scanning {split_path}: {exc}", exc_info=True)
                continue
        
        return videos_needing_thumbs
    
    def _generate_thumbnail_for_video(
        self,
        video_id: str,
        video_path: Path,
    ) -> bool:
        """Generate thumbnail for a single video.
        
        Args:
            video_id: Video identifier
            video_path: Path to video file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            thumbnail_path = self.thumbs_path / f"{video_id}.jpg"
            self.generator.generate_thumbnail(
                video_path=video_path,
                output_path=thumbnail_path,
                overwrite=False,
            )
            self._processed_videos.add(video_id)
            logger.info(f"Generated thumbnail for: {video_id}")
            return True
            
        except ThumbnailGenerationError as exc:
            logger.error(f"Failed to generate thumbnail for {video_id}: {exc}")
            # Don't add to processed set so we can retry later
            return False
        except Exception as exc:
            logger.error(
                f"Unexpected error generating thumbnail for {video_id}: {exc}",
                exc_info=True,
            )
            return False
    
    async def _watch_loop(self) -> None:
        """Main watch loop that runs continuously."""
        logger.info("Thumbnail watcher started")
        
        while self._running:
            try:
                # Scan for new videos
                videos_to_process = self._scan_for_new_videos()
                
                if videos_to_process:
                    logger.info(
                        f"Found {len(videos_to_process)} videos needing thumbnails"
                    )
                    
                    # Process each video
                    for video_id, video_path in videos_to_process:
                        if not self._running:
                            break
                        
                        # Run thumbnail generation in executor to avoid blocking
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            self._generate_thumbnail_for_video,
                            video_id,
                            video_path,
                        )
                
                # Wait before next scan
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                logger.info("Thumbnail watcher cancelled")
                break
            except Exception as exc:
                logger.error(f"Error in watch loop: {exc}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
        
        logger.info("Thumbnail watcher stopped")
    
    async def start(self) -> None:
        """Start the thumbnail watcher service."""
        if self._running:
            logger.warning("Thumbnail watcher already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("Thumbnail watcher service started")
    
    async def stop(self) -> None:
        """Stop the thumbnail watcher service."""
        if not self._running:
            return
        
        logger.info("Stopping thumbnail watcher service...")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Thumbnail watcher service stopped")
    
    def get_stats(self) -> dict:
        """Get service statistics.
        
        Returns:
            Dictionary with service stats
        """
        return {
            "running": self._running,
            "processed_count": len(self._processed_videos),
            "watch_splits": self.watch_splits,
            "poll_interval": self.poll_interval,
            "thumbs_path": str(self.thumbs_path),
        }
