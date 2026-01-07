# Agent 1 — Ingest Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Ingest Agent receives new videos (uploads or generated) and registers them in the system. It computes SHA256 checksums, stores videos in `/videos/temp/`, extracts metadata via FFprobe, generates thumbnails, and emits `ingest.completed` events.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: increment.attempt | n8n-nodes-base.code | increment_attempt |
| Code: normalize.payload | n8n-nodes-base.code | normalize_payload |
| HTTP: check.status | n8n-nodes-base.httpRequest | check_status |
| HTTP: emit.completed | n8n-nodes-base.httpRequest | emit_event |
| HTTP: media.pull | n8n-nodes-base.httpRequest | media_pull |
| IF: auth.check | n8n-nodes-base.if | auth_check |
| IF: status.done? | n8n-nodes-base.if | is_done |
| Postgres: insert.video | n8n-nodes-base.postgres | db_insert |
| Respond: 401 Unauthorized | n8n-nodes-base.respondToWebhook | respond_401 |
| Respond: success | n8n-nodes-base.respondToWebhook | respond_success |
| Wait: 3s | n8n-nodes-base.wait | wait_poll |
| Webhook: ingest.video | n8n-nodes-base.webhook | webhook_trigger |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: ingest.video
    │
    ▼
IF: auth.check ─────────────────► Respond: 401 Unauthorized (False branch)
    │ (True branch)
    ▼
Code: normalize.payload
    │
    ▼
HTTP: media.pull
    │
    ▼
Wait: 3s ◄──────────────────────┐
    │                           │
    ▼                           │
HTTP: check.status              │
    │                           │
    ▼                           │
IF: status.done? ───────────────┤ (False branch)
    │ (True branch)             │
    ▼                           │
Postgres: insert.video          │
    │                           │
    ▼                           │
HTTP: emit.completed            │
    │                           │
    ▼                           │
Respond: success                │
                                │
Code: increment.attempt ────────┘
```

---

## Node Details

### 1. Webhook: ingest.video

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-400, 300]  
**Purpose:** Entry point for the workflow. Receives POST requests with video generation data from external sources (e.g., Luma, Runway).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests only |
| `path` | `video_gen_hook` | URL path: `{N8N_HOST}/webhook/video_gen_hook` |
| `responseMode` | `onReceived` | Respond immediately, process async |
| `options.responseCode` | `202` | Return HTTP 202 Accepted |
| `webhookId` | `ingest-video-hook` | Unique webhook identifier |

#### Input Schema (Expected Request Body)

```json
{
  "source_url": "https://...",    // Required: URL to download video from
  "label": "happy|sad",           // Optional: emotion label
  "generator": "luma|runway",     // Optional: video generator source
  "meta": {}                      // Optional: additional metadata
}
```

#### Headers Expected

| Header | Purpose |
|--------|---------|
| `X-INGEST-KEY` | Authentication token (compared against `$env.INGEST_TOKEN`) |
| `X-Correlation-ID` | Optional tracing ID |
| `Idempotency-Key` | Optional deduplication key |

#### Related Code

- **No direct code mapping** — n8n native webhook functionality
- **Environment Variable:** `INGEST_TOKEN` (defined in `requirements.md` §7.1)

#### Test Status: ✅ OPERATIONAL

---

### 2. IF: auth.check

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [-200, 300]  
**Purpose:** Validates the `X-INGEST-KEY` header against the configured `INGEST_TOKEN` environment variable.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.string[0].value1` | `={{$json.headers['x-ingest-key']}}` | Extract header from request |
| `conditions.string[0].operation` | `equals` | Exact match comparison |
| `conditions.string[0].value2` | `={{$env.INGEST_TOKEN}}` | Compare against env var |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True (index 0) | Header matches token | Code: normalize.payload |
| False (index 1) | Header missing/invalid | Respond: 401 Unauthorized |

#### Related Code

- **No direct code mapping** — n8n expression evaluation
- **Environment Variable:** `INGEST_TOKEN`

#### Test Status: ✅ OPERATIONAL

---

### 3. Respond: 401 Unauthorized

**Type:** `n8n-nodes-base.respondToWebhook` (v1)  
**Position:** [-200, 400]  
**Purpose:** Returns HTTP 401 when authentication fails.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `respondWith` | `json` | JSON response body |
| `responseBody` | `={{ {"error": "unauthorized", "message": "Invalid or missing X-INGEST-KEY header"} }}` | Error details |
| `options.responseCode` | `401` | HTTP 401 Unauthorized |

#### Related Code

- **No direct code mapping** — n8n native response

#### Test Status: ✅ OPERATIONAL

---

### 4. Code: normalize.payload

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [0, 200]  
**Purpose:** Normalizes incoming payloads from various video generation sources into a consistent format.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `mode` | `runOnceForAllItems` | Process all items in single execution |

#### JavaScript Code

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

return [
  {
    json: {
      source_url: sourceUrl,
      label,
      meta,
      correlation_id: correlationId,
      idempotency_key: idempotencyKey,
      timestamp: new Date().toISOString()
    }
  }
];
```

#### Output Schema

```json
{
  "source_url": "string",
  "label": "string|null",
  "meta": { "generator": "string" },
  "correlation_id": "string",
  "idempotency_key": "string",
  "timestamp": "ISO8601 string"
}
```

#### Related Code

- **Similar logic in:** `apps/api/app/routers/ingest.py` lines 252-398 (`pull_video` endpoint)
- **Pydantic model:** `PullVideoRequest` (lines 39-45)

#### Test Status: ✅ OPERATIONAL

---

### 5. HTTP: media.pull

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [200, 200]  
**Purpose:** Initiates async video download via Media Mover API.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull` | Media Mover pull endpoint |
| `authentication` | `genericCredentialType` | Use credential store |
| `genericAuthType` | `httpHeaderAuth` | Header-based auth |
| `sendHeaders` | `true` | Include custom headers |
| `sendBody` | `true` | Include request body |
| `options.timeout` | `120000` | 2 minute timeout |

#### Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` | Deduplication |
| `X-Correlation-ID` | `={{$json.correlation_id}}` | Request tracing |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `source_url` | `={{$json.source_url}}` | Video URL to download |
| `label` | `={{$json.label}}` | Optional emotion label |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |
| `compute_thumb` | `true` | Generate thumbnail |
| `ffprobe` | `true` | Extract video metadata |
| `dest_split` | `temp` | Store in temp directory |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/media.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `media_pull()` | 388-488 | POST `/api/media/pull` endpoint |
| `_process_pull_job()` | 310-385 | Background job processor |
| `_download_video()` | 295-307 | HTTP download helper |
| `_compute_sha256()` | 212-218 | Hash computation |
| `_run_ffprobe()` | 221-267 | Metadata extraction |
| `_generate_thumbnail()` | 270-292 | Thumbnail generation |

**File:** `apps/api/app/routers/ingest.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `pull_video()` | 252-413 | POST `/api/v1/ingest/pull` (alternative endpoint) |
| `download_video()` | 94-99 | Async download helper |
| `compute_sha256()` | 102-104 | Hash computation |
| `ffprobe_metadata()` | 107-180 | Async FFprobe wrapper |
| `generate_thumbnail()` | 183-223 | Async thumbnail generation |

#### Expected Response

```json
{
  "status": "pending",
  "job_id": "uuid",
  "status_url": "/api/media/pull/status/{job_id}"
}
```

#### Test Status: ✅ OPERATIONAL

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/media/pull \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"source_url": "https://example.com/video.mp4", "dest_split": "temp"}'
```

---

### 6. Wait: 3s

**Type:** `n8n-nodes-base.wait` (v1.1)  
**Position:** [400, 200]  
**Purpose:** Polling delay before checking job status.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `amount` | `3` | Wait duration |
| `unit` | `seconds` | Time unit |
| `webhookId` | `ingest-wait` | Unique identifier |

#### Related Code

- **No direct code mapping** — n8n native wait functionality

#### Test Status: ✅ OPERATIONAL

---

### 7. HTTP: check.status

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [600, 200]  
**Purpose:** Polls the Media Mover status endpoint to check if video processing is complete.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$json.status_url}}` | Dynamic status URL from media.pull response |
| `authentication` | `genericCredentialType` | Use credential store |
| `genericAuthType` | `httpHeaderAuth` | Header-based auth |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/media.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `media_pull_status()` | 491-506 | GET `/api/media/pull/status/{job_id}` |

#### Expected Response (Complete)

```json
{
  "status": "done",
  "video_id": "uuid",
  "file_path": "temp/uuid.mp4",
  "sha256": "hex string",
  "size_bytes": 12345,
  "ffprobe": {
    "duration": 5.0,
    "fps": 30.0,
    "width": 1920,
    "height": 1080
  },
  "thumb_path": "thumbs/uuid.jpg",
  "label": "happy|sad|null"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 8. IF: status.done?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [800, 200]  
**Purpose:** Checks if the video processing job has completed.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.string[0].value1` | `={{$json.status}}` | Job status field |
| `conditions.string[0].operation` | `equals` | Exact match |
| `conditions.string[0].value2` | `done` | Expected completion status |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True (index 0) | `status === "done"` | Postgres: insert.video |
| False (index 1) | `status !== "done"` | Code: increment.attempt |

#### Related Code

- **No direct code mapping** — n8n expression evaluation

#### Test Status: ✅ OPERATIONAL

---

### 9. Code: increment.attempt

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [800, 400]  
**Purpose:** Implements polling retry logic with max attempt limit.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `mode` | `runOnceForAllItems` | Process all items |

#### JavaScript Code

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

#### Behavior

- **Max Attempts:** 20 (with 3s wait = 60s max polling time)
- **On Max Reached:** Throws error, workflow fails
- **Output:** Loops back to Wait: 3s node

#### Related Code

- **No direct code mapping** — n8n workflow logic

#### Test Status: ✅ OPERATIONAL

---

### 10. Postgres: insert.video

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [1000, 100]  
**Purpose:** Inserts video metadata into the PostgreSQL database.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `executeQuery` | Run raw SQL |

#### SQL Query

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

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `Video` | 33-78 | SQLAlchemy model for video table |

**Database Schema (from models.py):**

| Column | Type | Constraints |
|--------|------|-------------|
| `video_id` | `String(36)` | Primary Key |
| `file_path` | `String(1024)` | NOT NULL |
| `split` | `SplitEnum` | NOT NULL, default='temp' |
| `label` | `EmotionEnum` | NULLABLE |
| `duration_sec` | `Float` | NULLABLE |
| `fps` | `Float` | NULLABLE |
| `width` | `Integer` | NULLABLE |
| `height` | `Integer` | NULLABLE |
| `size_bytes` | `BigInteger` | NOT NULL |
| `sha256` | `String(64)` | NOT NULL |
| `created_at` | `DateTime` | Auto-generated |
| `updated_at` | `DateTime` | Auto-generated |

**Constraints:**
- `uq_video_sha256_size`: Unique constraint on (sha256, size_bytes)
- `chk_video_split_label_policy`: Check constraint for split/label rules

#### Test Status: ✅ OPERATIONAL

**Test Command:**
```sql
-- Verify table structure
\d video

-- Test insert (dry run)
EXPLAIN INSERT INTO video (video_id, file_path, split, size_bytes, sha256)
VALUES ('test-id', 'temp/test.mp4', 'temp', 1000, 'abc123');
```

---

### 11. HTTP: emit.completed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [1200, 100]  
**Purpose:** Emits `ingest.completed` event to the Gateway API for downstream processing.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/ingest` | Gateway events endpoint |
| `sendBody` | `true` | Include event payload |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `ingest.completed` | Event identifier |
| `video_id` | `={{$json.video_id}}` | Video UUID |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |
| `file_path` | `={{$json.file_path}}` | Relative path to video |
| `sha256` | `={{$json.sha256}}` | Video checksum |

#### Related Code

**File:** `apps/api/app/routers/gateway_upstream.py` (TBD)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/events/ingest` | **TBD** | Event ingestion endpoint not yet implemented |

#### Test Status: ⚠️ TBD

**Required Actions:**
1. Implement `/api/events/ingest` endpoint in `gateway_upstream.py`
2. Define event schema for `ingest.completed`
3. Add event logging/forwarding logic

---

### 12. Respond: success

**Type:** `n8n-nodes-base.respondToWebhook` (v1)  
**Position:** [1400, 100]  
**Purpose:** Returns success response to the original webhook caller.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `respondWith` | `json` | JSON response body |
| `responseBody` | `={{ {"status": "success", "video_id": $json.video_id, "correlation_id": $json.correlation_id} }}` | Success details |

#### Response Schema

```json
{
  "status": "success",
  "video_id": "uuid",
  "correlation_id": "string"
}
```

#### Related Code

- **No direct code mapping** — n8n native response

#### Test Status: ✅ OPERATIONAL

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `INGEST_TOKEN` | Authentication token for webhook | `secret-token-123` |
| `MEDIA_MOVER_BASE_URL` | Base URL for Media Mover API | `http://10.0.4.130:8000` |
| `GATEWAY_BASE_URL` | Base URL for Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 1 | Media Mover Auth | HTTP Header Auth | Authenticate to Media Mover API |
| 2 | PostgreSQL - reachy_local | PostgreSQL | Database connection |

---

## Workflow Settings

```json
{
  "executionOrder": "v1",
  "saveManualExecutions": true,
  "callerPolicy": "workflowsFromSameOwner",
  "errorWorkflow": "error_handler"
}
```

---

## Tags

- `agent`
- `ingest`
- `phase4`

---

## Code Testing Summary

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Media Pull API | `apps/api/routers/media.py` | 388-488 | ✅ Imports OK |
| Pull Status API | `apps/api/routers/media.py` | 491-506 | ✅ Imports OK |
| Video Model | `apps/api/app/db/models.py` | 33-78 | ✅ Imports OK |
| Ingest Router | `apps/api/app/routers/ingest.py` | 252-413 | ✅ Imports OK |
| Events Endpoint | `apps/api/app/routers/gateway_upstream.py` | TBD | ⚠️ Not implemented |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `POST /api/events/ingest` in gateway_upstream.py |
| Error Handler Workflow | MEDIUM | Create `error_handler` workflow for error notifications |
| Integration Tests | MEDIUM | Create end-to-end test for full ingest flow |

---

## Connections Summary

```json
{
  "webhook_trigger": { "main": [["auth_check"]] },
  "auth_check": { "main": [["normalize_payload"], ["respond_401"]] },
  "normalize_payload": { "main": [["media_pull"]] },
  "media_pull": { "main": [["wait_poll"]] },
  "wait_poll": { "main": [["check_status"]] },
  "check_status": { "main": [["is_done"]] },
  "is_done": { "main": [["db_insert"], ["increment_attempt"]] },
  "db_insert": { "main": [["emit_event"]] },
  "emit_event": { "main": [["respond_success"]] },
  "increment_attempt": { "main": [["wait_poll"]] }
}
```
