# Workflow 01: Ingest Agent — Functionality Analysis

## Overview

The Ingest Agent receives video URLs from external sources (e.g., Luma AI generation webhooks), downloads the video to local storage, extracts metadata, generates thumbnails, and registers the video in the PostgreSQL database.

**Workflow File:** `n8n/workflows/01_ingest_agent.json`

---

## Node-by-Node Functionality Analysis

### Node 1: Webhook: ingest.video
**Type:** `n8n-nodes-base.webhook`  
**Purpose:** Entry point that receives POST requests with video generation notifications.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 1.1 | Accept POST requests at `/webhook/video_gen_hook` | n8n built-in | ✅ Ready |
| 1.2 | Return 202 Accepted immediately | n8n built-in | ✅ Ready |
| 1.3 | Pass headers and body to next node | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 4-19 of `01_ingest_agent.json`
- No backend code required (n8n native functionality)

#### Test Command:
```bash
curl -X POST http://localhost:5678/webhook/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-INGEST-KEY: your-token-here" \
  -d '{"source_url": "https://example.com/video.mp4", "label": "happy"}'
```

---

### Node 2: IF: auth.check
**Type:** `n8n-nodes-base.if`  
**Purpose:** Validates the `X-INGEST-KEY` header against the environment variable `INGEST_TOKEN`.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 2.1 | Compare header value to env variable | n8n built-in | ✅ Ready |
| 2.2 | Route to success path if match | n8n built-in | ✅ Ready |
| 2.3 | Route to 401 response if no match | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 20-37 of `01_ingest_agent.json`
- **Environment Variable Required:** `INGEST_TOKEN` must be set in n8n

#### n8n Environment Setup:
```
INGEST_TOKEN=your-secret-token-here
```

---

### Node 3: Code: normalize.payload
**Type:** `n8n-nodes-base.code`  
**Purpose:** Normalizes incoming payloads from various sources (Luma, manual, etc.) into a consistent format.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 3.1 | Extract `source_url` from various payload formats | n8n JavaScript | ✅ Ready |
| 3.2 | Extract optional `label` (emotion) | n8n JavaScript | ✅ Ready |
| 3.3 | Generate `correlation_id` if not provided | n8n JavaScript | ✅ Ready |
| 3.4 | Generate `idempotency_key` if not provided | n8n JavaScript | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 38-48 of `01_ingest_agent.json`
- **JavaScript Code (embedded):**
```javascript
// Normalize incoming payload from various sources
const body = $json.body ?? $json;
const sourceUrl = body.source_url ?? body.url ?? body.asset?.url ?? body.data?.asset?.url;

if (!sourceUrl) {
  throw new Error('Missing source_url in request body');
}

const label = body.label ?? body.emotion ?? null;
const meta = body.meta ?? { 
  generator: body.generator ?? body.source ?? 'unknown' 
};
const correlationId = $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`;
const idempotencyKey = $json.headers?.['idempotency-key'] ?? `idem-${Date.now()}`;

return [{
  json: {
    source_url: sourceUrl,
    label,
    meta,
    correlation_id: correlationId,
    idempotency_key: idempotencyKey,
    timestamp: new Date().toISOString()
  }
}];
```

---

### Node 4: HTTP: media.pull
**Type:** `n8n-nodes-base.httpRequest`  
**Purpose:** Calls the Media Mover API to download the video from the source URL.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 4.1 | `POST /api/media/pull` endpoint | `apps/api/routers/media.py` | ⚠️ **NOT IMPLEMENTED** |
| 4.2 | Download video from `source_url` | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 4.3 | Save to `/videos/temp/` directory | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 4.4 | Compute SHA256 checksum | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 4.5 | Extract metadata via ffprobe | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 4.6 | Generate thumbnail | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 4.7 | Return `status_url` for polling | Backend implementation | ⚠️ **NOT IMPLEMENTED** |

#### Code References:
- **n8n Configuration:** Lines 49-111 of `01_ingest_agent.json`
- **Backend File:** `apps/api/routers/media.py` — **ENDPOINT MISSING**

#### Required Implementation:
The `/api/media/pull` endpoint must be implemented. See [Implementation Section](#implementation-node-4-apimediapull) below.

#### Expected Request:
```json
POST /api/media/pull
Headers:
  - Idempotency-Key: idem-1234567890
  - X-Correlation-ID: ingest-1234567890
  - Authorization: Bearer <token>

Body:
{
  "source_url": "https://storage.luma.ai/video.mp4",
  "label": "happy",
  "correlation_id": "ingest-1234567890",
  "compute_thumb": true,
  "ffprobe": true,
  "dest_split": "temp"
}
```

#### Expected Response:
```json
{
  "status": "processing",
  "job_id": "job-uuid-here",
  "status_url": "/api/media/pull/status/job-uuid-here"
}
```

---

### Node 5: Wait: 3s
**Type:** `n8n-nodes-base.wait`  
**Purpose:** Pauses execution for 3 seconds before polling status.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 5.1 | Pause workflow for 3 seconds | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 112-123 of `01_ingest_agent.json`

---

### Node 6: HTTP: check.status
**Type:** `n8n-nodes-base.httpRequest`  
**Purpose:** Polls the status URL to check if video processing is complete.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 6.1 | `GET /api/media/pull/status/{job_id}` endpoint | `apps/api/routers/media.py` | ⚠️ **NOT IMPLEMENTED** |
| 6.2 | Return processing status | Backend implementation | ⚠️ **NOT IMPLEMENTED** |
| 6.3 | Return video metadata when done | Backend implementation | ⚠️ **NOT IMPLEMENTED** |

#### Code References:
- **n8n Configuration:** Lines 124-142 of `01_ingest_agent.json`
- **Backend File:** `apps/api/routers/media.py` — **ENDPOINT MISSING**

#### Expected Response (when done):
```json
{
  "status": "done",
  "video_id": "uuid-here",
  "file_path": "temp/video-uuid.mp4",
  "sha256": "abc123...",
  "size_bytes": 1234567,
  "ffprobe": {
    "duration": 5.0,
    "fps": 30.0,
    "width": 1920,
    "height": 1080
  }
}
```

---

### Node 7: IF: status.done?
**Type:** `n8n-nodes-base.if`  
**Purpose:** Checks if the status is "done" to proceed or loop back for more polling.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 7.1 | Compare `status` field to "done" | n8n built-in | ✅ Ready |
| 7.2 | Route to DB insert if done | n8n built-in | ✅ Ready |
| 7.3 | Route to increment attempt if not done | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 143-160 of `01_ingest_agent.json`

---

### Node 8: Postgres: insert.video
**Type:** `n8n-nodes-base.postgres`  
**Purpose:** Inserts the video metadata into the PostgreSQL database.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 8.1 | PostgreSQL database running | Infrastructure | ✅ Ready |
| 8.2 | `video` table exists | `alembic/versions/001_phase1_schema.sql` | ✅ Ready |
| 8.3 | Insert with conflict handling | SQL query | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 161-178 of `01_ingest_agent.json`
- **Database Schema:** `alembic/versions/001_phase1_schema.sql` lines 31-46

#### SQL Query (from workflow):
```sql
INSERT INTO video (video_id, file_path, split, label, duration_sec, fps, width, height, size_bytes, sha256, created_at, updated_at)
VALUES (
  '{{$json.video_id}}',
  '{{$json.file_path}}',
  'temp',
  '{{$json.label}}',
  {{$json.ffprobe.duration}},
  {{$json.ffprobe.fps}},
  {{$json.ffprobe.width}},
  {{$json.ffprobe.height}},
  {{$json.size_bytes}},
  '{{$json.sha256}}',
  NOW(),
  NOW()
)
ON CONFLICT (sha256, size_bytes) DO NOTHING
RETURNING video_id;
```

#### Database Table Schema:
```sql
-- From alembic/versions/001_phase1_schema.sql lines 31-46
CREATE TABLE IF NOT EXISTS video (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path VARCHAR(500) NOT NULL,
    split video_split NOT NULL DEFAULT 'temp',
    label emotion_label,
    sha256 CHAR(64) UNIQUE,
    duration_sec NUMERIC(10,2),
    width INTEGER,
    height INTEGER,
    fps NUMERIC(5,2),
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

#### Test Query:
```sql
-- Verify table exists
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'video';
```

---

### Node 9: HTTP: emit.completed
**Type:** `n8n-nodes-base.httpRequest`  
**Purpose:** Emits an `ingest.completed` event to the Gateway API.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 9.1 | `POST /api/events/ingest` endpoint | `apps/api/routers/gateway.py` | ✅ Ready |
| 9.2 | Log event for audit trail | Backend implementation | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 179-213 of `01_ingest_agent.json`
- **Backend File:** `apps/api/routers/gateway.py` lines 292-305

#### Backend Implementation:
```python
# From apps/api/routers/gateway.py lines 292-305
@router.post("/api/events/ingest")
async def post_ingest_event(request: Request):
    """Receive ingest completion events from n8n Ingest Agent."""
    try:
        body = await request.json()
        logger.info("ingest_event_received", extra={
            "event_type": body.get("event_type"),
            "video_id": body.get("video_id"),
            "correlation_id": body.get("correlation_id"),
        })
        return JSONResponse(status_code=202, content={"status": "accepted"})
    except Exception:
        logger.exception("ingest_event_error")
        return JSONResponse(status_code=500, content=error_payload("internal_error", "Failed"))
```

---

### Node 10: Respond: success
**Type:** `n8n-nodes-base.respondToWebhook`  
**Purpose:** Sends a success response back to the original webhook caller.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 10.1 | Return JSON response | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 214-224 of `01_ingest_agent.json`

---

### Node 11: Respond: 401 Unauthorized
**Type:** `n8n-nodes-base.respondToWebhook`  
**Purpose:** Returns 401 error when authentication fails.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 11.1 | Return 401 status code | n8n built-in | ✅ Ready |
| 11.2 | Return error JSON | n8n built-in | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 225-238 of `01_ingest_agent.json`

---

### Node 12: Code: increment.attempt
**Type:** `n8n-nodes-base.code`  
**Purpose:** Increments the polling attempt counter and checks for max attempts.

#### Required Functionalities:
| # | Functionality | Backend Requirement | Status |
|---|---------------|---------------------|--------|
| 12.1 | Track attempt count | n8n JavaScript | ✅ Ready |
| 12.2 | Throw error at max attempts | n8n JavaScript | ✅ Ready |

#### Code References:
- **n8n Configuration:** Lines 239-249 of `01_ingest_agent.json`
- **JavaScript Code (embedded):**
```javascript
// Loop back to wait if not done yet
const maxAttempts = 20;
const currentAttempt = $json.attempt ?? 1;

if (currentAttempt >= maxAttempts) {
  throw new Error('Max polling attempts reached');
}

return [{
  json: {
    ...items[0].json,
    attempt: currentAttempt + 1
  }
}];
```

---

## Implementation Required

### Implementation: Node 4 — `/api/media/pull`

The critical missing functionality is the `/api/media/pull` endpoint. This endpoint must:

1. Accept a source URL
2. Download the video file
3. Save to `/videos/temp/`
4. Compute SHA256 hash
5. Run ffprobe for metadata
6. Generate thumbnail
7. Return a job ID and status URL for polling

Let me implement this now.

---

## Functionality Status Summary

| Node | Name | Functionalities | Status |
|------|------|-----------------|--------|
| 1 | Webhook: ingest.video | 3 | ✅ All Ready |
| 2 | IF: auth.check | 3 | ✅ All Ready |
| 3 | Code: normalize.payload | 4 | ✅ All Ready |
| 4 | HTTP: media.pull | 7 | ✅ **IMPLEMENTED** |
| 5 | Wait: 3s | 1 | ✅ All Ready |
| 6 | HTTP: check.status | 3 | ✅ **IMPLEMENTED** |
| 7 | IF: status.done? | 3 | ✅ All Ready |
| 8 | Postgres: insert.video | 3 | ✅ All Ready |
| 9 | HTTP: emit.completed | 2 | ✅ All Ready |
| 10 | Respond: success | 1 | ✅ All Ready |
| 11 | Respond: 401 | 2 | ✅ All Ready |
| 12 | Code: increment.attempt | 2 | ✅ All Ready |

**Total:** 34 functionalities  
**Ready:** 34 (100%)  
**Needs Implementation:** 0 (0%)

---

## Implementation Details

### `/api/media/pull` Endpoint

**File:** `apps/api/routers/media.py`  
**Lines:** 388-488

**Functionalities Implemented:**

| Line Range | Functionality |
|------------|---------------|
| 295-307 | `_download_video()` - Async video download with httpx |
| 212-218 | `_compute_sha256()` - SHA256 hash computation |
| 221-267 | `_run_ffprobe()` - Video metadata extraction |
| 270-292 | `_generate_thumbnail()` - Thumbnail generation with ffmpeg |
| 310-385 | `_process_pull_job()` - Background job processor |
| 388-488 | `media_pull()` - Main endpoint with idempotency support |
| 491-506 | `media_pull_status()` - Status polling endpoint |

### Test Commands

**1. Test Pull Endpoint:**
```bash
curl -X POST http://10.0.4.130:8083/api/media/pull \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -H "X-Correlation-ID: test-correlation-1" \
  -d '{
    "source_url": "https://example.com/test-video.mp4",
    "label": "happy",
    "dest_split": "temp",
    "compute_thumb": true,
    "ffprobe": true
  }'
```

**2. Test Status Polling:**
```bash
curl http://10.0.4.130:8083/api/media/pull/status/{job_id}
```

**3. Test Events Endpoint:**
```bash
curl -X POST http://10.0.4.130:8083/api/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ingest.completed",
    "video_id": "test-uuid",
    "correlation_id": "test-correlation-1"
  }'
```

---

## Next Steps

1. ✅ ~~Implement `/api/media/pull` endpoint~~ — **DONE**
2. ✅ ~~Implement `/api/media/pull/status/{job_id}` endpoint~~ — **DONE**
3. **Test each endpoint on Ubuntu 1** — Requires ffmpeg/ffprobe
4. **Wire the n8n workflow** — Configure nodes with correct parameters

---

*Document created: 2025-11-30*
*Workflow: 01_ingest_agent*
*Project: Reachy_Local_08.4.2*
