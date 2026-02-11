# Tutorial 9: Web UI — Generate Page

> **Priority**: MEDIUM — Synthetic video generation interface
> **Time estimate**: 6-8 hours
> **Difficulty**: Easy-Moderate
> **Prerequisites**: Luma AI API key (optional), Streamlit basics

---

## Why This Matters

The Generate page (`apps/web/pages/01_Generate.py`) is a 24-line stub.
However, the landing page (`apps/web/landing_page.py`) already has a
working Luma AI integration. This tutorial extracts that logic into
the dedicated page.

---

## What You'll Build

A Streamlit page that:
1. Generates synthetic face videos via Luma AI (if API key available)
2. Creates simulated test images (always available, no API key needed)
3. Displays generated content for review

---

## Step 1: Read the Existing Luma Integration

```bash
cat -n apps/web/luma_client.py
```

Note the key functions: API calls, polling for completion, downloading.

---

## Step 2: Implement the Generate Page

Replace `apps/web/pages/01_Generate.py` with:

```python
"""
Video Generation Page — Create synthetic training data.

Provides two modes:
1. Luma AI: Generate realistic face videos (requires API key)
2. Simulated: Generate simple test images (always available)
"""

import streamlit as st
import numpy as np
import cv2
import tempfile
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Generate Data", page_icon="🎬", layout="wide")

st.title("Generate Training Data")

tab_simulated, tab_luma = st.tabs(["Simulated Data", "Luma AI (Advanced)"])


# ---- Tab 1: Simulated Data ----

with tab_simulated:
    st.markdown(
        "Generate simple synthetic images for pipeline testing. "
        "These are pattern-based images, not real faces."
    )

    col1, col2 = st.columns(2)
    with col1:
        num_images = st.slider("Images per class", 10, 200, 50)
    with col2:
        image_size = st.selectbox("Image size", [112, 224, 336], index=1)

    if st.button("Generate Simulated Dataset", type="primary"):
        output_dir = Path(tempfile.mkdtemp(prefix="reachy_sim_"))

        progress = st.progress(0, text="Generating...")

        classes = ["happy", "sad", "neutral"]
        total = num_images * len(classes)
        generated = 0

        for label in classes:
            label_dir = output_dir / "train" / label
            label_dir.mkdir(parents=True, exist_ok=True)

            for i in range(num_images):
                image = np.zeros((image_size, image_size, 3), dtype=np.uint8)

                if label == "happy":
                    image[:, :] = [255, 220, 150]
                    center = (image_size // 2, image_size // 2 + image_size // 6)
                    cv2.ellipse(image, center, (image_size // 5, image_size // 8),
                                0, 0, 180, (200, 80, 80), 3)
                elif label == "sad":
                    image[:, :] = [140, 160, 200]
                    center = (image_size // 2, image_size // 2 + image_size // 4)
                    cv2.ellipse(image, center, (image_size // 5, image_size // 8),
                                0, 180, 360, (100, 80, 120), 3)
                else:
                    image[:, :] = [190, 185, 175]
                    y = image_size // 2 + image_size // 5
                    cv2.line(image,
                             (image_size // 2 - image_size // 6, y),
                             (image_size // 2 + image_size // 6, y),
                             (140, 110, 100), 2)

                # Add noise for variation
                rng = np.random.RandomState(i)
                noise = rng.randint(-15, 15, image.shape, dtype=np.int16)
                image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

                filename = f"{label}_{i:04d}.jpg"
                cv2.imwrite(str(label_dir / filename), image)

                generated += 1
                progress.progress(generated / total, text=f"Generating {label}...")

        progress.progress(1.0, text="Complete!")
        st.success(
            f"Generated {total} images in `{output_dir}`\n\n"
            f"Use this path as `data_root` in your training config."
        )
        st.code(str(output_dir))


# ---- Tab 2: Luma AI ----

with tab_luma:
    st.markdown(
        "Generate realistic synthetic face videos using Luma AI. "
        "Requires a `LUMAAI_API_KEY` environment variable."
    )

    import os
    api_key = os.environ.get("LUMAAI_API_KEY")

    if not api_key:
        st.warning(
            "Luma AI API key not set. Set the `LUMAAI_API_KEY` "
            "environment variable to enable this feature."
        )
        st.code("export LUMAAI_API_KEY='your-key-here'")
    else:
        st.success("Luma AI API key detected.")

        emotion = st.selectbox("Target emotion", ["happy", "sad", "neutral"])
        prompt = st.text_area(
            "Generation prompt",
            value=f"A close-up video of a person's face showing a {emotion} expression, "
                  f"natural lighting, neutral background, 3 seconds",
        )

        if st.button("Generate Video", type="primary"):
            st.info("Video generation would be triggered here. "
                    "See `apps/web/luma_client.py` for the implementation.")

st.markdown("---")
st.caption("Simulated data is suitable for pipeline testing only. "
           "Use real face data for production training.")
```

---

## Checklist

- [ ] `apps/web/pages/01_Generate.py` replaced with functional page
- [ ] Simulated data tab generates images correctly
- [ ] Luma AI tab shows API key status
- [ ] Page loads without errors
