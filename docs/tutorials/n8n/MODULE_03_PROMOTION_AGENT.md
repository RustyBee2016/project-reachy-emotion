# Module 3: Promotion Agent — Two-Phase Approval & Dry-Run Patterns

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~4 hours  
**Prerequisites**: Completed Modules 0-2

---

## Learning Objectives

By the end of this module, you will:
1. Implement a **two-phase approval workflow** (dry-run → approval → execute)
2. Use **multiple webhooks** within one workflow for human-in-the-loop patterns
3. Generate **stable idempotency keys** using cryptographic hashing
4. Chain **API calls** with data merging between steps
5. Understand the **manifest rebuild** pattern for dataset consistency

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **Two-phase approval** | Multiple Webhooks | Production safety for destructive operations |
| **Dry-run pattern** | HTTP Request with flag | Preview changes before committing |
| **Stable idempotency** | SHA256 hash of content | Same request = same key, every time |
| **Workflow pausing** | Second webhook as gate | Human approval checkpoint |
| **Manifest rebuild** | POST-commit action | Keep training data manifests in sync |

---

## Pre-Wiring Checklist: Backend Functionality Verification

> **CRITICAL**: This workflow modifies files. Complete ALL verifications before wiring.

### Functionality Checklist

| # | Node | Backend Functionality | Endpoint/Service | Status |
|---|------|----------------------|------------------|--------|
| 1 | Webhook: request.promotion | n8n webhook server | `POST /webhook/promotion/v1` | ⬜ |
| 2 | Code: validate.request | JavaScript runtime | (native) | ⬜ |
| 3 | HTTP: dryrun.promote | Media Mover API | `POST /api/promote` (dry_run=true) | ⬜ |
| 4 | Code: summarize.plan | JavaScript runtime | (native) | ⬜ |
| 5 | Webhook: await.approval | n8n webhook server | `POST /webhook/promotion/approve` | ⬜ |
| 6 | IF: approved? | n8n conditional | (native) | ⬜ |
| 7 | HTTP: real.promote | Media Mover API | `POST /api/promote` (dry_run=false) | ⬜ |
| 8 | HTTP: rebuild.manifest | Media Mover API | `POST /api/manifest/rebuild` | ⬜ |
| 9 | HTTP: emit.completed | Gateway API | `POST /api/events/promotion` | ⬜ |
| 10 | Respond: success | n8n response | (native) | ⬜ |
| 11 | Respond: rejected | n8n response | (native) | ⬜ |

---

### Verification Procedures

#### Test 1: Promote Endpoint (Dry-Run Mode)

```bash
curl -X POST http://10.0.4.130:8083/api/promote \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Idempotency-Key: test-dryrun-001" \
  -d '{
    "video_id": "test-video-id",
    "dest_split": "train",
    "label": "happy",
    "dry_run": true,
    "correlation_id": "test-001"
  }'
```

**Expected Response**:
```json
{
  "status": "ok",
  "src": "/videos/temp/test-video-id.mp4",
  "dst": "/videos/train/test-video-id.mp4",
  "dry_run": true
}
```

**Status**: ⬜ → [ ] Complete

---

#### Test 2: Manifest Rebuild Endpoint

```bash
curl -X POST http://10.0.4.130:8083/api/manifest/rebuild \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "splits": ["train", "test"]
  }'
```

**Expected Response**:
```json
{
  "status": "ok",
  "manifests_rebuilt": ["train", "test"],
  "train_count": 50,
  "test_count": 20
}
```

**Status**: ⬜ → [ ] Complete

---

#### Test 3: Events Endpoint (Promotion)

```bash
curl -X POST http://10.0.4.140:8000/api/events/promotion \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "promotion.completed",
    "video_id": "test-id",
    "dest_split": "train",
    "correlation_id": "test-001"
  }'
```

**⚠️ TBD**: This endpoint may not exist yet. If it returns 404, you can either:
1. Implement it (recommended)
2. Set "Continue On Fail" on the node
3. Skip this node during testing

**Status**: ⬜ → [ ] Complete (or N/A)

---

## Part 1: Understanding Two-Phase Approval

### Why Two-Phase?

Moving files between directories is a **destructive operation** — if done wrong, you could:
- Corrupt your training dataset
- Create duplicates
- Lose data

The two-phase pattern provides safety:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TWO-PHASE APPROVAL PATTERN                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1: DRY-RUN (Preview)                                             │
│  ──────────────────────────────                                         │
│  1. Request received                                                    │
│  2. Validate inputs                                                     │
│  3. Call API with dry_run=true                                          │
│  4. API returns WHAT WOULD HAPPEN (no changes made)                     │
│  5. Generate human-readable summary                                     │
│                                                                         │
│  PHASE 2: APPROVAL (Human Gate)                                         │
│  ──────────────────────────────                                         │
│  6. Workflow PAUSES                                                     │
│  7. Human reviews plan                                                  │
│  8. Human sends approval/rejection to second webhook                    │
│                                                                         │
│  PHASE 3: EXECUTION (If Approved)                                       │
│  ──────────────────────────────                                         │
│  9. Call API with dry_run=false                                         │
│  10. Files actually move                                                │
│  11. Rebuild manifests                                                  │
│  12. Emit completion event                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Workflow Architecture

```
Webhook: request.promotion ──► Code: validate.request ──► HTTP: dryrun.promote
                                                                    │
                                                                    ▼
                                                         Code: summarize.plan
                                                                    │
                                                                    ▼
                                                 ┌─── Webhook: await.approval ◄── (Human sends approval)
                                                 │              │
                                                 │              ▼
                                                 │       IF: approved?
                                                 │        │         │
                                                 │   [True]         [False]
                                                 │        │              │
                                                 │        ▼              ▼
                                                 │ HTTP: real.promote  Respond: rejected
                                                 │        │
                                                 │        ▼
                                                 │ HTTP: rebuild.manifest
                                                 │        │
                                                 │        ▼
                                                 │ HTTP: emit.completed
                                                 │        │
                                                 │        ▼
                                                 └─► Respond: success
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create new workflow: `Agent 3 — Promotion Agent (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`, Save Manual Executions = `true`

---

### Step 2: Add Request Webhook

**Node Name**: `Webhook: request.promotion`

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `promotion/v1` |
| Response Mode | `Respond Using "Respond to Webhook" Node` |

---

### Step 3: Add Validation with Stable Idempotency Key

**Node Name**: `Code: validate.request`

This code demonstrates **stable idempotency key generation** — the same content always produces the same key.

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

// Generate STABLE idempotency key
// Same inputs = same key = idempotent operation
const crypto = require('crypto');
const keySource = `${body.video_id}|${target}|${body.label}`;
const idem = body.idempotency_key || crypto.createHash('sha256')
  .update(keySource)
  .digest('hex')
  .slice(0, 32);

return [{
  json: {
    video_id: body.video_id,
    label: body.label,
    target,
    idempotency_key: idem,
    correlation_id: body.correlation_id || `promo-${Date.now()}`,
    dry_run: true  // Always start with dry-run
  }
}];
```

**Key Pattern**: Stable Idempotency
```javascript
// Input: video_id=abc123, target=train, label=happy
// Hash of: "abc123|train|happy"
// Always produces: "7f83b1657ff1fc53b92dc18148a1d65d"
```

---

### Step 4: Add Dry-Run HTTP Request

**Node Name**: `HTTP: dryrun.promote`

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
| `dest_split` | `={{$json.target}}` |
| `label` | `={{$json.label}}` |
| `dry_run` | `true` |
| `correlation_id` | `={{$json.correlation_id}}` |

**Note**: `dry_run: true` means the API validates and returns what WOULD happen, but makes no changes.

---

### Step 5: Add Plan Summary

**Node Name**: `Code: summarize.plan`

This code accesses data from **previous nodes** to build a summary:

```javascript
// Summarize dry-run plan for human approval
const plan = $json;  // Response from dry-run

return [{
  json: {
    approval_request: {
      title: 'Video Promotion Request',
      video_id: $('Code: validate.request').item.json.video_id,
      label: $('Code: validate.request').item.json.label,
      target_split: $('Code: validate.request').item.json.target,
      plan_summary: {
        source: plan.src,
        destination: plan.dst,
        will_update_db: true,
        dry_run_status: plan.status
      },
      // Pass through for later use
      correlation_id: $('Code: validate.request').item.json.correlation_id,
      idempotency_key: $('Code: validate.request').item.json.idempotency_key
    }
  }
}];
```

**Key Pattern**: Node Reference
```javascript
$('NodeName').item.json.fieldName
```

---

### Step 6: Add Approval Webhook (The Pause Point)

**Node Name**: `Webhook: await.approval`

This is the **human gate** — the workflow pauses here until someone calls this webhook.

| Parameter | Value |
|-----------|-------|
| HTTP Method | `POST` |
| Path | `promotion/approve` |
| Response Mode | `When Last Node Finishes` |

**How the pause works**:
1. Workflow reaches this node
2. n8n execution waits for an incoming HTTP request
3. Human reviews the plan (from previous step)
4. Human sends POST to `/webhook/promotion/approve` with approval decision
5. Workflow resumes with approval data

---

### Step 7: Add Approval Check

**Node Name**: `IF: approved?`

| Parameter | Value |
|-----------|-------|
| Condition Type | Boolean |
| Value 1 | `={{$json.body.approved}}` or `={{$json.approved}}` |
| Operation | `equals` |
| Value 2 | `true` |

---

### Step 8: Add Real Promotion

**Node Name**: `HTTP: real.promote`

Connect: IF (True branch) → real.promote

Same as dry-run, but with `dry_run: false`:

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MEDIA_MOVER_BASE_URL}}/api/promote` |

**Body** (key difference):
| Name | Value |
|------|-------|
| `dry_run` | `false` |

---

### Step 9: Add Manifest Rebuild

**Node Name**: `HTTP: rebuild.manifest`

After promotion, rebuild manifests to keep training data consistent:

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.MEDIA_MOVER_BASE_URL}}/api/manifest/rebuild` |

**Body**:
```json
{
  "splits": ["train", "test"]
}
```

---

### Step 10: Add Event Emission

**Node Name**: `HTTP: emit.completed`

| Parameter | Value |
|-----------|-------|
| Method | `POST` |
| URL | `={{$env.GATEWAY_BASE_URL}}/api/events/promotion` |

**Body**:
| Name | Value |
|------|-------|
| `event_type` | `promotion.completed` |
| `video_id` | `={{$json.video_id}}` |
| `dest_split` | `={{$json.target_split}}` |
| `correlation_id` | `={{$json.correlation_id}}` |

---

### Step 11: Add Response Nodes

**Node Name**: `Respond: success`

| Parameter | Value |
|-----------|-------|
| Respond With | JSON |
| Response Body | See below |

```javascript
={{
  {
    "status": "success",
    "video_id": $json.video_id,
    "dest_split": $json.target_split,
    "correlation_id": $json.correlation_id
  }
}}
```

**Node Name**: `Respond: rejected`

Connect: IF (False branch) → rejected

| Parameter | Value |
|-----------|-------|
| Respond With | JSON |
| Response Code | `403` |

```javascript
={{
  {
    "status": "rejected",
    "message": "Promotion not approved",
    "correlation_id": $json.correlation_id
  }
}}
```

---

## Part 3: Testing the Two-Phase Flow

### Test 1: Request Promotion (Phase 1)

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/promotion/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "test-video-123",
    "label": "happy",
    "target": "train"
  }'
```

**Expected**: Workflow pauses at await.approval node. Check execution history — it should show "waiting".

### Test 2: Approve (Phase 2)

In a **new terminal**, send approval:

```bash
curl -X POST http://10.0.4.130:5678/webhook/promotion/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "video_id": "test-video-123",
    "target_split": "train",
    "label": "happy",
    "correlation_id": "promo-xxx",
    "idempotency_key": "xxx",
    "approver": "russ@example.com"
  }'
```

**Expected**: First workflow resumes, executes promotion, returns success.

### Test 3: Rejection

```bash
curl -X POST http://10.0.4.130:5678/webhook/promotion/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "video_id": "test-video-123"
  }'
```

**Expected**: HTTP 403 with "Promotion not approved".

---

## Part 4: Production Considerations

### Approval Timeout

In production, you should add a timeout:

```javascript
// In Code node before await.approval
const approvalDeadline = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours
return [{
  json: {
    ...items[0].json,
    approval_deadline: approvalDeadline.toISOString()
  }
}];
```

### Approval Validation

The approval request should be validated to match the original:

```javascript
// In Code node after await.approval
const original = $('Code: summarize.plan').item.json.approval_request;
const approval = $json.body || $json;

if (approval.video_id !== original.video_id ||
    approval.target_split !== original.target_split) {
  throw new Error('Approval does not match original request');
}
```

---

## Module 3 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| Two-phase approval | Request → Dry-run → Pause → Approve → Execute |
| Stable idempotency | SHA256 hash of content |
| Workflow pause | Second webhook as gate |
| Data forwarding | `$('NodeName').item.json.field` |
| Manifest sync | POST-commit rebuild |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Webhook: request.promotion | Webhook | Entry point |
| 2 | Code: validate.request | Code | Validation + idempotency |
| 3 | HTTP: dryrun.promote | HTTP Request | Preview changes |
| 4 | Code: summarize.plan | Code | Human-readable summary |
| 5 | Webhook: await.approval | Webhook | Human gate |
| 6 | IF: approved? | IF | Route by decision |
| 7 | HTTP: real.promote | HTTP Request | Execute promotion |
| 8 | HTTP: rebuild.manifest | HTTP Request | Sync manifests |
| 9 | HTTP: emit.completed | HTTP Request | Event emission |
| 10 | Respond: success | Respond to Webhook | Success response |
| 11 | Respond: rejected | Respond to Webhook | Rejection response |

---

## Next Steps

Proceed to **Module 4: Reconciler Agent** where you'll learn:
- **Scheduled triggers** (cron expressions)
- **SSH commands** for filesystem scanning
- **Parallel execution** (multiple paths from one trigger)
- **Email notifications** for alerts

---

*Module 3 Complete — Proceed to Module 4: Reconciler Agent*
