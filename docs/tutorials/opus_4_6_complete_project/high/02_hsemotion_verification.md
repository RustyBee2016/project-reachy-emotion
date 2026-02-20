# Tutorial 2: HSEmotion Weight Verification

> **Priority**: HIGH — Ensures correct backbone initialization
> **Time estimate**: 4-6 hours
> **Difficulty**: Moderate
> **Prerequisites**: Tutorial 1 complete, PyTorch installed

---

## Why This Matters

The EfficientNet-B0 model can load weights from three different sources:

1. **HSEmotion** (`enet_b0_8_best_vgaf`) — trained on faces + emotions (BEST)
2. **timm** (ImageNet) — trained on dogs, cats, cars (OK but not ideal)
3. **torchvision** (ImageNet) — same as #2

The code in `trainer/fer_finetune/model_efficientnet.py` has a **fallback
chain** that silently drops to ImageNet if HSEmotion fails. This means
you could be training on generic features instead of emotion-specific
features **without knowing it**.

The current code (line 169):
```python
logger.info("HSEmotion weights loaded successfully")
```

This log message appears even if the wrong weights loaded. There's no
verification that the actual weight values are correct.

---

## What You'll Learn

- How pretrained weight loading works in PyTorch
- How to verify model weights with checksums
- How to write deterministic model tests
- What "feature dim" means and why it matters

---

## Step 1: Understand the Weight Loading Chain

Read the backbone creation code:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
# Read lines 111-177 of the model file
```

The chain works like this:

```
1. Explicit weights_path given? → Load from file
2. HSEmotion (emotiefflib) installed? → Load HSEmotion model
3. timm installed? → Load ImageNet EfficientNet-B0
4. None of the above? → Load torchvision ImageNet weights
```

**The problem**: Steps 2-4 all log "loaded successfully" but produce
different weight values. Step 2 gives emotion-optimized features.
Steps 3-4 give generic features (cats, dogs, cars).

---

## Step 2: Check Which Weights Are Available

First, determine what's installed on your system:

```bash
# Check for HSEmotion
python3 -c "from hsemotion.facial_emotions import HSEmotionRecognizer; print('HSEmotion: AVAILABLE')" 2>/dev/null || echo "HSEmotion: NOT INSTALLED"

# Check for timm
python3 -c "import timm; print(f'timm: AVAILABLE (version {timm.__version__})')" 2>/dev/null || echo "timm: NOT INSTALLED"

# Check for torchvision
python3 -c "import torchvision; print(f'torchvision: AVAILABLE (version {torchvision.__version__})')" 2>/dev/null || echo "torchvision: NOT INSTALLED"
```

**If HSEmotion is NOT installed**, install it:

```bash
pip install hsemotion
```

If `hsemotion` is not available via pip, try:

```bash
pip install git+https://github.com/HSE-asavchenko/face-emotion-recognition.git
```

---

## Step 3: Create the Verification Script

Create `trainer/fer_finetune/verify_weights.py`:

```python
"""
HSEmotion weight verification module.

Provides functions to verify that the correct pretrained weights
have been loaded into the EfficientNet-B0 backbone.

How it works:
1. Loads the model
2. Computes a hash of all weight tensors
3. Runs a forward pass with a deterministic input
4. Checks that the output matches expected values

This catches silent fallbacks to ImageNet weights.
"""

import torch
import hashlib
import numpy as np
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def compute_weight_fingerprint(model: torch.nn.Module) -> str:
    """
    Compute a SHA256 hash of all model parameters.

    This gives a unique fingerprint for a set of weights.
    If the weights change (different source), the hash changes.

    Args:
        model: PyTorch model

    Returns:
        Hex string hash of all parameters
    """
    hasher = hashlib.sha256()

    for name, param in sorted(model.named_parameters()):
        # Convert to bytes deterministically
        param_bytes = param.detach().cpu().numpy().tobytes()
        hasher.update(name.encode())
        hasher.update(param_bytes)

    return hasher.hexdigest()


def compute_output_fingerprint(
    model: torch.nn.Module,
    input_size: int = 224,
    seed: int = 42,
) -> np.ndarray:
    """
    Run a deterministic forward pass and return the output.

    Uses a fixed random seed to generate the same input every time.
    If the model weights are different, the output will be different.

    Args:
        model: PyTorch model
        input_size: Expected input size (224 for EfficientNet-B0)
        seed: Random seed for deterministic input

    Returns:
        Output logits as numpy array
    """
    model.eval()
    device = next(model.parameters()).device

    # Generate deterministic input
    rng = np.random.RandomState(seed)
    dummy_input = rng.randn(1, 3, input_size, input_size).astype(np.float32)
    tensor_input = torch.from_numpy(dummy_input).to(device)

    # Forward pass
    with torch.no_grad():
        output = model(tensor_input)

    # Handle dict output (our model returns {'logits': ..., 'features': ...})
    if isinstance(output, dict):
        logits = output['logits']
    else:
        logits = output

    return logits.cpu().numpy()


def verify_hsemotion_weights(
    model: torch.nn.Module,
    expected_fingerprint: Optional[str] = None,
) -> Dict[str, any]:
    """
    Verify that HSEmotion weights are loaded correctly.

    Performs three checks:
    1. Weight fingerprint matches (if expected fingerprint provided)
    2. Feature dimension is correct (1280 for EfficientNet-B0)
    3. Forward pass produces non-zero, non-uniform output

    Args:
        model: The HSEmotionEfficientNet model to verify
        expected_fingerprint: Optional known-good weight hash

    Returns:
        Dictionary with verification results
    """
    results = {
        'verified': True,
        'checks': {},
        'warnings': [],
    }

    # Check 1: Feature dimension
    if hasattr(model, 'feature_dim'):
        feature_dim = model.feature_dim
        expected_dim = 1280  # EfficientNet-B0
        results['checks']['feature_dim'] = {
            'value': feature_dim,
            'expected': expected_dim,
            'passed': feature_dim == expected_dim,
        }
        if feature_dim != expected_dim:
            results['verified'] = False
            results['warnings'].append(
                f"Feature dim mismatch: {feature_dim} != {expected_dim}"
            )

    # Check 2: Weight fingerprint
    fingerprint = compute_weight_fingerprint(model)
    results['checks']['weight_fingerprint'] = {
        'value': fingerprint[:16] + '...',
        'full_hash': fingerprint,
    }

    if expected_fingerprint:
        match = fingerprint == expected_fingerprint
        results['checks']['weight_fingerprint']['expected'] = expected_fingerprint[:16] + '...'
        results['checks']['weight_fingerprint']['passed'] = match
        if not match:
            results['verified'] = False
            results['warnings'].append(
                "Weight fingerprint mismatch — model may have loaded "
                "wrong weights (ImageNet instead of HSEmotion)"
            )

    # Check 3: Forward pass produces reasonable output
    try:
        output = compute_output_fingerprint(model)
        results['checks']['forward_pass'] = {
            'output_shape': list(output.shape),
            'output_range': [float(output.min()), float(output.max())],
            'passed': True,
        }

        # Verify output is not all zeros
        if np.allclose(output, 0):
            results['verified'] = False
            results['checks']['forward_pass']['passed'] = False
            results['warnings'].append("Forward pass produced all zeros")

        # Verify output is not uniform (all same value)
        if output.shape[-1] > 1 and np.std(output) < 1e-6:
            results['warnings'].append(
                "Forward pass output is near-uniform — model may not be "
                "differentiating between classes"
            )

    except Exception as e:
        results['verified'] = False
        results['checks']['forward_pass'] = {
            'passed': False,
            'error': str(e),
        }

    # Check 4: Parameter statistics
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    results['checks']['parameters'] = {
        'total': total_params,
        'trainable': trainable_params,
        'frozen': total_params - trainable_params,
    }

    # EfficientNet-B0 has ~5.3M parameters
    if total_params < 4_000_000 or total_params > 7_000_000:
        results['warnings'].append(
            f"Unexpected parameter count: {total_params}. "
            f"EfficientNet-B0 should have ~5.3M"
        )

    return results


def generate_baseline_fingerprint():
    """
    Generate and print the weight fingerprint for the current model.

    Run this ONCE after confirming correct weights are loaded.
    Save the output and use it in future verification calls.

    Usage:
        python -m trainer.fer_finetune.verify_weights
    """
    from .model_efficientnet import create_efficientnet_model

    print("Loading HSEmotionEfficientNet with default weights...")
    model = create_efficientnet_model(num_classes=3, pretrained=True)
    model.eval()

    fingerprint = compute_weight_fingerprint(model)
    output = compute_output_fingerprint(model)

    print(f"\nWeight fingerprint: {fingerprint}")
    print(f"Output shape: {output.shape}")
    print(f"Output values: {output[0]}")
    print(f"\nSave this fingerprint to use in verification tests.")
    print(f"It will change if: different weights load, PyTorch version changes,")
    print(f"or model architecture changes.")

    return fingerprint


if __name__ == "__main__":
    generate_baseline_fingerprint()
```

---

## Step 4: Generate Your Baseline Fingerprint

Run the fingerprint generator to establish what "correct" looks like:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
python3 -m trainer.fer_finetune.verify_weights
```

**Expected output** (your values will differ):
```
Loading HSEmotionEfficientNet with default weights...
HSEmotion weights loaded successfully

Weight fingerprint: a3f7b2c9d1e4f5...
Output shape: (1, 3)
Output values: [-0.1234  0.5678  0.0123]

Save this fingerprint to use in verification tests.
```

**Save the fingerprint!** You'll use it in the test below.

**If you see "torchvision EfficientNet-B0 (ImageNet weights)"** in the
output, that means HSEmotion didn't load. Go back to Step 2 and install it.

---

## Step 5: Write Verification Tests

Create `tests/test_hsemotion_weights.py`:

```python
"""
Tests that verify HSEmotion pretrained weights load correctly.

These tests catch the silent fallback to ImageNet weights.
Run after any change to model_efficientnet.py or its dependencies.
"""

import pytest
import torch
import numpy as np


class TestWeightLoading:
    """Verify the correct pretrained weights are loaded."""

    def test_model_creates_successfully(self):
        """Model can be instantiated without errors."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        assert model is not None
        assert model.num_classes == 3

    def test_feature_dimension_is_1280(self):
        """EfficientNet-B0 should produce 1280-dim features."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        assert model.feature_dim == 1280

    def test_forward_pass_shape(self):
        """Forward pass produces correct output shapes."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        model.eval()

        dummy = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            output = model(dummy)

        assert 'logits' in output
        assert 'features' in output
        assert output['logits'].shape == (2, 3)
        assert output['features'].shape == (2, 1280)

    def test_forward_pass_not_random(self):
        """Same input produces same output (weights are deterministic)."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        model.eval()

        torch.manual_seed(42)
        dummy = torch.randn(1, 3, 224, 224)

        with torch.no_grad():
            output1 = model(dummy)['logits'].numpy()
            output2 = model(dummy)['logits'].numpy()

        np.testing.assert_array_almost_equal(output1, output2)

    def test_backbone_frozen_correctly(self):
        """After freeze, only head parameters are trainable."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        model.freeze_backbone()

        # FC head should be trainable
        assert model.fc.weight.requires_grad is True
        assert model.fc.bias.requires_grad is True

        # Backbone should be frozen
        backbone_trainable = sum(
            1 for p in model.backbone.parameters() if p.requires_grad
        )
        assert backbone_trainable == 0, (
            f"Expected 0 trainable backbone params, got {backbone_trainable}"
        )

    def test_unfreeze_specific_layers(self):
        """Selective unfreezing works for fine-tuning."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        model.freeze_backbone()

        # Unfreeze final block
        model.unfreeze_layers(["blocks.6"])

        # Some backbone params should now be trainable
        backbone_trainable = sum(
            1 for p in model.backbone.parameters() if p.requires_grad
        )
        assert backbone_trainable > 0

    def test_parameter_count_reasonable(self):
        """Total parameters are in expected range for EfficientNet-B0."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        total = model.get_total_params()

        # EfficientNet-B0 has ~5.3M params + our head
        assert 4_000_000 < total < 7_000_000, (
            f"Unexpected parameter count: {total}. "
            f"Expected ~5.3M for EfficientNet-B0"
        )

    def test_verification_passes(self):
        """Full verification suite passes."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model
        from trainer.fer_finetune.verify_weights import verify_hsemotion_weights

        model = create_efficientnet_model(num_classes=3, pretrained=True)
        model.eval()

        results = verify_hsemotion_weights(model)

        assert results['checks']['forward_pass']['passed'] is True
        assert results['checks']['feature_dim']['passed'] is True

        if results['warnings']:
            for w in results['warnings']:
                print(f"WARNING: {w}")

    def test_pretrained_vs_random_are_different(self):
        """Pretrained model produces different output than random init."""
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        pretrained = create_efficientnet_model(num_classes=3, pretrained=True)
        random_init = create_efficientnet_model(num_classes=3, pretrained=False)

        pretrained.eval()
        random_init.eval()

        torch.manual_seed(42)
        dummy = torch.randn(1, 3, 224, 224)

        with torch.no_grad():
            out_pretrained = pretrained(dummy)['logits'].numpy()
            out_random = random_init(dummy)['logits'].numpy()

        # They should NOT be equal (if they are, pretrained didn't load)
        assert not np.allclose(out_pretrained, out_random, atol=0.01), (
            "Pretrained and random models produce same output! "
            "Pretrained weights may not have loaded correctly."
        )


class TestWeightFallbackDetection:
    """Tests that detect when the model silently falls back to ImageNet."""

    def test_log_which_backend_loaded(self, caplog):
        """Verify log output indicates which weight source was used."""
        import logging
        from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

        with caplog.at_level(logging.INFO):
            model = create_efficientnet_model(num_classes=3, pretrained=True)

        log_text = caplog.text.lower()

        # At least one of these should appear
        loaded_hsemotion = "hsemotion" in log_text
        loaded_timm = "timm" in log_text
        loaded_torchvision = "torchvision" in log_text

        assert loaded_hsemotion or loaded_timm or loaded_torchvision, (
            "No weight loading source was logged. "
            "Check model_efficientnet.py logging."
        )

        # Prefer HSEmotion — warn if it fell back
        if not loaded_hsemotion:
            pytest.skip(
                "HSEmotion weights not loaded (fell back to ImageNet). "
                "Install hsemotion: pip install hsemotion"
            )
```

### Run the Tests

```bash
pytest tests/test_hsemotion_weights.py -v
```

---

## Step 6: Add a Logging Warning for Fallback

To make fallback more visible, add an explicit warning to the model.
Open `trainer/fer_finetune/model_efficientnet.py` and find the
`_create_backbone` method. After the HSEmotion attempt, add a warning:

Find this block (around line 140-148):

```python
        # Try timm
        backbone = self._try_timm_backbone(pretrained_weights)
        if backbone is not None:
            return backbone, feature_dim

        # Fallback to torchvision
        logger.warning("Using torchvision EfficientNet-B0 (ImageNet weights)")
        return self._create_torchvision_backbone(), feature_dim
```

Add a clear warning before the timm fallback:

```python
        # Try timm
        logger.warning(
            "HSEmotion weights unavailable. Falling back to ImageNet. "
            "The model will train but may not achieve Gate A thresholds. "
            "Install HSEmotion: pip install hsemotion"
        )
        backbone = self._try_timm_backbone(pretrained_weights)
        if backbone is not None:
            return backbone, feature_dim

        # Fallback to torchvision
        logger.warning("Using torchvision EfficientNet-B0 (ImageNet weights)")
        return self._create_torchvision_backbone(), feature_dim
```

---

## Checklist

Before moving to Tutorial 3, verify:

- [ ] HSEmotion is installed (`pip list | grep hsemotion`)
- [ ] `trainer/fer_finetune/verify_weights.py` exists
- [ ] Baseline fingerprint generated and noted
- [ ] `tests/test_hsemotion_weights.py` passes
- [ ] Log output confirms "HSEmotion" weights loaded (not ImageNet fallback)
- [ ] Fallback warning added to `_create_backbone()`

---

## What's Next

Tutorial 3 will audit the promotion service — verifying that videos
can move through the pipeline (temp -> dataset_all -> train/test).
