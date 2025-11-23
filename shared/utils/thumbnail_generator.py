"""Thumbnail generation utility using FFmpeg.

This module provides functionality to extract thumbnail images from video files
using FFmpeg. Thumbnails are extracted from the first second of the video.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ThumbnailGenerationError(Exception):
    """Raised when thumbnail generation fails."""
    pass


class ThumbnailGenerator:
    """Generate thumbnail images from video files using FFmpeg."""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        """Initialize the thumbnail generator.
        
        Args:
            ffmpeg_path: Path to the ffmpeg binary (default: "ffmpeg" from PATH)
        """
        self.ffmpeg_path = ffmpeg_path
        self._validate_ffmpeg()
    
    def _validate_ffmpeg(self) -> None:
        """Verify that FFmpeg is available."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0:
                raise ThumbnailGenerationError(
                    f"FFmpeg validation failed: {result.stderr}"
                )
            logger.debug(f"FFmpeg validated: {self.ffmpeg_path}")
        except FileNotFoundError as exc:
            raise ThumbnailGenerationError(
                f"FFmpeg not found at: {self.ffmpeg_path}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ThumbnailGenerationError(
                "FFmpeg validation timed out"
            ) from exc
    
    def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: str = "00:00:01",
        overwrite: bool = False,
    ) -> Path:
        """Generate a thumbnail from a video file.
        
        Args:
            video_path: Path to the source video file
            output_path: Path where the thumbnail should be saved
            timestamp: Timestamp to extract frame from (default: 1 second)
            overwrite: Whether to overwrite existing thumbnail (default: False)
            
        Returns:
            Path to the generated thumbnail
            
        Raises:
            ThumbnailGenerationError: If generation fails
            FileNotFoundError: If video file doesn't exist
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path.exists() and not overwrite:
            logger.info(f"Thumbnail already exists: {output_path}")
            return output_path
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        # -ss: seek to timestamp
        # -i: input file
        # -vframes 1: extract one frame
        # -q:v 2: quality (2 is high quality for JPEG)
        # -y: overwrite output file
        cmd = [
            self.ffmpeg_path,
            "-ss", timestamp,
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
        ]
        
        if overwrite:
            cmd.append("-y")
        
        cmd.append(str(output_path))
        
        try:
            logger.info(
                f"Generating thumbnail for {video_path.name} -> {output_path.name}"
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            
            if result.returncode != 0:
                raise ThumbnailGenerationError(
                    f"FFmpeg failed with return code {result.returncode}: {result.stderr}"
                )
            
            if not output_path.exists():
                raise ThumbnailGenerationError(
                    f"Thumbnail was not created at: {output_path}"
                )
            
            logger.info(f"Thumbnail generated successfully: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired as exc:
            raise ThumbnailGenerationError(
                f"Thumbnail generation timed out for: {video_path}"
            ) from exc
        except Exception as exc:
            raise ThumbnailGenerationError(
                f"Unexpected error generating thumbnail: {exc}"
            ) from exc
    
    def generate_thumbnail_for_video_id(
        self,
        video_id: str,
        videos_root: Path,
        split: str = "temp",
        overwrite: bool = False,
    ) -> Optional[Path]:
        """Generate thumbnail for a video by ID.
        
        Searches for the video file in the specified split and generates
        a thumbnail in the thumbs directory.
        
        Args:
            video_id: Video identifier (filename without extension)
            videos_root: Root directory containing video splits
            split: Split directory to search (default: "temp")
            overwrite: Whether to overwrite existing thumbnail
            
        Returns:
            Path to generated thumbnail, or None if video not found
            
        Raises:
            ThumbnailGenerationError: If generation fails
        """
        split_path = videos_root / split
        thumbs_path = videos_root / "thumbs"
        
        # Find video file with any extension
        video_file = None
        for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
            candidate = split_path / f"{video_id}{ext}"
            if candidate.exists():
                video_file = candidate
                break
        
        if not video_file:
            logger.warning(f"Video not found for ID: {video_id} in {split}")
            return None
        
        # Generate thumbnail
        thumbnail_path = thumbs_path / f"{video_id}.jpg"
        return self.generate_thumbnail(
            video_path=video_file,
            output_path=thumbnail_path,
            overwrite=overwrite,
        )
