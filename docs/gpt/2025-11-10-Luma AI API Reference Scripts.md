# VIDEO GENERATION using Luma API Scripts

## Authentication

Get a key from [Luma Labs API Keys](https://lumalabs.ai/dream-machine/api/keys).  
Use the key as a Bearer token to call any of the API endpoints.

```
Authorization: Bearer <luma_api_key>
```

---

## Models

| Name | Model Param |
|------|--------------|
| Ray 2 Flash | `ray-flash-2` |
| Ray 2 | `ray-2` |
| Ray 1.6 | `ray-1-6` |

---

## API Reference

### Ray 2 Text to Video

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "an old lady laughing underwater, wearing a scuba diving suit",
  "model": "ray-2",
  "resolution": "720p",
  "duration": "5s"
}
'
```

**Resolution options:** 540p, 720p, 1080p, 4k

---

### Ray 2 Image to Video

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "A tiger walking in snow",
  "model": "ray-2",
  "keyframes": {
    "frame0": {
      "type": "image",
      "url": "https://storage.cdn-luma.com/dream_machine/7e4fe07f-1dfd-4921-bc97-4bcf5adea39a/video_0_thumb.jpg"
    }
  }
}
'
```

---

## Using Concepts

To apply visual or motion concepts:

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "a car",
  "model": "ray-2",
  "resolution": "720p",
  "duration": "5s",
  "concepts": [
  	{"key": "dolly_zoom"}
  ]
}
'
```

List available concepts:
```
GET https://api.lumalabs.ai/dream-machine/v1/generations/concepts/list
```

---

### Text to Video (Basic)

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "an old lady laughing underwater, wearing a scuba diving suit",
  "model": "ray-2"
}
'
```

---

## Downloading a Video

```bash
curl -o video.mp4 https://example.com/video.mp4
```

---

## With Loop and Aspect Ratio

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "an old lady laughing underwater, wearing a scuba diving suit",
  "model": "ray-2",
  "aspect_ratio": "16:9",
  "loop": true
}
'
```

---

## Image to Video (Advanced)

You must host your own image on a CDN and use the URL in the request.

### With Start Frame

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "A tiger walking in snow",
  "model": "ray-2",
  "keyframes": {
    "frame0": {
      "type": "image",
      "url": "https://storage.cdn-luma.com/dream_machine/7e4fe07f-1dfd-4921-bc97-4bcf5adea39a/video_0_thumb.jpg"
    }
  }
}
'
```

### With Start Frame, Loop, Aspect Ratio

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "A tiger walking in snow",
  "model": "ray-2",
  "keyframes": {
    "frame0": {
      "type": "image",
      "url": "https://storage.cdn-luma.com/dream_machine/7e4fe07f-1dfd-4921-bc97-4bcf5adea39a/video_0_thumb.jpg"
    }
  },
  "loop": false,
  "aspect_ratio": "16:9"
}
'
```

---

### With Ending Frame

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "A tiger walking in snow",
  "model": "ray-2",
  "keyframes": {
    "frame1": {
      "type": "image",
      "url": "https://storage.cdn-luma.com/dream_machine/7e4fe07f-1dfd-4921-bc97-4bcf5adea39a/video_0_thumb.jpg"
    }
  },
  "loop": false,
  "aspect_ratio": "16:9"
}
'
```

---

## Extend or Interpolate Videos

> Supported only for completed generations.

### Extend

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "The tiger rolls around",
  "model": "ray-2",
  "keyframes": {
    "frame0": {
      "type": "generation",
      "id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }
}
'
```

### Reverse Extend

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "The tiger rolls around",
  "model": "ray-2",
  "keyframes": {
    "frame1": {
      "type": "generation",
      "id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }
}
'
```

### Interpolate Between Two Videos

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "The tiger rolls around",
  "model": "ray-2",
  "keyframes": {
    "frame0": {"type": "generation", "id": "123e4567-e89b-12d3-a456-426614174000"},
    "frame1": {"type": "generation", "id": "123e4567-e89b-12d3-a456-426614174000"}
  }
}
'
```

---

## Manage Generations

### Get Generation by ID
```bash
curl --request GET      --url https://api.lumalabs.ai/dream-machine/v1/generations/123e4567-e89b-12d3-a456-426614174000      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'
```

### List All Generations
```bash
curl --request GET      --url 'https://api.lumalabs.ai/dream-machine/v1/generations?limit=10&offset=10'      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'
```

### Delete Generation
```bash
curl --request DELETE      --url https://api.lumalabs.ai/dream-machine/v1/generations/123e4567-e89b-12d3-a456-426614174000      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'
```

---

## Camera Motions

### Get All Supported Motions

```bash
curl --request GET      --url https://api.lumalabs.ai/dream-machine/v1/generations/camera_motion/list      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'
```

You can add camera motion strings (e.g. `"camera orbit left"`) directly in the prompt.

---

## Callback for Generation Updates

Luma can send status updates (`dreaming`, `completed`, `failed`) and final video URLs to your callback endpoint.

The callback URL must:
- Return HTTP 200 OK.
- Handle retries (up to 3 attempts, 100 ms delay).
- Respond within 5 seconds.

Example:

```bash
curl --request POST      --url https://api.lumalabs.ai/dream-machine/v1/generations      --header 'accept: application/json'      --header 'authorization: Bearer luma-xxxx'      --header 'content-type: application/json'      --data '
{
  "prompt": "an old lady laughing underwater, wearing a scuba diving suit",
  "callback_url": "<your_api_endpoint_here>"
}
'
```
