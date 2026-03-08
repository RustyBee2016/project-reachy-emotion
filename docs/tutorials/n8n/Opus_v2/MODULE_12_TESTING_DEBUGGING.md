# MODULE 12 -- Testing & Debugging Strategies

**Duration:** ~2 hours
**Prerequisites:** MODULES 00-11 complete
**Outcome:** A systematic approach to testing all 10 workflows, debugging failed executions, and validating end-to-end data flow

---

## 12.1 The Testing Challenge

With 10 interconnected workflows and 111+ nodes, testing the Reachy agentic system requires a structured approach. This module covers:

1. **Unit testing** individual workflows in isolation
2. **Integration testing** workflow chains (e.g., Ingest → Labeling → Promotion)
3. **End-to-end testing** the full ML pipeline
4. **Debugging** failed executions using n8n's built-in tools

---

## 12.2 n8n's Testing Tools

### Test vs Production Webhooks

Every webhook node has two URLs:

| URL Type | Format | When to Use |
|----------|--------|-------------|
| **Test URL** | `/webhook-test/path` | During development, fires instantly |
| **Production URL** | `/webhook/path` | When workflow is active |

**Critical Rule**: Always use `-test` URLs during development. Production URLs only work when the workflow is **Active**.

### Execution History

n8n stores execution results, accessible via:

1. Open any workflow → **Executions** tab
2. Click any execution to see node-by-node results
3. Each node shows its input data, output data, and any errors

### Pin Data

n8n allows you to **pin** data on any node, which freezes its output for testing:

1. Execute a workflow once to get real data
2. Click on a node → view its output
3. Click **Pin Data** (pin icon)
4. Now this node always outputs the pinned data, regardless of input

**Use case**: Pin data on `webhook_start` to test downstream logic without sending HTTP requests.

---

## 12.3 Unit Testing Each Workflow

### Test Script: Ingest Agent (Module 01)

```bash
#!/bin/bash
# test_ingest.sh -- Unit test for Agent 1

echo "=== Test 1: Valid ingestion ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${INGEST_TOKEN}" \
  -d '{
    "source": "webcam_livingroom",
    "filename": "test_happy_001.mp4",
    "label": "happy",
    "duration_sec": 3.2,
    "resolution": "640x480"
  }' | jq .

echo ""
echo "=== Test 2: Missing required field ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${INGEST_TOKEN}" \
  -d '{
    "source": "webcam_livingroom"
  }' | jq .

echo ""
echo "=== Test 3: Duplicate filename (idempotency) ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${INGEST_TOKEN}" \
  -d '{
    "source": "webcam_livingroom",
    "filename": "test_happy_001.mp4",
    "label": "happy",
    "duration_sec": 3.2,
    "resolution": "640x480"
  }' | jq .

echo ""
echo "=== Test 4: Invalid auth ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong_token" \
  -d '{"filename": "test.mp4"}' | jq .
```

### Test Script: Labeling Agent (Module 02)

```bash
#!/bin/bash
# test_labeling.sh -- Unit test for Agent 2

echo "=== Test 1: Label a video ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/label/video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 1,
    "label": "happy",
    "confidence": 0.92,
    "labeler": "test_user"
  }' | jq .

echo ""
echo "=== Test 2: Invalid label ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/label/video \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": 1,
    "label": "angry",
    "confidence": 0.5,
    "labeler": "test_user"
  }' | jq .
```

### Test Script: ML Pipeline Orchestrator (Module 10)

```bash
#!/bin/bash
# test_orchestrator.sh -- Unit test for Agent 10

echo "=== Test 1: Start pipeline (no auto-deploy) ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "model": "efficientnet-b0-hsemotion",
    "auto_deploy": false
  }' | jq .

echo ""
echo "=== Test 2: Start pipeline (auto-deploy) ==="
curl -s -X POST http://10.0.4.130:5678/webhook-test/ml/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "model": "efficientnet-b0-hsemotion",
    "auto_deploy": true
  }' | jq .
```

---

## 12.4 Integration Testing

### Data Pipeline Chain: Ingest → Labeling → Promotion

This tests the most critical data flow in the system.

```bash
#!/bin/bash
# test_data_pipeline.sh -- Integration test

echo "Step 1: Ingest a test video"
INGEST_RESULT=$(curl -s -X POST http://10.0.4.130:5678/webhook-test/ingest/video \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${INGEST_TOKEN}" \
  -d '{
    "source": "integration_test",
    "filename": "inttest_'"$(date +%s)"'.mp4",
    "label": "happy",
    "duration_sec": 3.0,
    "resolution": "640x480"
  }')
echo "$INGEST_RESULT" | jq .
VIDEO_ID=$(echo "$INGEST_RESULT" | jq -r '.video_id')

echo ""
echo "Step 2: Label the video (video_id=$VIDEO_ID)"
curl -s -X POST http://10.0.4.130:5678/webhook-test/label/video \
  -H "Content-Type: application/json" \
  -d "{
    \"video_id\": $VIDEO_ID,
    \"label\": \"happy\",
    \"confidence\": 0.95,
    \"labeler\": \"integration_test\"
  }" | jq .

echo ""
echo "Step 3: Promote the video (dry-run)"
curl -s -X POST http://10.0.4.130:5678/webhook-test/promote/video \
  -H "Content-Type: application/json" \
  -d "{
    \"video_id\": $VIDEO_ID,
    \"target_split\": \"train\",
    \"dry_run\": true
  }" | jq .

echo ""
echo "Step 4: Verify database state"
psql -h localhost -U reachy_dev -d reachy_emotion -c \
  "SELECT id, filename, label, split, status FROM video WHERE id = $VIDEO_ID;"
```

### Verify Data Consistency

After running the integration test, check these invariants:

```sql
-- No video should be in 'train' or 'test' without a label
SELECT COUNT(*) AS unlabeled_in_split
FROM video
WHERE split IN ('train', 'test')
  AND label IS NULL;
-- Expected: 0

-- No duplicate filenames
SELECT filename, COUNT(*) AS cnt
FROM video
GROUP BY filename
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Label distribution should be balanced (within 20%)
SELECT
  split,
  label,
  COUNT(*) AS count
FROM video
WHERE split IN ('train', 'test')
GROUP BY split, label
ORDER BY split, label;
```

---

## 12.5 Debugging Failed Executions

### Step 1: Find the Failure

1. Open the failed workflow → **Executions** tab
2. Look for executions with a red icon (failed)
3. Click to open the execution details

### Step 2: Inspect Node-by-Node

n8n shows each node's status:

| Icon | Meaning |
|------|---------|
| Green check | Node executed successfully |
| Red X | Node failed |
| Gray circle | Node was not reached |

Click the **red X node** to see:
- **Input data**: What the node received
- **Error message**: The actual error
- **Stack trace**: For Code nodes, the line number

### Step 3: Common Error Patterns

#### Pattern 1: "Cannot read property 'X' of undefined"

**Cause**: An upstream node produced no data, or the data structure changed.

**Debug steps:**
1. Click the node immediately before the failing node
2. Check its output -- is it empty?
3. If empty, trace back further to find where data was lost

**Fix**: Add null checks in Code nodes:
```javascript
const data = $input.first()?.json?.body || {};
const value = data.field || 'default_value';
```

#### Pattern 2: "ECONNREFUSED" or "ETIMEDOUT"

**Cause**: The target service is down or unreachable.

**Debug steps:**
1. Note the URL from the HTTP Request node
2. Test it directly:
   ```bash
   curl -v http://10.0.4.130:8083/api/health
   ```
3. Check if the service is running:
   ```bash
   systemctl status media-mover  # or docker ps
   ```

**Fix**: Ensure the service is running. Add retry logic (Module 11).

#### Pattern 3: "duplicate key value violates unique constraint"

**Cause**: Attempting to insert a record that already exists.

**Debug steps:**
1. Check the Postgres node's input data
2. Query the database for the existing record:
   ```sql
   SELECT * FROM video WHERE filename = 'the_filename.mp4';
   ```

**Fix**: Use `ON CONFLICT` clauses (already in place for Ingest Agent).

#### Pattern 4: SSH Command Returns Non-Zero Exit Code

**Cause**: The remote command failed on the Jetson or training server.

**Debug steps:**
1. Check the SSH node output for stderr
2. SSH manually and run the same command:
   ```bash
   ssh ubuntu1 "cd /path && python train.py --config spec.yaml"
   ```
3. Check logs on the remote machine

**Fix**: Ensure paths, permissions, and dependencies are correct on the remote host.

#### Pattern 5: Code Node "Error in line X"

**Cause**: JavaScript error in a Code node.

**Debug steps:**
1. n8n shows the error line number
2. Click the Code node and review line X
3. Check the input data -- often the error is caused by unexpected input format

**Common culprits:**
```javascript
// Array is empty
const first = items[0].json;  // fails if items is empty
// Fix:
const first = items[0]?.json || {};

// String instead of number
const total = a + b;  // "12" instead of 3 if a="1", b="2"
// Fix:
const total = Number(a) + Number(b);
```

---

## 12.6 Using n8n's Debug Features

### Expression Editor

When configuring expressions (e.g., `{{ $json.field }}`), use the expression editor:

1. Click the expression field
2. The left panel shows **available data** from previous nodes
3. The right panel shows the **resolved value**
4. If the resolved value is `[undefined]`, the expression is wrong

### Workflow Execution Preview

In the execution details view:
1. Click any node to see its data
2. Use the **Table** view for structured data
3. Use the **JSON** view for raw data inspection
4. Use the **Binary** tab for file attachments

### Console Logging in Code Nodes

Add `console.log()` statements to Code nodes for debugging:

```javascript
console.log('Input items:', JSON.stringify($input.all().map(i => i.json)));
console.log('Pipeline state:', $('init_pipeline').first().json);

// Your logic here...

console.log('Output:', JSON.stringify(result));
return result;
```

View logs in the n8n server output (stdout/stderr).

---

## 12.7 Testing Checklist

Use this checklist before activating any workflow in production:

### Per-Workflow Checks

- [ ] **Happy path**: Workflow completes successfully with valid input
- [ ] **Missing fields**: Workflow handles missing required fields gracefully
- [ ] **Duplicate data**: Idempotency works (same input twice doesn't create duplicates)
- [ ] **Empty results**: Workflow handles empty database query results
- [ ] **Error workflow linked**: Workflow settings point to the Error Handler
- [ ] **Timeouts set**: Execution timeout is configured appropriately

### System-Wide Checks

- [ ] **All 10 workflows active**: Verify in the workflow list
- [ ] **Error Handler active**: The global error handler workflow is active
- [ ] **Credentials valid**: All PostgreSQL, SSH, HTTP Auth credentials are current
- [ ] **Environment variables set**: All required env vars are configured in n8n
- [ ] **Database tables exist**: Run migration/schema check
- [ ] **Services reachable**: Media Mover, Gateway, MLflow, PostgreSQL all responding

### End-to-End Smoke Test

```bash
#!/bin/bash
# smoke_test.sh -- Quick system health check

echo "1. n8n health..."
curl -s http://10.0.4.130:5678/healthz && echo " OK" || echo " FAIL"

echo "2. Media Mover health..."
curl -s http://10.0.4.130:8083/api/health && echo " OK" || echo " FAIL"

echo "3. Gateway health..."
curl -s http://10.0.4.140:8000/health && echo " OK" || echo " FAIL"

echo "4. PostgreSQL..."
psql -h localhost -U reachy_dev -d reachy_emotion -c "SELECT 1;" > /dev/null 2>&1 \
  && echo " OK" || echo " FAIL"

echo "5. MLflow..."
curl -s http://10.0.4.130:5000/api/2.0/mlflow/experiments/list > /dev/null 2>&1 \
  && echo " OK" || echo " FAIL"

echo "6. Prometheus endpoints..."
curl -s http://localhost:5678/metrics > /dev/null 2>&1 \
  && echo " n8n metrics OK" || echo " n8n metrics FAIL"
curl -s http://10.0.4.130:9101/metrics > /dev/null 2>&1 \
  && echo " Media Mover metrics OK" || echo " Media Mover metrics FAIL"
curl -s http://10.0.4.140:9100/metrics > /dev/null 2>&1 \
  && echo " Gateway metrics OK" || echo " Gateway metrics FAIL"
```

---

## 12.8 Regression Testing After Changes

When modifying any workflow:

1. **Before changes**: Note the current execution count and last successful execution
2. **Make changes**: Edit the workflow
3. **Test with pinned data**: Use Pin Data to replay the last known-good input
4. **Test with live data**: Execute with a test webhook call
5. **Check downstream**: If this workflow triggers others, verify the chain still works
6. **Monitor**: Watch the next 3-5 automatic executions for errors

### Version Control for Workflows

Export workflows as JSON for version control:

1. Open workflow → **...** menu → **Download**
2. Save to `n8n/workflows/ml-agentic-ai_v.2/` in the repository
3. Commit with a descriptive message

To restore:
1. n8n → **Import From File** → select the JSON
2. Review and activate

---

## 12.9 Key Concepts Learned

- **Test vs Production webhook URLs** -- always develop with `-test`
- **Pin Data** for repeatable testing without external triggers
- **Execution history** for inspecting node-by-node data flow
- **Common error patterns** and their debugging approaches
- **Integration testing** across the Ingest → Label → Promote chain
- **Smoke testing** to verify all services are reachable
- **Console logging** in Code nodes for debugging
- **Regression testing** workflow for safe modifications

---

*Previous: [MODULE 11 -- Error Handling & Recovery](MODULE_11_ERROR_HANDLING.md)*
*Next: [MODULE 13 -- Production Operations](MODULE_13_PRODUCTION_OPS.md)*
