# Tutorial 4: Stratified Dataset Splitting

> **Priority**: HIGH — Prevents class imbalance in train/test sets
> **Time estimate**: 3-4 hours
> **Difficulty**: Easy-Moderate
> **Prerequisites**: scikit-learn installed (`pip install scikit-learn`)

---

## Why This Matters

The current dataset preparation code (`trainer/prepare_dataset.py`)
splits data like this:

```python
random.shuffle(videos)
split_idx = int(len(videos) * train_fraction)
train_videos = videos[:split_idx]
test_videos = videos[split_idx:]
```

**The problem**: With a small dataset and unequal class sizes, this naive
split can produce a test set with **zero samples of one class**.

Example with 20 videos (14 happy, 6 sad), 70/30 split:

| Split | Naive Random | Stratified |
|-------|-------------|------------|
| Train (14) | 12 happy, 2 sad | 10 happy, 4 sad |
| Test (6) | 2 happy, 4 sad | 4 happy, 2 sad |

With bad luck, naive random could give you 0 sad in test — making your
F1 score meaningless.

**Stratified splitting** ensures each split has the same class proportions
as the original dataset.

---

## What You'll Learn

- What stratified sampling is and why it matters
- How to use `sklearn.model_selection.train_test_split`
- How to verify class distribution after splitting

---

## Step 1: Read the Current Code

Open `trainer/prepare_dataset.py` and look at lines 75-81:

```python
# Shuffle for randomness
random.shuffle(videos)

# Split into train/test
split_idx = int(len(videos) * train_fraction)
train_videos = videos[:split_idx]
test_videos = videos[split_idx:]
```

This is the code we need to fix.

---

## Step 2: Install scikit-learn (if not already)

```bash
pip install scikit-learn
```

Verify:
```bash
python3 -c "from sklearn.model_selection import train_test_split; print('sklearn OK')"
```

---

## Step 3: Modify the Dataset Preparer

Open `trainer/prepare_dataset.py` and replace the
`prepare_training_dataset` method.

### Replace the naive split code

Find this block (lines ~64-81):

```python
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
```

Replace with:

```python
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

        if len(videos) == 0:
            logger.warning("No videos found in dataset_all")
            return {
                'run_id': run_id,
                'train_count': 0,
                'test_count': 0,
                'seed': seed,
                'dataset_hash': '',
            }

        # Extract labels for stratification
        labels = [v['label'] for v in videos]

        # Check if stratification is possible
        # (need at least 2 samples per class)
        from collections import Counter
        label_counts = Counter(labels)
        min_count = min(label_counts.values())

        if min_count < 2:
            logger.warning(
                f"Class with only {min_count} sample(s) detected. "
                f"Using random split instead of stratified. "
                f"Distribution: {dict(label_counts)}"
            )
            # Fall back to random split
            random.shuffle(videos)
            split_idx = int(len(videos) * train_fraction)
            train_videos = videos[:split_idx]
            test_videos = videos[split_idx:]
        else:
            # Stratified split preserves class proportions
            from sklearn.model_selection import train_test_split

            train_videos, test_videos = train_test_split(
                videos,
                train_size=train_fraction,
                random_state=seed,
                stratify=labels,
            )

        # Log the resulting distribution
        train_labels = Counter(v['label'] for v in train_videos)
        test_labels = Counter(v['label'] for v in test_videos)
        logger.info(f"Train distribution: {dict(train_labels)}")
        logger.info(f"Test distribution: {dict(test_labels)}")
```

### Add the import at the top of the file

Add `from collections import Counter` to the imports at the top of
`prepare_dataset.py` (around line 1-15). Note: `Counter` is also
imported inline in the code above, so having it at the top is cleaner
but not strictly required.

---

## Step 4: Write Tests

Create `tests/test_stratified_splitting.py`:

```python
"""
Tests for stratified dataset splitting.

Verifies that train/test splits preserve class proportions.
"""

import pytest
import tempfile
import os
from pathlib import Path
from collections import Counter
from trainer.prepare_dataset import DatasetPreparer


@pytest.fixture
def dataset_dir():
    """
    Create a temporary dataset with known class distribution.

    Structure:
    temp_dir/
      dataset_all/
        happy/
          vid_001.mp4, vid_002.mp4, ... (20 files)
        sad/
          vid_001.mp4, vid_002.mp4, ... (10 files)
        neutral/
          vid_003.mp4, vid_004.mp4, ... (5 files)

    We create empty .mp4 files (just for the directory structure).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create dataset_all with imbalanced classes
        for label, count in [("happy", 20), ("sad", 10), ("neutral", 5)]:
            label_dir = base / "dataset_all" / label
            label_dir.mkdir(parents=True)
            for i in range(count):
                (label_dir / f"vid_{label}_{i:03d}.mp4").touch()

        yield tmpdir


class TestStratifiedSplitting:
    """Test that splitting preserves class proportions."""

    def test_split_preserves_proportions(self, dataset_dir):
        """Train and test sets have similar class ratios."""
        preparer = DatasetPreparer(dataset_dir)
        result = preparer.prepare_training_dataset(
            run_id="test-run-001",
            train_fraction=0.7,
            seed=42,
        )

        # Verify counts
        assert result['train_count'] > 0
        assert result['test_count'] > 0
        assert result['train_count'] + result['test_count'] == 35  # 20+10+5

        # Check that both train and test have all classes
        train_dir = Path(dataset_dir) / "train"
        test_dir = Path(dataset_dir) / "test"

        train_classes = {d.name for d in train_dir.iterdir() if d.is_dir()}
        test_classes = {d.name for d in test_dir.iterdir() if d.is_dir()}

        assert train_classes == {"happy", "sad", "neutral"}
        assert test_classes == {"happy", "sad", "neutral"}

    def test_proportions_are_close(self, dataset_dir):
        """Class ratios in each split match the original distribution."""
        preparer = DatasetPreparer(dataset_dir)
        preparer.prepare_training_dataset(
            run_id="test-run-002",
            train_fraction=0.7,
            seed=42,
        )

        # Count files in each split
        train_dir = Path(dataset_dir) / "train"
        test_dir = Path(dataset_dir) / "test"

        train_counts = {}
        test_counts = {}

        for label_dir in train_dir.iterdir():
            if label_dir.is_dir():
                train_counts[label_dir.name] = len(list(label_dir.glob("*.mp4")))

        for label_dir in test_dir.iterdir():
            if label_dir.is_dir():
                test_counts[label_dir.name] = len(list(label_dir.glob("*.mp4")))

        # Original ratio: happy=57%, sad=29%, neutral=14%
        # Both splits should be close to these ratios
        train_total = sum(train_counts.values())
        test_total = sum(test_counts.values())

        for label in ["happy", "sad", "neutral"]:
            original_ratio = {"happy": 20/35, "sad": 10/35, "neutral": 5/35}[label]
            train_ratio = train_counts[label] / train_total
            test_ratio = test_counts[label] / test_total

            # Allow 15% tolerance (small dataset = some variation)
            assert abs(train_ratio - original_ratio) < 0.15, (
                f"Train ratio for {label}: {train_ratio:.2f} "
                f"(expected ~{original_ratio:.2f})"
            )
            assert abs(test_ratio - original_ratio) < 0.15, (
                f"Test ratio for {label}: {test_ratio:.2f} "
                f"(expected ~{original_ratio:.2f})"
            )

    def test_deterministic_with_seed(self, dataset_dir):
        """Same seed produces same split."""
        preparer1 = DatasetPreparer(dataset_dir)
        result1 = preparer1.prepare_training_dataset(
            run_id="test-run-003",
            train_fraction=0.7,
            seed=42,
        )

        # Get the files in train
        train_files_1 = sorted(
            str(p) for p in (Path(dataset_dir) / "train").rglob("*.mp4")
        )

        # Re-run with same seed
        preparer2 = DatasetPreparer(dataset_dir)
        result2 = preparer2.prepare_training_dataset(
            run_id="test-run-004",
            train_fraction=0.7,
            seed=42,
        )

        train_files_2 = sorted(
            str(p) for p in (Path(dataset_dir) / "train").rglob("*.mp4")
        )

        # Same files should be in train both times
        assert len(train_files_1) == len(train_files_2)

    def test_empty_dataset_handled(self):
        """Empty dataset_all doesn't crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "dataset_all").mkdir()

            preparer = DatasetPreparer(tmpdir)
            result = preparer.prepare_training_dataset(
                run_id="test-empty",
                train_fraction=0.7,
                seed=42,
            )

            assert result['train_count'] == 0
            assert result['test_count'] == 0

    def test_single_sample_class_falls_back(self):
        """Class with 1 sample uses random split (can't stratify)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # 10 happy, 1 sad (can't stratify sad)
            happy_dir = base / "dataset_all" / "happy"
            happy_dir.mkdir(parents=True)
            for i in range(10):
                (happy_dir / f"vid_{i}.mp4").touch()

            sad_dir = base / "dataset_all" / "sad"
            sad_dir.mkdir(parents=True)
            (sad_dir / "vid_0.mp4").touch()

            preparer = DatasetPreparer(tmpdir)
            result = preparer.prepare_training_dataset(
                run_id="test-fallback",
                train_fraction=0.7,
                seed=42,
            )

            # Should still work (falls back to random)
            assert result['train_count'] + result['test_count'] == 11
```

### Run the Tests

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
pytest tests/test_stratified_splitting.py -v
```

---

## Step 5: Verify Manually

Create a quick test dataset and verify the split:

```python
"""Manual verification of stratified splitting."""
import tempfile
from pathlib import Path
from collections import Counter
from trainer.prepare_dataset import DatasetPreparer

# Create temp dataset: 30 happy, 10 sad, 5 neutral
with tempfile.TemporaryDirectory() as tmpdir:
    base = Path(tmpdir)
    for label, count in [("happy", 30), ("sad", 10), ("neutral", 5)]:
        d = base / "dataset_all" / label
        d.mkdir(parents=True)
        for i in range(count):
            (d / f"vid_{i:03d}.mp4").touch()

    preparer = DatasetPreparer(tmpdir)
    result = preparer.prepare_training_dataset(
        run_id="manual-test",
        train_fraction=0.7,
        seed=42,
    )

    print(f"Total: 45 videos")
    print(f"Train: {result['train_count']}")
    print(f"Test: {result['test_count']}")

    # Check distribution
    for split in ["train", "test"]:
        split_dir = base / split
        counts = {}
        for label_dir in split_dir.iterdir():
            if label_dir.is_dir():
                counts[label_dir.name] = len(list(label_dir.glob("*.mp4")))
        print(f"\n{split} distribution: {counts}")
        total = sum(counts.values())
        for label, count in counts.items():
            print(f"  {label}: {count}/{total} = {count/total:.1%}")
```

Expected output:
```
Total: 45 videos
Train: 31
Test: 14

train distribution: {'happy': 21, 'sad': 7, 'neutral': 3}
  happy: 21/31 = 67.7%
  sad: 7/31 = 22.6%
  neutral: 3/31 = 9.7%

test distribution: {'happy': 9, 'sad': 3, 'neutral': 2}
  happy: 9/14 = 64.3%
  sad: 3/14 = 21.4%
  neutral: 2/14 = 14.3%
```

Both splits should have approximately the same class ratios as the
original (67%, 22%, 11%).

---

## Checklist

Before moving to Tutorial 5, verify:

- [ ] `scikit-learn` is installed
- [ ] `trainer/prepare_dataset.py` uses `train_test_split(stratify=labels)`
- [ ] Fallback to random split when any class has < 2 samples
- [ ] Empty dataset returns zeros (not crash)
- [ ] `tests/test_stratified_splitting.py` passes
- [ ] Manual test shows proportional class distribution

---

## What's Next

Tutorial 5 is the most important one: **executing an actual training run**
and validating that it passes Gate A. This is the definition of Phase 1
"done".
