# MODULE 02 -- Labeling Agent

**Duration:** ~3 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
**Nodes to Wire:** 9
**Prerequisite:** MODULE 01 complete
**Outcome:** A workflow that processes human label submissions, applies labels to videos, routes actions (label-only, promote, discard), and reports class balance

---

## 2.1 What Does the Labeling Agent Do?

After a video is ingested (Module 01), a human reviewer watches it and assigns an emotion label. The Labeling Agent:

1. Receives the label submission via webhook
2. Validates the label is one of the 3 allowed classes
3. Validates the action (label-only, promote to train/test, discard)
4. Fetches the current video record from the database
5. Atomically applies the label using a CTE (Common Table Expression)
6. Routes to the appropriate file-system action via a Switch node
7. Reports the current class balance

### Architecture Context

```
 Human Reviewer ────►  LABELING AGENT (Agent 2)
 (via Streamlit)       │
                       ├──► PostgreSQL (label_event + video update)
                       ├──► Media Mover (relabel or promote files)
                       └──► Response with class balance stats
```

---

## 2.2 Pre-Wiring Checklist

- [ ] **Module 01** is complete and tested
- [ ] **PostgreSQL** has the `label_event` table:
  ```bash
  psql -h localhost -U reachy_dev -d reachy_emotion -c "\d label_event"
  ```
- [ ] **Media Mover** relabel and promote endpoints are available
- [ ] At least one video exists in the `video` table (from Module 01 testing)

---

## 2.3 Create the Workflow

1. Click **Add Workflow**
2. Name: `Agent 2 -- Labeling Agent (Reachy 08.4.2)`
3. Workflow Settings:
   - Execution Order: `v1`
   - Save Manual Executions: `Yes`
   - Tags: `agent`, `labeling`, `phase4`

---

## 2.4 Wire Node 1: webhook_label

### Step-by-Step

1. Add a **Webhook** node → rename to `webhook_label`
2. Configure:

| Parameter | Value | Why |
|-----------|-------|-----|
| **HTTP Method** | `POST` | Receiving label data |
| **Path** | `label` | Full URL: `/webhook/label` |
| **Response Mode** | `Using 'Respond to Webhook' Node` | We send the response from `respond_success` at the end, so the caller gets class balance data |

### Why "Respond to Webhook Node" Mode?

Unlike the Ingest Agent (which uses `On Received` to return 202 immediately), the Labeling Agent processes synchronously and returns the class balance in the response. Setting response mode to `Using 'Respond to Webhook' Node` means the HTTP response is held open until we explicitly send it via a Respond to Webhook node later in the workflow.

---

## 2.5 Wire Node 2: validate_payload

### Step-by-Step

1. Click `+` on `webhook_label` → add a **Code** node → rename to `validate_payload`
2. Set Mode: `Run Once for All Items`
3. Paste this JavaScript:

```javascript
const body = $input.first().json.body;

const allowedLabels = ['happy', 'sad', 'neutral'];
const allowedActions = ['label_only', 'promote_train', 'promote_test', 'discard'];

const video_id = body.video_id;
const label = body.label;
const action = body.action || 'label_only';
const rater_id = body.rater_id || 'anonymous';
const notes = body.notes || '';

// Validate required fields
if (!video_id) {
  throw new Error('video_id is required');
}
if (!label || !allowedLabels.includes(label)) {
  throw new Error(
    `Invalid label: "${label}". Allowed values: ${allowedLabels.join(', ')}`
  );
}
if (!allowedActions.includes(action)) {
  throw new Error(
    `Invalid action: "${action}". Allowed values: ${allowedActions.join(', ')}`
  );
}

// Generate idempotency key
const crypto = require('crypto');
const idempotency_key = crypto
  .createHash('sha256')
  .update(`${video_id}-${label}-${rater_id}-${Date.now()}`)
  .digest('hex')
  .substring(0, 16);

const correlation_id = 'lbl-' + Date.now() + '-' +
  Math.random().toString(36).substr(2, 8);

return [{
  json: {
    video_id,
    label,
    action,
    rater_id,
    notes,
    idempotency_key,
    correlation_id
  }
}];
```

### What This Does

- Validates `label` is one of `happy`, `sad`, `neutral` (3-class system)
- Validates `action` is one of the 4 allowed actions
- Generates an idempotency key to prevent duplicate label events
- Defaults `action` to `label_only` if not provided

---

## 2.6 Wire Node 3: db_fetch_video

### Step-by-Step

1. Click `+` on `validate_payload` → add a **Postgres** node → rename to `db_fetch_video`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
SELECT
  video_id,
  split,
  label AS current_label,
  file_path
FROM video
WHERE video_id = '{{ $json.video_id }}'
LIMIT 1;
```

### Why Fetch First?

We need to verify the video exists and check its current state before modifying it. This prevents applying labels to non-existent videos.

---

## 2.7 Wire Node 4: db_apply_label

### Step-by-Step

1. Click `+` on `db_fetch_video` → add a **Postgres** node → rename to `db_apply_label`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
WITH label_insert AS (
  INSERT INTO label_event (
    video_id,
    label,
    rater_id,
    notes,
    idempotency_key,
    created_at
  )
  VALUES (
    '{{ $('validate_payload').item.json.video_id }}',
    '{{ $('validate_payload').item.json.label }}',
    '{{ $('validate_payload').item.json.rater_id }}',
    '{{ $('validate_payload').item.json.notes }}',
    '{{ $('validate_payload').item.json.idempotency_key }}',
    NOW()
  )
  ON CONFLICT (idempotency_key) DO NOTHING
  RETURNING label_event_id
)
UPDATE video
SET
  label = '{{ $('validate_payload').item.json.label }}',
  updated_at = NOW()
WHERE video_id = '{{ $('validate_payload').item.json.video_id }}'
RETURNING video_id, label, split;
```

### Key Concepts

- **CTE (Common Table Expression):** The `WITH` clause lets us perform two operations atomically -- insert the label event AND update the video record in a single transaction.
- **`ON CONFLICT (idempotency_key) DO NOTHING`:** If the same label submission is sent twice (e.g., due to a network retry), the duplicate is silently ignored.
- **Referencing a previous node:** `$('validate_payload').item.json.video_id` pulls data from the validate_payload node's output, not the immediately preceding node.

---

## 2.8 Wire Node 5: branch_action

This is the first time we use a **Switch** node. It routes to different paths based on the action.

### Step-by-Step

1. Click `+` on `db_apply_label` → search for **Switch** → rename to `branch_action`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Mode** | `Rules` |
| **Routing Rule Value** | `{{ $('validate_payload').item.json.action }}` |

3. Add 4 rules (outputs):

| Rule # | Operation | Value | Output Name |
|--------|-----------|-------|-------------|
| 0 | `equals` | `label_only` | label_only |
| 1 | `equals` | `promote_train` | promote_train |
| 2 | `equals` | `promote_test` | promote_test |
| 3 | `equals` | `discard` | discard |

### What a Switch Node Does

Think of it like a `switch` statement in programming. The value of `action` determines which output branch executes. Each branch can have different downstream nodes.

---

## 2.9 Wire Node 6: mm_relabel

This handles the `label_only` action -- just relabels the file in place.

### Step-by-Step

1. Click `+` on the **first output** (label_only) of `branch_action` → add an **HTTP Request** → rename to `mm_relabel`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/relabel` |
| **Authentication** | `Predefined Credential Type` → `Header Auth` → `Media Mover Auth` |
| **Send Body** | `Yes` |
| **Body Content Type** | `JSON` |

3. Body fields:

| Field | Value |
|-------|-------|
| `video_id` | `{{ $('validate_payload').item.json.video_id }}` |
| `label` | `{{ $('validate_payload').item.json.label }}` |
| `correlation_id` | `{{ $('validate_payload').item.json.correlation_id }}` |

---

## 2.10 Wire Node 7: mm_promote

This handles both `promote_train` and `promote_test` actions.

### Step-by-Step

1. Click `+` on the **second output** (promote_train) of `branch_action` → add an **HTTP Request** → rename to `mm_promote`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.MEDIA_MOVER_BASE_URL }}/api/promote` |
| **Authentication** | `Predefined Credential Type` → `Header Auth` → `Media Mover Auth` |
| **Send Body** | `Yes` |
| **Body Content Type** | `JSON` |

3. Body fields:

| Field | Value |
|-------|-------|
| `video_id` | `{{ $('validate_payload').item.json.video_id }}` |
| `dest_split` | `{{ $('validate_payload').item.json.action === 'promote_train' ? 'train' : 'test' }}` |
| `label` | `{{ $('validate_payload').item.json.label }}` |
| `dry_run` | `false` |

4. **Also connect** the **third output** (promote_test) of `branch_action` to this same `mm_promote` node. Both promote actions use the same node -- the `dest_split` expression handles the difference.

### Expression Spotlight

```
{{ $('validate_payload').item.json.action === 'promote_train' ? 'train' : 'test' }}
```

This is a ternary expression. It checks the action and sets `dest_split` to either `train` or `test`.

---

## 2.11 Wire Node 8: db_class_balance

All action paths converge here to check the class balance.

### Step-by-Step

1. Add a **Postgres** node → rename to `db_class_balance`
2. **Connect all action outputs to this node:**
   - `mm_relabel` → `db_class_balance`
   - `mm_promote` → `db_class_balance`
   - Fourth output (discard) of `branch_action` → `db_class_balance`
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
SELECT
  COUNT(*) FILTER (WHERE label = 'happy') AS happy_count,
  COUNT(*) FILTER (WHERE label = 'sad') AS sad_count,
  COUNT(*) FILTER (WHERE label = 'neutral') AS neutral_count,
  COUNT(*) AS total_train
FROM video
WHERE split = 'train';
```

### What This Query Does

- Counts how many videos of each emotion class are in the training split
- `FILTER (WHERE ...)` is PostgreSQL syntax for conditional aggregation -- cleaner than `CASE WHEN`
- The result helps the reviewer understand if the dataset is balanced

---

## 2.12 Wire Node 9: respond_success

### Step-by-Step

1. Click `+` on `db_class_balance` → add a **Respond to Webhook** node → rename to `respond_success`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Response Code** | `200` |
| **Response Body** | `JSON` |
| **Response Data** | *(see below)* |

```json
{
  "status": "labeled",
  "video_id": "{{ $('validate_payload').item.json.video_id }}",
  "label": "{{ $('validate_payload').item.json.label }}",
  "action": "{{ $('validate_payload').item.json.action }}",
  "class_balance": {
    "happy": {{ $json.happy_count }},
    "sad": {{ $json.sad_count }},
    "neutral": {{ $json.neutral_count }},
    "total_train": {{ $json.total_train }},
    "balanced": {{ Math.max($json.happy_count, $json.sad_count, $json.neutral_count) - Math.min($json.happy_count, $json.sad_count, $json.neutral_count) <= 10 }}
  }
}
```

### The Balance Check

`balanced` is `true` when the difference between the largest and smallest class counts is 10 or fewer. This tells the reviewer whether the training set is balanced enough for training.

---

## 2.13 Final Connection Map

```
webhook_label ──► validate_payload ──► db_fetch_video ──► db_apply_label ──► branch_action
                                                                                   │
                              ┌───────────────┬───────────────┬───────────────────┘
                              ▼               ▼               ▼               ▼
                        [label_only]    [promote_train]  [promote_test]    [discard]
                              │               │               │               │
                              ▼               └───────┬───────┘               │
                         mm_relabel              mm_promote                   │
                              │                      │                        │
                              └──────────┬───────────┘────────────────────────┘
                                         ▼
                                  db_class_balance ──► respond_success
```

---

## 2.14 Testing

### Test 1: Label Only

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<use a real video_id from the DB>",
    "label": "happy",
    "action": "label_only",
    "rater_id": "russ"
  }'
```

**Expected:** 200 OK with label confirmation and class balance stats.

### Test 2: Invalid Label

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "some-id",
    "label": "angry",
    "action": "label_only"
  }'
```

**Expected:** Error -- `angry` is not in the allowed 3-class list.

### Test 3: Promote to Train

```bash
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<use a real video_id>",
    "label": "sad",
    "action": "promote_train"
  }'
```

**Expected:** Video is moved from `temp` to `train/sad/`, class balance updated.

---

## 2.15 Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Invalid label: angry" | Using old 6-class labels | Only `happy`, `sad`, `neutral` are valid in 3-class system |
| CTE query fails | `label_event` table missing | Run the DDL from the README to create it |
| Switch node has no output | Action value doesn't match any rule | Check that action is exactly one of the 4 allowed values |
| mm_promote returns 404 | Media Mover promote endpoint not configured | Check `MEDIA_MOVER_BASE_URL` env var |
| Class balance shows all zeros | No videos in train split yet | Use the promote action to move videos to train |

---

## 2.16 Key Concepts Learned

- **Switch Node** for multi-way routing (4 branches from one decision point)
- **CTE (WITH clause)** for atomic multi-table operations in PostgreSQL
- **Idempotency** via `ON CONFLICT DO NOTHING` on the idempotency_key
- **Cross-node references** to pull data from non-adjacent nodes
- **Ternary expressions** in n8n for conditional values
- **Converging paths** -- multiple branches feeding into one node (db_class_balance)
- **Response Mode: Using Respond Node** -- delaying HTTP response until processing completes

---

*Previous: [MODULE 01 -- Ingest Agent](MODULE_01_INGEST_AGENT.md)*
*Next: [MODULE 03 -- Promotion Agent](MODULE_03_PROMOTION_AGENT.md)*
