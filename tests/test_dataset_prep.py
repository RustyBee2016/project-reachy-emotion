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

from trainer.prepare_dataset import DatasetPreparer


@pytest.fixture
def temp_dataset_dir():
    """Create temporary dataset directory structure."""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)
    
    # Create dataset_all with sample structure
    dataset_all = base_path / 'dataset_all'
    dataset_all.mkdir()
    
    # Create emotion directories with sample files
    for emotion in ['happy', 'sad']:
        emotion_dir = dataset_all / emotion
        emotion_dir.mkdir()
        
        # Create 10 dummy video files per emotion
        for i in range(10):
            video_file = emotion_dir / f'{emotion}_{i:03d}.mp4'
            video_file.write_text(f'dummy video content {i}')
    
    yield base_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestDatasetPreparer:
    """Test dataset preparation functionality."""
    
    def test_initialization(self, temp_dataset_dir):
        """Test DatasetPreparer initialization."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        assert preparer.base_path == temp_dataset_dir
        assert preparer.dataset_all_path.exists()
        assert preparer.manifests_path.exists()
        assert preparer.train_path.exists()
        assert preparer.test_path.exists()
    
    def test_prepare_training_dataset(self, temp_dataset_dir):
        """Test complete dataset preparation."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        result = preparer.prepare_training_dataset(
            run_id='test_run_001',
            train_fraction=0.7,
            seed=42
        )
        
        # Check result structure
        assert 'run_id' in result
        assert 'train_count' in result
        assert 'test_count' in result
        assert 'seed' in result
        assert 'dataset_hash' in result
        
        # Check counts (20 total videos, 70/30 split)
        assert result['train_count'] == 14
        assert result['test_count'] == 6
        assert result['seed'] == 42
    
    def test_train_test_split_ratio(self, temp_dataset_dir):
        """Test train/test split maintains correct ratio."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        # Test different fractions
        for fraction in [0.6, 0.7, 0.8]:
            result = preparer.prepare_training_dataset(
                run_id=f'test_run_{fraction}',
                train_fraction=fraction,
                seed=42
            )
            
            total = result['train_count'] + result['test_count']
            actual_fraction = result['train_count'] / total
            
            # Allow small variance due to rounding
            assert abs(actual_fraction - fraction) < 0.1
    
    def test_reproducibility_with_seed(self, temp_dataset_dir):
        """Test same seed produces same split."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        # Run twice with same seed
        result1 = preparer.prepare_training_dataset(
            run_id='test_run_1',
            train_fraction=0.7,
            seed=42
        )
        
        # Clear splits
        shutil.rmtree(preparer.train_path)
        shutil.rmtree(preparer.test_path)
        preparer.train_path.mkdir()
        preparer.test_path.mkdir()
        
        result2 = preparer.prepare_training_dataset(
            run_id='test_run_2',
            train_fraction=0.7,
            seed=42
        )
        
        # Should have same counts
        assert result1['train_count'] == result2['train_count']
        assert result1['test_count'] == result2['test_count']
    
    def test_different_seeds_produce_different_splits(self, temp_dataset_dir):
        """Test different seeds produce different splits."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        result1 = preparer.prepare_training_dataset(
            run_id='test_run_1',
            train_fraction=0.7,
            seed=42
        )
        
        # Clear splits
        shutil.rmtree(preparer.train_path)
        shutil.rmtree(preparer.test_path)
        preparer.train_path.mkdir()
        preparer.test_path.mkdir()
        
        result2 = preparer.prepare_training_dataset(
            run_id='test_run_2',
            train_fraction=0.7,
            seed=99
        )
        
        # Counts should be same but actual files different
        assert result1['train_count'] == result2['train_count']
        assert result1['test_count'] == result2['test_count']
    
    def test_manifest_generation(self, temp_dataset_dir):
        """Test JSONL manifest files are generated correctly."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        run_id = 'test_run_manifest'
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
        
        assert len(train_lines) == 14  # 70% of 20
        
        # Check each line is valid JSON
        for line in train_lines:
            entry = json.loads(line)
            assert 'video_id' in entry
            assert 'path' in entry
            assert 'label' in entry
            assert entry['label'] in ['happy', 'sad']
    
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
        
        # Add a new video
        new_video = preparer.dataset_all_path / 'happy' / 'happy_new.mp4'
        new_video.write_text('new video content')
        
        hash2 = preparer.calculate_dataset_hash()
        
        # Hash should be different
        assert hash1 != hash2
    
    def test_files_copied_to_train_test_dirs(self, temp_dataset_dir):
        """Test videos are copied to train/test directories."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        preparer.prepare_training_dataset(
            run_id='test_run_copy',
            train_fraction=0.7,
            seed=42
        )
        
        # Check train directory has files
        train_files = list(preparer.train_path.rglob('*.mp4'))
        assert len(train_files) == 14
        
        # Check test directory has files
        test_files = list(preparer.test_path.rglob('*.mp4'))
        assert len(test_files) == 6
        
        # Check label subdirectories exist
        assert (preparer.train_path / 'happy').exists()
        assert (preparer.train_path / 'sad').exists()
        assert (preparer.test_path / 'happy').exists()
        assert (preparer.test_path / 'sad').exists()
    
    def test_empty_dataset_handling(self):
        """Test handling of empty dataset."""
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        # Create empty dataset_all
        dataset_all = base_path / 'dataset_all'
        dataset_all.mkdir()
        
        preparer = DatasetPreparer(str(base_path))
        
        result = preparer.prepare_training_dataset(
            run_id='test_empty',
            train_fraction=0.7,
            seed=42
        )
        
        # Should handle gracefully
        assert result['train_count'] == 0
        assert result['test_count'] == 0
        
        shutil.rmtree(temp_dir)
    
    def test_single_class_dataset(self):
        """Test dataset with only one emotion class."""
        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)
        
        # Create dataset with only happy
        dataset_all = base_path / 'dataset_all'
        dataset_all.mkdir()
        
        happy_dir = dataset_all / 'happy'
        happy_dir.mkdir()
        
        for i in range(10):
            video_file = happy_dir / f'happy_{i:03d}.mp4'
            video_file.write_text(f'video {i}')
        
        preparer = DatasetPreparer(str(base_path))
        
        result = preparer.prepare_training_dataset(
            run_id='test_single_class',
            train_fraction=0.7,
            seed=42
        )
        
        # Should still work
        assert result['train_count'] + result['test_count'] == 10
        
        shutil.rmtree(temp_dir)


class TestManifestFormat:
    """Test manifest file format and structure."""
    
    def test_manifest_jsonl_format(self, temp_dataset_dir):
        """Test manifests are valid JSONL."""
        preparer = DatasetPreparer(str(temp_dataset_dir))
        
        run_id = 'test_jsonl'
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
        
        run_id = 'test_fields'
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
