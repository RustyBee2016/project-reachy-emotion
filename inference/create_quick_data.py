"""
Create synthetic training data for quick testing.
This creates colored images that simulate happy (warm) and sad (cool) tones.
"""

import numpy as np
from PIL import Image
from pathlib import Path

def create_synthetic_dataset(output_dir='data_quick', n_train=50, n_val=12):
    """Create a minimal synthetic dataset."""

    output_dir = Path(output_dir)

    # Color schemes for each emotion
    colors = {
        'happy': {'base': [255, 220, 150], 'var': 30},  # Warm yellow/orange
        'sad': {'base': [100, 120, 180], 'var': 25},    # Cool blue
    }

    print("Creating synthetic dataset...")
    print(f"Output: {output_dir}")

    for split, n in [('train', n_train), ('val', n_val)]:
        for emotion, color_info in colors.items():
            class_dir = output_dir / split / emotion
            class_dir.mkdir(parents=True, exist_ok=True)

            for i in range(n):
                # Create base image
                img = np.full((224, 224, 3), color_info['base'], dtype=np.uint8)

                # Add random variation
                var = color_info['var']
                noise = np.random.randint(-var, var, (224, 224, 3), dtype=np.int16)
                img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

                # Add some structure (simulate face-like patterns)
                center_y, center_x = 112, 112
                for dy in range(-30, 31):
                    for dx in range(-30, 31):
                        if dy*dy + dx*dx < 900:  # Circle
                            y, x = center_y + dy, center_x + dx
                            # Slightly different color in center
                            img[y, x] = np.clip(img[y, x].astype(np.int16) + 20, 0, 255)

                # Save
                Image.fromarray(img).save(class_dir / f'{emotion}_{i:04d}.jpg')

            print(f"  {split}/{emotion}: {n} images")

    print(f"\nDataset created!")
    print(f"  Train: {n_train * 2} images")
    print(f"  Val: {n_val * 2} images")
    return output_dir

if __name__ == '__main__':
    create_synthetic_dataset()