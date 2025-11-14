"""
Luma AI Video Generation Client
Handles video generation using Luma Dream Machine API (Ray 2 model)
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LumaVideoGenerator:
    """Client for Luma AI Dream Machine video generation"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Luma client
        
        Args:
            api_key: Luma API key. If None, reads from LUMAAI_API_KEY env var
        """
        self.api_key = api_key or os.getenv("LUMAAI_API_KEY")
        if not self.api_key:
            raise ValueError("Luma API key required. Set LUMAAI_API_KEY or pass api_key parameter")
        
        self.base_url = "https://api.lumalabs.ai/dream-machine/v1"
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }
    
    def create_generation(
        self,
        prompt: str,
        model: str = "ray-2",
        resolution: str = "720p",
        duration: str = "5s",
        aspect_ratio: str = "3:4",
        loop: bool = False,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new video generation request
        
        Args:
            prompt: Text description of the video to generate
            model: Model to use (ray-2, ray-flash-2, ray-1-6)
            resolution: Video resolution (540p, 720p, 1080p, 4k)
            duration: Video duration (5s)
            aspect_ratio: Aspect ratio (16:9, 3:4, etc.)
            loop: Whether video should loop
            callback_url: Optional webhook URL for status updates
            
        Returns:
            Generation response with id and initial state
        """
        payload = {
            "prompt": prompt,
            "model": model,
            "resolution": resolution,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "loop": loop
        }
        
        if callback_url:
            payload["callback_url"] = callback_url
        
        response = requests.post(
            f"{self.base_url}/generations",
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """
        Get status of a generation
        
        Args:
            generation_id: UUID of the generation
            
        Returns:
            Generation object with current state and assets
        """
        response = requests.get(
            f"{self.base_url}/generations/{generation_id}",
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def poll_until_complete(
        self,
        generation_id: str,
        poll_interval: int = 3,
        max_attempts: int = 100
    ) -> Dict[str, Any]:
        """
        Poll generation status until completed or failed
        
        Args:
            generation_id: UUID of the generation
            poll_interval: Seconds between polls
            max_attempts: Maximum polling attempts
            
        Returns:
            Completed generation object
            
        Raises:
            RuntimeError: If generation fails or times out
        """
        for attempt in range(max_attempts):
            generation = self.get_generation(generation_id)
            state = generation.get("state")
            
            if state == "completed":
                logger.info(f"Generation {generation_id} completed")
                return generation
            elif state == "failed":
                failure_reason = generation.get("failure_reason", "Unknown")
                raise RuntimeError(f"Generation failed: {failure_reason}")
            
            logger.debug(f"Generation {generation_id} state: {state} (attempt {attempt + 1}/{max_attempts})")
            time.sleep(poll_interval)
        
        raise RuntimeError(f"Generation timed out after {max_attempts} attempts")
    
    def download_video(
        self,
        video_url: str,
        output_path: Path,
        filename: Optional[str] = None
    ) -> Path:
        """
        Download generated video to local filesystem
        
        Args:
            video_url: URL of the generated video
            output_path: Directory to save video
            filename: Optional custom filename (defaults to timestamp-based)
            
        Returns:
            Path to downloaded video file
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"luma_{timestamp}.mp4"
        
        file_path = output_path / filename
        
        logger.info(f"Downloading video from {video_url} to {file_path}")
        response = requests.get(video_url, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Video downloaded: {file_path} ({file_path.stat().st_size} bytes)")
        return file_path
    
    def generate_and_download(
        self,
        prompt: str,
        output_path: Path,
        filename: Optional[str] = None,
        **generation_kwargs
    ) -> tuple[Path, Dict[str, Any]]:
        """
        Complete workflow: generate video and download when ready
        
        Args:
            prompt: Text description of video
            output_path: Directory to save video
            filename: Optional custom filename
            **generation_kwargs: Additional arguments for create_generation
            
        Returns:
            Tuple of (downloaded_file_path, generation_metadata)
        """
        # Create generation
        logger.info(f"Creating generation with prompt: '{prompt}'")
        generation = self.create_generation(prompt, **generation_kwargs)
        generation_id = generation["id"]
        
        # Poll until complete
        logger.info(f"Polling generation {generation_id}...")
        completed = self.poll_until_complete(generation_id)
        
        # Extract video URL
        video_url = completed.get("assets", {}).get("video")
        if not video_url:
            raise RuntimeError("No video URL in completed generation")
        
        # Download
        file_path = self.download_video(video_url, output_path, filename)
        
        return file_path, completed


def send_to_n8n_ingest(
    video_file_path: Path,
    n8n_webhook_url: str,
    ingest_token: str,
    label: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send video to n8n Ingest Agent webhook
    
    Args:
        video_file_path: Path to the video file
        n8n_webhook_url: Full webhook URL (e.g., http://n8n:5678/webhook/video_gen_hook)
        ingest_token: Authentication token for x-ingest-key header
        label: Optional emotion label (happy, sad)
        correlation_id: Optional correlation ID for tracking
        
    Returns:
        Response from n8n webhook
    """
    # For local files, we need to make them accessible via URL
    # This assumes the file is in a directory that can be accessed by the media mover
    # We'll send the local file path as source_url since media mover can access it
    
    payload = {
        "source_url": str(video_file_path.absolute()),
        "meta": {
            "generator": "luma",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if label:
        payload["label"] = label
    
    headers = {
        "Content-Type": "application/json",
        "x-ingest-key": ingest_token
    }
    
    if correlation_id:
        headers["x-correlation-id"] = correlation_id
    
    logger.info(f"Sending video to n8n ingest webhook: {n8n_webhook_url}")
    response = requests.post(
        n8n_webhook_url,
        json=payload,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    
    return response.json()
