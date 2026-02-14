# Luma Python SDK — Dream Machine API Guide

## Overview
With the Dream Machine Python SDK, you can generate images and videos. Both processes work similarly: you create a request, which returns an ID, and you can poll for completion to retrieve the result.

---

## Installation

```bash
pip install lumaai
```
[PyPI Project Page](https://pypi.org/project/lumaai/)

---

## Authentication

1. Get your API key from [https://lumalabs.ai/dream-machine/api/keys](https://lumalabs.ai/dream-machine/api/keys)
2. Provide it to the client SDK by either:
   - Setting the environment variable `LUMAAI_API_KEY`
   - Passing the key directly using `auth_token` when creating the client

---

## Models

| Name | Model Param |
|------|--------------|
| Ray 2 Flash | `ray-flash-2` |
| Ray 2 | `ray-2` |
| Ray 1.6 | `ray-1-6` |

---

## Setting Up the Client

### Using Environment Variable
```python
from lumaai import LumaAI

client = LumaAI()
```

### Using `auth_token` Parameter
```python
import os
from lumaai import LumaAI

client = LumaAI(auth_token=os.environ.get("LUMAAI_API_KEY"))
```

---

## Getting the Video for a Generation

Currently, the only supported way is via polling.  
The `create` endpoint returns a UUIDv4 ID, which can be used to poll for updates. The video URL is available at `generation.assets.video` once completed.

### Example
```python
import requests
import time
from lumaai import LumaAI

client = LumaAI()

generation = client.generations.create(
    prompt="A teddy bear in sunglasses playing electric guitar and dancing",
)

while True:
    generation = client.generations.get(id=generation.id)
    if generation.state == "completed":
        break
    elif generation.state == "failed":
        raise RuntimeError(f"Generation failed: {generation.failure_reason}")
    print("Dreaming...")
    time.sleep(3)

video_url = generation.assets.video
response = requests.get(video_url, stream=True)
with open(f"{generation.id}.mp4", "wb") as file:
    file.write(response.content)

print(f"File downloaded as {generation.id}.mp4")
```

---

## Async Library

### Using `AsyncLumaAI`
```python
import os
from lumaai import AsyncLumaAI

client = AsyncLumaAI(auth_token=os.environ.get("LUMAAI_API_KEY"))
```

### Example (Async)
```python
generation = await client.generations.create(
    prompt="A teddy bear in sunglasses playing electric guitar and dancing",
    model="ray-2"
)
```

---

## Ray 2 — Text to Video
```python
generation = client.generations.create(
    prompt="A teddy bear in sunglasses playing electric guitar and dancing",
    model="ray-2",
    resolution="720p",
    duration="5s"
)
```
**Supported resolutions:** 540p, 720p, 1080p, 4k

---

## Ray 2 — Image to Video
```python
generation = client.generations.create(
    prompt="Low-angle shot of a majestic tiger prowling through a snowy landscape",
    model="ray-2",
    keyframes={
        "frame0": {
            "type": "image",
            "url": "https://storage.cdn-luma.com/dream_machine/sample_image.jpg"
        }
    }
)
```

---

## Using Concepts
```python
generation = client.generations.create(
    prompt="A car",
    model="ray-2",
    resolution="720p",
    duration="5s",
    concepts=[{"key": "handheld"}]
)
```

Retrieve all available concepts:  
`https://api.lumalabs.ai/dream-machine/v1/generations/concepts/list`

---

## Downloading a Video
```python
import requests

url = "https://example.com/video.mp4"
response = requests.get(url, stream=True)

with open("video.mp4", "wb") as file:
    file.write(response.content)

print("File downloaded as video.mp4")
```

---

## Advanced Options

### Loop and Aspect Ratio
```python
generation = client.generations.create(
    prompt="A teddy bear in sunglasses playing electric guitar and dancing",
    model="ray-2",
    loop=True,
    aspect_ratio="3:4"
)
```

### Keyframes and Extensions
The SDK supports **start**, **end**, and **interpolated** keyframes using images or previously generated videos.

Examples include extending, reversing, and interpolating between videos.  
Each operation references a completed generation by ID.

---

## Generations Management

```python
generation = client.generations.get(id="d1968551-6113-4b46-b567-09210c2e79b0")
generation_list = client.generations.list(limit=100, offset=0)
client.generations.delete(id="d1968551-6113-4b46-b567-09210c2e79b0")
```

---

## Camera Motions

You can control the virtual camera via language in the prompt.

```python
supported_camera_motions = client.generations.camera_motion.list()
```

Use returned motion strings (e.g., `"camera orbit left"`) directly in prompts.

---

## Callbacks for Generation Updates

To receive automatic updates:
- Provide a POST endpoint (`callback_url`) during generation.
- Your endpoint will receive multiple POST requests with the generation object as JSON.
- Retries (up to 3 times) are performed if the endpoint does not return `HTTP 200`.

### Example
```python
generation = await client.generations.create(
    prompt="A teddy bear in sunglasses playing electric guitar and dancing",
    callback_url="<your_api_endpoint_here>"
)
```

---

## References

- [Luma API Docs](https://docs.lumalabs.ai/docs/api)
- [Python SDK Docs](https://docs.lumalabs.ai/docs/python)
- [Dream Machine Overview](https://lumalabs.ai/dream-machine)
