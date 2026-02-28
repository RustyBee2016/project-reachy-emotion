# Module 12: Testing & Debugging Strategies

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~2 hours  
**Prerequisites**: Completed Modules 0-11

---

## Learning Objectives

By the end of this module, you will:
1. Use **webhook-test endpoints** for development
2. Analyze **execution history** for debugging
3. Debug **expressions** using the expression editor
4. Use **pinned data** for reproducible tests
5. Implement **testing strategies** for workflows

---

## Part 1: Development vs Production Webhooks

### Webhook URLs

| Mode | URL Pattern | Behavior |
|------|-------------|----------|
| **Test** | `/webhook-test/path` | Always active, no auth |
| **Production** | `/webhook/path` | Only when workflow active |

### Using Test Endpoints

```bash
# Test endpoint (always works, even if workflow inactive)
curl -X POST http://10.0.4.130:5678/webhook-test/label \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test-123", "label": "happy"}'

# Production endpoint (requires active workflow)
curl -X POST http://10.0.4.130:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{"video_id": "test-123", "label": "happy"}'
```

### Best Practice

1. **Development**: Use `/webhook-test/`
2. **Testing**: Use `/webhook-test/`
3. **Production**: Use `/webhook/` with workflow activated

---

## Part 2: Execution History

### Accessing History

1. Open workflow
2. Click "Executions" in left sidebar
3. View list of past runs

### Execution Details

Each execution shows:
- **Status**: Success, Error, Waiting
- **Started**: Timestamp
- **Duration**: Running time
- **Mode**: Manual, Webhook, Schedule

### Drilling Into Failures

1. Click failed execution
2. View the workflow with data at each node
3. Click the failed node (red border)
4. See error message and input data

### Filtering Executions

- By status: Success, Error, Waiting
- By date range
- By workflow (in n8n settings)

---

## Part 3: Expression Debugging

### Expression Editor

1. Click expression field (shows `=`)
2. Click "Expression" tab
3. Enter expression
4. See live result preview

### Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Wrong path | `undefined` | Check `$json` structure |
| Missing data | `null` | Previous node didn't output |
| Type error | `NaN` | Cast with `parseInt()`, etc. |
| Syntax error | Red underline | Check brackets, quotes |

### Debugging Tips

**Log intermediate values**:
```javascript
// In Code node
console.log('Input:', JSON.stringify($json, null, 2));
```

**Check with IF node**:
Add temporary IF to inspect:
- Value 1: `={{$json.field}}`
- Check what the expression evaluates to

**Use Set node**:
Add Set node to explicitly define expected values and compare.

---

## Part 4: Pinned Data

### What is Pinned Data?

Saved input data for a node that's used instead of executing previous nodes. Perfect for:
- Reproducible tests
- Skipping slow operations
- Testing edge cases

### Creating Pinned Data

1. Execute workflow once
2. Click node with data you want to pin
3. Click "Pin" icon in output panel
4. Data is now fixed for that node

### Managing Pinned Data

- Pinned nodes show 📌 icon
- To unpin: Click pin icon again
- To edit: Click output, modify JSON

### Use Cases

| Scenario | Pin Strategy |
|----------|--------------|
| Test validation logic | Pin webhook with edge case data |
| Skip training | Pin after training with mock results |
| Test error handling | Pin with error response |
| Slow API | Pin successful response |

---

## Part 5: Testing Strategies

### Unit Testing Workflows

**Test individual nodes**:
1. Create test workflow
2. Add Set node with test data
3. Add node under test
4. Add IF/Code to assert expected output

**Example: Test Validation Code**:
```javascript
// Set node: test data
{
  "body": {
    "video_id": "",  // Invalid - should fail
    "label": "happy"
  }
}

// After validation Code node, check:
// IF: $json.error contains "video_id required"
```

### Integration Testing

**Test node chains**:
1. Pin realistic data at start
2. Execute through chain
3. Verify final output

### End-to-End Testing

**Test complete workflow**:
```bash
# Script for E2E test
#!/bin/bash

# 1. Trigger workflow
RESPONSE=$(curl -s -X POST http://localhost:5678/webhook-test/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_url": "http://example.com/test.mp4"}')

# 2. Check response
echo "$RESPONSE" | jq '.status'

# 3. Verify side effects (database, files)
psql -c "SELECT * FROM video WHERE source_url LIKE '%test.mp4%'"
```

---

## Part 6: Common Debugging Scenarios

### Scenario 1: Node Returns Empty

**Symptoms**: Next node has no data

**Debug Steps**:
1. Check previous node's output tab
2. Verify expression path
3. Check if filter/IF blocked items
4. Look for `runOnceForAllItems` vs `runOnceForEachItem`

### Scenario 2: Expression Undefined

**Symptoms**: `={{$json.field}}` shows undefined

**Debug Steps**:
1. Check input data structure (Output tab)
2. Verify field name (case-sensitive)
3. Check if data is nested: `$json.body.field`
4. Verify previous node executed

### Scenario 3: HTTP Request Fails

**Symptoms**: 4xx or 5xx error

**Debug Steps**:
1. Check URL (use Edit Expression to see resolved value)
2. Verify headers and auth
3. Check body format (JSON vs form)
4. Test same request with curl
5. Check target service logs

### Scenario 4: Loop Never Ends

**Symptoms**: Workflow runs forever

**Debug Steps**:
1. Check IF condition logic
2. Verify status value changes between iterations
3. Add max iteration counter
4. Check Wait node is in the loop

---

## Part 7: Debugging Checklist

### Before Testing

- [ ] Workflow saved
- [ ] Required nodes connected
- [ ] Credentials configured
- [ ] Environment variables set
- [ ] Backend services running

### During Testing

- [ ] Check each node's output
- [ ] Verify data flows correctly
- [ ] Watch for type mismatches
- [ ] Monitor execution duration

### After Failure

- [ ] Note exact error message
- [ ] Check which node failed
- [ ] Review input data to failed node
- [ ] Compare expected vs actual
- [ ] Check logs of external services

---

## Part 8: Testing the Agentic System

### Test Sequence

1. **Ingest Agent** — Start with ingest test
2. **Labeling Agent** — Label the ingested video
3. **Promotion Agent** — Promote to train
4. **Reconciler** — Verify consistency
5. **Training** — (Mock or real)
6. **Evaluation** — (Mock or real)
7. **Deployment** — (Mock or real)
8. **Observability** — Verify metrics collected
9. **Pipeline Orchestrator** — Full E2E test

### Test Data Setup

```sql
-- Create test videos for system testing
INSERT INTO video (video_id, file_path, split, label, size_bytes)
VALUES 
  ('test-001', 'temp/test-001.mp4', 'temp', NULL, 1000),
  ('test-002', 'temp/test-002.mp4', 'temp', NULL, 1000);
```

---

## Module 12 Summary

### Debugging Toolkit

| Tool | Use Case |
|------|----------|
| webhook-test | Development without activation |
| Execution history | Post-mortem analysis |
| Expression editor | Live expression testing |
| Pinned data | Reproducible tests |
| Console.log | Code node debugging |
| curl | External request testing |

### Testing Levels

| Level | Scope | Method |
|-------|-------|--------|
| Unit | Single node | Pinned data + assertions |
| Integration | Node chain | Mock data flow |
| E2E | Full workflow | curl + DB verification |
| System | All agents | Scripted test suite |

---

## Next Steps

Proceed to **Module 13: Production Operations** where you'll learn:
- **Workflow versioning** and backup
- **Activation management**
- **Monitoring production workflows**
- **Scaling considerations**

---

*Module 12 Complete — Proceed to Module 13: Production Operations*
