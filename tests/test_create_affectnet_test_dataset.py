"""Tests for AffectNet+ test dataset creation pipeline."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import pytest

from trainer.create_affectnet_test_dataset import (
    AFFECTNET_EMOTION_CODES,
    TARGET_CLASSES,
    copy_test_image,
    create_test_dataset,
    filter_annotations,
    load_affectnet_annotations,
    sample_balanced,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_test_image(path: Path, size: int = 224) -> None:
    """Create a synthetic test image (solid color with noise)."""
    img = np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
    cv2.imwrite(str(path), img)


def _make_annotation(
    image_stem: str,
    human_label: int,
    soft_label: List[float],
    subset: int = 0,
    valence: float = 0.5,
    arousal: float = 0.3,
) -> Dict[str, Any]:
    """Create a synthetic AffectNet+ annotation dict."""
    return {
        "Human-Label": human_label,
        "Soft-Label": soft_label,
        "Subset": subset,
        "Metadata": {
            "Age": 30,
            "Gender": {"male": 0.6, "female": 0.4},
            "Race": {"White": 0.8, "Black": 0.1, "Asian": 0.1},
            "Pose": {"Yaw": 0.0, "Pitch": 0.0, "Roll": 0.0},
            "Valence": valence,
            "Arousal": arousal,
        },
        "_image_stem": image_stem,
    }


@pytest.fixture
def affectnet_dir(tmp_path: Path) -> Path:
    """Create a mock AffectNet+ directory with images and annotations."""
    ann_dir = tmp_path / "annotations"
    img_dir = tmp_path / "images"
    ann_dir.mkdir()
    img_dir.mkdir()

    # Create happy samples (code=1)
    for i in range(20):
        stem = f"happy_{i:04d}"
        _make_test_image(img_dir / f"{stem}.jpg")
        soft = [0.05, 0.80, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02]
        ann = _make_annotation(stem, human_label=1, soft_label=soft, subset=0)
        with open(ann_dir / f"{stem}.json", "w") as f:
            json.dump(ann, f)

    # Create sad samples (code=2)
    for i in range(20):
        stem = f"sad_{i:04d}"
        _make_test_image(img_dir / f"{stem}.jpg")
        soft = [0.05, 0.05, 0.80, 0.02, 0.02, 0.02, 0.02, 0.02]
        ann = _make_annotation(stem, human_label=2, soft_label=soft, subset=0)
        with open(ann_dir / f"{stem}.json", "w") as f:
            json.dump(ann, f)

    # Create neutral samples (code=0) — should be filtered out
    for i in range(5):
        stem = f"neutral_{i:04d}"
        _make_test_image(img_dir / f"{stem}.jpg")
        soft = [0.80, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02]
        ann = _make_annotation(stem, human_label=0, soft_label=soft, subset=0)
        with open(ann_dir / f"{stem}.json", "w") as f:
            json.dump(ann, f)

    # Create low-confidence happy sample — should be filtered out
    stem = "ambiguous_happy"
    _make_test_image(img_dir / f"{stem}.jpg")
    soft = [0.30, 0.40, 0.10, 0.05, 0.05, 0.05, 0.03, 0.02]
    ann = _make_annotation(stem, human_label=1, soft_label=soft, subset=0)
    with open(ann_dir / f"{stem}.json", "w") as f:
        json.dump(ann, f)

    # Create difficult sample (subset=2) — should be filtered with max_complexity=1
    stem = "difficult_sad"
    _make_test_image(img_dir / f"{stem}.jpg")
    soft = [0.05, 0.05, 0.75, 0.05, 0.02, 0.02, 0.04, 0.02]
    ann = _make_annotation(stem, human_label=2, soft_label=soft, subset=2)
    with open(ann_dir / f"{stem}.json", "w") as f:
        json.dump(ann, f)

    return tmp_path


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Provide a clean output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# Tests: annotation loading
# ---------------------------------------------------------------------------

class TestLoadAnnotations:
    def test_loads_all_valid_annotations(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        # 20 happy + 20 sad + 5 neutral + 1 ambiguous + 1 difficult = 47
        assert len(annotations) == 47

    def test_annotations_have_image_paths(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        for ann in annotations:
            assert "_image_path" in ann
            assert Path(ann["_image_path"]).exists()

    def test_empty_directory_returns_empty(self, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        annotations = load_affectnet_annotations(empty)
        assert annotations == []


# ---------------------------------------------------------------------------
# Tests: filtering
# ---------------------------------------------------------------------------

class TestFilterAnnotations:
    def test_filters_target_classes_only(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        filtered = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=2, min_confidence=0.0
        )
        # Only happy and sad keys
        assert set(filtered.keys()) == {"happy", "sad"}
        # Neutral samples excluded
        for items in filtered.values():
            for ann in items:
                code = int(ann["Human-Label"])
                assert code in TARGET_CLASSES

    def test_complexity_filter(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)

        # Include all complexities
        filtered_all = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=2, min_confidence=0.0
        )
        total_all = sum(len(v) for v in filtered_all.values())

        # Exclude difficult
        filtered_easy = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=1, min_confidence=0.0
        )
        total_easy = sum(len(v) for v in filtered_easy.values())

        # difficult_sad should be excluded
        assert total_easy < total_all

    def test_confidence_filter(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)

        # No confidence filter
        filtered_all = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=2, min_confidence=0.0
        )
        total_all = sum(len(v) for v in filtered_all.values())

        # With confidence filter
        filtered_conf = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=2, min_confidence=0.6
        )
        total_conf = sum(len(v) for v in filtered_conf.values())

        # ambiguous_happy (conf=0.40) should be excluded
        assert total_conf < total_all


# ---------------------------------------------------------------------------
# Tests: balanced sampling
# ---------------------------------------------------------------------------

class TestSampleBalanced:
    def test_balanced_output(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        filtered = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=1, min_confidence=0.6
        )
        sampled = sample_balanced(filtered, samples_per_class=10, seed=42)

        class_counts: Dict[str, int] = {}
        for ann in sampled:
            cls = ann["_assigned_class"]
            class_counts[cls] = class_counts.get(cls, 0) + 1

        assert class_counts["happy"] == 10
        assert class_counts["sad"] == 10

    def test_caps_at_available(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        filtered = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=1, min_confidence=0.6
        )
        # Request more than available
        sampled = sample_balanced(filtered, samples_per_class=999, seed=42)
        # Should not exceed actual available
        assert len(sampled) <= 40  # 20 happy + 20 sad max

    def test_reproducible_with_seed(self, affectnet_dir: Path):
        annotations = load_affectnet_annotations(affectnet_dir)
        filtered = filter_annotations(
            annotations, TARGET_CLASSES, max_complexity=1, min_confidence=0.6
        )
        s1 = sample_balanced(filtered, samples_per_class=5, seed=123)
        s2 = sample_balanced(filtered, samples_per_class=5, seed=123)

        names1 = [ann["_image_path"] for ann in s1]
        names2 = [ann["_image_path"] for ann in s2]
        assert names1 == names2


# ---------------------------------------------------------------------------
# Tests: image copying
# ---------------------------------------------------------------------------

class TestCopyTestImage:
    def test_copies_valid_image(self, tmp_path: Path):
        img_path = tmp_path / "test.jpg"
        _make_test_image(img_path)

        out_path = tmp_path / "output.jpg"
        result = copy_test_image(img_path, out_path)

        assert result is True
        assert out_path.exists()
        assert out_path.stat().st_size > 0

        # Verify image properties
        img = cv2.imread(str(out_path))
        assert img is not None
        assert img.shape[:2] == (224, 224)

    def test_resizes_non_224_image(self, tmp_path: Path):
        img_path = tmp_path / "big.jpg"
        _make_test_image(img_path, size=512)

        out_path = tmp_path / "resized.jpg"
        result = copy_test_image(img_path, out_path)

        assert result is True
        img = cv2.imread(str(out_path))
        assert img.shape[:2] == (224, 224)

    def test_missing_image_returns_false(self, tmp_path: Path):
        out_path = tmp_path / "test.jpg"
        result = copy_test_image(tmp_path / "nonexistent.jpg", out_path)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: end-to-end dataset creation
# ---------------------------------------------------------------------------

class TestCreateTestDataset:
    def test_creates_unlabeled_test_directory(self, affectnet_dir: Path, output_dir: Path):
        summary = create_test_dataset(
            affectnet_root=affectnet_dir,
            output_root=output_dir,
            samples_per_class=5,
            min_confidence=0.6,
            max_complexity=1,
            seed=42,
        )

        assert summary["success"] is True
        assert summary["total_created"] == 10  # 5 happy + 5 sad

        # Test directory should have images with neutral names
        test_dir = Path(summary["test_dir"])
        assert test_dir.exists()
        images = sorted(test_dir.glob("*.jpg"))
        assert len(images) == 10

        # Verify filenames contain NO emotion labels
        for img in images:
            name = img.name.lower()
            assert "happy" not in name
            assert "sad" not in name
            assert name.startswith("affectnet_")

    def test_creates_label_map(self, affectnet_dir: Path, output_dir: Path):
        summary = create_test_dataset(
            affectnet_root=affectnet_dir,
            output_root=output_dir,
            samples_per_class=5,
            seed=42,
        )

        label_map_path = Path(summary["label_map_path"])
        assert label_map_path.exists()

        # Parse label map
        entries = []
        with open(label_map_path) as f:
            for line in f:
                entries.append(json.loads(line))

        assert len(entries) == 10

        # Each entry should have required fields
        for entry in entries:
            assert "filename" in entry
            assert entry["filename"].endswith(".jpg")
            assert "label" in entry
            assert entry["label"] in ("happy", "sad")
            assert "affectnet_emotion_code" in entry
            assert "soft_label" in entry
            assert "source_image" in entry

    def test_label_map_not_in_test_dir(self, affectnet_dir: Path, output_dir: Path):
        summary = create_test_dataset(
            affectnet_root=affectnet_dir,
            output_root=output_dir,
            samples_per_class=5,
            seed=42,
        )

        test_dir = Path(summary["test_dir"])
        # No JSONL files should be in the test directory
        jsonl_files = list(test_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 0

    def test_class_balance(self, affectnet_dir: Path, output_dir: Path):
        summary = create_test_dataset(
            affectnet_root=affectnet_dir,
            output_root=output_dir,
            samples_per_class=8,
            seed=42,
        )

        assert summary["class_counts"]["happy"] == 8
        assert summary["class_counts"]["sad"] == 8

    def test_empty_affectnet_returns_error(self, tmp_path: Path, output_dir: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        summary = create_test_dataset(
            affectnet_root=empty,
            output_root=output_dir,
            samples_per_class=5,
        )
        assert summary["success"] is False
