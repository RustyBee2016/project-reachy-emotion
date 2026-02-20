# Module 2: Labeling Agent — Database State Management & Multi-Path Routing

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~3 hours  
**Prerequisites**: Completed Module 0 & Module 1

---

## Learning Objectives

By the end of this module, you will:
1. Use the **Switch node** for multi-path branching
2. Write **complex SQL queries** with CTEs (Common Table Expressions)
3. Understand **idempotency patterns** for database operations
4. Implement **validation logic** in Code nodes
5. Build a workflow that integrates with multiple downstream systems

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Multi-path routing** | Switch node | Handle multiple action types in one workflow |
| **CTE (WITH clause)** | Postgres node | Combine insert + update atomically |
| **Idempotency** | ON CONFLICT clause | Prevent duplicate operations |
| **Data merging** | Expressions | Combine data from multiple sources |
| **Validation** | Code node | Enforce business rules before DB operations |

---

## Pre-Wiring Checklist: Backend Functionality Verification

> **IMPORTANT**: Complete ALL verifications before wiring nodes.

### Functionality Checklist

| # | Node | Backend Functionality | Endpoint/Service | Status |
|---|------|----------------------|------------------|--------|
| 1 | Webhook: label.submitted | n8n webhook server | `POST /webhook/label` | ⬜ Pending |
| 2 | Code: validate.payload | JavaScript runtime | (native) | ⬜ Pending |
| 3 | Postgres: fetch.video | PostgreSQL database | `reachy_emotion.video` | ⬜ Pending |
| 4 | Postgres: apply.label | PostgreSQL database | `reachy_emotion.label_event` | ⬜ Pending |
| 5 | Switch: branch.action | n8n switch node | (native) | ⬜ Pending |
| 6 | HTTP: mm.relabel | Media Mover API | `POST /api/relabel` | ⬜ Pending |
| 7 | HTTP: mm.promote | Media Mover API | `POST /api/promote` | ⬜ Pending |
| 8 | Postgres: class.balance | PostgreSQL database | Query on `video` table | ⬜ Pending |
| 9 | Respond: success | n8n response mechanism | (native) | ⬜ Pending |

---

### Verification Procedures

#### Test 1: PostgreSQL — label_event Table Exists

**Purpose**: The workflow inserts audit records into `label_event`.

**Verification Steps**:

```bash
psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion
```

```sql
-- Check if table exists
\d label_event

-- If missing, create it:
CREATE TABLE IF NOT EXISTS label_event (
  event_id BIGSERIAL PRIMARY KEY,
  video_id VARCHAR(36) REFERENCES video(video_id),
  label VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL CHECK (action IN ('label_only', 'promote_train', 'promote_test', 'discard', 'relabel')),
  rater_id VARCHAR(255),
  notes TEXT,
  idempotency_key VARCHAR(64),
  correlation_id VARCHAR(36),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(video_id, idempotency_key)
);
```

**Expected columns**:
- `event_id` (bigserial, PRIMARY KEY)
- `video_id` (varchar, FK to video)
- `label` (varchar, NOT NULL)
- `action` (varchar, CHECK constraint)
- `rater_id` (varchar, nullable)
- `notes` (text, nullable)
- `idempotency_key` (varchar, unique per video)
- `correlation_id` (varchar, nullable)
- `created_at` (timestamptz)

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 2: Video Table — Label Column Accepts Values

**Purpose**: The workflow updates `video.label`.

**Verification Steps**:

```sql
-- Check video table structure
\d video

-- Test label update (pick an existing video_id or insert test data)
UPDATE video SET label = 'happy' WHERE video_id = 'test-id-here';

-- Verify the label constraint allows: happy, sad, neutral
-- Or that it's a free varchar that accepts these values
```

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 3: Media Mover — Relabel Endpoint

**Purpose**: The workflow calls `POST /api/relabel` for label-only actions.

**Verification Steps**:

```bash
curl -X POST http://10.0.4.130:8083/api/relabel \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Idempotency-Key: test-relabel-001" \
  -d '{
    "video_id": "test-video-id",
    "label": "happy",
    "correlation_id": "test-corr-001"
  }'
```

**Expected Response**:
```json
{
  "status": "ok",
  "video_id": "test-video-id",
  "label": "happy"
}
```

**⚠️ If endpoint doesn't exist**: This is marked as **TBD** in the spec. You may need to:
1. Implement the endpoint in `apps/api/routers/media.py`
2. Or skip this test and handle the error gracefully in the workflow

**Status**: ⬜ Pending → [ ] Complete (or N/A if skipping)

---

#### Test 4: Media Mover — Promote Endpoint

**Purpose**: The workflow calls `POST /api/promote` for promote_train/promote_test actions.

**Verification Steps**:

```bash
# First, ensure you have a video in temp split
curl -X POST http://10.0.4.130:8083/api/promote \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Idempotency-Key: test-promote-001" \
  -d '{
    "video_id": "test-video-id",
    "dest_split": "train",
    "label": "happy",
    "correlation_id": "test-corr-002",
    "dry_run": true
  }'
```

**Expected Response (dry_run=true)**:
```json
{
  "status": "ok",
  "dry_run": true,
  "src": "/videos/temp/test-video-id.mp4",
  "dst": "/videos/train/test-video-id.mp4"
}
```

**Status**: ⬜ Pending → [ ] Complete

---

#### Test 5: PostgreSQL — Class Balance Query

**Purpose**: The workflow queries class distribution.

**Verification Steps**:

```sql
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

**Expected**: Returns three numeric columns (may be 0 if no training data yet)

**Status**: ⬜ Pending → [ ] Complete

---

### Checklist Summary

| # | Component | Status | Notes |
|---|-----------|--------|-------|
| 1 | n8n Webhook | ✅ Complete | Native functionality |
| 2 | label_event table | ⬜ | |
| 3 | video.label update | ⬜ | |
| 4 | /api/relabel endpoint | ⬜ | TBD - may not exist |
| 5 | /api/promote endpoint | ⬜ | Should be implemented from Module 1 |
| 6 | Class balance query | ⬜ | |

**⚠️ DO NOT proceed to wiring until ALL critical items show ✅ Complete**

---

## Part 1: Understanding the Labeling Agent

### What Does the Labeling Agent Do?

The Labeling Agent is the **human-in-the-loop** component of the Reachy system. When a user classifies a video:

1. **Validates** the label submission (valid label, valid action)
2. **Verifies** the video exists in the database
3. **Records** the label and audit trail
4. **Routes** to the appropriate handler based on action:
   - `label_only` → Update label, no file move
   - `promote_train` → Move to training set
   - `promote_test` → Move to test set
   - `discard` → Mark for deletion
5. **Reports** class balance for 50/50 tracking

### Why Multi-Path Routing?

Unlike the Ingest Agent (linear flow), the Labeling Agent handles **four different user intents** with a single webhook. The Switch node lets us handle all cases without duplicating logic.

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       LABELING AGENT FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐                                                   │
│  │     Webhook:     │  POST /webhook/label                              │
│  │ label.submitted  │  {video_id, label, action, rater_id, notes}       │
│  └────────┬─────────┘                                                   │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────┐                                                   │
│  │      Code:       │  Validate: video_id required                      │
│  │ validate.payload │  label ∈ {happy, sad, neutral}        │
│  │                  │  action ∈ {label_only, promote_train, ...}        │
│  └────────┬─────────┘                                                   │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────┐                                                   │
│  │    Postgres:     │  SELECT video_id, split, label, file_path         │
│  │   fetch.video    │  FROM video WHERE video_id = ?                    │
│  └────────┬─────────┘                                                   │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────┐                                                   │
│  │    Postgres:     │  WITH ins AS (INSERT INTO label_event...)         │
│  │   apply.label    │  UPDATE video SET label = ?                       │
│  └────────┬─────────┘                                                   │
│           │                                                             │
│           ▼                                                             │
│  ┌──────────────────┐                                                   │
│  │     Switch:      │                                                   │
│  │  branch.action   │                                                   │
│  └───┬───┬───┬───┬──┘                                                   │
│      │   │   │   │                                                      │
│      │   │   │   └──► [discard] ──────────────────────────┐             │
│      │   │   │                                            │             │
│      │   │   └──────► [promote_test] ──► HTTP: promote ───┤             │
│      │   │                                                │             │
│      │   └──────────► [promote_train] ─► HTTP: promote ───┤             │
│      │                                                    │             │
│      └──────────────► [label_only] ────► HTTP: relabel ───┤             │
│                                                           │             │
│                                                           ▼             │
│                                              ┌──────────────────┐       │
│                                              │    Postgres:     │       │
│                                              │  class.balance   │       │
│                                              └────────┬─────────┘       │
│                                                       │                 │
│                                                       ▼                 │
│                                              ┌──────────────────┐       │
│                                              │    Respond:      │       │
│                                              │     success      │       │
│                                              └──────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. In n8n, click **+ New Workflow**
2. Rename to: `Agent 2 — Labeling Agent (Reachy 08.4.2)`
3. Configure workflow settings:
   - **Execution Order**: `v1`
   - **Save Manual Executions**: `true`

---

### Step 2: Add the Webhook Trigger

**Node Name**: `Webhook: label.submitted`

1. Add a **Webhook** node
2. Configure:

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| HTTP Method | `POST` | Receive label submissions |
| Path | `label` | URL: `/webhook/label` |
| Response Mode | `Respond Using "Respond to Webhook" Node` | Control response timing |

**Note**: Unlike the Ingest Agent (202 async), this webhook waits for the full workflow to complete before responding. This is because labeling is a synchronous operation — the user expects immediate feedback.

---

### Step 3: Add Validation Code Node

**Node Name**: `Code: validate.payload`

This is the most important Code node you've built so far. It demonstrates **input validation** — a critical skill for production workflows.

1. Add a **Code** node after the Webhook
2. Configure:

| Parameter | Value |
|-----------|-------|
| Mode | `Run Once for All Items` |

**JavaScript Code**:

```javascript
// Validate and normalize label submission
const body = $json.body ?? $json;

// Define allowed values (business rules)
const allowedLabels = new Set([
  'happy', 'sad', 'angry', 'neutral', 'surprise', 'fearful'
]);
const allowedActions = new Set([
  'label_only', 'promote_train', 'promote_test', 'discard'
]);

// UUID generator for idempotency keys
function uuidv4() {
  return crypto.randomUUID ? crypto.randomUUID() : 
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
}

// Extract and normalize fields
const video_id = body.video_id;
const label = (body.label || '').toLowerCase();  // Normalize to lowercase
const action = body.action || 'label_only';      // Default action
const rater_id = body.rater_id || 'anonymous';   // Default rater
const notes = body.notes || '';                  // Optional notes
const idempotency_key = body.idempotency_key || uuidv4();

// Validation with clear error messages
if (!video_id) {
  throw new Error('video_id required');
}
if (!allowedLabels.has(label)) {
  throw new Error(`Invalid label: ${label}. Allowed: ${[...allowedLabels].join(', ')}`);
}
if (!allowedActions.has(action)) {
  throw new Error(`Invalid action: ${action}. Allowed: ${[...allowedActions].join(', ')}`);
}

// Return validated and normalized data
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

**Code Explanation**:

| Pattern | Purpose |
|---------|---------|
| `new Set([...])` | Fast membership check for allowed values |
| `.toLowerCase()` | Normalize case variations ("Happy" → "happy") |
| `body.action \|\| 'label_only'` | Provide sensible defaults |
| `throw new Error(...)` | Stop workflow with clear error message |
| `crypto.randomUUID()` | Generate unique idempotency key |

**Why validate in Code vs. IF nodes?**

- **Centralized**: All validation in one place
- **Clear errors**: Custom error messages
- **Extensible**: Easy to add new validations
- **Efficient**: Single node vs. multiple IF branches

---

### Step 4: Add Fetch Video Query

**Node Name**: `Postgres: fetch.video`

This query verifies the video exists before we try to label it.

1. Add a **Postgres** node
2. Connect: validate.payload → fetch.video
3. Configure:

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL Query**:

```sql
SELECT 
  v.video_id, 
  v.split, 
  v.label AS current_label, 
  v.file_path
FROM video v
WHERE v.video_id = '{{$json.video_id}}'::uuid;
```

**SQL Explanation**:

| Element | Purpose |
|---------|---------|
| `v.label AS current_label` | Alias to distinguish from new label |
| `'{{$json.video_id}}'::uuid` | Cast string to UUID type |
| `WHERE v.video_id = ?` | Find the specific video |

**What if video doesn't exist?**

The query returns empty results. In a production workflow, you'd add an IF node to check for empty results and return 404. For now, the workflow will proceed with empty data, and the next Postgres node will fail (which is acceptable for learning).

---

### Step 5: Add Apply Label Query (CTE Pattern)

**Node Name**: `Postgres: apply.label`

This is the most advanced SQL you've written. It uses a **Common Table Expression (CTE)** to:
1. Insert an audit record into `label_event`
2. Update the video's label
3. Return combined results

**All in one atomic operation!**

1. Add a **Postgres** node
2. Connect: fetch.video → apply.label
3. Configure:

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL Query**:

```sql
WITH ins AS (
  INSERT INTO label_event (
    video_id, 
    label, 
    action, 
    rater_id, 
    notes, 
    idempotency_key
  )
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
SET 
  label = '{{$json.label}}',
  updated_at = NOW()
WHERE video_id = '{{$json.video_id}}'::uuid
RETURNING 
  video_id, 
  label, 
  split,
  (SELECT event_id FROM ins) AS event_id;
```

**SQL Deep Dive**:

| Clause | Purpose |
|--------|---------|
| `WITH ins AS (...)` | CTE — execute INSERT first, name result "ins" |
| `INSERT INTO label_event` | Create audit record |
| `ON CONFLICT ... DO NOTHING` | Idempotency — skip if same video+key combo |
| `RETURNING event_id` | Get the new record's ID |
| `UPDATE video SET label = ?` | Apply the label to the video |
| `(SELECT event_id FROM ins)` | Include the audit ID in the result |

**Why CTE instead of two separate queries?**

1. **Atomicity**: Both operations succeed or both fail
2. **Efficiency**: Single round-trip to database
3. **Consistency**: No race conditions between insert and update

**Idempotency Explained**:

If someone submits the same label request twice (same video_id + idempotency_key):
- First request: INSERT succeeds, UPDATE runs
- Second request: INSERT skipped (conflict), UPDATE runs (idempotent)

This prevents duplicate audit records while still ensuring the label is applied.

---

### Step 6: Add the Switch Node (Multi-Path Routing)

**Node Name**: `Switch: branch.action`

The **Switch node** is like a multi-way IF. Instead of just True/False, it has multiple outputs based on matching conditions.

1. Add a **Switch** node
2. Connect: apply.label → branch.action
3. Configure:

**Mode**: `Rules`

**Rules** (add 4 rules):

| Rule # | Output Name | Condition |
|--------|-------------|-----------|
| 0 | `label_only` | `$json.action` equals `label_only` |
| 1 | `promote_train` | `$json.action` equals `promote_train` |
| 2 | `promote_test` | `$json.action` equals `promote_test` |
| 3 | `discard` | `$json.action` equals `discard` |

**For each rule, configure**:

```
Conditions → String → Add Condition
  Value 1: ={{$json.action}}
  Operation: Equals
  Value 2: label_only  (or promote_train, etc.)

Options:
  Rename Output: true
  Output Key: label_only  (or promote_train, etc.)
```

**Visual Result**:

The Switch node now has 4 colored outputs:
- 🔵 label_only
- 🟢 promote_train
- 🟡 promote_test
- 🔴 discard

---

### Step 7: Add Relabel HTTP Request

**Node Name**: `HTTP: mm.relabel`

This handles the `label_only` action — updating the label without moving the file.

1. Add an **HTTP Request** node
2. Connect: Switch (label_only output) → mm.relabel
3. Configure:

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel` |
| Authentication | Generic Credential Type → HTTP Header Auth |
| Credential | `Media Mover Auth` |

**Headers** (Add Header):
| Name | Value |
|------|-------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` |

**Body** (Send Body = true, JSON):
| Name | Value |
|------|-------|
| `video_id` | `={{$json.video_id}}` |
| `label` | `={{$json.label}}` |
| `correlation_id` | `={{$json.correlation_id}}` |

**⚠️ Note**: If the `/api/relabel` endpoint isn't implemented, this node will fail. You can:
1. Implement the endpoint (recommended)
2. Set **Continue On Fail** = true in node settings
3. Replace with a No-Op Code node for testing

---

### Step 8: Add Promote HTTP Request

**Node Name**: `HTTP: mm.promote`

This handles both `promote_train` and `promote_test` actions. Notice both Switch outputs connect to the **same node**!

1. Add an **HTTP Request** node
2. Connect: 
   - Switch (promote_train output) → mm.promote
   - Switch (promote_test output) → mm.promote
3. Configure:

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MEDIA_MOVER_BASE_URL}}/api/promote` |
| Authentication | Generic Credential Type → HTTP Header Auth |
| Credential | `Media Mover Auth` |

**Headers**:
| Name | Value |
|------|-------|
| `Idempotency-Key` | `={{$json.idempotency_key}}` |

**Body**:
| Name | Value |
|------|-------|
| `video_id` | `={{$json.video_id}}` |
| `dest_split` | `={{$json.action === 'promote_train' ? 'train' : 'test'}}` |
| `label` | `={{$json.label}}` |
| `correlation_id` | `={{$json.correlation_id}}` |
| `dry_run` | `false` |

**Key Expression**:

```javascript
$json.action === 'promote_train' ? 'train' : 'test'
```

This **ternary expression** determines the destination:
- If action is `promote_train` → `dest_split = "train"`
- Otherwise → `dest_split = "test"`

**Why one node for two actions?**

The logic is identical except for the destination. Using conditional expressions keeps the workflow simple.

---

### Step 9: Add Class Balance Query

**Node Name**: `Postgres: class.balance`

This query provides feedback on the training set distribution — critical for maintaining 50/50 balance.

1. Add a **Postgres** node
2. Connect **ALL paths** to this node:
   - mm.relabel → class.balance
   - mm.promote → class.balance
   - Switch (discard output) → class.balance
3. Configure:

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Execute Query` |

**SQL Query**:

```sql
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

**SQL Explanation**:

| Pattern | Purpose |
|---------|---------|
| `CASE WHEN ... THEN 1 END` | Conditional counting |
| `COUNT(CASE ...)` | Count only matching rows |
| `FILTER (WHERE ...)` | PostgreSQL-specific COUNT filter |

**Output Example**:
```json
{
  "happy_count": 45,
  "sad_count": 42,
  "total_train": 87
}
```

---

### Step 10: Add Success Response

**Node Name**: `Respond: success`

1. Add a **Respond to Webhook** node
2. Connect: class.balance → respond_success
3. Configure:

| Parameter | Value |
|-----------|-------|
| Respond With | `JSON` |

**Response Body** (this is a complex expression):

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

**Expression Deep Dive**:

| Part | Purpose |
|------|---------|
| `={{ { ... } }}` | Return a JavaScript object |
| `$json.happy_count` | Access query result |
| `Math.abs(... - ...) <= 5` | Calculate if balanced (within 5) |

**⚠️ Data Merging Issue**:

The `class.balance` node outputs query results, but we also need `video_id`, `label`, etc. from earlier nodes. In n8n, data flows forward — you can access previous node data using `$('NodeName').item.json.field`.

**Alternative Response Body** (if data is lost):

```javascript
={{
  {
    "status": "success",
    "video_id": $('Code: validate.payload').item.json.video_id,
    "label": $('Code: validate.payload').item.json.label,
    "action": $('Code: validate.payload').item.json.action,
    "class_balance": {
      "happy": $json.happy_count,
      "sad": $json.sad_count,
      "total_train": $json.total_train,
      "balanced": Math.abs($json.happy_count - $json.sad_count) <= 5
    },
    "correlation_id": $('Code: validate.payload').item.json.correlation_id
  }
}}
```

---

### Step 11: Verify Connections

Your workflow should have these connections:

```
webhook_label → validate_payload → db_fetch_video → db_apply_label → branch_action
                                                                          │
                    ┌─────────────────┬─────────────────┬─────────────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
              [label_only]     [promote_train]   [promote_test]    [discard]
                    │                 │                 │              │
                    ▼                 └────────┬────────┘              │
               mm_relabel                      │                       │
                    │                          ▼                       │
                    │                     mm_promote                   │
                    │                          │                       │
                    └──────────────────────────┼───────────────────────┘
                                               │
                                               ▼
                                        db_class_balance
                                               │
                                               ▼
                                        respond_success
```

---

## Part 3: Testing the Workflow

### Test 1: Label Only

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "YOUR_VIDEO_ID",
    "label": "happy",
    "action": "label_only",
    "rater_id": "russ@example.com"
  }'
```

**Expected**: Label updated, no file move, class balance returned.

### Test 2: Promote to Train

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "YOUR_VIDEO_ID",
    "label": "sad",
    "action": "promote_train",
    "rater_id": "russ@example.com",
    "notes": "Clear sad expression"
  }'
```

**Expected**: File moved to `/videos/train/`, database updated.

### Test 3: Invalid Label

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test-123",
    "label": "invalid_emotion",
    "action": "label_only"
  }'
```

**Expected**: Error "Invalid label: invalid_emotion"

### Test 4: Missing video_id

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "label": "happy"
  }'
```

**Expected**: Error "video_id required"

---

## Module 2 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Multi-path routing | Switch node with 4 outputs |
| CTE (WITH clause) | Atomic insert + update in one query |
| Idempotency | ON CONFLICT DO NOTHING |
| Input validation | Code node with throw Error |
| Conditional expressions | Ternary for dest_split |
| Data reference | `$('NodeName').item.json.field` |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: label.submitted | Webhook | Entry point |
| 2 | Code: validate.payload | Code | Input validation |
| 3 | Postgres: fetch.video | Postgres | Verify video exists |
| 4 | Postgres: apply.label | Postgres | Apply label + audit log |
| 5 | Switch: branch.action | Switch | Route by action type |
| 6 | HTTP: mm.relabel | HTTP Request | Label-only handler |
| 7 | HTTP: mm.promote | HTTP Request | Promotion handler |
| 8 | Postgres: class.balance | Postgres | Get class distribution |
| 9 | Respond: success | Respond to Webhook | Return results |

### Key Patterns Learned

1. **Switch for multi-path** — Multiple outputs from one decision point
2. **CTE for atomic operations** — Combine INSERT + UPDATE
3. **Validation in Code** — Centralized, clear error messages
4. **Shared downstream nodes** — Multiple inputs to one node
5. **Conditional expressions** — Ternary for dynamic values

---

## Next Steps

Proceed to **Module 3: Promotion Agent** where you'll learn:
- **Idempotency** with explicit keys
- **Dry-run patterns** for safe operations
- **Human approval gates** (optional Slack integration)
- **Manifest rebuilding** after file moves

---

*Module 2 Complete — Proceed to Module 3: Promotion Agent*
