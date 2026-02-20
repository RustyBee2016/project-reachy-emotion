"""
Quick Start: Run emotion inference on a test image.
This script demonstrates the complete inference pipeline.
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path

# Import our model
from trainer.fer_finetune.model_efficientnet import HSEmotionEfficientNet

def create_test_image():
    """Create a simple test image (yellow = happy-ish, blue = sad-ish)."""
    # Create a 224x224 image with warm colors (simulates happy face tones)
    img = np.full((224, 224, 3), [255, 200, 150], dtype=np.uint8)
    # Add some variation
    noise = np.random.randint(-20, 20, (224, 224, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(img)

def preprocess_image(img):
    """Preprocess image for model input."""
    # Resize to 224x224
    img = img.resize((224, 224))

    # Convert to numpy and normalize
    img_array = np.array(img).astype(np.float32) / 255.0

    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    img_array = (img_array - mean) / std

    # Convert to tensor: HWC -> CHW -> NCHW
    img_tensor = torch.from_numpy(img_array.transpose(2, 0, 1)).unsqueeze(0)

    return img_tensor.float()

def run_inference():
    """Run inference with pre-trained model."""

    print("=" * 60)
    print("QUICK START: EfficientNet-B0 Emotion Inference")
    print("=" * 60)

    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n1. Device: {device}")

    # Load model with HSEmotion pre-trained weights
    print("\n2. Loading EfficientNet-B0 (HSEmotion weights)...")
    model = HSEmotionEfficientNet(
        num_classes=3,  # happy, sad, neutral
        pretrained_weights='enet_b0_8_best_vgaf',
        dropout_rate=0.3,
    )
    model = model.to(device)
    model.eval()
    print(f"   Model loaded! Parameters: {model.get_total_params():,}")

    # Create or load test image
    print("\n3. Creating test image...")
    test_img = create_test_image()
    test_img.save('test_image.jpg')
    print("   Saved to: test_image.jpg")

    # Preprocess
    print("\n4. Preprocessing image...")
    input_tensor = preprocess_image(test_img).to(device)
    print(f"   Input shape: {input_tensor.shape}")

    # Run inference
    print("\n5. Running inference...")
    with torch.no_grad():
        output = model(input_tensor)
        logits = output['logits']
        probs = torch.softmax(logits, dim=1)

    # Interpret results
    class_names = ['happy', 'sad', 'neutral']
    predicted_idx = probs.argmax(dim=1).item()
    confidence = probs[0, predicted_idx].item()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nPredicted emotion: {class_names[predicted_idx].upper()}")
    print(f"Confidence: {confidence:.1%}")
    print(f"\nAll probabilities:")
    for i, name in enumerate(class_names):
        bar = "█" * int(probs[0, i].item() * 20)
        print(f"  {name:8s}: {probs[0, i].item():.1%} {bar}")

    print("\n" + "=" * 60)
    print("SUCCESS! You just ran emotion inference.")
    print("=" * 60)

    return probs

if __name__ == '__main__':
    run_inference()