# Tutorial 1: Implement Face Detection in the Training Pipeline

> **Priority**: HIGH — Blocks model quality
> **Time estimate**: 12-16 hours
> **Difficulty**: Moderate
> **Prerequisites**: Python 3.12, pip, OpenCV installed

---

## Why This Matters

Right now, the emotion classifier receives **full video frames** — background,
furniture, walls, and a small face somewhere in the image. The model will learn
to associate backgrounds with emotions instead of learning facial expressions.

The file `trainer/fer_finetune/dataset.py` has a stub at line 235:

```python
def _crop_face(self, image: np.ndarray) -> np.ndarray:
    # Placeholder for face detection
    # In production, use RetinaFace, SCRFD, or similar
    # For now, return original image
    return image
```

You will replace this with a real face detector.

---

## What You'll Learn

- How face detection works (bounding boxes, confidence scores)
- How to integrate MTCNN (Multi-Task Cascaded Convolutional Networks)
- How to handle edge cases (no face found, multiple faces)
- How to write tests for image processing code

---

## Step 1: Understand the Current Code

Read the dataset module to see how `_crop_face` is called:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
cat -n trainer/fer_finetune/dataset.py | head -185
```

Key observations:
- Line 59: The constructor accepts an optional `face_detector` parameter
- Line 167-168: Face cropping only runs if `self.face_detector is not None`
- Line 235-247: The actual stub — returns the image unchanged

This means the face detector is **opt-in**. When we implement it, existing
code that doesn't pass a detector still works (backward compatible).

---

## Step 2: Install the Face Detection Library

We'll use `facenet-pytorch` which provides MTCNN — a well-tested face
detector that runs on CPU or GPU.

```bash
pip install facenet-pytorch
```

**Why MTCNN?**
- Pure Python/PyTorch — no C++ compilation needed
- Returns bounding boxes AND facial landmarks
- Works on CPU (important for development) and GPU
- Well-maintained, MIT licensed
- ~50ms per image on CPU, ~5ms on GPU

Verify the install:

```python
python3 -c "from facenet_pytorch import MTCNN; print('MTCNN imported OK')"
```

---

## Step 3: Create the Face Detector Module

Create a new file for the face detection logic. We keep it separate from
the dataset code so it can be tested independently.

Create the file `trainer/fer_finetune/face_detector.py`:

```python
"""
Face detection module for emotion classification preprocessing.

Uses MTCNN (Multi-Task Cascaded Convolutional Networks) to detect and crop
faces from video frames before feeding them to the emotion classifier.

Why face detection matters:
- Without it, the model sees full frames (walls, furniture, etc.)
- The model might learn "blue wall = happy" instead of "smile = happy"
- Face cropping forces the model to focus on facial expressions
"""

import numpy as np
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import MTCNN
try:
    from facenet_pytorch import MTCNN
    import torch
    MTCNN_AVAILABLE = True
except ImportError:
    MTCNN_AVAILABLE = False
    logger.warning(
        "facenet-pytorch not installed. Face detection unavailable. "
        "Install with: pip install facenet-pytorch"
    )


class FaceDetector:
    """
    MTCNN-based face detector for preprocessing emotion training data.

    Usage:
        detector = FaceDetector()
        cropped_face = detector.detect_and_crop(image)

    The detector:
    1. Finds all faces in the image
    2. Selects the largest face (closest to camera)
    3. Adds padding around the face (forehead, chin)
    4. Crops and resizes to target_size x target_size
    5. Falls back to center crop if no face is found
    """

    def __init__(
        self,
        target_size: int = 224,
        margin_fraction: float = 0.3,
        min_confidence: float = 0.9,
        device: Optional[str] = None,
    ):
        """
        Initialize the face detector.

        Args:
            target_size: Output image size (224 for EfficientNet-B0)
            margin_fraction: Extra space around the face as a fraction
                of the face size. 0.3 = 30% padding on each side.
                This captures forehead, chin, and some hair.
            min_confidence: Minimum detection confidence (0-1).
                Higher = fewer false positives but might miss faces.
                0.9 is a good default for clear video frames.
            device: 'cuda' or 'cpu'. Auto-detects if None.
        """
        if not MTCNN_AVAILABLE:
            raise RuntimeError(
                "facenet-pytorch is required for face detection. "
                "Install with: pip install facenet-pytorch"
            )

        self.target_size = target_size
        self.margin_fraction = margin_fraction
        self.min_confidence = min_confidence

        # Auto-detect device
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device

        # Initialize MTCNN
        # keep_all=True returns ALL detected faces (we pick the largest)
        # post_process=False gives us raw bounding boxes (not aligned faces)
        self._mtcnn = MTCNN(
            keep_all=True,
            post_process=False,
            device=device,
            thresholds=[0.6, 0.7, 0.7],  # Detection thresholds per stage
        )

        self._faces_detected = 0
        self._faces_missed = 0
        self._total_processed = 0

        logger.info(
            f"FaceDetector initialized: target_size={target_size}, "
            f"margin={margin_fraction}, min_conf={min_confidence}, "
            f"device={device}"
        )

    def detect_and_crop(self, image: np.ndarray) -> np.ndarray:
        """
        Detect the primary face in an image and crop it.

        This is the main method you'll call from the dataset.

        Args:
            image: Input image as numpy array [H, W, 3] in RGB format

        Returns:
            Cropped face as numpy array [target_size, target_size, 3] RGB

        If no face is detected, returns a center crop of the original image.
        """
        self._total_processed += 1

        # Detect faces
        boxes, confidences = self._detect_faces(image)

        if boxes is None or len(boxes) == 0:
            self._faces_missed += 1
            logger.debug(
                f"No face detected (total misses: {self._faces_missed}/"
                f"{self._total_processed})"
            )
            return self._center_crop(image)

        # Select the largest face (most likely the main subject)
        best_box, best_conf = self._select_largest_face(boxes, confidences)

        if best_conf < self.min_confidence:
            self._faces_missed += 1
            logger.debug(
                f"Face confidence too low: {best_conf:.2f} < "
                f"{self.min_confidence}"
            )
            return self._center_crop(image)

        self._faces_detected += 1

        # Add margin and crop
        cropped = self._crop_with_margin(image, best_box)

        return cropped

    def _detect_faces(
        self, image: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Run MTCNN face detection on an image.

        Args:
            image: RGB image [H, W, 3]

        Returns:
            Tuple of (boxes [N, 4], confidences [N])
            boxes are in format [x1, y1, x2, y2]
        """
        try:
            # MTCNN expects PIL or numpy RGB
            boxes, confidences = self._mtcnn.detect(image)
            return boxes, confidences
        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return None, None

    def _select_largest_face(
        self,
        boxes: np.ndarray,
        confidences: np.ndarray,
    ) -> Tuple[np.ndarray, float]:
        """
        Select the largest face from detected faces.

        "Largest" = biggest bounding box area. This is usually the person
        closest to the camera, which is the one we care about.

        Args:
            boxes: Detected face boxes [N, 4] as [x1, y1, x2, y2]
            confidences: Detection confidences [N]

        Returns:
            Tuple of (best_box [4], confidence)
        """
        # Calculate area of each face box
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

        # Find the largest
        largest_idx = np.argmax(areas)

        return boxes[largest_idx], float(confidences[largest_idx])

    def _crop_with_margin(
        self, image: np.ndarray, box: np.ndarray
    ) -> np.ndarray:
        """
        Crop face region with margin padding and resize.

        The margin ensures we capture forehead, chin, and some context
        around the face — important for emotion recognition (eyebrows,
        jaw tension, etc.)

        Args:
            image: Original image [H, W, 3]
            box: Face bounding box [x1, y1, x2, y2]

        Returns:
            Cropped and resized face [target_size, target_size, 3]
        """
        import cv2

        h, w = image.shape[:2]
        x1, y1, x2, y2 = box

        # Calculate face dimensions
        face_w = x2 - x1
        face_h = y2 - y1

        # Add margin (percentage of face size)
        margin_x = face_w * self.margin_fraction
        margin_y = face_h * self.margin_fraction

        # Expand box with margin, clamping to image bounds
        x1 = max(0, int(x1 - margin_x))
        y1 = max(0, int(y1 - margin_y))
        x2 = min(w, int(x2 + margin_x))
        y2 = min(h, int(y2 + margin_y))

        # Crop
        cropped = image[y1:y2, x1:x2]

        # Resize to target size
        cropped = cv2.resize(
            cropped,
            (self.target_size, self.target_size),
            interpolation=cv2.INTER_AREA,  # Best for downscaling
        )

        return cropped

    def _center_crop(self, image: np.ndarray) -> np.ndarray:
        """
        Fallback: center crop when no face is detected.

        Takes the largest possible square from the center of the image
        and resizes it to target_size.

        Args:
            image: Original image [H, W, 3]

        Returns:
            Center-cropped image [target_size, target_size, 3]
        """
        import cv2

        h, w = image.shape[:2]
        crop_size = min(h, w)

        # Calculate center crop coordinates
        start_x = (w - crop_size) // 2
        start_y = (h - crop_size) // 2

        cropped = image[start_y:start_y + crop_size, start_x:start_x + crop_size]

        cropped = cv2.resize(
            cropped,
            (self.target_size, self.target_size),
            interpolation=cv2.INTER_AREA,
        )

        return cropped

    def get_stats(self) -> dict:
        """Return detection statistics for monitoring."""
        return {
            "total_processed": self._total_processed,
            "faces_detected": self._faces_detected,
            "faces_missed": self._faces_missed,
            "detection_rate": (
                self._faces_detected / self._total_processed
                if self._total_processed > 0
                else 0.0
            ),
        }
```

---

## Step 4: Integrate with the Dataset

Now modify `trainer/fer_finetune/dataset.py` to use the real face detector.

### 4a. Replace the stub `_crop_face` method

Open `trainer/fer_finetune/dataset.py` and replace lines 235-247:

**Old code (delete this):**
```python
def _crop_face(self, image: np.ndarray) -> np.ndarray:
    """
    Detect and crop face from image.

    Falls back to center crop if no face detected.
    """
    if self.face_detector is None:
        return image

    # Placeholder for face detection
    # In production, use RetinaFace, SCRFD, or similar
    # For now, return original image
    return image
```

**New code (replace with this):**
```python
def _crop_face(self, image: np.ndarray) -> np.ndarray:
    """
    Detect and crop face from image.

    Falls back to center crop if no face detected.
    Uses the face_detector passed during initialization.
    """
    if self.face_detector is None:
        return image

    return self.face_detector.detect_and_crop(image)
```

### 4b. Update `create_dataloaders` to use face detection

Open `trainer/fer_finetune/dataset.py` and update the `create_dataloaders`
function (around line 509) to accept an optional face detector:

**Find this function signature:**
```python
def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    num_workers: int = 4,
    input_size: int = 224,
    class_names: Optional[List[str]] = None,
    frame_sampling_train: str = "random",
    frame_sampling_val: str = "middle",
) -> Tuple[DataLoader, DataLoader]:
```

**Replace with:**
```python
def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    num_workers: int = 4,
    input_size: int = 224,
    class_names: Optional[List[str]] = None,
    frame_sampling_train: str = "random",
    frame_sampling_val: str = "middle",
    use_face_detection: bool = True,
) -> Tuple[DataLoader, DataLoader]:
```

**Then add this at the start of the function body (before `train_dataset = ...`):**
```python
    # Set up face detection
    face_detector = None
    if use_face_detection:
        try:
            from .face_detector import FaceDetector
            face_detector = FaceDetector(target_size=input_size)
            logger.info("Face detection enabled for training data")
        except (ImportError, RuntimeError) as e:
            logger.warning(f"Face detection unavailable: {e}. Using full frames.")
```

**Then pass the detector to both datasets:**
```python
    train_dataset = EmotionDataset(
        data_dir=data_dir,
        split="train",
        transform=get_train_transforms(input_size),
        class_names=class_names,
        frame_sampling=frame_sampling_train,
        face_detector=face_detector,  # ADD THIS LINE
    )

    val_dataset = EmotionDataset(
        data_dir=data_dir,
        split="test",
        transform=get_val_transforms(input_size),
        class_names=class_names,
        frame_sampling=frame_sampling_val,
        face_detector=face_detector,  # ADD THIS LINE
    )
```

---

## Step 5: Test with Simulated Data

Before testing with real videos, let's verify the detector works with
synthetic images. Create a test file:

Create `tests/test_face_detector.py`:

```python
"""
Tests for the face detection module.

These tests use synthetically generated face-like images
so they can run without real video data.
"""

import numpy as np
import pytest
from pathlib import Path


# Skip all tests if facenet-pytorch is not installed
pytest.importorskip("facenet_pytorch", reason="facenet-pytorch not installed")


from trainer.fer_finetune.face_detector import FaceDetector


@pytest.fixture
def detector():
    """Create a face detector instance (CPU mode for testing)."""
    return FaceDetector(target_size=224, device="cpu")


@pytest.fixture
def sample_image_with_face():
    """
    Create a synthetic image with a face-like pattern.

    This is a 640x480 image with a bright oval in the center
    (simulating a face against a darker background).
    Real MTCNN may not detect this as a face — that's OK.
    We use this to test the fallback (center crop) path.
    """
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some background
    image[:, :] = [40, 60, 80]  # Dark blue-gray

    # Draw a face-like oval in the center
    import cv2
    center = (320, 240)
    axes = (80, 100)  # Width, height of oval
    cv2.ellipse(image, center, axes, 0, 0, 360, (220, 180, 160), -1)

    # Draw simple eyes
    cv2.circle(image, (290, 220), 10, (60, 40, 30), -1)
    cv2.circle(image, (350, 220), 10, (60, 40, 30), -1)

    # Draw mouth
    cv2.ellipse(image, (320, 270), (30, 15), 0, 0, 180, (180, 100, 100), 2)

    return image


@pytest.fixture
def blank_image():
    """A plain white image with no face."""
    return np.ones((480, 640, 3), dtype=np.uint8) * 255


class TestFaceDetector:
    """Test suite for FaceDetector."""

    def test_initialization(self, detector):
        """Verify detector initializes with correct defaults."""
        assert detector.target_size == 224
        assert detector.margin_fraction == 0.3
        assert detector.min_confidence == 0.9
        assert detector.device == "cpu"

    def test_output_shape(self, detector, sample_image_with_face):
        """Output is always target_size x target_size x 3."""
        result = detector.detect_and_crop(sample_image_with_face)
        assert result.shape == (224, 224, 3)
        assert result.dtype == np.uint8

    def test_blank_image_returns_center_crop(self, detector, blank_image):
        """When no face is found, center crop is returned."""
        result = detector.detect_and_crop(blank_image)
        assert result.shape == (224, 224, 3)

    def test_stats_tracking(self, detector, blank_image):
        """Statistics are tracked across calls."""
        assert detector.get_stats()["total_processed"] == 0

        detector.detect_and_crop(blank_image)
        stats = detector.get_stats()
        assert stats["total_processed"] == 1

    def test_center_crop_is_square(self, detector):
        """Center crop works on non-square images."""
        # Wide image
        wide = np.zeros((100, 400, 3), dtype=np.uint8)
        result = detector._center_crop(wide)
        assert result.shape == (224, 224, 3)

        # Tall image
        tall = np.zeros((400, 100, 3), dtype=np.uint8)
        result = detector._center_crop(tall)
        assert result.shape == (224, 224, 3)

    def test_select_largest_face(self, detector):
        """Largest face (by area) is selected."""
        boxes = np.array([
            [10, 10, 50, 50],    # Area: 1600 (small face)
            [100, 100, 300, 300],  # Area: 40000 (large face)
            [200, 200, 250, 250],  # Area: 2500 (medium face)
        ])
        confidences = np.array([0.95, 0.92, 0.98])

        best_box, best_conf = detector._select_largest_face(boxes, confidences)

        # Should pick index 1 (largest area), even though index 2 has
        # higher confidence
        assert best_conf == 0.92
        np.testing.assert_array_equal(best_box, [100, 100, 300, 300])

    def test_crop_with_margin_clamps_to_bounds(self, detector):
        """Margin expansion doesn't go outside image boundaries."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        # Box near the edge
        box = np.array([0.0, 0.0, 50.0, 50.0])

        result = detector._crop_with_margin(image, box)
        assert result.shape == (224, 224, 3)

    def test_small_image_handling(self, detector):
        """Detector handles very small images gracefully."""
        tiny = np.zeros((32, 32, 3), dtype=np.uint8)
        result = detector.detect_and_crop(tiny)
        assert result.shape == (224, 224, 3)
```

### Run the Tests

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
pytest tests/test_face_detector.py -v
```

Expected output: All tests pass. Some tests exercise the center-crop
fallback path (which is fine — synthetic images aren't real faces).

---

## Step 6: Test with a Real Image

Download a sample face image to verify MTCNN actually detects a face:

```python
"""Quick manual test — run this interactively."""
import cv2
import numpy as np
from trainer.fer_finetune.face_detector import FaceDetector

# Create detector
detector = FaceDetector(target_size=224, device="cpu")

# Load a test image (use any image with a face)
# If you don't have one, use the webcam:
cap = cv2.VideoCapture(0)  # 0 = default webcam
ret, frame = cap.read()
cap.release()

if ret:
    # OpenCV captures in BGR, convert to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect and crop face
    cropped = detector.detect_and_crop(rgb_frame)
    print(f"Input shape: {rgb_frame.shape}")
    print(f"Output shape: {cropped.shape}")
    print(f"Stats: {detector.get_stats()}")

    # Save result for inspection
    cv2.imwrite("/tmp/face_crop_test.jpg", cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
    print("Saved cropped face to /tmp/face_crop_test.jpg")
else:
    print("No webcam available. Use a file instead.")
```

If no webcam is available, use any `.jpg` file with a face:

```python
image = cv2.imread("/path/to/photo.jpg")
rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
cropped = detector.detect_and_crop(rgb_image)
```

---

## Step 7: Verify with the Full Dataset Pipeline

Test that face detection works end-to-end with the EmotionDataset:

```python
"""Integration test: dataset with face detection."""
from trainer.fer_finetune.dataset import EmotionDataset
from trainer.fer_finetune.face_detector import FaceDetector

# Create a detector
detector = FaceDetector(target_size=224, device="cpu")

# Create a dataset with face detection enabled
# (Adjust path to your actual data directory)
dataset = EmotionDataset(
    data_dir="/media/project_data/reachy_emotion/videos",
    split="train",
    class_names=["happy", "sad", "neutral"],
    face_detector=detector,
)

# Load one sample
if len(dataset) > 0:
    image, label = dataset[0]
    print(f"Image tensor shape: {image.shape}")
    print(f"Label: {label}")
    print(f"Face detection stats: {detector.get_stats()}")
else:
    print("No data found. Check your data directory path.")
```

---

## Step 8: Performance Considerations

Face detection adds processing time. Here's what to expect:

| Device | Per-image time | 1000 images |
|--------|---------------|-------------|
| CPU    | ~50-80 ms     | ~60 seconds |
| GPU    | ~5-10 ms      | ~8 seconds  |

For training, this is fine — face detection runs once per image load,
and DataLoader parallelizes it across `num_workers` processes.

**Tip**: If training is slow, you can pre-crop faces and save them:

```python
"""Optional: pre-crop all faces and save as images."""
import cv2
from pathlib import Path
from trainer.fer_finetune.face_detector import FaceDetector

detector = FaceDetector(target_size=224, device="cpu")
source_dir = Path("/media/project_data/reachy_emotion/videos/dataset_all")
output_dir = Path("/media/project_data/reachy_emotion/faces")

for emotion_dir in source_dir.iterdir():
    if not emotion_dir.is_dir():
        continue

    out_emotion = output_dir / emotion_dir.name
    out_emotion.mkdir(parents=True, exist_ok=True)

    for video_path in emotion_dir.glob("*.mp4"):
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
        ret, frame = cap.read()
        cap.release()

        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face = detector.detect_and_crop(rgb)
            out_path = out_emotion / f"{video_path.stem}.jpg"
            cv2.imwrite(str(out_path), cv2.cvtColor(face, cv2.COLOR_RGB2BGR))

print(f"Detection stats: {detector.get_stats()}")
```

---

## Checklist

Before moving to Tutorial 2, verify:

- [ ] `facenet-pytorch` is installed (`pip list | grep facenet`)
- [ ] `trainer/fer_finetune/face_detector.py` exists with `FaceDetector` class
- [ ] The stub in `dataset.py` `_crop_face()` is replaced (2 lines)
- [ ] `create_dataloaders()` accepts `use_face_detection` parameter
- [ ] `tests/test_face_detector.py` passes: `pytest tests/test_face_detector.py -v`
- [ ] Manual test with a real image produces a cropped face

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: facenet_pytorch` | `pip install facenet-pytorch` |
| CUDA out of memory | Use `device="cpu"` for detection |
| MTCNN very slow | Normal on CPU (~50ms). Use GPU or pre-crop. |
| No face detected on clear face photo | Lower `min_confidence` to 0.7 |
| `cv2` not found | `pip install opencv-python-headless` |

---

## What's Next

Tutorial 2 will verify that the HSEmotion pretrained weights load
correctly, so you know the backbone is learning from emotion-specific
features rather than generic ImageNet features.
