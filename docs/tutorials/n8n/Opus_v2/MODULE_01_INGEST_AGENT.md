# MODULE 01 -- Ingest Agent

**Duration:** ~4 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`
**Nodes to Wire:** 12
**Prerequisite:** MODULE 00 complete, credentials configured
**Outcome:** A working ingest pipeline that receives video URLs, downloads via Media Mover, stores metadata in PostgreSQL, and emits completion events

---

## 1.1 What Does the Ingest Agent Do?

The Ingest Agent is the **entry point** for all video data entering the Reachy system. When a video URL is submitted (from the Streamlit UI or an external system), this agent:

1. Authenticates the request using a shared secret header
2. Normalizes the incoming payload
3. Sends the video to Media Mover for download
4. Polls until the download completes
5. Inserts the video record into PostgreSQL (with deduplication)
6. Emits an `ingest.completed` event to the Gateway
7. Returns a success response

### Architecture Context

```
                    ┌────────────────────────────┐
 Streamlit UI ─────►│   INGEST AGENT (Agent 1)   │
 or External        │   n8n Workflow              │
 System             │                             │
                    │  webhook_trigger             │
                    │    → auth_check              │
                    │    → normalize_payload        │
                    │    → media_pull ──────────────┼──► Media Mover API
                    │    → wait/poll loop           │     (Ubuntu 1)
                    │    → db_insert ───────────────┼──► PostgreSQL
                    │    → emit_event ──────────────┼──► Gateway API
                    │    → respond_success          │     (Ubuntu 2)
                    └────────────────────────────────┘
```

---

## 1.2 Pre-Wiring Checklist

Before creating this workflow, verify that these backend services are running:

- [ ] **Media Mover API** is accessible at `http://10.0.4.130:8083/api/v1/health`
  ```bash
  curl -s http://10.0.4.130:8083/api/v1/health | jq .
  # Expected: {
  #   "status": "success",
  #   "data.status": "healthy",
  #   "data.checks.directories.status": "ok" or "warning"
  # }
  ```
  - `directories.status = "warning"` simply means one of the optional split folders (e.g., `purged/`) hasn’t been created yet; this is acceptable for dev setups.
- [ ] **PostgreSQL** has the `video` table
  ```bash
  psql -h localhost -U reachy_dev -d reachy_emotion -c "\d video"
  ```
- [ ] **Gateway API** is accessible at `http://10.0.4.140:8000`
  ```bash
  curl -s http://10.0.4.140:8000/health | jq .
  ```
- [ ] **Environment variables** are set in n8n:
  - `INGEST_TOKEN` = `tkn3848`
  - `MEDIA_MOVER_BASE_URL` = `http://10.0.4.130:8083`
  - `GATEWAY_BASE_URL` = `http://10.0.4.140:8000`

---

## 1.3 Create the Workflow

1. In n8n, click **Add Workflow** (top-left `+`)
2. Name it: `Agent 1 -- Ingest Agent (Reachy 08.4.2)`
3. Open **Workflow Settings** (gear icon):
   - Execution Order: `v1`
   - Save Manual Executions: `Yes`
   - Tags: Add `agent`, `ingest`, `phase4`
4. Click **Save**

---

## 1.4 Wire Node 1: webhook_trigger

This is the entry point. External systems POST video URLs here.

### Step-by-Step

1. On the canvas, click the `+` button → search for **Webhook**
2. Click to add the Webhook node
3. Double-click the node to open its configuration
4. Rename it to `webhook_trigger` (click the pencil icon next to the name)
5. Configure these parameters:

| Parameter | Value | Why |
|-----------|-------|-----|
| **HTTP Method** | `POST` | We're receiving data |
| **Path** | `video_gen_hook` | This is the endpoint path. The full URL will be `http://<n8n-host>:5678/webhook/video_gen_hook` |
| **Authentication** | `None` | We handle auth ourselves in the next node |
| **Response Mode** | `Immediately` | Returns 202 immediately before processing completes |
| **Response Code** | `202` | 202 Accepted indicates async processing |

6. Click **Save** on the node

### What You Should See

The node shows:
- **Test URL:** `http://10.0.4.130:5678/webhook-test/video_gen_hook`
- **Production URL:** `http://10.0.4.130:5678/webhook/video_gen_hook`

### Test It

Click **Listen for Test Event**, then in a terminal:

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-Ingest-Key: tkn3848" \
  -d '{
    "source_url": "https://example.com/test_video.mp4",
    "label": "happy",
    "meta": {"camera": "front", "session": "test-001"}
  }'
```

You should see the incoming data appear in the node's output panel.

---

## 1.5 Wire Node 2: auth_check

This IF node validates the authentication header.

### Step-by-Step

1. Click the `+` on the right side of `webhook_trigger` → search for **IF**
2. Rename to `auth_check`
3. Configure the condition:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.headers['x-ingest-key'] }}` |
| **Operation** | `is equal to` |
| **Value 2** | `{{ $env.INGEST_TOKEN }}` |

### How Expressions Work Here

- `$json.headers['x-ingest-key']` -- The Webhook node makes HTTP headers available under `$json.headers`. We reference the custom header name in bracket notation because it contains hyphens.
- `$env.INGEST_TOKEN` -- References the environment variable you set in Module 00.

### Output

- **True branch** → request is authenticated → continue processing
- **False branch** → unauthorized → return 401

---

## 1.6 Wire Node 3: respond_401

This node handles unauthorized requests.

### Step-by-Step

1. Click the `+` on the **false** (bottom) output of `auth_check` → search for **Respond to Webhook**
2. Rename to `respond_401`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Response Code** | `401` |
| **Response Body** | `JSON` |
| **Response Data** | `{ "error": "Unauthorized", "message": "Invalid or missing X-Ingest-Key header" }` |

---

## 1.7 Wire Node 4: normalize_payload

This Code node standardizes the incoming data.

### Step-by-Step

1. Click the `+` on the **true** (top) output of `auth_check` → search for **Code**
2. Rename to `normalize_payload`
3. Set **Mode** to `Run Once for All Items`
4. Paste this JavaScript:

```javascript
const body = $input.first().json.body;

const source_url = body.source_url;
const label = body.label || null;
const meta = body.meta || {};

// Generate a correlation ID for tracing this request across services
const correlation_id = 'ing-' + Date.now() + '-' + Math.random().toString(36).substr(2, 8);

// Generate idempotency key from source URL to prevent duplicate ingests
const crypto = require('crypto');
const idempotency_key = crypto
  .createHash('sha256')
  .update(source_url + (label || ''))
  .digest('hex')
  .substring(0, 16);

return [{
  json: {
    source_url,
    label,
    meta,
    correlation_id,
    idempotency_key
  }
}];
```

### What This Does

- Extracts `source_url`, `label`, and `meta` from the POST body
- Generates a unique `correlation_id` for tracking this ingestion across all services
- Creates an `idempotency_key` from the SHA256 hash of the source URL to prevent duplicate processing

---

## 1.8 Wire Node 5: media_pull

This HTTP Request node sends the video URL to Media Mover for download.

### Step-by-Step

1. Click the `+` on `normalize_payload` → search for **HTTP Request**
2. Rename to `media_pull`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/media/pull` |
| **Authentication** | `Predefined Credential Type` |
| **Credential Type** | `Header Auth` |
| **Credential** | Select `Media Mover Auth` |
| **Send Body** | `Yes` |
| **Body Content Type** | `JSON` |
| **Specify Body** | `Using Fields Below` |

4. Add body fields:

| Field | Value |
|-------|-------|
| `source_url` | `{{ $json.source_url }}` |
| `label` | `{{ $json.label }}` |
| `compute_thumb` | `true` |
| `ffprobe` | `true` |
| `dest_split` | `temp` |

5. Under **Options**, set:
   - **Timeout:** `120000` (120 seconds -- video downloads can be slow)

### What This Does

- Sends the video URL to Media Mover, which downloads the video file
- `dest_split=temp` means the video is stored in the `/videos/temp/` directory initially
- `compute_thumb=true` generates a thumbnail for the UI
- `ffprobe=true` extracts video metadata (duration, resolution, fps)
- Returns a `status_url` that we'll poll in the next steps

---

## 1.9 Wire Node 6: wait_poll

This Wait node creates a pause before we check if the download is done.

### Step-by-Step

1. Click the `+` on `media_pull` → search for **Wait**
2. Rename to `wait_poll`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Resume** | `After Time Interval` |
| **Amount** | `3` |
| **Unit** | `Seconds` |

### Why 3 Seconds?

Most video downloads complete within 10-30 seconds. Polling every 3 seconds gives us a good balance between responsiveness and API load. With a max of 20 attempts, this gives us a 60-second timeout.

---

## 1.10 Wire Node 7: check_status

This HTTP Request node polls the Media Mover status endpoint.

### Step-by-Step

1. Click the `+` on `wait_poll` → search for **HTTP Request**
2. Rename to `check_status`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `{{ $json.status_url }}` |
| **Authentication** | `Predefined Credential Type` |
| **Credential Type** | `Header Auth` |
| **Credential** | Select `Media Mover Auth` |

### What's Happening

- `$json.status_url` was returned by the `media_pull` node in the previous step
- The status endpoint returns `{ "status": "pending" | "processing" | "done" | "failed", ... }`
- When `done`, it also returns the file metadata (path, sha256, size, duration, etc.)

---

## 1.11 Wire Node 8: is_done

This IF node checks if the download has completed.

### Step-by-Step

1. Click the `+` on `check_status` → search for **IF**
2. Rename to `is_done`
3. Configure the condition:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.status }}` |
| **Operation** | `is equal to` |
| **Value 2** | `done` |

---

## 1.12 Wire Node 9: increment_attempt

This Code node handles the retry logic when the download isn't done yet.

### Step-by-Step

1. Click the `+` on the **false** (bottom) output of `is_done` → search for **Code**
2. Rename to `increment_attempt`
3. Set **Mode** to `Run Once for All Items`
4. Paste this JavaScript:

```javascript
const item = $input.first().json;
const attempt = (item.attempt || 0) + 1;
const maxAttempts = 20;

if (attempt >= maxAttempts) {
  throw new Error(
    `Media pull timed out after ${maxAttempts} attempts (${maxAttempts * 3}s). ` +
    `Last status: ${item.status}. URL: ${item.source_url || 'unknown'}`
  );
}

return [{
  json: {
    ...item,
    attempt,
    status_url: item.status_url
  }
}];
```

### Important: Connect the Loop

Now you need to create the polling loop:

1. **Drag a connection** from the output of `increment_attempt` back to the input of `wait_poll`
2. This creates a loop: wait → check → not done? → increment → wait → check → ...

This is the **Async Polling Loop** pattern from Module 00.

---

## 1.13 Wire Node 10: db_insert

This Postgres node stores the video metadata in the database.

### Step-by-Step

1. Click the `+` on the **true** (top) output of `is_done` → search for **Postgres**
2. Rename to `db_insert`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | Select `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

4. Paste this SQL query:

```sql
INSERT INTO video (
  file_path,
  label,
  split,
  sha256,
  size_bytes,
  duration_sec,
  fps,
  width,
  height,
  source_url,
  correlation_id,
  created_at
)
VALUES (
  '{{ $json.file_path }}',
  '{{ $json.label }}',
  'temp',
  '{{ $json.sha256 }}',
  {{ $json.size_bytes }},
  {{ $json.duration_sec || 0 }},
  {{ $json.fps || 0 }},
  {{ $json.width || 0 }},
  {{ $json.height || 0 }},
  '{{ $json.source_url }}',
  '{{ $('normalize_payload').item.json.correlation_id }}',
  NOW()
)
ON CONFLICT (sha256, size_bytes) DO NOTHING
RETURNING video_id, file_path, sha256;
```

### Key Points

- **`ON CONFLICT (sha256, size_bytes) DO NOTHING`** -- This is the deduplication mechanism. If a video with the same SHA256 hash and file size already exists, the insert is silently skipped.
- **`$('normalize_payload').item.json.correlation_id`** -- References the correlation_id from the normalize_payload node's output. This allows us to trace the entire ingestion flow.
- **`RETURNING`** -- Returns the video_id of the newly inserted row (or nothing if deduplicated).

---

## 1.14 Wire Node 11: emit_event

This HTTP Request node notifies the Gateway that ingestion is complete.

### Step-by-Step

1. Click the `+` on `db_insert` → search for **HTTP Request**
2. Rename to `emit_event`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/events/ingest` |
| **Send Body** | `Yes` |
| **Body Content Type** | `JSON` |
| **Specify Body** | `Using Fields Below` |

4. Add body fields:

| Field | Value |
|-------|-------|
| `event_type` | `ingest.completed` |
| `video_id` | `{{ $json.video_id }}` |
| `file_path` | `{{ $json.file_path }}` |
| `correlation_id` | `{{ $('normalize_payload').item.json.correlation_id }}` |
| `timestamp` | `{{ $now.toISO() }}` |

### Why Emit Events?

The Gateway API acts as an event bus. Other agents (Labeling, Observability) can react to `ingest.completed` events. This creates a loosely coupled system where agents communicate through events rather than direct calls.

---

## 1.15 Wire Node 12: respond_success

This final node sends a success response back to the original caller.

### Step-by-Step

1. Click the `+` on `emit_event` → search for **Respond to Webhook**
2. Rename to `respond_success`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Response Code** | `200` |
| **Response Body** | `JSON` |
| **Response Data** | *(see below)* |

4. Set the response data:

```json
{
  "status": "ingested",
  "video_id": "{{ $('db_insert').item.json.video_id }}",
  "file_path": "{{ $('db_insert').item.json.file_path }}",
  "correlation_id": "{{ $('normalize_payload').item.json.correlation_id }}"
}
```

---

## 1.16 Final Connection Map

Verify all connections match this diagram:

```
webhook_trigger ──► auth_check
                       │
              [false]  │  [true]
                 │     │
                 ▼     ▼
           respond_401  normalize_payload
                              │
                              ▼
                         media_pull
                              │
                              ▼
                  ┌──── wait_poll ◄────────┐
                  │          │              │
                  │          ▼              │
                  │     check_status        │
                  │          │              │
                  │          ▼              │
                  │       is_done           │
                  │     [true]  [false]     │
                  │       │        │        │
                  │       │        ▼        │
                  │       │  increment_attempt
                  │       │        │
                  │       │        └────────┘
                  │       ▼
                  │    db_insert
                  │       │
                  │       ▼
                  │   emit_event
                  │       │
                  │       ▼
                  │  respond_success
                  └────────────────────────
```

---

## 1.17 Testing

### Test 1: Successful Ingestion

1. Click **Execute Workflow** (or activate it and use the production URL)
2. Run this curl command:

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-Ingest-Key: tkn3848" \
  -d '{
    "source_url": "https://example.com/happy_test.mp4",
    "label": "happy",
    "meta": {"camera": "front"}
  }'
```

**Expected:** HTTP 202, then the workflow processes asynchronously.

### Test 2: Authentication Failure

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "X-Ingest-Key: wrong-token" \
  -d '{"source_url": "https://example.com/test.mp4"}'
```

**Expected:** HTTP 401 with `{"error": "Unauthorized"}`.

### Test 3: Duplicate Video

Run Test 1 again with the same URL. The `ON CONFLICT DO NOTHING` should prevent a duplicate insert.

---

## 1.18 Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Webhook returns 404 | Workflow not saved or not active | Save the workflow; for production use, toggle Active ON |
| Auth check always fails | Header name mismatch | Check that the header is `x-ingest-key` (lowercase). n8n lowercases all headers |
| Media pull times out | Media Mover not running | Check `curl http://10.0.4.130:8083/health` |
| Polling loop runs forever | Status never reaches "done" | Check Media Mover logs; the video URL may be unreachable |
| DB insert fails | Missing columns or wrong types | Run `\d video` in psql to verify the table schema |
| `$env.INGEST_TOKEN` is undefined | Environment variable not set | Go to Settings → Variables and verify |

---

## 1.19 Key Concepts Learned

- **Webhook Trigger** with custom response codes (202 Accepted)
- **IF Node** for authentication routing
- **Code Node** for payload normalization and ID generation
- **HTTP Request** with credential-based authentication
- **Wait + IF Loop** for async polling (the polling pattern)
- **Postgres** with `ON CONFLICT DO NOTHING` for idempotent inserts
- **Cross-node references** using `$('node_name').item.json.field`
- **Event emission** for inter-agent communication

---

*Previous: [MODULE 00 -- n8n Fundamentals](MODULE_00_N8N_FUNDAMENTALS.md)*
*Next: [MODULE 02 -- Labeling Agent](MODULE_02_LABELING_AGENT.md)*
