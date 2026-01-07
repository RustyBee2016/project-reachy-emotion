# Agent 2 — Labeling Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Labeling Agent manages user-assisted classification and dataset promotion. It validates label submissions, applies labels to videos in the database, and routes actions to appropriate handlers (label_only, promote_train, promote_test, discard). It maintains training split integrity and tracks class balance for 50/50 happy/sad distribution.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: validate.payload | n8n-nodes-base.code | validate_payload |
| HTTP: mm.promote | n8n-nodes-base.httpRequest | mm_promote |
| HTTP: mm.relabel | n8n-nodes-base.httpRequest | mm_relabel |
| Postgres: apply.label | n8n-nodes-base.postgres | db_apply_label |
| Postgres: class.balance | n8n-nodes-base.postgres | db_class_balance |
| Postgres: fetch.video | n8n-nodes-base.postgres | db_fetch_video |
| Respond: success | n8n-nodes-base.respondToWebhook | respond_success |
| Switch: branch.action | n8n-nodes-base.switch | branch_action |
| Webhook: label.submitted | n8n-nodes-base.webhook | webhook_label |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: label.submitted
    │
    ▼
Code: validate.payload
    │
    ▼
Postgres: fetch.video
    │
    ▼
Postgres: apply.label
    │
    ▼
Switch: branch.action
    │
    ├──► [label_only] ──► HTTP: mm.relabel ──────┐
    │                                            │
    ├──► [promote_train] ──► HTTP: mm.promote ───┤
    │                                            │
    ├──► [promote_test] ──► HTTP: mm.promote ────┤
    │                                            │
    └──► [discard] ──────────────────────────────┤
                                                 │
                                                 ▼
                                    Postgres: class.balance
                                                 │
                                                 ▼
                                       Respond: success
```

---

## Node Details

### 1. Webhook: label.submitted

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-600, 300]  
**Purpose:** Entry point for label submission requests from the web UI or API clients.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests only |
| `path` | `label` | URL path: `{N8N_HOST}/webhook/label` |
| `responseMode` | `responseNode` | Response handled by Respond to Webhook node |
| `webhookId` | `label-submitted` | Unique webhook identifier |

#### Input Schema (Expected Request Body)

```json
{
  "video_id": "uuid",                    // Required: Video UUID
  "label": "happy|sad|angry|neutral|surprise|fearful",  // Required: Emotion label
  "action": "label_only|promote_train|promote_test|discard",  // Optional: default "label_only"
  "rater_id": "string",                  // Optional: default "anonymous"
  "notes": "string",                     // Optional: rater notes
  "idempotency_key": "string",           // Optional: auto-generated if missing
  "correlation_id": "string"             // Optional: auto-generated if missing
}
```

#### Related Code

- **No direct code mapping** — n8n native webhook functionality

#### Test Status: ✅ OPERATIONAL

---

### 2. Code: validate.payload

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-400, 300]  
**Purpose:** Validates and normalizes label submission payload, ensuring required fields and valid values.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `mode` | `runOnceForAllItems` | Process all items in single execution |

#### JavaScript Code

```javascript
// Validate and normalize label submission
const body = $json.body ?? $json;
const allowedLabels = new Set(['happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful']);
const allowedActions = new Set(['label_only', 'promote_train', 'promote_test', 'discard']);

function uuidv4() {
  return crypto.randomUUID ? crypto.randomUUID() : 
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
}

const video_id = body.video_id;
const label = (body.label || '').toLowerCase();
const action = body.action || 'label_only';
const rater_id = body.rater_id || 'anonymous';
const notes = body.notes || '';
const idempotency_key = body.idempotency_key || uuidv4();

if (!video_id) throw new Error('video_id required');
if (!allowedLabels.has(label)) throw new Error(`Invalid label: ${label}`);
if (!allowedActions.has(action)) throw new Error(`Invalid action: ${action}`);

return [{
  json: {
    video_id,
    label,
    action,
    rater_id,
    notes,
    idempotency_key,
    correlation_id: body.correlation_id || `label-${Date.now()}`
  }
}];
```

#### Validation Rules

| Field | Validation | Error Message |
|-------|------------|---------------|
| `video_id` | Required, non-empty | `video_id required` |
| `label` | Must be in allowed set | `Invalid label: {value}` |
| `action` | Must be in allowed set | `Invalid action: {value}` |

#### Allowed Values

| Field | Allowed Values |
|-------|----------------|
| `label` | `happy`, `sad`, `angry`, `neutral`, `surprise`, `fearful` |
| `action` | `label_only`, `promote_train`, `promote_test`, `discard` |

#### Output Schema

```json
{
  "video_id": "uuid",
  "label": "string",
  "action": "string",
  "rater_id": "string",
  "notes": "string",
  "idempotency_key": "string",
  "correlation_id": "string"
}
```

#### Related Code

- **Similar validation in:** `apps/api/app/db/models.py` lines 174-178 (`chk_label_event_action` constraint)

#### Test Status: ✅ OPERATIONAL

---

### 3. Postgres: fetch.video

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [-200, 300]  
**Purpose:** Fetches current video metadata from database to verify existence and current state.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `executeQuery` | Run raw SQL |

#### SQL Query

```sql
SELECT v.video_id, v.split, v.label AS current_label, v.file_path
FROM video v
WHERE v.video_id = '{{$json.video_id}}'::uuid;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Expected Output

```json
{
  "video_id": "uuid",
  "split": "temp|train|test|dataset_all",
  "current_label": "happy|sad|null",
  "file_path": "temp/uuid.mp4"
}
```

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `Video` | 33-78 | Video model with split and label fields |

#### Test Status: ✅ OPERATIONAL

---

### 4. Postgres: apply.label

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [0, 300]  
**Purpose:** Applies the label to the video and creates an audit log entry in the `label_event` table.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `executeQuery` | Run raw SQL |

#### SQL Query

```sql
WITH ins AS (
  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)
  VALUES (
    '{{$json.video_id}}'::uuid,
    '{{$json.label}}',
    '{{$json.action}}',
    '{{$json.rater_id}}',
    '{{$json.notes}}',
    '{{$json.idempotency_key}}'
  )
  ON CONFLICT (video_id, idempotency_key) DO NOTHING
  RETURNING event_id
)
UPDATE video
SET label = '{{$json.label}}',
    updated_at = NOW()
WHERE video_id = '{{$json.video_id}}'::uuid
RETURNING 
  video_id, 
  label, 
  split,
  (SELECT event_id FROM ins) AS event_id;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Behavior

- **Idempotency:** Uses `ON CONFLICT (video_id, idempotency_key) DO NOTHING` to prevent duplicate label events
- **Atomic:** CTE ensures label_event insert and video update happen together
- **Audit Trail:** Creates `label_event` record for every labeling action

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `LabelEvent` | 150-182 | Audit log for labeling actions |
| `Video` | 33-78 | Video model with label field |

**LabelEvent Schema:**

| Column | Type | Constraints |
|--------|------|-------------|
| `event_id` | `BigInteger` | Primary Key, Auto-increment |
| `video_id` | `String(36)` | FK to video.video_id |
| `label` | `EmotionEnum` | NOT NULL |
| `action` | `String(50)` | NOT NULL, CHECK constraint |
| `rater_id` | `String(255)` | NULLABLE |
| `notes` | `Text` | NULLABLE |
| `idempotency_key` | `String(64)` | UNIQUE, NULLABLE |
| `correlation_id` | `String(36)` | NULLABLE |
| `created_at` | `DateTime` | Auto-generated |

**Check Constraint (`chk_label_event_action`):**
```sql
action IN ('label_only', 'promote_train', 'promote_test', 'discard', 'relabel')
```

#### Test Status: ✅ OPERATIONAL

---

### 5. Switch: branch.action

**Type:** `n8n-nodes-base.switch` (v3)  
**Position:** [200, 300]  
**Purpose:** Routes the workflow based on the requested action (label_only, promote_train, promote_test, discard).

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `rules.values` | Array of 4 rules | Define routing conditions |

#### Routing Rules

| Output Index | Output Key | Condition | Next Node |
|--------------|------------|-----------|-----------|
| 0 | `label_only` | `action === "label_only"` | HTTP: mm.relabel |
| 1 | `promote_train` | `action === "promote_train"` | HTTP: mm.promote |
| 2 | `promote_test` | `action === "promote_test"` | HTTP: mm.promote |
| 3 | `discard` | `action === "discard"` | Postgres: class.balance |

#### Rule Configuration (Example: label_only)

```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{$json.action}}",
        "value2": "label_only"
      }
    ]
  },
  "renameOutput": true,
  "outputKey": "label_only"
}
```

#### Related Code

- **No direct code mapping** — n8n native switch functionality

#### Test Status: ✅ OPERATIONAL

---

### 6. HTTP: mm.relabel

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [400, 200]  
**Purpose:** Calls Media Mover relabel endpoint to update label metadata without moving the file.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel` | Media Mover relabel endpoint |
| `authentication` | `genericCredentialType` | Use credential store |
| `genericAuthType` | `httpHeaderAuth` | Header-based auth |
| `sendHeaders` | `true` | Include custom headers |
| `sendBody` | `true` | Include request body |

#### Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` | Deduplication |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `video_id` | `={{$json.video_id}}` | Video UUID |
| `label` | `={{$json.label}}` | New label |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/gateway.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `relabel_video()` | 225-239 | POST `/api/relabel` proxy endpoint |

**File:** `apps/api/routers/media.py`

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/relabel` | ⚠️ **TBD** | Not implemented in media.py |

#### Test Status: ⚠️ TBD

**Required Actions:**
1. Implement `POST /api/relabel` endpoint in `apps/api/routers/media.py`
2. Update label metadata in filesystem or database as needed

---

### 7. HTTP: mm.promote

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [400, 400]  
**Purpose:** Calls Media Mover promote endpoint to move video from temp to train/test split.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/promote` | Media Mover promote endpoint |
| `authentication` | `genericCredentialType` | Use credential store |
| `genericAuthType` | `httpHeaderAuth` | Header-based auth |
| `sendHeaders` | `true` | Include custom headers |
| `sendBody` | `true` | Include request body |

#### Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` | Deduplication |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `video_id` | `={{$json.video_id}}` | Video UUID |
| `dest_split` | `={{$json.action === 'promote_train' ? 'train' : 'test'}}` | Target split (train or test) |
| `label` | `={{$json.label}}` | Emotion label |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |
| `dry_run` | `false` | Execute real promotion |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/media.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `promote()` | 33-126 | POST `/api/media/promote` endpoint |

**File:** `apps/api/routers/gateway.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `post_promotion()` | 173-222 | POST `/api/promote` proxy endpoint |

**File:** `apps/api/app/routers/promote.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `stage_videos()` | 41-86 | POST `/api/v1/promote/stage` endpoint |

#### Promotion Logic (from media.py lines 33-126)

```python
# Validates schema_version, clip, target, label, correlation_id
# Supports adapter mode for new-style requests (video_id, dest_split)
# Moves file from /videos/temp/{clip} to /videos/{target}/{clip}
# Returns: {"status": "ok", "src": "...", "dst": "...", "dry_run": false}
```

#### Test Status: ✅ OPERATIONAL

---

### 8. Postgres: class.balance

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [600, 300]  
**Purpose:** Queries current class distribution in the training set to report balance status.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `executeQuery` | Run raw SQL |

#### SQL Query

```sql
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Expected Output

```json
{
  "happy_count": 45,
  "sad_count": 42,
  "total_train": 87
}
```

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `Video` | 33-78 | Video model with label and split fields |

**Balance Calculation:**
- **Balanced:** `Math.abs(happy_count - sad_count) <= 5`
- **Target:** 50/50 distribution between happy and sad

#### Test Status: ✅ OPERATIONAL

---

### 9. Respond: success

**Type:** `n8n-nodes-base.respondToWebhook` (v1)  
**Position:** [800, 300]  
**Purpose:** Returns success response with labeling result and class balance information.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `respondWith` | `json` | JSON response body |

#### Response Body Expression

```javascript
={{
  {
    "status": "success",
    "video_id": $json.video_id,
    "label": $json.label,
    "action": $json.action,
    "class_balance": {
      "happy": $json.happy_count,
      "sad": $json.sad_count,
      "total_train": $json.total_train,
      "balanced": Math.abs($json.happy_count - $json.sad_count) <= 5
    },
    "correlation_id": $json.correlation_id
  }
}}
```

#### Response Schema

```json
{
  "status": "success",
  "video_id": "uuid",
  "label": "happy|sad",
  "action": "label_only|promote_train|promote_test|discard",
  "class_balance": {
    "happy": 45,
    "sad": 42,
    "total_train": 87,
    "balanced": true
  },
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
| `MEDIA_MOVER_BASE_URL` | Base URL for Media Mover API | `http://10.0.4.130:8000` |

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
  "callerPolicy": "workflowsFromSameOwner"
}
```

---

## Tags

- `agent`
- `labeling`
- `phase4`

---

## Database Schema Dependencies

### Video Table

| Column | Type | Used By |
|--------|------|---------|
| `video_id` | `String(36)` | fetch.video, apply.label |
| `split` | `SplitEnum` | fetch.video, class.balance |
| `label` | `EmotionEnum` | apply.label, class.balance |
| `file_path` | `String(1024)` | fetch.video |

### LabelEvent Table

| Column | Type | Used By |
|--------|------|---------|
| `event_id` | `BigInteger` | apply.label (returned) |
| `video_id` | `String(36)` | apply.label |
| `label` | `EmotionEnum` | apply.label |
| `action` | `String(50)` | apply.label |
| `rater_id` | `String(255)` | apply.label |
| `notes` | `Text` | apply.label |
| `idempotency_key` | `String(64)` | apply.label (conflict check) |

---

## Code Testing Summary

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Video Model | `apps/api/app/db/models.py` | 33-78 | ✅ Imports OK |
| LabelEvent Model | `apps/api/app/db/models.py` | 150-182 | ✅ Imports OK |
| Promote Endpoint | `apps/api/routers/media.py` | 33-126 | ✅ Imports OK |
| Gateway Relabel | `apps/api/routers/gateway.py` | 225-239 | ✅ Imports OK |
| Relabel Endpoint | `apps/api/routers/media.py` | N/A | ⚠️ Not implemented |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Relabel Endpoint | HIGH | Implement `POST /api/relabel` in `apps/api/routers/media.py` |
| Discard Logic | MEDIUM | Implement discard action (mark as purged or delete) |
| Label Validation | LOW | Consider adding label validation against EmotionEnum in API |

---

## Connections Summary

```json
{
  "webhook_label": { "main": [["validate_payload"]] },
  "validate_payload": { "main": [["db_fetch_video"]] },
  "db_fetch_video": { "main": [["db_apply_label"]] },
  "db_apply_label": { "main": [["branch_action"]] },
  "branch_action": { 
    "main": [
      ["mm_relabel"],      // label_only
      ["mm_promote"],      // promote_train
      ["mm_promote"],      // promote_test
      ["db_class_balance"] // discard
    ] 
  },
  "mm_relabel": { "main": [["db_class_balance"]] },
  "mm_promote": { "main": [["db_class_balance"]] },
  "db_class_balance": { "main": [["respond_success"]] }
}
```

---

## Usage Example

### Label Only (No Promotion)

```bash
curl -X POST http://localhost:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123-def456",
    "label": "happy",
    "action": "label_only",
    "rater_id": "user@example.com"
  }'
```

### Promote to Training Set

```bash
curl -X POST http://localhost:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123-def456",
    "label": "sad",
    "action": "promote_train",
    "rater_id": "user@example.com",
    "notes": "Clear sad expression"
  }'
```

### Expected Response

```json
{
  "status": "success",
  "video_id": "abc123-def456",
  "label": "sad",
  "action": "promote_train",
  "class_balance": {
    "happy": 45,
    "sad": 43,
    "total_train": 88,
    "balanced": true
  },
  "correlation_id": "label-1701234567890"
}
```
