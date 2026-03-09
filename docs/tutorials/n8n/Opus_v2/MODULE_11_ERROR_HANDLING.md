# MODULE 11 -- Error Handling & Recovery

**Duration:** ~2 hours
**Prerequisites:** MODULES 00-10 complete
**Outcome:** Implement robust error handling across all 10 workflows using n8n's built-in error workflow, retry logic, and dead-letter patterns

---

## 11.1 Why Error Handling Matters

In the 10 workflows you've built, failures can occur at many points:

- **Network errors**: SSH timeouts to Jetson, unreachable Prometheus endpoints
- **Data errors**: Malformed payloads, missing fields, empty database results
- **Infrastructure errors**: PostgreSQL down, MLflow unreachable, disk full on training server
- **Logic errors**: Division by zero in metrics, unexpected pipeline states, Gate A/B edge cases

Without error handling, a single failure can leave the system in an inconsistent state -- for example, a training run that starts but never completes, leaving the Orchestrator polling forever.

### The Three Layers of Error Handling in n8n

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: NODE-LEVEL                                     │
│  Retry on failure, timeout settings                      │
├─────────────────────────────────────────────────────────┤
│  Layer 2: WORKFLOW-LEVEL                                 │
│  Error Trigger node, error workflow                      │
├─────────────────────────────────────────────────────────┤
│  Layer 3: SYSTEM-LEVEL                                   │
│  Dead-letter queue, alerting, manual recovery            │
└─────────────────────────────────────────────────────────┘
```

---

## 11.2 Layer 1: Node-Level Error Settings

Every node in n8n has built-in error handling options under **Settings**.

### Retry on Fail

1. Open any node → click **Settings** (gear icon)
2. Enable **Retry On Fail**

| Parameter | Recommended Value | Why |
|-----------|-------------------|-----|
| **Max Tries** | `3` | Enough for transient failures |
| **Wait Between Tries** | `1000` ms | Prevents hammering a service |

### Which Nodes Should Retry?

| Agent | Node | Retry? | Reason |
|-------|------|--------|--------|
| 01 Ingest | `http_fetch_media` | Yes (3×) | External file download can fail |
| 04 Reconciler | `ssh_list_jetson` | Yes (3×) | SSH over network is unreliable |
| 06 Training | `ssh_start_training` | Yes (2×) | SSH command can timeout |
| 06 Training | `check_mlflow_run` | Yes (3×) | MLflow API may be slow to respond |
| 08 Deployment | `scp_model_to_jetson` | Yes (3×) | Large file transfer over network |
| 09 Observability | All `fetch_*` nodes | Yes (2×) | Prometheus endpoints may be temporarily down |

### Continue On Fail

For non-critical operations, enable **Continue On Fail** so the workflow keeps running:

| Setting | Behavior |
|---------|----------|
| **Continue On Fail: OFF** (default) | Node failure stops the workflow |
| **Continue On Fail: ON** | Node adds `$json.error` to output, workflow continues |

**Use Continue On Fail for:**
- Observability agent fetch nodes (one endpoint being down shouldn't block others)
- Notification/event emission nodes (failure to notify shouldn't block the pipeline)
- Non-critical logging inserts

**Never use Continue On Fail for:**
- Database writes that are part of the data pipeline (Ingest, Labeling, Promotion)
- SSH commands that start training or deploy models
- Any node where downstream logic depends on the result

### Timeout Settings

| Parameter | Default | Recommended |
|-----------|---------|-------------|
| **Execution Timeout** | Unlimited | Set per workflow |
| **Node Timeout** | None | Set for SSH/HTTP nodes |

For long-running workflows (Training Orchestrator, ML Pipeline Orchestrator), set generous execution timeouts:

```
Training Orchestrator: 120 minutes
ML Pipeline Orchestrator: 240 minutes
All other workflows: 30 minutes
```

---

## 11.3 Layer 2: Error Workflow

n8n has a powerful **Error Trigger** node that catches unhandled errors from any workflow.

### Create the Error Handler Workflow

1. Create a new workflow: `Error Handler -- Global (Reachy 08.4.2)`
2. Tags: `error-handler`, `system`

### Wire Node 1: error_trigger

1. Add an **Error Trigger** node → rename to `error_trigger`
2. No configuration needed -- it fires automatically when any linked workflow fails

The Error Trigger receives this data:

```json
{
  "execution": {
    "id": "12345",
    "url": "http://10.0.4.130:5678/workflow/abc123/executions/12345",
    "error": {
      "message": "ETIMEDOUT: SSH connection timed out",
      "name": "NodeOperationError",
      "node": {
        "name": "ssh_start_training",
        "type": "n8n-nodes-base.ssh"
      }
    },
    "lastNodeExecuted": "ssh_start_training",
    "mode": "trigger"
  },
  "workflow": {
    "id": "abc123",
    "name": "Agent 5 -- Training Orchestrator"
  }
}
```

### Wire Node 2: classify_error

1. Add a **Code** node → rename to `classify_error`
2. Code:

```javascript
const exec = $input.first().json.execution;
const workflow = $input.first().json.workflow;

const errorMsg = exec.error?.message || 'Unknown error';
const nodeName = exec.lastNodeExecuted || 'unknown';
const workflowName = workflow.name || 'unknown';

// Classify severity
let severity = 'warning';
let category = 'unknown';

if (errorMsg.includes('ETIMEDOUT') || errorMsg.includes('ECONNREFUSED')) {
  severity = 'critical';
  category = 'network';
} else if (errorMsg.includes('ENOMEM') || errorMsg.includes('disk')) {
  severity = 'critical';
  category = 'infrastructure';
} else if (errorMsg.includes('duplicate key') || errorMsg.includes('unique constraint')) {
  severity = 'warning';
  category = 'data_conflict';
} else if (errorMsg.includes('permission') || errorMsg.includes('EACCES')) {
  severity = 'critical';
  category = 'permissions';
} else if (errorMsg.includes('null') || errorMsg.includes('undefined')) {
  severity = 'error';
  category = 'data_quality';
}

return [{
  json: {
    severity,
    category,
    workflow_name: workflowName,
    workflow_id: workflow.id,
    execution_id: exec.id,
    execution_url: exec.url,
    failed_node: nodeName,
    error_message: errorMsg,
    timestamp: new Date().toISOString()
  }
}];
```

### Wire Node 3: db_log_error

1. Add a **Postgres** node → rename to `db_log_error`
2. Query:

```sql
INSERT INTO error_log (
  severity, category, workflow_name, workflow_id,
  execution_id, failed_node, error_message, ts
) VALUES (
  '{{ $json.severity }}',
  '{{ $json.category }}',
  '{{ $json.workflow_name }}',
  '{{ $json.workflow_id }}',
  '{{ $json.execution_id }}',
  '{{ $json.failed_node }}',
  '{{ $json.error_message }}',
  '{{ $json.timestamp }}'::timestamptz
);
```

**Create the table first:**

```sql
CREATE TABLE IF NOT EXISTS error_log (
  id SERIAL PRIMARY KEY,
  severity VARCHAR(20) NOT NULL,
  category VARCHAR(50),
  workflow_name TEXT,
  workflow_id TEXT,
  execution_id TEXT,
  failed_node TEXT,
  error_message TEXT,
  ts TIMESTAMPTZ DEFAULT NOW()
);
```

### Wire Node 4: if_critical

1. Add an **IF** node → rename to `if_critical`

| Parameter | Value |
|-----------|-------|
| **Value 1** | `{{ $json.severity }}` |
| **Operation** | `is equal to` |
| **Value 2** | `critical` |

### Wire Node 5: send_alert

Connected to **true** output of `if_critical`.

1. Add an **HTTP Request** node → rename to `send_alert`
2. Configure to POST to your alerting endpoint (Slack webhook, email API, etc.)

| Parameter | Value |
|-----------|-------|
| **Method** | `POST` |
| **URL** | `{{ $env.ALERT_WEBHOOK_URL }}` |

Body:

```json
{
  "text": "🚨 CRITICAL: {{ $json.workflow_name }} failed at node '{{ $json.failed_node }}'\nError: {{ $json.error_message }}\nExecution: {{ $json.execution_url }}"
}
```

### Link Workflows to the Error Handler

For each of the 10 agent workflows:

1. Open the workflow → **Settings** (gear icon in the top bar)
2. Under **Error Workflow**, select `Error Handler -- Global (Reachy 08.4.2)`
3. Save

```
Agent 1 (Ingest)         ──┐
Agent 2 (Labeling)        ──┤
Agent 3 (Promotion)       ──┤
Agent 4 (Reconciler)      ──┤
Agent 5 (Privacy)         ──┤──► Error Handler -- Global
Agent 6 (Training)        ──┤
Agent 7 (Evaluation)      ──┤
Agent 8 (Deployment)      ──┤
Agent 9 (Observability)   ──┤
Agent 10 (Orchestrator)   ──┘
```

---

## 11.4 Layer 3: Dead-Letter Queue Pattern

For critical operations where retries are exhausted and the error handler has fired, implement a dead-letter queue (DLQ) to capture failed items for manual recovery.

### DLQ Table

```sql
CREATE TABLE IF NOT EXISTS dead_letter_queue (
  id SERIAL PRIMARY KEY,
  source_workflow TEXT NOT NULL,
  source_node TEXT,
  payload JSONB NOT NULL,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  status VARCHAR(20) DEFAULT 'pending',  -- pending, retrying, resolved, abandoned
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);
```

### Adding DLQ to the Ingest Agent

The Ingest Agent (Module 01) is the most important place for a DLQ, because lost ingestion events mean lost training data.

After the main `http_fetch_media` node, add an error branch:

```
http_fetch_media ──[success]──► db_insert_video
                 │
                 └──[error]──► dlq_insert
```

**dlq_insert** (Postgres node):

```sql
INSERT INTO dead_letter_queue (source_workflow, source_node, payload, error_message)
VALUES (
  'Agent 1 -- Ingest Agent',
  'http_fetch_media',
  '{{ JSON.stringify($json) }}'::jsonb,
  '{{ $json.error?.message || "Unknown error" }}'
);
```

### DLQ Retry Workflow

Create a simple scheduled workflow that retries DLQ items:

1. **Schedule Trigger**: Every 15 minutes
2. **Postgres**: `SELECT * FROM dead_letter_queue WHERE status = 'pending' AND retry_count < max_retries LIMIT 10`
3. **Split In Batches**: Process one at a time
4. **HTTP Request**: Re-attempt the original operation
5. **IF**: Check success
6. **Postgres (success)**: `UPDATE dead_letter_queue SET status = 'resolved', resolved_at = NOW() WHERE id = {{ $json.id }}`
7. **Postgres (failure)**: `UPDATE dead_letter_queue SET retry_count = retry_count + 1 WHERE id = {{ $json.id }}`

---

## 11.5 Recovery Patterns for Each Agent

### Idempotent Recovery

Several agents already have idempotency built in (you implemented these in earlier modules):

| Agent | Idempotency Mechanism |
|-------|----------------------|
| 01 Ingest | `ON CONFLICT (filename)` in PostgreSQL insert |
| 02 Labeling | `WHERE NOT EXISTS` check before label assignment |
| 03 Promotion | Dry-run check + human approval gate |

This means retrying these operations is safe -- duplicate events won't create duplicate data.

### Training Recovery

If Agent 6 (Training) fails mid-training:

1. The MLflow run remains in `RUNNING` state
2. On retry, check for existing active runs:
   ```sql
   SELECT run_id FROM mlflow_runs
   WHERE status = 'RUNNING'
   AND experiment = 'efficientnet-b0'
   ORDER BY start_time DESC LIMIT 1;
   ```
3. If found, resume monitoring that run instead of starting a new one

### Deployment Rollback

Agent 8 (Deployment) already has rollback logic. If deployment fails:

1. The previous model remains active on Jetson
2. The `gate_b_passed` flag stays `false`
3. The error handler logs the failure
4. Manual intervention: SSH to Jetson and verify the current model version

---

## 11.6 Testing Error Handling

### Simulate Network Failure

1. Temporarily change an HTTP URL to an invalid address
2. Execute the workflow
3. Verify:
   - Node retries 3 times (check execution details)
   - Error workflow fires
   - Error is logged to `error_log` table
   - Alert is sent (if critical)

### Simulate Data Error

1. Send a malformed payload to the Ingest webhook:
   ```bash
   curl -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
     -H "Content-Type: application/json" \
     -d '{"invalid": "payload"}'
   ```
2. Verify the workflow handles missing fields gracefully

### Simulate Database Down

1. Stop PostgreSQL temporarily
2. Trigger any workflow
3. Verify error classification is `critical` / `infrastructure`
4. Restart PostgreSQL and verify DLQ retry picks up failed items

---

## 11.7 Error Handling Final Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    n8n Workflow Execution                     │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Node A   │───►│ Node B   │───►│ Node C   │               │
│  │ retry:3  │    │ retry:2  │    │ continue │               │
│  └──────────┘    └──────────┘    │ on fail  │               │
│                       │          └──────────┘               │
│                       │ (failure after retries)              │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │ Error Trigger   │                             │
│              │ (Error Handler  │                             │
│              │  Workflow)      │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│         ┌─────────────┼─────────────┐                        │
│         ▼             ▼             ▼                        │
│  ┌────────────┐ ┌──────────┐ ┌───────────┐                  │
│  │ db_log     │ │ classify │ │ DLQ       │                  │
│  │ error      │ │ + alert  │ │ insert    │                  │
│  └────────────┘ └──────────┘ └───────────┘                  │
│                                     │                        │
│                                     ▼                        │
│                              ┌───────────┐                   │
│                              │ DLQ Retry │                   │
│                              │ (15 min)  │                   │
│                              └───────────┘                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 11.8 Key Concepts Learned

- **Retry on Fail** for transient network errors (SSH, HTTP)
- **Continue on Fail** for non-critical operations (metrics, notifications)
- **Error Trigger** workflow for centralized error handling
- **Error classification** by severity and category
- **Dead-letter queue** for capturing failed items for manual/automatic retry
- **Idempotent recovery** -- safe retries thanks to database constraints
- **Execution timeouts** to prevent runaway workflows

---

*Previous: [MODULE 10 -- ML Pipeline Orchestrator](MODULE_10_ML_PIPELINE_ORCHESTRATOR.md)*
*Next: [MODULE 12 -- Testing & Debugging Strategies](MODULE_12_TESTING_DEBUGGING.md)*
