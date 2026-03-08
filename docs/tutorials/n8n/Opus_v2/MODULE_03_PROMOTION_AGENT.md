# MODULE 03 -- Promotion/Curation Agent

**Duration:** ~4 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`
**Nodes to Wire:** 11
**Prerequisite:** MODULE 02 complete
**Outcome:** A two-phase promotion workflow with dry-run preview, human-in-the-loop approval, and manifest rebuilding

---

## 3.1 What Does the Promotion Agent Do?

The Promotion Agent implements a **human-in-the-loop approval gate** for moving videos between dataset splits. Unlike the Labeling Agent's inline promote (which is immediate), this agent provides a preview-then-approve pattern:

1. Receives a promotion request
2. Runs a **dry-run** to preview what will happen
3. Summarizes the plan for human review
4. **Waits for a second webhook** call with approval/rejection
5. If approved: executes the promotion, rebuilds manifests, emits events
6. If rejected: returns 403

### Why Two Phases?

Moving videos between splits changes the training dataset. Bad promotions can corrupt model quality. The dry-run + approval pattern prevents accidental data corruption.

```
Phase 1: Preview                     Phase 2: Execute
┌─────────────────────┐             ┌─────────────────────┐
│ Request → Dry-Run   │             │ Approve → Execute   │
│ → Summarize Plan    │────wait────►│ → Rebuild Manifest  │
│                     │             │ → Emit Event        │
└─────────────────────┘             └─────────────────────┘
```

---

## 3.2 Pre-Wiring Checklist

- [ ] **Module 02** complete
- [ ] **Media Mover** promote endpoint works: `POST /api/promote`
- [ ] **Media Mover** manifest rebuild endpoint works: `POST /api/manifest/rebuild`
- [ ] Videos exist in `temp` split to promote

---

## 3.3 Create the Workflow

1. Click **Add Workflow**
2. Name: `Agent 3 -- Promotion/Curation Agent (Reachy 08.4.2)`
3. Tags: `agent`, `promotion`, `phase4`

---

## 3.4 Wire Node 1: webhook_promotion

### Step-by-Step

1. Add a **Webhook** node → rename to `webhook_promotion`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `promotion/v1` |
| **Response Mode** | `Using 'Respond to Webhook' Node` |

---

## 3.5 Wire Node 2: validate_request

1. Add a **Code** node after `webhook_promotion` → rename to `validate_request`
2. Mode: `Run Once for All Items`
3. Code:

```javascript
const body = $input.first().json.body;

const video_id = body.video_id;
const label = body.label;
const target = body.target || 'train';

if (!video_id) throw new Error('video_id is required');
if (!label) throw new Error('label is required');
if (!['train', 'test'].includes(target)) {
  throw new Error('target must be "train" or "test"');
}

// Generate stable idempotency key from the promotion parameters
const crypto = require('crypto');
const idempotency_key = crypto
  .createHash('sha256')
  .update(`${video_id}:${label}:${target}`)
  .digest('hex')
  .substring(0, 16);

const correlation_id = 'prm-' + Date.now() + '-' +
  Math.random().toString(36).substr(2, 8);

return [{
  json: {
    video_id,
    label,
    target,
    idempotency_key,
    correlation_id,
    dry_run: true  // Phase 1 always starts with dry_run
  }
}];
```

### Key: dry_run = true

The first call to Media Mover always uses `dry_run=true`. This returns what *would* happen without making changes.

---

## 3.6 Wire Node 3: http_dryrun

1. Add an **HTTP Request** node → rename to `http_dryrun`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/promote` |
| **Authentication** | `Header Auth` → `Media Mover Auth` |
| **Body** | JSON with fields below |

Body fields:

| Field | Value |
|-------|-------|
| `video_id` | `{{ $json.video_id }}` |
| `dest_split` | `{{ $json.target }}` |
| `label` | `{{ $json.label }}` |
| `dry_run` | `true` |

---

## 3.7 Wire Node 4: summarize_plan

1. Add a **Code** node → rename to `summarize_plan`
2. Code:

```javascript
const dryRunResult = $input.first().json;
const request = $('validate_request').first().json;

const plan = {
  title: `Promote video ${request.video_id} to ${request.target}/${request.label}`,
  plan_summary: {
    video_id: request.video_id,
    from_split: dryRunResult.from_split || 'temp',
    to_split: request.target,
    label: request.label,
    file_operations: dryRunResult.file_operations || [],
    conflicts: dryRunResult.conflicts || []
  },
  approval_url: `/webhook/promotion/approve`,
  correlation_id: request.correlation_id,
  idempotency_key: request.idempotency_key
};

return [{ json: plan }];
```

### What the Approval URL Means

The `approval_url` tells the caller where to send the approval. In practice, the Streamlit UI shows the plan summary and provides "Approve" / "Reject" buttons that POST to this URL.

---

## 3.8 Wire Node 5: webhook_approval

This is the **second webhook** in the workflow -- it blocks execution until a human approves or rejects.

### Step-by-Step

1. Add a **Webhook** node → rename to `webhook_approval`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **HTTP Method** | `POST` |
| **Path** | `promotion/approve` |
| **Response Mode** | `On Received` |
| **Response Code** | `200` |

### How This Works (Two-Webhook Pattern)

This is an advanced n8n pattern. The workflow starts with `webhook_promotion`, processes through the dry-run and summary, then **pauses** at `webhook_approval` waiting for a second HTTP call. The execution remains in memory until someone POSTs to `/webhook/promotion/approve`.

The second POST should include:
```json
{
  "approved": true,
  "approver": "russ"
}
```

---

## 3.9 Wire Node 6: if_approved

1. Add an **IF** node → rename to `if_approved`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.body.approved }}` |
| **Operation** | `is equal to` |
| **Value 2** | `true` |

---

## 3.10 Wire Node 7: http_real_promote

Connected to the **true** output of `if_approved`.

1. Add an **HTTP Request** node → rename to `http_real_promote`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/promote` |
| **Authentication** | `Header Auth` → `Media Mover Auth` |

Body fields:

| Field | Value |
|-------|-------|
| `video_id` | `{{ $('validate_request').item.json.video_id }}` |
| `dest_split` | `{{ $('validate_request').item.json.target }}` |
| `label` | `{{ $('validate_request').item.json.label }}` |
| `dry_run` | `false` |

### Note: `dry_run: false`

This time we execute for real. The same endpoint, same parameters, but `dry_run=false`.

---

## 3.11 Wire Node 8: http_rebuild_manifest

1. Add an **HTTP Request** node → rename to `http_rebuild_manifest`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/manifest/rebuild` |
| **Authentication** | `Header Auth` → `Media Mover Auth` |

Body fields:

| Field | Value |
|-------|-------|
| `splits` | `["train", "test"]` |

### What Is a Manifest?

A manifest is a JSONL file listing all videos in a split with their paths and labels. The training pipeline reads this manifest to know which files to load. After promoting a video, we rebuild the manifest to include it.

---

## 3.12 Wire Node 9: emit_completed

1. Add an **HTTP Request** node → rename to `emit_completed`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.GATEWAY_BASE_URL }}/api/events/promotion` |

Body fields:

| Field | Value |
|-------|-------|
| `event_type` | `promotion.completed` |
| `video_id` | `{{ $('validate_request').item.json.video_id }}` |
| `dest_split` | `{{ $('validate_request').item.json.target }}` |
| `label` | `{{ $('validate_request').item.json.label }}` |
| `dataset_hash` | `{{ $json.dataset_hash }}` |
| `correlation_id` | `{{ $('validate_request').item.json.correlation_id }}` |

---

## 3.13 Wire Node 10: respond_success

1. Add a **Respond to Webhook** node → rename to `respond_success`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Response Code** | `200` |
| **Response Body** | JSON |

```json
{
  "status": "promoted",
  "video_id": "{{ $('validate_request').item.json.video_id }}",
  "dest_split": "{{ $('validate_request').item.json.target }}",
  "label": "{{ $('validate_request').item.json.label }}",
  "dataset_hash": "{{ $('http_rebuild_manifest').item.json.dataset_hash }}"
}
```

---

## 3.14 Wire Node 11: respond_rejected

Connected to the **false** output of `if_approved`.

1. Add a **Respond to Webhook** node → rename to `respond_rejected`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Response Code** | `403` |
| **Response Body** | JSON |

```json
{
  "status": "rejected",
  "message": "Promotion was rejected by approver"
}
```

---

## 3.15 Final Connection Map

```
webhook_promotion ──► validate_request ──► http_dryrun ──► summarize_plan
                                                                  │
                                                                  ▼
                                                          webhook_approval
                                                                  │
                                                                  ▼
                                                            if_approved
                                                           │          │
                                                     [true]          [false]
                                                        │               │
                                                        ▼               ▼
                                                http_real_promote  respond_rejected
                                                        │
                                                        ▼
                                              http_rebuild_manifest
                                                        │
                                                        ▼
                                                  emit_completed
                                                        │
                                                        ▼
                                                 respond_success
```

---

## 3.16 Testing

### Test Phase 1: Request Promotion

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/promotion/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<real video_id>",
    "label": "happy",
    "target": "train"
  }'
```

**Expected:** Dry-run results with plan summary.

### Test Phase 2: Approve

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/promotion/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "approver": "russ"}'
```

**Expected:** 200 with promoted status.

### Test Phase 2: Reject

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/promotion/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": false}'
```

**Expected:** 403 with rejected status.

---

## 3.17 Key Concepts Learned

- **Two-Webhook Pattern** -- using two webhook nodes in one workflow for human-in-the-loop approval
- **Dry-Run / Execute Pattern** -- same API, same params, toggle `dry_run` flag
- **Manifest Rebuilding** -- regenerating JSONL index files after dataset changes
- **Idempotency Keys** -- SHA256-based keys from stable input parameters
- **Event Emission** -- notifying downstream systems about dataset changes

---

*Previous: [MODULE 02 -- Labeling Agent](MODULE_02_LABELING_AGENT.md)*
*Next: [MODULE 04 -- Reconciler Agent](MODULE_04_RECONCILER_AGENT.md)*
