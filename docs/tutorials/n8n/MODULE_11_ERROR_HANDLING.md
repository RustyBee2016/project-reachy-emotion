# Module 11: Error Handling & Recovery

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~2 hours  
**Prerequisites**: Completed Modules 0-10

---

## Learning Objectives

By the end of this module, you will:
1. Configure **global error workflows** for centralized error handling
2. Implement **retry patterns** with exponential backoff
3. Use **try-catch patterns** in Code nodes
4. Create **dead letter queues** for failed tasks
5. Set up **alerting** on workflow failures

---

## Part 1: Error Handling Strategies

### Types of Errors

| Type | Example | Strategy |
|------|---------|----------|
| **Transient** | Network timeout | Retry with backoff |
| **Permanent** | Invalid data | Log and alert |
| **Resource** | Database down | Circuit breaker |
| **Logic** | Code bug | Fix and redeploy |

### n8n Error Handling Options

| Level | Configuration | Use Case |
|-------|---------------|----------|
| **Node** | Continue On Fail | Non-critical operations |
| **Node** | Retry On Fail | Transient errors |
| **Workflow** | Error Workflow | Centralized handling |
| **Code** | try-catch | Custom logic |

---

## Part 2: Node-Level Error Handling

### Continue On Fail

For non-critical nodes where failure shouldn't stop the workflow:

1. Select the node
2. Settings → Continue On Fail = `true`
3. Downstream nodes receive: `$json.error`

**Use Cases**:
- Optional metrics collection
- Logging to external service
- Notification sends

### Retry On Fail

For transient errors that may succeed on retry:

1. Select the node
2. Settings → Retry On Fail = `true`
3. Max Tries = `3`
4. Wait Between Tries = `1000` ms

**Use Cases**:
- API rate limits
- Network timeouts
- Database locks

---

## Part 3: Code Node Try-Catch

### Basic Pattern

```javascript
try {
  const result = JSON.parse($json.data);
  return [{ json: { success: true, data: result } }];
} catch (error) {
  return [{ json: { 
    success: false, 
    error: error.message,
    original: $json.data 
  } }];
}
```

### With Fallback

```javascript
try {
  const response = await fetch($json.url);
  const data = await response.json();
  return [{ json: { data, source: 'primary' } }];
} catch (error) {
  // Try fallback
  try {
    const fallback = await fetch($json.fallback_url);
    const data = await fallback.json();
    return [{ json: { data, source: 'fallback' } }];
  } catch (fallbackError) {
    return [{ json: { 
      error: 'Both primary and fallback failed',
      primary_error: error.message,
      fallback_error: fallbackError.message
    } }];
  }
}
```

---

## Part 4: Global Error Workflow

### Creating an Error Workflow

1. Create new workflow: `Error Handler — Global`
2. Add **Error Trigger** node (under "Trigger")
3. Add error processing logic

**Error Trigger** provides:
- `$json.execution.id` — Failed execution ID
- `$json.workflow.id` — Failed workflow ID
- `$json.workflow.name` — Failed workflow name
- `$json.error.message` — Error message
- `$json.error.stack` — Stack trace

### Example Error Workflow

```
Error Trigger
     │
     ▼
Code: format.error
     │
     ├──► Postgres: log.error
     │
     └──► HTTP: send.alert (Slack/Email)
```

**Code: format.error**:
```javascript
return [{
  json: {
    timestamp: new Date().toISOString(),
    workflow_id: $json.workflow.id,
    workflow_name: $json.workflow.name,
    execution_id: $json.execution.id,
    error_message: $json.error.message,
    error_type: $json.error.name || 'UnknownError',
    correlation_id: $json.execution.data?.correlation_id || null
  }
}];
```

### Attaching Error Workflow

1. Open any workflow (e.g., Ingest Agent)
2. Workflow Settings → Error Workflow
3. Select "Error Handler — Global"
4. Save

---

## Part 5: Exponential Backoff Pattern

### Manual Implementation

When built-in retry isn't sufficient:

```javascript
// In Code node before risky operation
const attempt = $json.retry_attempt || 0;
const maxAttempts = 5;
const baseDelay = 1000; // 1 second

if (attempt >= maxAttempts) {
  throw new Error(`Max retries (${maxAttempts}) exceeded`);
}

// Calculate delay: 1s, 2s, 4s, 8s, 16s
const delay = baseDelay * Math.pow(2, attempt);
// Add jitter (±25%)
const jitter = delay * 0.25 * (Math.random() - 0.5);
const actualDelay = Math.round(delay + jitter);

return [{
  json: {
    ...$json,
    retry_attempt: attempt + 1,
    retry_delay_ms: actualDelay
  }
}];
```

Then use a **Wait** node with dynamic delay:
- Amount: `={{$json.retry_delay_ms}}`
- Unit: `Milliseconds`

---

## Part 6: Dead Letter Queue

### Concept

When a message fails permanently, send it to a "dead letter queue" for human review instead of losing it.

### Implementation

**Table for DLQ**:
```sql
CREATE TABLE dead_letter_queue (
  dlq_id BIGSERIAL PRIMARY KEY,
  source_workflow VARCHAR(255),
  source_execution VARCHAR(255),
  payload JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ,
  reviewed_by VARCHAR(255),
  resolution VARCHAR(50) -- 'retried', 'ignored', 'fixed'
);
```

**Add to Error Workflow**:
```sql
INSERT INTO dead_letter_queue (
  source_workflow, 
  source_execution, 
  payload, 
  error_message
) VALUES (
  '{{$json.workflow_name}}',
  '{{$json.execution_id}}',
  '{{JSON.stringify($json)}}',
  '{{$json.error_message}}'
);
```

### Review Process

1. Query DLQ daily
2. Investigate root cause
3. Fix data/code
4. Mark as resolved or retry

---

## Part 7: Alerting Integration

### Slack Alert

```javascript
// In Error Workflow after logging
const slackWebhook = $env.SLACK_WEBHOOK_URL;

// HTTP Request node configuration
// URL: {{slackWebhook}}
// Method: POST
// Body:
{
  "text": ":rotating_light: *Workflow Failed*",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Workflow:* {{$json.workflow_name}}\n*Error:* {{$json.error_message}}\n*Time:* {{$json.timestamp}}"
      }
    }
  ]
}
```

### Email Alert

Use Email Send node with:
- Subject: `[ALERT] Workflow Failed: {{$json.workflow_name}}`
- Body: Include error details, execution ID, timestamp

---

## Part 8: Circuit Breaker Pattern

### Concept

When a service is down, stop hammering it. Open the circuit, wait, then try again.

### Implementation with Redis/Memory

```javascript
// Check circuit state
const circuitKey = `circuit:${$json.service}`;
const circuitState = await redis.get(circuitKey);

if (circuitState === 'open') {
  const cooldownEnd = await redis.get(`${circuitKey}:cooldown`);
  if (Date.now() < cooldownEnd) {
    throw new Error(`Circuit open for ${$json.service}`);
  }
  // Try half-open
}

try {
  // Attempt operation
  const result = await callService();
  // Success - close circuit
  await redis.set(circuitKey, 'closed');
  return [{ json: result }];
} catch (error) {
  // Increment failure count
  const failures = await redis.incr(`${circuitKey}:failures`);
  if (failures >= 5) {
    // Open circuit
    await redis.set(circuitKey, 'open');
    await redis.set(`${circuitKey}:cooldown`, Date.now() + 60000); // 1 minute
  }
  throw error;
}
```

---

## Module 11 Summary

### Error Handling Levels

| Level | Technique | When to Use |
|-------|-----------|-------------|
| Node | Continue On Fail | Non-critical |
| Node | Retry On Fail | Transient errors |
| Code | try-catch | Custom logic |
| Workflow | Error Workflow | Centralized |
| System | Dead Letter Queue | Permanent failures |

### Best Practices

1. **Log everything** — Structured logs with correlation IDs
2. **Alert fast** — Don't wait for user reports
3. **Fail gracefully** — Partial success is better than total failure
4. **Review DLQ** — Don't let failures pile up
5. **Test failures** — Intentionally break things in dev

---

## Next Steps

Proceed to **Module 12: Testing & Debugging Strategies** where you'll learn:
- **Manual testing** with webhook-test endpoints
- **Execution history** analysis
- **Expression debugging**
- **Pinned data** for reproducible tests

---

*Module 11 Complete — Proceed to Module 12: Testing & Debugging*
