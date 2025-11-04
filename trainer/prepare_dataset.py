"""
Dataset preparation module for training pipeline.
Handles balanced sampling, manifest generation, and dataset hashing.
"""

import os
import json
import hashlib
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class DatasetPreparer:
    """Prepare datasets for TAO training with balanced sampling."""
    
    def __init__(self, base_path: str):
        """
        Initialize dataset preparer.
        
        Args:
            base_path: Root directory containing dataset_all
        """
        self.base_path = Path(base_path)
        self.dataset_all_path = self.base_path / 'dataset_all'
        self.manifests_path = self.base_path / 'manifests'
        self.train_path = self.base_path / 'train'
        self.test_path = self.base_path / 'test'
        
        # Create directories
        self.manifests_path.mkdir(exist_ok=True)
        self.train_path.mkdir(exist_ok=True)
        self.test_path.mkdir(exist_ok=True)
    
    def prepare_training_dataset(
        self,
        run_id: str,
        train_fraction: float = 0.7,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare train/test splits for a training run.
        
        Args:
            run_id: Unique identifier for this training run
            train_fraction: Fraction of data for training (rest is test)
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary with run metadata
        """
        if seed is None:
            seed = int(hashlib.md5(run_id.encode()).hexdigest(), 16) % (2**31)
        
        random.seed(seed)
        
        # Collect all videos from dataset_all
        videos = []
        for emotion_dir in self.dataset_all_path.iterdir():
            if emotion_dir.is_dir():
                emotion_label = emotion_dir.name
                for video_file in emotion_dir.glob('*.mp4'):
                    videos.append({
                        'path': str(video_file),
                        'label': emotion_label,
                        'video_id': str(uuid.uuid4())
                    })
        
        # Shuffle for randomness
        random.shuffle(videos)
        
        # Split into train/test
        split_idx = int(len(videos) * train_fraction)
        train_videos = videos[:split_idx]
        test_videos = videos[split_idx:]
        
        # Copy files to train/test directories (for TAO)
        self._copy_videos_to_splits(train_videos, test_videos)
        
        # Generate manifests
        self._generate_manifests(run_id, train_videos, test_videos)
        
        # Calculate dataset hash
        dataset_hash = self.calculate_dataset_hash()
        
        return {
            'run_id': run_id,
            'train_count': len(train_videos),
            'test_count': len(test_videos),
            'seed': seed,
            'dataset_hash': dataset_hash
        }
    
    def _copy_videos_to_splits(
        self,
        train_videos: List[Dict],
        test_videos: List[Dict]
    ):
        """Copy videos to train/test directories maintaining structure."""
        # Clear existing splits
        for path in [self.train_path, self.test_path]:
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(exist_ok=True)
        
        # Copy training videos
        for video in train_videos:
            src = Path(video['path'])
            label = video['label']
            
            # Create label directory
            dst_dir = self.train_path / label
            dst_dir.mkdir(exist_ok=True)
            
            # Copy file
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
        
        # Copy test videos
        for video in test_videos:
            src = Path(video['path'])
            label = video['label']
            
            # Create label directory
            dst_dir = self.test_path / label
            dst_dir.mkdir(exist_ok=True)
            
            # Copy file
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
    
    def _generate_manifests(
        self,
        run_id: str,
        train_videos: List[Dict],
        test_videos: List[Dict]
    ):
        """Generate JSONL manifest files for training."""
        # Train manifest
        train_manifest_path = self.manifests_path / f'{run_id}_train.jsonl'
        with open(train_manifest_path, 'w') as f:
            for video in train_videos:
                entry = {
                    'video_id': video['video_id'],
                    'path': video['path'],
                    'label': video['label']
                }
                f.write(json.dumps(entry) + '\n')
        
        # Test manifest
        test_manifest_path = self.manifests_path / f'{run_id}_test.jsonl'
        with open(test_manifest_path, 'w') as f:
            for video in test_videos:
                entry = {
                    'video_id': video['video_id'],
                    'path': video['path'],
                    'label': video['label']
                }
                f.write(json.dumps(entry) + '\n')
    
    def calculate_dataset_hash(self) -> str:
        """
        Calculate SHA256 hash of dataset for reproducibility.
        
        Returns:
            Hex string of dataset hash
        """
        hasher = hashlib.sha256()
        
        # Sort files for deterministic ordering
        all_files = sorted(self.dataset_all_path.rglob('*.mp4'))
        
        for file_path in all_files:
            # Include relative path and file size
            rel_path = file_path.relative_to(self.dataset_all_path)
            hasher.update(str(rel_path).encode())
            hasher.update(str(file_path.stat().st_size).encode())
        
        return hasher.hexdigest()
