# API Endpoint Reference - Complete Guide

**Version**: 0.09.0  
**Last Updated**: 2026-02-18  
**Base URL**: `http://localhost:8083`

---

## Table of Contents

1. [V1 API Endpoints](#v1-api-endpoints) (Production)
2. [Legacy Endpoints](#legacy-endpoints) (Deprecated)
3. [Gateway Endpoints](#gateway-endpoints) (External Service)
4. [Nginx Static Endpoints](#nginx-static-endpoints)
5. [Quick Reference](#quick-reference)

---

## V1 API Endpoints

**Base Path**: `/api/v1/`  
**Status**: Production Ready ✅  
**Response Format**: Standardized envelope with `status`, `data`, `meta`

### Health & Monitoring

#### GET `/api/v1/health`
**Purpose**: Health check for monitoring and load balancers  
**Authentication**: None  
**Response Format**: Standardized envelope

**Response**:
```json
{
  "status": "success",
  "data": {
    "service": "media-mover",
    "version": "0.08.4.3",
    "status": "healthy",
    "checks": {
      "videos_root": {
        "status": "ok",
        "path": "/media/rusty_admin/project_data/reachy_emotion/videos"
      },
      "directories": {
        "status": "ok",
        "accessible": 6,
        "total": 6
      }
    }
  },
  "meta": {
    "correlation_id": "uuid-here",
    "timestamp": "2025-11-14T19:56:00Z",
    "version": "v1"
  }
}
```

**Use Cases**:
- Kubernetes liveness probes
- Load balancer health checks
- Monitoring dashboards
- Service discovery

**Related Services**: None (standalone)

---

#### GET `/api/v1/ready`
**Purpose**: Readiness check for orchestration systems  
**Authentication**: None  
**Response Format**: Same as health check

**Difference from Health**: More strict - returns 503 if service is not fully ready to accept traffic

**Use Cases**:
- Kubernetes readiness probes
- Rolling deployments
- Traffic routing decisions

**Related Services**: None (standalone)

---

### Media Management

#### GET `/api/v1/media/list`
**Purpose**: List videos from a specific split with pagination  
**Authentication**: Optional (Bearer token via `REACHY_API_TOKEN`)  
**Response Format**: Standardized envelope with pagination

**Query Parameters**:
- `split` (required): Video split - `temp`, `dataset_all`, `train`, or `test`
- `limit` (optional): Maximum items to return (1-1000, default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Request**:
```bash
GET /api/v1/media/list?split=temp&limit=10&offset=0
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "video_id": "video1",
        "file_path": "temp/video1.mp4",
        "size_bytes": 1048576,
        "mtime": 1699999999.123,
        "split": "temp"
      }
    ],
    "pagination": {
      "total": 42,
      "limit": 10,
      "offset": 0,
      "has_more": true
    }
  },
  "meta": {
    "correlation_id": "uuid-here",
    "timestamp": "2025-11-14T19:56:00Z",
    "version": "v1"
  }
}
```

**Use Cases**:
- Video gallery display
- Dataset management
- Training data selection
- Video browser

**Related Services**:
- Nginx (serves actual video files)
- PostgreSQL (metadata storage)

---

#### GET `/api/v1/media/{video_id}`
**Purpose**: Get metadata for a specific video  
**Authentication**: Optional  
**Response Format**: Standardized envelope

**Path Parameters**:
- `video_id` (required): Video identifier (filename without extension)

**Request**:
```bash
GET /api/v1/media/video_temp1
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "video_id": "video_temp1",
    "file_path": "temp/video_temp1.mp4",
    "size_bytes": 2097152,
    "mtime": 1699999999.456,
    "split": "temp"
  },
  "meta": {
    "correlation_id": "uuid-here",
    "timestamp": "2025-11-14T19:56:00Z",
    "version": "v1"
  }
}
```

**Error Response (404)**:
```json
{
  "detail": {
    "error": "not_found",
    "message": "Video not found: video_temp1"
  }
}
```

**Use Cases**:
- Video detail page
- Metadata verification
- File existence check

**Related Services**: Filesystem

---

#### GET `/api/v1/media/{video_id}/thumb`
**Purpose**: Get thumbnail URL for a video  
**Authentication**: Optional  
**Response Format**: Standardized envelope

**Path Parameters**:
- `video_id` (required): Video identifier

**Request**:
```bash
GET /api/v1/media/video_temp1/thumb
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "video_id": "video_temp1",
    "thumbnail_url": "http://localhost:8082/thumbs/video_temp1.jpg"
  },
  "meta": {
    "correlation_id": "uuid-here",
    "timestamp": "2025-11-14T19:56:00Z",
    "version": "v1"
  }
}
```

**Use Cases**:
- Video gallery thumbnails
- Preview generation
- UI display

**Related Services**: Nginx (serves thumbnail files)

---

### Video Promotion

#### POST `/api/media/promote` (Current)
**Purpose**: Promote clips from `temp` to `train/<label>` or `test` (current runtime flow)  
**Authentication**: Optional/Environment-dependent  
**Response Format**: JSON status payload

**Headers**:
- `Content-Type`: `application/json`
- `Idempotency-Key` (recommended from gateway clients)

**Request Body**:
```json
{
  "video_id": "<video-uuid>",
  "dest_split": "train",
  "label": "happy",
  "dry_run": false,
  "correlation_id": "<uuid>"
}
```

**Parameters**:
- `video_id` (required): UUID for the clip record.
- `dest_split` (required): `train` or `test`.
- `label` (required when `dest_split=train`): must be one of `happy`, `sad`, `neutral`.
- `dry_run` (optional): validate path + payload without mutating files/DB.
- `correlation_id` (optional): trace ID for logs and troubleshooting.

**Behavior Notes**:
- Train promotion writes files to `train/<label>/...`.
- Test promotion clears label (`label = null`) in DB policy flow.
- Endpoint supports adapter input from gateway payload shape.

---

#### POST `/api/v1/promote/stage`
**Purpose**: Deprecated compatibility endpoint (legacy stage flow)  
**Status**: Deprecated compatibility only ⚠️  
**Authentication**: Optional  
**Response Format**: Legacy compatibility model (or validation error)

**Headers**:
- `X-Correlation-ID` (optional): Request tracking ID
- `Content-Type`: `application/json`

**Request Body**:
```json
{
  "video_ids": ["video1", "video2", "video3"],
  "label": "happy",
  "dry_run": false
}
```

**Parameters**:
- `video_ids` (required): List of video IDs to stage
- `label` (required): Emotion label - `happy`, `sad`, `neutral`
- `dry_run` (optional): If true, validate without executing (default: false)

**Current Runtime Behavior**:
- Returns deprecation warning header.
- Service rejects this operation and instructs clients to use `/api/media/promote` with `dest_split='train'`.

**Legacy Response Shape** (for older clients):
```json
{
  "promoted_ids": ["video1", "video2"],
  "skipped_ids": ["video3"],
  "failed_ids": [],
  "label": "happy",
  "dry_run": false
}
```

**Use Cases**:
- Backward compatibility for old integrations only

**Related Services**:
- PostgreSQL (metadata persistence)
- Filesystem (file operations)

---

#### POST `/api/v1/promote/sample`
**Purpose**: Deprecated compatibility endpoint (legacy sampling flow)  
**Status**: Deprecated compatibility only ⚠️  
**Authentication**: Optional  
**Response Format**: Legacy compatibility model (or validation error)

**Request Body**:
```json
{
  "run_id": "<run-uuid>",
  "target_split": "train",
  "sample_fraction": 0.8,
  "strategy": "balanced_random",
  "dry_run": false
}
```

**Parameters**:
- `run_id` (required): Training run UUID
- `target_split` (required): `train` or `test`
- `sample_fraction` (required): Fraction > 0
- `strategy` (optional): `balanced_random`
- `seed` (optional): deterministic integer seed
- `dry_run` (optional): Validate without executing (default: false)

**Current Runtime Behavior**:
- Returns deprecation warning header.
- Service rejects this operation and instructs clients to use run-scoped frame dataset preparation.

**Legacy Response Shape** (for older clients):
```json
{
  "run_id": "<run-uuid>",
  "target_split": "train",
  "copied_ids": ["video1", "video2"],
  "skipped_ids": [],
  "failed_ids": [],
  "dry_run": false
}
```

**Use Cases**:
- Backward compatibility for old integrations only

**Related Services**:
- PostgreSQL (metadata and sampling logic)
- Filesystem (file operations)

---

#### POST `/api/v1/promote/reset-manifest`
**Purpose**: Reset promotion manifest and optionally revert videos  
**Authentication**: Optional  
**Response Format**: Standardized envelope

**Request Body**:
```json
{
  "revert_videos": false,
  "reason": "Manual reset for testing"
}
```

**Parameters**:
- `revert_videos` (optional): If true, move videos back to temp (default: false)
- `reason` (optional): Reason for reset (logged)

**Response**:
```json
{
  "reset": true,
  "reverted_count": 0,
  "reason": "Manual reset for testing"
}
```

**Use Cases**:
- Dataset reset
- Testing workflows
- Error recovery

**Related Services**:
- PostgreSQL (manifest management)
- Filesystem (if reverting videos)

---

## Legacy Endpoints

**Status**: Deprecated ⚠️  
**Removal Date**: Planned for v0.09.x  
**Response Format**: Old format (unwrapped) for backward compatibility

All legacy endpoints include deprecation headers:
```
X-API-Deprecated: true
X-API-Deprecation-Message: This endpoint is deprecated...
X-API-Sunset: 2026-01-01
```

### Legacy Media Endpoints

#### GET `/api/videos/list`
**Purpose**: Legacy video listing endpoint  
**Status**: Deprecated - Use `/api/v1/media/list` instead  
**Response Format**: Old format (unwrapped)

**Query Parameters**: Same as v1 endpoint

**Response** (Old Format):
```json
{
  "items": [...],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

**Migration**: Update to `/api/v1/media/list` and parse new response format

---

#### GET `/api/media/videos/list`
**Purpose**: Alternative legacy listing endpoint  
**Status**: Deprecated - Use `/api/v1/media/list` instead  
**Response Format**: Old format (unwrapped)

Same as `/api/videos/list` - provided for compatibility with different client versions

---

#### POST `/api/media/promote`
**Purpose**: Legacy promotion endpoint (stub)  
**Status**: Deprecated - Use `/api/v1/promote/stage` instead  
**Response Format**: Deprecation message

**Response**:
```json
{
  "error": "deprecated",
  "message": "Use /api/v1/promote/stage instead"
}
```

---

#### GET `/media/health`
**Purpose**: Legacy health check  
**Status**: Deprecated - Use `/api/v1/health` instead  
**Response Format**: Old format

**Migration**: Update to `/api/v1/health` and parse new response format

---

#### GET `/api/media`
**Purpose**: Legacy media root endpoint  
**Status**: Deprecated  
**Response Format**: Deprecation message

---

## Gateway Endpoints

**Base URL**: `http://localhost:8000`  
**Service**: Gateway API (separate service)  
**Purpose**: External integrations and workflows

### Media Ingestion

#### POST `/api/media/ingest`
**Purpose**: Upload video for processing  
**Authentication**: Required (Bearer token)

**Request** (multipart/form-data):
```
file: <video file>
for_training: "true"
correlation_id: "uuid-here"
meta[emotion]: "happy"
```

**Use Cases**:
- Video upload from web UI
- Batch ingestion
- External integrations

**Related Services**:
- Media Mover API (file storage)
- n8n (workflow orchestration)

---

### Generation Requests

#### POST `/api/gen/request`
**Purpose**: Request video generation from prompt  
**Authentication**: Required

**Request Body**:
```json
{
  "schema_version": "v1",
  "prompt": "Generate happy emotion video",
  "correlation_id": "uuid-here"
}
```

**Use Cases**:
- AI video generation
- Synthetic data creation

**Related Services**:
- n8n (workflow orchestration)
- AI generation services

---

### Privacy & Redaction

#### POST `/api/privacy/redact/{video_id}`
**Purpose**: Reject/redact a video for privacy reasons  
**Authentication**: Required

**Request Body**:
```json
{
  "correlation_id": "uuid-here",
  "reason": "Privacy concern"
}
```

**Use Cases**:
- Privacy compliance
- Content moderation
- User requests

**Related Services**:
- Media Mover API (file operations)
- PostgreSQL (audit log)

---

### Promotion (Gateway)

#### POST `/api/promote`
**Purpose**: Promote video via gateway (with idempotency)  
**Authentication**: Required

**Headers**:
- `Idempotency-Key` (required): Unique key for idempotent operations

**Request Body**:
```json
{
  "video_id": "<video-uuid>",
  "dest_split": "train",
  "label": "happy",
  "dry_run": false,
  "correlation_id": "uuid-here"
}
```

**Validation Notes**:
- `Idempotency-Key` is required.
- `dest_split` supports `train` or `test`.
- For `train`, `label` must be `happy`, `sad`, or `neutral`.

**Use Cases**:
- External promotion requests
- Idempotent operations
- Gateway-mediated workflows

**Related Services**:
- Media Mover API (actual promotion)
- n8n (workflow orchestration)

---

## Nginx Static Endpoints

**Base URL**: `http://localhost:8082`  
**Service**: Nginx (static file server)  
**Purpose**: Serve video files and thumbnails

### Video Files

#### GET `/videos/{split}/{filename}`
**Purpose**: Serve video files directly  
**Authentication**: None (public)

**Example**:
```
GET http://localhost:8082/videos/temp/video1.mp4
```

**Use Cases**:
- Video playback
- Direct file access
- Streaming

**Related Services**: Filesystem

---

### Thumbnails

#### GET `/thumbs/{video_id}.jpg`
**Purpose**: Serve thumbnail images  
**Authentication**: None (public)

**Example**:
```
GET http://localhost:8082/thumbs/video1.jpg
```

**Use Cases**:
- Gallery display
- Preview images
- UI thumbnails

**Related Services**: Filesystem

---

## Quick Reference

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Media Mover API | 8083 | Main API service |
| Nginx | 8082 | Static file serving |
| Gateway API | 8000 | External integrations |
| PostgreSQL | 5432 | Database |
| n8n | 5678 | Workflow automation |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `REACHY_API_BASE` | `http://localhost:8083` | Media Mover API URL |
| `REACHY_GATEWAY_BASE` | `http://localhost:8000` | Gateway API URL |
| `REACHY_VIDEOS_ROOT` | `/media/.../videos` | Video storage path |
| `REACHY_API_PORT` | `8083` | API service port |
| `REACHY_ENABLE_LEGACY_ENDPOINTS` | `true` | Enable deprecated endpoints |

### Response Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Request completed successfully |
| 404 | Not Found | Video or resource doesn't exist |
| 422 | Validation Error | Invalid parameters |
| 500 | Server Error | Internal server error |
| 503 | Service Unavailable | Service not ready (readiness check) |

### Common Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `X-Correlation-ID` | Request tracking | `uuid-here` |
| `X-API-Version` | API version preference | `v1` |
| `Authorization` | Authentication | `Bearer <token>` |
| `Idempotency-Key` | Idempotent operations | `unique-key` |
| `X-API-Deprecated` | Deprecation warning | `true` |

---

## API Usage Examples

### Python Client

```python
from apps.web import api_client

# List videos
videos = api_client.list_videos("temp", limit=10, offset=0)
print(f"Found {videos['total']} videos")

# Get video metadata
metadata = api_client.get_video_metadata("video1")

# Stage videos
result = api_client.stage_to_dataset_all(
    video_ids=["video1", "video2"],
    label="happy",
    dry_run=False
)
```

### cURL Examples

```bash
# Health check
curl http://localhost:8083/api/v1/health

# List videos
curl "http://localhost:8083/api/v1/media/list?split=temp&limit=10&offset=0"

# Get video metadata
curl http://localhost:8083/api/v1/media/video1

# Get thumbnail URL
curl http://localhost:8083/api/v1/media/video1/thumb

# Promote a labeled clip directly to train
curl -X POST http://localhost:8083/api/media/promote \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-123" \
  -d '{
    "video_id": "11111111-1111-4111-8111-111111111111",
    "dest_split": "train",
    "label": "happy",
    "dry_run": false
  }'
```

### JavaScript/Fetch

```javascript
// List videos
const response = await fetch(
  'http://localhost:8083/api/v1/media/list?split=temp&limit=10&offset=0',
  {
    headers: {
      'X-API-Version': 'v1',
      'X-Correlation-ID': crypto.randomUUID()
    }
  }
);
const body = await response.json();
const videos = body.data.items;

// Promote directly to train
const promoteResponse = await fetch(
  'http://localhost:8083/api/media/promote',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-ID': crypto.randomUUID()
    },
    body: JSON.stringify({
      video_id: '11111111-1111-4111-8111-111111111111',
      dest_split: 'train',
      label: 'happy',
      dry_run: false
    })
  }
);
```

---

## Service Dependencies

### Media Mover API Dependencies

```
Media Mover API (8083)
├── Filesystem (video storage)
├── Nginx (8082) - static file serving
└── PostgreSQL (5432) - metadata (optional for basic operations)
```

### Gateway API Dependencies

```
Gateway API (8000)
├── Media Mover API (8083)
├── n8n (5678) - workflow orchestration
├── PostgreSQL (5432) - state management
└── External AI services
```

---

## Migration Guide

### From Legacy to V1

**Step 1**: Update endpoint URLs
```python
# Old
response = requests.get("http://localhost:8083/api/videos/list?split=temp")

# New
response = requests.get("http://localhost:8083/api/v1/media/list?split=temp")
```

**Step 2**: Parse new response format
```python
# Old
videos = response.json()["items"]

# New
body = response.json()
videos = body["data"]["items"]
```

**Step 3**: Use correlation IDs
```python
headers = {"X-Correlation-ID": str(uuid.uuid4())}
response = requests.get(url, headers=headers)
```

**Step 4**: Handle pagination metadata
```python
body = response.json()
data = body["data"]
has_more = data["pagination"]["has_more"]
```

---

## Troubleshooting

### Common Issues

**Issue**: Connection refused on port 8083  
**Solution**: Check if service is running: `./scripts/service-status.sh`

**Issue**: 404 for video  
**Solution**: Verify video exists in correct split directory

**Issue**: 503 on readiness check  
**Solution**: Check health endpoint for detailed status

**Issue**: Deprecation warnings  
**Solution**: Migrate to v1 endpoints

---

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8083/docs
- **ReDoc**: http://localhost:8083/redoc
- **OpenAPI Schema**: http://localhost:8083/openapi.json

### Additional Resources

- **Architecture Analysis**: `ENDPOINT_ARCHITECTURE_ANALYSIS.md`
- **Implementation Plan**: `ENDPOINT_REWRITE_ACTION_PLAN.md`
- **Project Complete**: `ENDPOINT_REWRITE_PROJECT_COMPLETE.md`

---

**Last Updated**: 2026-02-18  
**API Version**: v1  
**Service Version**: 0.09.0  
**Status**: Production Ready ✅
