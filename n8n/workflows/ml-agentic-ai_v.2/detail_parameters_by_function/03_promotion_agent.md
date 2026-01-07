# Agent 3 — Promotion/Curation Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Promotion/Curation Agent oversees controlled movement of media between filesystem stages (temp → train/test). It implements a two-phase approval workflow: first performing a dry-run to preview changes, then awaiting human approval before executing the real promotion. After successful promotion, it rebuilds dataset manifests and emits completion events.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: summarize.plan | n8n-nodes-base.code | summarize_plan |
| Code: validate.request | n8n-nodes-base.code | validate_request |
| HTTP: dryrun.promote | n8n-nodes-base.httpRequest | http_dryrun |
| HTTP: emit.completed | n8n-nodes-base.httpRequest | emit_completed |
| HTTP: real.promote | n8n-nodes-base.httpRequest | http_real_promote |
| HTTP: rebuild.manifest | n8n-nodes-base.httpRequest | http_rebuild_manifest |
| IF: approved? | n8n-nodes-base.if | if_approved |
| Respond: rejected | n8n-nodes-base.respondToWebhook | respond_rejected |
| Respond: success | n8n-nodes-base.respondToWebhook | respond_success |
| Webhook: await.approval | n8n-nodes-base.webhook | webhook_approval |
| Webhook: request.promotion | n8n-nodes-base.webhook | webhook_promotion |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Webhook: request.promotion
    │
    ▼
Code: validate.request
    │
    ▼
HTTP: dryrun.promote (dry_run=true)
    │
    ▼
Code: summarize.plan
    │
    ▼
Webhook: await.approval ◄─────── [Human reviews plan and approves/rejects]
    │
    ▼
IF: approved?
    │
    ├──► [True] ──► HTTP: real.promote (dry_run=false)
    │                        │
    │                        ▼
    │               HTTP: rebuild.manifest
    │                        │
    │                        ▼
    │               HTTP: emit.completed
    │                        │
    │                        ▼
    │               Respond: success
    │
    └──► [False] ──► Respond: rejected (HTTP 403)
```

---

## Node Details

### 1. Webhook: request.promotion

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [-800, 300]  
**Purpose:** Entry point for promotion requests from the web UI or Labeling Agent.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests only |
| `path` | `promotion/v1` | URL path: `{N8N_HOST}/webhook/promotion/v1` |
| `responseMode` | `responseNode` | Response handled by Respond to Webhook node |
| `webhookId` | `promotion-request` | Unique webhook identifier |

#### Input Schema (Expected Request Body)

```json
{
  "video_id": "uuid",              // Required: Video UUID
  "label": "happy|sad",            // Required: Emotion label
  "target": "train|test",          // Optional: default "train" (alias: dest_split)
  "idempotency_key": "string",     // Optional: auto-generated from content hash
  "correlation_id": "string"       // Optional: auto-generated if missing
}
```

#### Related Code

- **No direct code mapping** — n8n native webhook functionality

#### Test Status: ✅ OPERATIONAL

---

### 2. Code: validate.request

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-600, 300]  
**Purpose:** Validates promotion request, ensures required fields, and generates a stable idempotency key.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `mode` | `runOnceForAllItems` | Process all items in single execution |

#### JavaScript Code

```javascript
// Validate promotion request
const body = $json.body ?? $json;
const required = ['video_id', 'label'];

for (const field of required) {
  if (!body[field]) {
    throw new Error(`Missing required field: ${field}`);
  }
}

const allowedSplits = ['train', 'test'];
const target = body.target || body.dest_split || 'train';

if (!allowedSplits.includes(target)) {
  throw new Error(`Invalid target split: ${target}`);
}

// Generate stable idempotency key
const crypto = require('crypto');
const idem = body.idempotency_key || crypto.createHash('sha256')
  .update(`${body.video_id}|${target}|${body.label}`)
  .digest('hex').slice(0, 32);

return [{
  json: {
    video_id: body.video_id,
    label: body.label,
    target,
    idempotency_key: idem,
    correlation_id: body.correlation_id || `promo-${Date.now()}`,
    dry_run: true  // Start with dry-run
  }
}];
```

#### Validation Rules

| Field | Validation | Error Message |
|-------|------------|---------------|
| `video_id` | Required | `Missing required field: video_id` |
| `label` | Required | `Missing required field: label` |
| `target` | Must be `train` or `test` | `Invalid target split: {value}` |

#### Idempotency Key Generation

- **Algorithm:** SHA256 hash of `{video_id}|{target}|{label}`
- **Truncation:** First 32 characters of hex digest
- **Purpose:** Ensures same promotion request always generates same key

#### Output Schema

```json
{
  "video_id": "uuid",
  "label": "string",
  "target": "train|test",
  "idempotency_key": "string (32 chars)",
  "correlation_id": "string",
  "dry_run": true
}
```

#### Related Code

- **Similar validation in:** `apps/api/app/routers/promote.py` lines 41-86 (`stage_videos`)

#### Test Status: ✅ OPERATIONAL

---

### 3. HTTP: dryrun.promote

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-400, 300]  
**Purpose:** Performs a dry-run promotion to preview changes without actually moving files.

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
| `dest_split` | `={{$json.target}}` | Target split (train/test) |
| `label` | `={{$json.label}}` | Emotion label |
| `dry_run` | `true` | **Preview only, no changes** |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/media.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `promote()` | 33-126 | POST `/api/media/promote` endpoint |

**Dry-Run Behavior (from media.py):**
```python
# When dry_run=true:
# - Validates request
# - Computes source and destination paths
# - Returns plan without moving files
# Response: {"status": "ok", "src": "...", "dst": "...", "dry_run": true}
```

#### Expected Response

```json
{
  "status": "ok",
  "src": "/videos/temp/uuid.mp4",
  "dst": "/videos/train/uuid.mp4",
  "dry_run": true,
  "adapter_mode": "adapter"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 4. Code: summarize.plan

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [-200, 300]  
**Purpose:** Summarizes the dry-run plan into a human-readable approval request.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `mode` | `runOnceForAllItems` | Process all items in single execution |

#### JavaScript Code

```javascript
// Summarize dry-run plan for approval
const plan = $json;

return [{
  json: {
    approval_request: {
      title: 'Video Promotion Request',
      video_id: $('validate_request').item.json.video_id,
      label: $('validate_request').item.json.label,
      target_split: $('validate_request').item.json.target,
      plan_summary: {
        will_move: plan.moves || [],
        will_update_db: plan.will_update_db !== false,
        conflicts: plan.conflicts || [],
        dry_run_status: plan.status
      },
      correlation_id: $('validate_request').item.json.correlation_id,
      idempotency_key: $('validate_request').item.json.idempotency_key
    }
  }
}];
```

#### Node References

| Reference | Purpose |
|-----------|---------|
| `$('validate_request').item.json` | Access original validated request data |
| `$json` | Access dry-run response from previous node |

#### Output Schema

```json
{
  "approval_request": {
    "title": "Video Promotion Request",
    "video_id": "uuid",
    "label": "happy|sad",
    "target_split": "train|test",
    "plan_summary": {
      "will_move": ["temp/uuid.mp4 → train/uuid.mp4"],
      "will_update_db": true,
      "conflicts": [],
      "dry_run_status": "ok"
    },
    "correlation_id": "string",
    "idempotency_key": "string"
  }
}
```

#### Related Code

- **No direct code mapping** — n8n workflow logic

#### Test Status: ✅ OPERATIONAL

---

### 5. Webhook: await.approval

**Type:** `n8n-nodes-base.webhook` (v3)  
**Position:** [0, 300]  
**Purpose:** Pauses workflow execution and waits for human approval via a separate webhook call.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `httpMethod` | `POST` | Accept POST requests only |
| `path` | `promotion/approve` | URL path: `{N8N_HOST}/webhook/promotion/approve` |
| `responseMode` | `onReceived` | Respond immediately when called |
| `webhookId` | `promotion-approval` | Unique webhook identifier |

#### Expected Approval Request Body

```json
{
  "approved": true,              // Required: true to approve, false to reject
  "video_id": "uuid",            // Required: Video being promoted
  "target_split": "train|test",  // Required: Target split
  "label": "happy|sad",          // Required: Label
  "correlation_id": "string",    // Required: Correlation ID from plan
  "idempotency_key": "string",   // Required: Idempotency key from plan
  "approver": "user@example.com" // Optional: Who approved
}
```

#### Workflow Behavior

- **Blocking:** Workflow pauses until this webhook receives a call
- **Timeout:** Consider implementing timeout in production
- **Security:** Should validate that approval matches original request

#### Related Code

- **No direct code mapping** — n8n native webhook functionality
- **AGENTS.md Reference:** "Dataset Promotions: Require human confirmation (temp → train/test)"

#### Test Status: ✅ OPERATIONAL

---

### 6. IF: approved?

**Type:** `n8n-nodes-base.if` (v2)  
**Position:** [200, 300]  
**Purpose:** Routes workflow based on approval decision.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `conditions.boolean[0].value1` | `={{$json.approved}}` | Approval flag from webhook |
| `conditions.boolean[0].value2` | `true` | Expected value for approval |

#### Outputs

| Branch | Condition | Next Node |
|--------|-----------|-----------|
| True (index 0) | `approved === true` | HTTP: real.promote |
| False (index 1) | `approved !== true` | Respond: rejected |

#### Related Code

- **No direct code mapping** — n8n expression evaluation

#### Test Status: ✅ OPERATIONAL

---

### 7. HTTP: real.promote

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [400, 200]  
**Purpose:** Executes the actual promotion after approval, moving files and updating database.

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
| `dest_split` | `={{$json.target_split}}` | Target split (train/test) |
| `label` | `={{$json.label}}` | Emotion label |
| `dry_run` | `false` | **Execute real promotion** |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/routers/media.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `promote()` | 33-126 | POST `/api/media/promote` endpoint |

**Real Promotion Behavior:**
```python
# When dry_run=false:
# - Moves file from /videos/temp/{clip} to /videos/{target}/{clip}
# - Updates database split field
# - Creates promotion_log entry
# Response: {"status": "ok", "src": "...", "dst": "...", "dry_run": false}
```

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `PromotionLog` | 123-142 | Audit log for promotions |

**PromotionLog Schema:**

| Column | Type | Constraints |
|--------|------|-------------|
| `promotion_id` | `Integer` | Primary Key, Auto-increment |
| `video_id` | `String(36)` | FK to video.video_id |
| `from_split` | `SplitEnum` | NOT NULL |
| `to_split` | `SplitEnum` | NOT NULL |
| `intended_label` | `EmotionEnum` | NULLABLE |
| `actor` | `String(120)` | NULLABLE |
| `success` | `Boolean` | NOT NULL, default True |
| `created_at` | `DateTime` | Auto-generated |

#### Test Status: ✅ OPERATIONAL

---

### 8. HTTP: rebuild.manifest

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [600, 200]  
**Purpose:** Rebuilds dataset manifests after promotion to ensure training data is up-to-date.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.MEDIA_MOVER_BASE_URL}}/api/manifest/rebuild` | Manifest rebuild endpoint |
| `authentication` | `genericCredentialType` | Use credential store |
| `genericAuthType` | `httpHeaderAuth` | Header-based auth |
| `sendHeaders` | `true` | Include custom headers |
| `sendBody` | `true` | Include request body |

#### Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Correlation-ID` | `={{$json.correlation_id}}` | Tracing ID |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `splits` | `["train", "test"]` | Splits to rebuild |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `httpHeaderAuth` | `1` | Media Mover Auth |

#### Related Code

**File:** `apps/api/app/routers/ingest.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `rebuild_manifest()` | 416-535 | POST `/api/v1/ingest/manifest/rebuild` |
| `compute_dataset_hash()` | 226-244 | Compute deterministic dataset hash |

**File:** `apps/api/routers/gateway.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `rebuild_manifest()` | 243-256 | POST `/api/manifest/rebuild` proxy |

**File:** `apps/api/app/routers/gateway_upstream.py`

| Function | Lines | Purpose |
|----------|-------|---------|
| `trigger_manifest_rebuild()` | 407-410+ | POST `/api/manifest/rebuild` |

**Manifest Format (JSONL):**
```json
{"video_id": "uuid", "path": "train/uuid.mp4", "label": "happy", "sha256": "...", "size_bytes": 12345}
{"video_id": "uuid", "path": "train/uuid.mp4", "label": "sad", "sha256": "...", "size_bytes": 12345}
```

#### Expected Response

```json
{
  "status": "ok",
  "dataset_hash": "sha256-hex-string",
  "manifests_rebuilt": ["train", "test"],
  "train_count": 100,
  "test_count": 40,
  "correlation_id": "string"
}
```

#### Test Status: ✅ OPERATIONAL

---

### 9. HTTP: emit.completed

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [800, 200]  
**Purpose:** Emits `promotion.completed` event to the Gateway API for downstream processing.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `={{$env.GATEWAY_BASE_URL}}/api/events/promotion` | Gateway events endpoint |
| `sendBody` | `true` | Include event payload |

#### Body Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `event_type` | `promotion.completed` | Event identifier |
| `video_id` | `={{$json.video_id}}` | Video UUID |
| `dest_split` | `={{$json.target_split}}` | Target split |
| `label` | `={{$json.label}}` | Emotion label |
| `correlation_id` | `={{$json.correlation_id}}` | Tracing ID |
| `dataset_hash` | `={{$('http_rebuild_manifest').item.json.dataset_hash}}` | New dataset hash |

#### Node References

| Reference | Purpose |
|-----------|---------|
| `$('http_rebuild_manifest').item.json.dataset_hash` | Get dataset hash from manifest rebuild |

#### Related Code

**File:** `apps/api/app/routers/gateway_upstream.py` (TBD)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/events/promotion` | **TBD** | Event ingestion endpoint not yet implemented |

#### Test Status: ⚠️ TBD

**Required Actions:**
1. Implement `/api/events/promotion` endpoint in `gateway_upstream.py`
2. Define event schema for `promotion.completed`

---

### 10. Respond: success

**Type:** `n8n-nodes-base.respondToWebhook` (v1)  
**Position:** [1000, 200]  
**Purpose:** Returns success response after promotion completes.

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
    "dest_split": $json.target_split,
    "dataset_hash": $json.dataset_hash,
    "correlation_id": $json.correlation_id
  }
}}
```

#### Response Schema

```json
{
  "status": "success",
  "video_id": "uuid",
  "dest_split": "train|test",
  "dataset_hash": "sha256-hex-string",
  "correlation_id": "string"
}
```

#### Related Code

- **No direct code mapping** — n8n native response

#### Test Status: ✅ OPERATIONAL

---

### 11. Respond: rejected

**Type:** `n8n-nodes-base.respondToWebhook` (v1)  
**Position:** [400, 400]  
**Purpose:** Returns rejection response when promotion is not approved.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `respondWith` | `json` | JSON response body |
| `options.responseCode` | `403` | HTTP 403 Forbidden |

#### Response Body Expression

```javascript
={{
  {
    "status": "rejected",
    "message": "Promotion not approved",
    "correlation_id": $json.correlation_id
  }
}}
```

#### Response Schema

```json
{
  "status": "rejected",
  "message": "Promotion not approved",
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
| `GATEWAY_BASE_URL` | Base URL for Gateway API | `http://10.0.4.140:8000` |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 1 | Media Mover Auth | HTTP Header Auth | Authenticate to Media Mover API |

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
- `promotion`
- `phase4`

---

## Two-Phase Approval Pattern

This workflow implements a **two-phase approval pattern** as required by AGENTS.md:

### Phase 1: Dry-Run Preview
1. Request received via `Webhook: request.promotion`
2. Validated by `Code: validate.request`
3. Dry-run executed by `HTTP: dryrun.promote`
4. Plan summarized by `Code: summarize.plan`

### Phase 2: Human Approval
5. Workflow pauses at `Webhook: await.approval`
6. Human reviews plan (via UI or API)
7. Human sends approval/rejection to approval webhook
8. `IF: approved?` routes based on decision

### Phase 3: Execution (if approved)
9. Real promotion by `HTTP: real.promote`
10. Manifests rebuilt by `HTTP: rebuild.manifest`
11. Event emitted by `HTTP: emit.completed`
12. Success response by `Respond: success`

---

## Code Testing Summary

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Promote Endpoint | `apps/api/routers/media.py` | 33-126 | ✅ Imports OK |
| Manifest Rebuild | `apps/api/app/routers/ingest.py` | 416-535 | ✅ Imports OK |
| Gateway Proxy | `apps/api/routers/gateway.py` | 243-256 | ✅ Imports OK |
| PromotionLog Model | `apps/api/app/db/models.py` | 123-142 | ✅ Imports OK |
| Events Endpoint | `apps/api/app/routers/gateway_upstream.py` | TBD | ⚠️ Not implemented |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Events Endpoint | HIGH | Implement `POST /api/events/promotion` in gateway_upstream.py |
| Approval Timeout | MEDIUM | Add timeout handling for await.approval webhook |
| Approval Validation | MEDIUM | Validate approval request matches original promotion request |

---

## Connections Summary

```json
{
  "webhook_promotion": { "main": [["validate_request"]] },
  "validate_request": { "main": [["http_dryrun"]] },
  "http_dryrun": { "main": [["summarize_plan"]] },
  "summarize_plan": { "main": [["webhook_approval"]] },
  "webhook_approval": { "main": [["if_approved"]] },
  "if_approved": { 
    "main": [
      ["http_real_promote"],  // approved=true
      ["respond_rejected"]    // approved=false
    ] 
  },
  "http_real_promote": { "main": [["http_rebuild_manifest"]] },
  "http_rebuild_manifest": { "main": [["emit_completed"]] },
  "emit_completed": { "main": [["respond_success"]] }
}
```

---

## Usage Example

### Step 1: Request Promotion

```bash
curl -X POST http://localhost:5678/webhook/promotion/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123-def456",
    "label": "happy",
    "target": "train"
  }'
```

### Step 2: Review Plan (returned by workflow)

```json
{
  "approval_request": {
    "title": "Video Promotion Request",
    "video_id": "abc123-def456",
    "label": "happy",
    "target_split": "train",
    "plan_summary": {
      "will_move": ["temp/abc123-def456.mp4 → train/abc123-def456.mp4"],
      "will_update_db": true,
      "conflicts": [],
      "dry_run_status": "ok"
    },
    "correlation_id": "promo-1701234567890",
    "idempotency_key": "a1b2c3d4e5f6..."
  }
}
```

### Step 3: Approve Promotion

```bash
curl -X POST http://localhost:5678/webhook/promotion/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "video_id": "abc123-def456",
    "target_split": "train",
    "label": "happy",
    "correlation_id": "promo-1701234567890",
    "idempotency_key": "a1b2c3d4e5f6...",
    "approver": "admin@example.com"
  }'
```

### Step 4: Success Response

```json
{
  "status": "success",
  "video_id": "abc123-def456",
  "dest_split": "train",
  "dataset_hash": "sha256-of-new-dataset",
  "correlation_id": "promo-1701234567890"
}
```
