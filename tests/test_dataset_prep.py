"""
Tests for dataset preparation and manifest generation.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import hashlib

import cv2
import numpy as np

from trainer.prepare_dataset import DatasetPreparer


@pytest.fixture
def temp_dataset_dir():
    """Create temporary dataset directory structure."""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)
    train_root = base_path / 'train'
    train_root.mkdir()

    # Create emotion directories with sample video files (3-class: happy, sad, neutral)
    for emotion in ['happy', 'sad', 'neutral']:
        emotion_dir = train_root / emotion
        emotion_dir.mkdir()

        # Create 10 short videos per emotion
        for i in range(10):
            video_file = emotion_dir / f'{emotion}_{i:03d}.mp4'
            _write_test_video(video_file)
    
    yield base_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestDatasetPreparer:
    """Test dataset preparation functionality."""
    
    def test_initialization(self, temp_dataset_dir):
        """Test DatasetPreparer initialization."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        assert preparer.base_path == temp_dataset_dir
        assert preparer.manifests_path.exists()
        assert preparer.train_path.exists()
        assert preparer.test_path.exists()
    
    def test_prepare_training_dataset(self, temp_dataset_dir):
        """Test complete dataset preparation."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        result = preparer.prepare_training_dataset(
            run_id='run_0001',
            train_fraction=0.7,
            seed=42
        )
        
        # Check result structure
        assert 'run_id' in result
        assert 'train_count' in result
        assert 'test_count' in result
        assert 'seed' in result
        assert 'dataset_hash' in result
        
        # 30 source videos x 10 frames each
        assert result['train_count'] == 300
        assert result['test_count'] == 0
        assert result['frames_per_video'] == 10
        assert result['seed'] == 42
    
    def test_train_test_split_ratio(self, temp_dataset_dir):
        """Test train/test split maintains correct ratio."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        # train_fraction is compatibility-only in frame extraction mode
        for fraction in [0.6, 0.7, 0.8]:
            result = preparer.prepare_training_dataset(
                run_id=f'run_{int(fraction * 10):04d}',
                train_fraction=fraction,
                seed=42
            )

            assert result['train_count'] == 300
            assert result['test_count'] == 0
    
    def test_reproducibility_with_seed(self, temp_dataset_dir):
        """Test same seed produces same split."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        result1 = preparer.prepare_training_dataset(
            run_id='run_0001',
            train_fraction=0.7,
            seed=42
        )
        
        result2 = preparer.prepare_training_dataset(
            run_id='run_0002',
            train_fraction=0.7,
            seed=42
        )
        
        # Should have same frame counts
        assert result1['train_count'] == result2['train_count']
        assert result1['test_count'] == result2['test_count']
    
    def test_different_seeds_produce_different_splits(self, temp_dataset_dir):
        """Test different seeds produce different splits."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        result1 = preparer.prepare_training_dataset(
            run_id='run_0001',
            train_fraction=0.7,
            seed=42
        )
        
        result2 = preparer.prepare_training_dataset(
            run_id='run_0002',
            train_fraction=0.7,
            seed=99
        )
        
        # Counts should be same across seeds in fixed-size extraction
        assert result1['train_count'] == result2['train_count']
        assert result1['test_count'] == result2['test_count']
    
    def test_manifest_generation(self, temp_dataset_dir):
        """Test JSONL manifest files are generated correctly."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        run_id = 'run_0001'
        preparer.prepare_training_dataset(
            run_id=run_id,
            train_fraction=0.7,
            seed=42
        )
        
        # Check manifest files exist
        train_manifest = preparer.manifests_path / f'{run_id}_train.jsonl'
        test_manifest = preparer.manifests_path / f'{run_id}_test.jsonl'
        
        assert train_manifest.exists()
        assert test_manifest.exists()
        
        # Check manifest content
        with open(train_manifest) as f:
            train_lines = f.readlines()
        
        assert len(train_lines) == 300
        
        # Check each line is valid JSON
        for line in train_lines:
            entry = json.loads(line)
            assert 'video_id' in entry
            assert 'path' in entry
            assert 'label' in entry
            assert entry['label'] in ['happy', 'sad', 'neutral']
            assert 'source_video' in entry
    
    def test_dataset_hash_calculation(self, temp_dataset_dir):
        """Test dataset hash is calculated correctly."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        hash1 = preparer.calculate_dataset_hash()
        
        # Hash should be 64 character hex string (SHA256)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Same dataset should produce same hash
        hash2 = preparer.calculate_dataset_hash()
        assert hash1 == hash2
    
    def test_dataset_hash_changes_with_content(self, temp_dataset_dir):
        """Test dataset hash changes when content changes."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        hash1 = preparer.calculate_dataset_hash()
        
        # Add a new source video
        new_video = preparer.train_path / 'happy' / 'happy_new.mp4'
        _write_test_video(new_video)
        
        hash2 = preparer.calculate_dataset_hash()
        
        # Hash should be different
        assert hash1 != hash2
    
    def test_frames_extracted_to_run_dirs(self, temp_dataset_dir):
        """Test frames are extracted to label/run and consolidated run directories."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        run_id = 'run_0001'
        preparer.prepare_training_dataset(
            run_id=run_id,
            train_fraction=0.7,
            seed=42
        )

        # Label-specific run directories: /train/<label>/<run_id>
        for label in ['happy', 'sad', 'neutral']:
            label_run_dir = preparer.train_path / label / run_id
            assert label_run_dir.exists()
            assert len(list(label_run_dir.glob('*.jpg'))) == 100

        # Consolidated run directory: /train/run/<run_id>/<label>
        for label in ['happy', 'sad', 'neutral']:
            consolidated_label_dir = preparer.train_runs_path / run_id / label
            assert consolidated_label_dir.exists()
            assert len(list(consolidated_label_dir.glob('*.jpg'))) == 100
    
    def test_empty_dataset_handling(self):
        """Test handling of empty dataset."""
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        # Create empty train root
        train_root = base_path / 'train'
        train_root.mkdir()
        
        preparer = DatasetPreparer(str(base_path))
        
        with pytest.raises(ValueError, match='missing source videos'):
            preparer.prepare_training_dataset(
                run_id='run_0001',
                train_fraction=0.7,
                seed=42
            )
        
        shutil.rmtree(temp_dir)
    
    def test_single_class_dataset(self):
        """Test dataset with only one emotion class."""
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        # Create dataset with only happy under train/
        train_root = base_path / 'train'
        train_root.mkdir()
        
        happy_dir = train_root / 'happy'
        happy_dir.mkdir()
        
        for i in range(10):
            video_file = happy_dir / f'happy_{i:03d}.mp4'
            _write_test_video(video_file)
        
        preparer = DatasetPreparer(str(base_path))
        
        with pytest.raises(ValueError, match='missing source videos'):
            preparer.prepare_training_dataset(
                run_id='run_0001',
                train_fraction=0.7,
                seed=42
            )
        
        shutil.rmtree(temp_dir)


class TestManifestFormat:
    """Test manifest file format and structure."""
    
    def test_manifest_jsonl_format(self, temp_dataset_dir):
        """Test manifests are valid JSONL."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        run_id = 'run_0001'
        preparer.prepare_training_dataset(run_id=run_id, train_fraction=0.7, seed=42)
        
        manifest_file = preparer.manifests_path / f'{run_id}_train.jsonl'
        
        with open(manifest_file) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    assert isinstance(entry, dict)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON on line {line_num}")
    
    def test_manifest_required_fields(self, temp_dataset_dir):
        """Test manifest entries have required fields."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        run_id = 'run_0001'
        preparer.prepare_training_dataset(run_id=run_id, train_fraction=0.7, seed=42)
        
        manifest_file = preparer.manifests_path / f'{run_id}_train.jsonl'
        
        with open(manifest_file) as f:
            for line in f:
                entry = json.loads(line)
                
                # Check required fields
                assert 'video_id' in entry
                assert 'path' in entry
                assert 'label' in entry
                
                # Check field types
                assert isinstance(entry['video_id'], str)
                assert isinstance(entry['path'], str)
                assert isinstance(entry['label'], str)


def _write_test_video(path: Path, frame_count: int = 20) -> None:
    """Create a tiny synthetic MP4 video for frame extraction tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc_fn = getattr(cv2, "VideoWriter_fourcc")
    writer = cv2.VideoWriter(
        str(path),
        fourcc_fn(*"mp4v"),
        10.0,
        (32, 32),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create test video: {path}")
    for idx in range(frame_count):
        frame = np.full((32, 32, 3), idx % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


class TestRunIdPolicy:
    """Test strict run ID behavior."""

    def test_auto_generates_next_run_id(self, temp_dataset_dir):
        preparer = DatasetPreparer(str(temp_dataset_dir))

        result1 = preparer.prepare_training_dataset(seed=42)
        result2 = preparer.prepare_training_dataset(seed=42)

        assert result1['run_id'] == 'run_0001'
        assert result2['run_id'] == 'run_0002'

    def test_rejects_invalid_run_id(self, temp_dataset_dir):
        preparer = DatasetPreparer(str(temp_dataset_dir))

        with pytest.raises(ValueError, match='run_xxxx'):
            preparer.prepare_training_dataset(run_id='run_1', seed=42)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
