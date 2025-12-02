# Module 1: Ingest Agent — Your First Complete Workflow

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~4 hours  
**Prerequisites**: Completed Module 0 (n8n Fundamentals)

---

## Learning Objectives

By the end of this module, you will:
1. Verify all backend functionalities required for the Ingest Agent
2. Understand the complete data flow from video URL to database record
3. Wire a 12-node workflow from scratch
4. Implement authentication, polling loops, and database operations
5. Test the workflow end-to-end

---

## Pre-Wiring Checklist: Backend Functionality Verification

> **IMPORTANT**: Before wiring ANY node, we must confirm that the backend services it depends on are operational. This ensures that when we complete the workflow, the entire system works end-to-end.

### Functionality Checklist

| # | Node | Backend Functionality | Endpoint/Service | Status |
|---|------|----------------------|------------------|--------|
| 1 | Webhook: ingest.video | n8n webhook server | `POST /webhook/video_gen_hook` | ⬜ Pending |
| 2 | IF: auth.check | Environment variable | `$env.INGEST_TOKEN` | ⬜ Pending |
| 3 | Respond: 401 | n8n response mechanism | (native) | ⬜ Pending |
| 4 | Code: normalize.payload | JavaScript runtime | (native) | ⬜ Pending |
| 5 | HTTP: media.pull | Media Mover API | `POST /api/media/pull` | ⬜ Pending |
| 6 | Wait: 3s | n8n wait mechanism | (native) | ⬜ Pending |
| 7 | HTTP: check.status | Media Mover API | `GET /api/media/pull/status/{job_id}` | ⬜ Pending |
| 8 | IF: status.done? | Expression evaluation | (native) | ⬜ Pending |
| 9 | Code: increment.attempt | JavaScript runtime | (native) | ⬜ Pending |
| 10 | Postgres: insert.video | PostgreSQL database | `reachy_emotion.video` table | ⬜ Pending |
| 11 | HTTP: emit.completed | Gateway API | `POST /api/events/ingest` | ⬜ Pending |
| 12 | Respond: success | n8n response mechanism | (native) | ⬜ Pending |

### Verification Procedures

#### Test 1: n8n Webhook Server ✅

The n8n webhook server is built-in. No external verification needed.

**Status**: ✅ Complete (native n8n functionality)

---

#### Test 2: Environment Variable — INGEST_TOKEN

**Purpose**: The workflow uses `$env.INGEST_TOKEN` for authentication.

**Verification Steps**:

1. Check if the environment variable is set in your n8n configuration:

```bash
# SSH to Ubuntu 1
ssh rusty_admin@10.0.4.130

# Check docker-compose.yml or .env for n8n
cat /path/to/n8n/.env | grep INGEST_TOKEN
# OR
docker exec n8n-container env | grep INGEST_TOKEN
```

2. If not set, add it to your n8n environment:

```bash
# In .env file
INGEST_TOKEN=your-secret-ingest-token-here

# Restart n8n
docker-compose restart n8n
```

3. Verify in n8n:
   - Create a test workflow with a Code node
   - Code: `return [{ json: { token: $env.INGEST_TOKEN ?? "NOT_SET" } }]`
   - Execute and check the output

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 3: Media Mover API — Pull Endpoint

**Purpose**: The workflow calls `POST /api/media/pull` to initiate video download.

**Verification Steps**:

1. Check if Media Mover is running:

```bash
curl -X GET http://10.0.4.130:8081/api/media/health
# Expected: {"status": "ok"} or similar
```

2. Test the pull endpoint:

```bash
curl -X POST http://10.0.4.130:8081/api/media/pull \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "source_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
    "dest_split": "temp",
    "compute_thumb": true,
    "ffprobe": true
  }'
```

**Expected Response**:
```json
{
  "status": "pending",
  "job_id": "uuid-here",
  "status_url": "/api/media/pull/status/uuid-here"
}
```

**If test fails**, check:
- Is the Media Mover service running? `systemctl status fastapi-media`
- Is port 8081 open? `netstat -tlnp | grep 8081`
- Check logs: `journalctl -u fastapi-media -n 50`

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 4: Media Mover API — Status Endpoint

**Purpose**: The workflow polls `GET /api/media/pull/status/{job_id}` until processing is complete.

**Verification Steps**:

1. Using the `job_id` from Test 3:

```bash
curl -X GET http://10.0.4.130:8081/api/media/pull/status/YOUR_JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (when complete)**:
```json
{
  "status": "done",
  "video_id": "abc123",
  "file_path": "temp/abc123.mp4",
  "sha256": "a1b2c3...",
  "size_bytes": 1048576,
  "ffprobe": {
    "duration": 5.0,
    "fps": 30.0,
    "width": 1280,
    "height": 720
  },
  "thumb_path": "thumbs/abc123.jpg"
}
```

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 5: PostgreSQL — Video Table

**Purpose**: The workflow inserts video metadata into the `video` table.

**Verification Steps**:

1. Connect to PostgreSQL:

```bash
psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion
```

2. Verify table structure:

```sql
\d video
```

**Expected columns**:
- `video_id` (varchar/uuid, PRIMARY KEY)
- `file_path` (text, NOT NULL)
- `split` (text, NOT NULL)
- `label` (text, NULLABLE)
- `duration_sec` (numeric)
- `fps` (numeric)
- `width` (integer)
- `height` (integer)
- `size_bytes` (bigint)
- `sha256` (text)
- `created_at` (timestamptz)
- `updated_at` (timestamptz)

3. Test insert (dry run):

```sql
-- Check constraints
\d+ video

-- Test insert syntax
EXPLAIN INSERT INTO video (video_id, file_path, split, size_bytes, sha256, created_at, updated_at)
VALUES ('test-id', 'temp/test.mp4', 'temp', 1000, 'abc123', NOW(), NOW());
```

4. Verify n8n credential:
   - In n8n, go to Credentials
   - Test `PostgreSQL - reachy_local` with: `SELECT 1;`

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 6: Gateway API — Events Endpoint

**Purpose**: The workflow emits `ingest.completed` events to `POST /api/events/ingest`.

**Verification Steps**:

1. Check if the endpoint exists:

```bash
curl -X POST http://10.0.4.140:8000/api/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ingest.completed",
    "video_id": "test-123",
    "correlation_id": "corr-456",
    "file_path": "temp/test.mp4",
    "sha256": "abc123"
  }'
```

**Expected Response** (200 OK):
```json
{
  "status": "received",
  "event_id": "evt-789"
}
```

**If endpoint doesn't exist**:

This endpoint may need to be implemented. Check `apps/api/routers/gateway.py`:

```python
@router.post("/api/events/ingest")
async def receive_ingest_event(event: dict):
    # Log the event
    logger.info(f"Ingest event received: {event}")
    return {"status": "received", "event_id": str(uuid.uuid4())}
```

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 7: HTTP Header Auth Credential

**Purpose**: The workflow uses `Media Mover Auth` credential for API calls.

**Verification Steps**:

1. In n8n, go to **Settings → Credentials**
2. Find `Media Mover Auth`
3. Verify it's configured as HTTP Header Auth:
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_TOKEN`

4. Test by creating a simple workflow:
   - Add HTTP Request node
   - URL: `http://10.0.4.130:8081/api/media/health`
   - Authentication: Generic Credential → HTTP Header Auth
   - Credential: `Media Mover Auth`
   - Execute and verify success

**Status**: ⬜ Pending → [ ] Complete

---

### Checklist Summary

Update this table as you complete each verification:

| # | Component | Status | Notes |
|---|-----------|--------|-------|
| 1 | n8n Webhook | ✅ Complete | Native functionality |
| 2 | INGEST_TOKEN env var | ⬜ | |
| 3 | Media Mover /pull | ⬜ | |
| 4 | Media Mover /status | ⬜ | |
| 5 | PostgreSQL video table | ⬜ | |
| 6 | Gateway /events/ingest | ⬜ | |
| 7 | Media Mover Auth credential | ⬜ | |

**⚠️ DO NOT proceed to wiring until ALL items show ✅ Complete**

---

## Part 1: Understanding the Ingest Agent

### What Does the Ingest Agent Do?

The Ingest Agent is the **entry point** for all videos in the Reachy system. When a video is generated (by Luma, Runway, or uploaded), this agent:

1. **Receives** the video URL via webhook
2. **Authenticates** the request
3. **Initiates** download via Media Mover
4. **Polls** for completion
5. **Stores** metadata in PostgreSQL
6. **Emits** completion event for downstream agents

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INGEST AGENT FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐                                                       │
│  │   Webhook    │ POST /webhook/video_gen_hook                          │
│  │  (Trigger)   │                                                       │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐     ┌──────────────┐                                  │
│  │  IF: Auth    │────▶│ Respond 401  │  (Unauthorized)                  │
│  │   Check      │     └──────────────┘                                  │
│  └──────┬───────┘                                                       │
│         │ (Authorized)                                                  │
│         ▼                                                               │
│  ┌──────────────┐                                                       │
│  │    Code:     │  Normalize payload from various sources               │
│  │  Normalize   │                                                       │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐                                                       │
│  │  HTTP: Pull  │  POST /api/media/pull                                 │
│  │  (Async)     │  Returns job_id + status_url                          │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐◀──────────────────────────────────────┐               │
│  │   Wait: 3s   │                                       │               │
│  └──────┬───────┘                                       │               │
│         │                                               │               │
│         ▼                                               │               │
│  ┌──────────────┐                                       │               │
│  │ HTTP: Check  │  GET /api/media/pull/status/{job_id}  │               │
│  │   Status     │                                       │               │
│  └──────┬───────┘                                       │               │
│         │                                               │               │
│         ▼                                               │               │
│  ┌──────────────┐     ┌──────────────┐                  │               │
│  │  IF: Done?   │────▶│    Code:     │──────────────────┘               │
│  │              │ No  │  Increment   │  (Loop back to Wait)             │
│  └──────┬───────┘     └──────────────┘                                  │
│         │ Yes                                                           │
│         ▼                                                               │
│  ┌──────────────┐                                                       │
│  │  Postgres:   │  INSERT INTO video (...)                              │
│  │   Insert     │                                                       │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐                                                       │
│  │ HTTP: Emit   │  POST /api/events/ingest                              │
│  │   Event      │  {event_type: "ingest.completed", ...}                │
│  └──────┬───────┘                                                       │
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐                                                       │
│  │  Respond:    │  {status: "success", video_id: "..."}                 │
│  │   Success    │                                                       │
│  └──────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. In n8n, click **+ New Workflow**
2. Click the workflow name (default: "My workflow")
3. Rename to: `Agent 1 — Ingest Agent (Reachy 08.4.2)`
4. Click the gear icon ⚙️ for workflow settings:
   - **Execution Order**: `v1`
   - **Save Manual Executions**: `true`
   - **Error Workflow**: `error_handler` (we'll create this later)

---

### Step 2: Add the Webhook Trigger

**Node Name**: `Webhook: ingest.video`

1. Click the **+** button on the canvas
2. Search for **Webhook** and add it
3. Configure parameters:

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| HTTP Method | `POST` | Only accept POST requests |
| Path | `video_gen_hook` | URL will be `/webhook/video_gen_hook` |
| Response Mode | `Respond Using "Respond to Webhook" Node` | We'll respond at the end |
| Response Code | `202` | Accepted (async processing) |

4. Under **Options**:
   - Response Code: `202`

**Screenshot Reference**: `n8n/workflows/screenshots/Webhook node_Parameters.png`

**Why these settings?**

- **POST method**: We're receiving data (video URL), not requesting it
- **Path `video_gen_hook`**: Descriptive name indicating this handles video generation callbacks
- **Response Mode "Respond Using..."**: We want to control when we respond (after processing)
- **202 Accepted**: Indicates the request was accepted but processing is async

---

### Step 3: Add Authentication Check

**Node Name**: `IF: auth.check`

1. Click **+** after the Webhook
2. Search for **IF** and add it
3. Connect Webhook → IF
4. Configure conditions:

**Condition 1 (String)**:
| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.headers['x-ingest-key']}}` |
| Operation | `Equals` |
| Value 2 | `={{$env.INGEST_TOKEN}}` |

**Screenshot Reference**: `n8n/workflows/screenshots/If node_Parameters.png`

**Understanding the Expression**:

```javascript
// Value 1: $json.headers['x-ingest-key']
// - $json refers to the current item (webhook payload)
// - .headers is the HTTP headers object
// - ['x-ingest-key'] accesses the header (bracket notation for hyphens)

// Value 2: $env.INGEST_TOKEN
// - $env accesses environment variables
// - INGEST_TOKEN is the secret we configured
```

**Outputs**:
- **True (Output 0)**: Header matches token → continue processing
- **False (Output 1)**: Header missing or wrong → reject with 401

---

### Step 4: Add 401 Unauthorized Response

**Node Name**: `Respond: 401 Unauthorized`

1. Click **+** on the **False** output of the IF node
2. Search for **Respond to Webhook** and add it
3. Connect IF (False) → Respond 401
4. Configure:

| Parameter | Value |
|-----------|-------|
| Respond With | `JSON` |
| Response Body | `={{ {"error": "unauthorized", "message": "Invalid or missing X-INGEST-KEY header"} }}` |

5. Under **Options**:
   - Response Code: `401`

**Why return a JSON object?**

The expression `={{ {"error": "...", "message": "..."} }}` returns a JavaScript object literal. The double braces: outer `={{ }}` is the expression wrapper, inner `{ }` is the object.

---

### Step 5: Add Payload Normalization

**Node Name**: `Code: normalize.payload`

1. Click **+** on the **True** output of the IF node
2. Search for **Code** and add it
3. Connect IF (True) → Code
4. Configure:

| Parameter | Value |
|-----------|-------|
| Mode | `Run Once for All Items` |

**JavaScript Code**:

```javascript
// Normalize incoming payload from various sources
// Different video generators (Luma, Runway, etc.) may have different payload structures

const body = $json.body ?? $json;

// Try multiple possible locations for the source URL
const sourceUrl = body.source_url 
  ?? body.url 
  ?? body.asset?.url 
  ?? body.data?.asset?.url;

// Validate we have a URL
if (!sourceUrl) {
  throw new Error('Missing source_url in request body');
}

// Extract optional fields with fallbacks
const label = body.label ?? body.emotion ?? null;
const meta = body.meta ?? { 
  generator: body.generator ?? body.source ?? 'unknown' 
};

// Extract tracing headers or generate defaults
const correlationId = $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`;
const idempotencyKey = $json.headers?.['idempotency-key'] ?? `idem-${Date.now()}`;

// Return normalized payload
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

**Screenshot Reference**: `n8n/workflows/screenshots/Code node_Parameters.png`

**Code Explanation**:

| Line | Purpose |
|------|---------|
| `$json.body ?? $json` | Handle both wrapped and unwrapped payloads |
| `body.source_url ?? body.url ?? ...` | Support multiple payload formats |
| `throw new Error(...)` | Stop workflow if no URL found |
| `$json.headers?.['x-correlation-id']` | Safe navigation for optional headers |
| `` `ingest-${Date.now()}` `` | Generate correlation ID if not provided |
| `return [{ json: {...} }]` | Return a single item with normalized data |

---

### Step 6: Add Media Pull Request

**Node Name**: `HTTP: media.pull`

1. Click **+** after the Code node
2. Search for **HTTP Request** and add it
3. Connect Code → HTTP Request
4. Configure:

**Main Settings**:
| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull` |

**Authentication**:
| Parameter | Value |
|-----------|-------|
| Authentication | `Generic Credential Type` |
| Generic Auth Type | `HTTP Header Auth` |
| Credential | `Media Mover Auth` |

**Headers** (click "Add Header"):
| Name | Value |
|------|-------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` |
| `X-Correlation-ID` | `={{$json.correlation_id}}` |

**Body** (check "Send Body"):
| Parameter | Value |
|-----------|-------|
| Body Content Type | `JSON` |

Then add body parameters:
| Name | Value |
|------|-------|
| `source_url` | `={{$json.source_url}}` |
| `label` | `={{$json.label}}` |
| `correlation_id` | `={{$json.correlation_id}}` |
| `compute_thumb` | `true` |
| `ffprobe` | `true` |
| `dest_split` | `temp` |

**Options**:
| Parameter | Value |
|-----------|-------|
| Timeout | `120000` (2 minutes) |

**Screenshot Reference**: `n8n/workflows/screenshots/HTTP Request node_Parameters_part 1.png`, `part 2.png`

**Understanding the Request**:

This calls Media Mover to:
1. Download the video from `source_url`
2. Store it in `/videos/temp/` (the `dest_split`)
3. Compute SHA256 hash
4. Generate thumbnail (`compute_thumb: true`)
5. Extract metadata via ffprobe (`ffprobe: true`)

The response includes a `status_url` for polling.

---

### Step 7: Add Wait Node (Polling Delay)

**Node Name**: `Wait: 3s`

1. Click **+** after the HTTP Request
2. Search for **Wait** and add it
3. Connect HTTP → Wait
4. Configure:

| Parameter | Value |
|-----------|-------|
| Resume | `After Time Interval` |
| Amount | `3` |
| Unit | `Seconds` |

**Screenshot Reference**: `n8n/workflows/screenshots/Wait node_Parameters.png`

**Why 3 seconds?**

Video download and processing takes time. We poll every 3 seconds to balance:
- Responsiveness (not too long)
- API load (not too frequent)

---

### Step 8: Add Status Check Request

**Node Name**: `HTTP: check.status`

1. Click **+** after the Wait node
2. Add **HTTP Request**
3. Connect Wait → HTTP Request
4. Configure:

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| URL | `={{$json.status_url}}` |

**Authentication**:
| Parameter | Value |
|-----------|-------|
| Authentication | `Generic Credential Type` |
| Generic Auth Type | `HTTP Header Auth` |
| Credential | `Media Mover Auth` |

**Note**: The URL is dynamic — it comes from the `status_url` field in the previous response.

---

### Step 9: Add Status Check IF

**Node Name**: `IF: status.done?`

1. Click **+** after the status check HTTP Request
2. Add **IF** node
3. Connect HTTP → IF
4. Configure:

**Condition 1 (String)**:
| Parameter | Value |
|-----------|-------|
| Value 1 | `={{$json.status}}` |
| Operation | `Equals` |
| Value 2 | `done` |

**Outputs**:
- **True (Output 0)**: Status is "done" → proceed to database insert
- **False (Output 1)**: Status is not "done" → loop back and wait more

---

### Step 10: Add Increment Attempt (Polling Loop)

**Node Name**: `Code: increment.attempt`

1. Click **+** on the **False** output of the IF node
2. Add **Code** node
3. Connect IF (False) → Code
4. Configure:

| Parameter | Value |
|-----------|-------|
| Mode | `Run Once for All Items` |

**JavaScript Code**:

```javascript
// Loop back to wait if not done yet
const maxAttempts = 20;
const currentAttempt = $json.attempt ?? 1;

// Prevent infinite loops
if (currentAttempt >= maxAttempts) {
  throw new Error('Max polling attempts reached');
}

// Return same data with incremented attempt counter
return [{
  json: {
    ...items[0].json,
    attempt: currentAttempt + 1
  }
}];
```

5. **Connect the loop**: Draw a connection from this Code node back to the **Wait: 3s** node.

**Understanding the Polling Loop**:

```
Wait: 3s  →  HTTP: check.status  →  IF: status.done?
    ↑                                       │
    │                                       │ (No)
    │                                       ▼
    └────────────────────────────  Code: increment.attempt
```

- Max 20 attempts × 3 seconds = 60 seconds max polling time
- If processing takes longer, the workflow fails with an error
- This prevents runaway workflows

---

### Step 11: Add Database Insert

**Node Name**: `Postgres: insert.video`

1. Click **+** on the **True** output of the IF node (status.done)
2. Search for **Postgres** and add it
3. Connect IF (True) → Postgres
4. Configure:

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**Query**:

```sql
INSERT INTO video (
  video_id, 
  file_path, 
  split, 
  label, 
  duration_sec, 
  fps, 
  width, 
  height, 
  size_bytes, 
  sha256, 
  created_at, 
  updated_at
)
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

**Screenshot Reference**: `n8n/workflows/screenshots/Postgres node_Parameters.png`

**SQL Explanation**:

| Clause | Purpose |
|--------|---------|
| `INSERT INTO video (...)` | Define columns to insert |
| `VALUES (...)` | Use n8n expressions for dynamic values |
| `'{{$json.video_id}}'` | String value — quotes around expression |
| `{{$json.ffprobe.duration}}` | Numeric value — no quotes needed |
| `ON CONFLICT ... DO NOTHING` | Skip if duplicate (same sha256 + size) |
| `RETURNING video_id` | Return the inserted ID for confirmation |

---

### Step 12: Add Event Emission

**Node Name**: `HTTP: emit.completed`

1. Click **+** after the Postgres node
2. Add **HTTP Request**
3. Connect Postgres → HTTP Request
4. Configure:

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/ingest` |

**Body** (check "Send Body"):
| Name | Value |
|------|-------|
| `event_type` | `ingest.completed` |
| `video_id` | `={{$json.video_id}}` |
| `correlation_id` | `={{$json.correlation_id}}` |
| `file_path` | `={{$json.file_path}}` |
| `sha256` | `={{$json.sha256}}` |

**Why emit events?**

The Reachy system uses **event-driven architecture**. When the Ingest Agent completes:
1. It emits an `ingest.completed` event
2. Other agents (Labeling, Promotion) can listen for this event
3. The system is loosely coupled — agents don't call each other directly

---

### Step 13: Add Success Response

**Node Name**: `Respond: success`

1. Click **+** after the event emission HTTP Request
2. Add **Respond to Webhook**
3. Connect HTTP → Respond to Webhook
4. Configure:

| Parameter | Value |
|-----------|-------|
| Respond With | `JSON` |
| Response Body | `={{ {"status": "success", "video_id": $json.video_id, "correlation_id": $json.correlation_id} }}` |

This closes the loop — the original webhook caller receives confirmation.

---

### Step 14: Save and Verify Connections

Your workflow should now have these connections:

```
webhook_trigger → auth_check
auth_check (True) → normalize_payload
auth_check (False) → respond_401
normalize_payload → media_pull
media_pull → wait_poll
wait_poll → check_status
check_status → is_done
is_done (True) → db_insert
is_done (False) → increment_attempt
increment_attempt → wait_poll (loop back!)
db_insert → emit_event
emit_event → respond_success
```

**Verify visually**: The workflow should match the architecture diagram from Part 1.

---

## Part 3: Testing the Workflow

### Test 1: Manual Execution with Pinned Data

1. Click on the **Webhook: ingest.video** node
2. Click **Test Workflow**
3. In the webhook panel, you'll see a test URL
4. From terminal:

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-INGEST-KEY: YOUR_INGEST_TOKEN" \
  -H "X-Correlation-ID: test-corr-001" \
  -d '{
    "source_url": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
    "label": "happy",
    "generator": "test"
  }'
```

### Test 2: Authentication Failure

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-INGEST-KEY: wrong-token" \
  -d '{"source_url": "https://example.com/video.mp4"}'
```

Expected: 401 Unauthorized response

### Test 3: Missing Source URL

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-INGEST-KEY: YOUR_INGEST_TOKEN" \
  -d '{"label": "happy"}'
```

Expected: Error "Missing source_url in request body"

---

## Part 4: Activating the Workflow

Once testing is complete:

1. Click the **Active** toggle in the top-right
2. The workflow is now live
3. The production webhook URL is: `http://10.0.4.130:5678/webhook/video_gen_hook`

---

## Module 1 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Webhook authentication | IF node comparing header to env var |
| Payload normalization | Code node with fallback patterns |
| Async processing | HTTP Request + Wait + polling loop |
| Database operations | Postgres node with parameterized SQL |
| Event-driven architecture | HTTP Request to emit completion events |
| Error handling | Max attempts, validation errors |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: ingest.video | Webhook | Entry point |
| 2 | IF: auth.check | IF | Authentication |
| 3 | Respond: 401 | Respond to Webhook | Auth failure |
| 4 | Code: normalize.payload | Code | Data transformation |
| 5 | HTTP: media.pull | HTTP Request | Initiate download |
| 6 | Wait: 3s | Wait | Polling delay |
| 7 | HTTP: check.status | HTTP Request | Poll status |
| 8 | IF: status.done? | IF | Check completion |
| 9 | Code: increment.attempt | Code | Loop control |
| 10 | Postgres: insert.video | Postgres | Store metadata |
| 11 | HTTP: emit.completed | HTTP Request | Emit event |
| 12 | Respond: success | Respond to Webhook | Return success |

### Key Patterns Learned

1. **Webhook → Auth → Process → Respond** — Standard API pattern
2. **Wait → HTTP → IF → Loop** — Polling pattern for async operations
3. **Expression interpolation** — `={{$json.field}}` for dynamic values
4. **Error prevention** — Max attempts, validation, conflict handling

---

## Next Steps

Proceed to **Module 2: Labeling Agent** where you'll learn:
- Database-driven state management
- Multi-path branching with Switch node
- Integration with the Promotion Agent

---

## Troubleshooting Guide

### Problem: "Cannot read property 'x-ingest-key' of undefined"

**Cause**: The webhook payload structure is unexpected.

**Fix**: Update the expression to handle missing headers:
```javascript
$json.headers?.['x-ingest-key'] ?? ''
```

### Problem: HTTP Request times out

**Cause**: Media Mover is slow or unreachable.

**Fix**:
1. Check Media Mover health: `curl http://10.0.4.130:8081/api/media/health`
2. Increase timeout in HTTP Request node (Options → Timeout)

### Problem: Postgres insert fails with constraint violation

**Cause**: Duplicate video (same sha256 + size).

**Fix**: This is expected behavior — the `ON CONFLICT DO NOTHING` handles duplicates. Check the video already exists in the database.

### Problem: Polling loop runs forever

**Cause**: Status never becomes "done".

**Fix**:
1. Check Media Mover logs for errors
2. Manually check status: `curl http://10.0.4.130:8081/api/media/pull/status/JOB_ID`
3. Verify the video URL is accessible

---

*Module 1 Complete — Proceed to Module 2: Labeling Agent*
