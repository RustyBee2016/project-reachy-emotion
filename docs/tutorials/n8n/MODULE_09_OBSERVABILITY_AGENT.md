# Module 9: Observability Agent — Metrics Collection & Time-Series Storage

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~3 hours  
**Prerequisites**: Completed Modules 0-8

---

## Learning Objectives

By the end of this module, you will:
1. Implement **high-frequency scheduled triggers** (30-second intervals)
2. Parse **Prometheus-format metrics**
3. Aggregate data from **multiple sources** in parallel
4. Store **time-series data** in PostgreSQL
5. Understand **observability SLOs** for the agentic system

---

## New Concepts in This Module

| Concept | Node/Technique | Why It Matters |
|---------|---------------|----------------|
| **High-frequency cron** | Every 30 seconds | Near real-time monitoring |
| **Prometheus format** | Text parsing | Standard metrics format |
| **Multi-source merge** | Parallel HTTP calls | Aggregate from services |
| **Time-series storage** | obs_samples table | Historical data for dashboards |
| **Regex parsing** | JavaScript RegExp | Extract metric values |

---

## Pre-Wiring Checklist: Backend Functionality Verification

### Functionality Checklist

| # | Node | Backend Functionality | Status |
|---|------|----------------------|--------|
| 1 | Cron: every 30s | n8n scheduler | ⬜ (native) |
| 2 | HTTP: n8n.metrics | n8n /metrics endpoint | ⬜ |
| 3 | HTTP: mediamover.metrics | Media Mover /metrics | ⬜ |
| 4 | HTTP: gateway.metrics | Gateway /metrics | ⬜ |
| 5 | Code: parse.metrics | JavaScript | ⬜ (native) |
| 6 | Postgres: store.metrics | obs_samples table | ⬜ |

---

### Verification Procedures

#### Test 1: n8n Built-in Metrics

```bash
curl http://10.0.4.130:5678/metrics
```

**Expected**: Prometheus-format text with n8n metrics.

**Status**: ⬜ → [ ] Complete

---

#### Test 2: obs_samples Table

```sql
-- Check if table exists
\d obs_samples

-- If missing, create it:
CREATE TABLE IF NOT EXISTS obs_samples (
  sample_id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  src VARCHAR(50) NOT NULL,
  metric VARCHAR(100) NOT NULL,
  value DOUBLE PRECISION,
  extra_data JSONB
);

-- Create index for time-range queries
CREATE INDEX IF NOT EXISTS idx_obs_samples_ts ON obs_samples(ts);
CREATE INDEX IF NOT EXISTS idx_obs_samples_src_metric ON obs_samples(src, metric);
```

**Status**: ⬜ → [ ] Complete

---

#### Test 3: Media Mover Metrics (TBD)

```bash
curl http://10.0.4.130:9101/metrics
```

**⚠️ Note**: This endpoint may not exist yet. You can skip this node or implement it later.

**Status**: ⬜ → [ ] Complete (or N/A)

---

## Part 1: Understanding Observability

### Why Observability?

The agentic system has 10 workflows running autonomously. Without observability:
- No visibility into system health
- Can't detect problems before users do
- No data for optimization

### Metrics Sources

| Source | URL | Metrics |
|--------|-----|---------|
| n8n | `http://localhost:5678/metrics` | Executions, queue depth |
| Media Mover | `http://10.0.4.130:9101/metrics` | Promotions, ingests |
| Gateway | `http://10.0.4.140:9100/metrics` | Requests, queue depth |

### Prometheus Format

```prometheus
# HELP n8n_active_executions Number of active executions
# TYPE n8n_active_executions gauge
n8n_active_executions 3

# HELP n8n_workflow_executions_total Total workflow executions
# TYPE n8n_workflow_executions_total counter
n8n_workflow_executions_total{status="success"} 1234
n8n_workflow_executions_total{status="error"} 12
```

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY AGENT FLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Cron: every 30s                                                        │
│        │                                                                │
│        ├──────────────────┬──────────────────┐                          │
│        │                  │                  │                          │
│        ▼                  ▼                  ▼                          │
│  HTTP: n8n         HTTP: mediamover    HTTP: gateway                    │
│   .metrics            .metrics           .metrics                       │
│        │                  │                  │                          │
│        └──────────────────┼──────────────────┘                          │
│                           │                                             │
│                           ▼                                             │
│                   Code: parse.metrics                                   │
│                           │                                             │
│                           ▼                                             │
│                   Postgres: store.metrics                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Wiring the Workflow — Step by Step

### Step 1: Create the Workflow

1. Create: `Agent 9 — Observability Agent (Reachy 08.4.2)`
2. Settings: Execution Order = `v1`

---

### Step 2: Add High-Frequency Cron

**Node Name**: `Cron: every 30s`

| Parameter | Value |
|-----------|-------|
| Trigger Mode | `Every X` |
| Value | `30` |
| Unit | `Seconds` |

**Alternative (Cron Expression)**:
```
*/30 * * * * *  (if seconds supported)
```

Or use two triggers:
- `0 * * * * *` (every minute at :00)
- `30 * * * * *` (every minute at :30)

---

### Step 3: Add n8n Metrics Fetch

**Node Name**: `HTTP: n8n.metrics`

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| URL | `http://localhost:5678/metrics` |
| Response Format | `String` |

**Note**: Use `localhost` because this runs ON the n8n server.

---

### Step 4: Add Media Mover Metrics Fetch

**Node Name**: `HTTP: mediamover.metrics`

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| URL | `http://10.0.4.130:9101/metrics` |
| Response Format | `String` |
| Continue On Fail | `true` |

**Continue On Fail**: Prevents workflow failure if this endpoint doesn't exist yet.

---

### Step 5: Add Gateway Metrics Fetch

**Node Name**: `HTTP: gateway.metrics`

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| URL | `http://10.0.4.140:9100/metrics` |
| Response Format | `String` |
| Continue On Fail | `true` |

---

### Step 6: Connect in Parallel

From the Cron trigger, connect to all three HTTP nodes:
- Cron → n8n.metrics
- Cron → mediamover.metrics
- Cron → gateway.metrics

All three execute concurrently.

---

### Step 7: Add Metrics Parser

**Node Name**: `Code: parse.metrics`

Connect ALL three HTTP nodes to this Code node.

```javascript
// Parse Prometheus-format metrics from multiple sources
function parseMetric(text, metricName) {
  if (!text) return null;
  const regex = new RegExp(`${metricName}\\s+([\\d.]+)`);
  const match = text.match(regex);
  return match ? parseFloat(match[1]) : null;
}

const ts = new Date().toISOString();
const items = [];

// Get raw text from each source
const n8nText = $('HTTP: n8n.metrics').first()?.json?.data || '';
const mmText = $('HTTP: mediamover.metrics').first()?.json?.data || '';
const gwText = $('HTTP: gateway.metrics').first()?.json?.data || '';

// Parse n8n metrics
const n8nActiveExec = parseMetric(n8nText, 'n8n_active_executions');
if (n8nActiveExec !== null) {
  items.push({
    json: { ts, src: 'n8n', metric: 'active_executions', value: n8nActiveExec }
  });
}

const n8nExecSuccess = parseMetric(n8nText, 'n8n_workflow_executions_total{status="success"}');
if (n8nExecSuccess !== null) {
  items.push({
    json: { ts, src: 'n8n', metric: 'executions_success', value: n8nExecSuccess }
  });
}

// Parse Media Mover metrics (if available)
const mmPromoteTotal = parseMetric(mmText, 'media_mover_promote_total');
if (mmPromoteTotal !== null) {
  items.push({
    json: { ts, src: 'media_mover', metric: 'promote_total', value: mmPromoteTotal }
  });
}

// Parse Gateway metrics (if available)
const gwQueueDepth = parseMetric(gwText, 'gateway_queue_depth');
if (gwQueueDepth !== null) {
  items.push({
    json: { ts, src: 'gateway', metric: 'queue_depth', value: gwQueueDepth }
  });
}

// Return only items with valid values
return items.filter(i => i.json.value !== null);
```

---

### Step 8: Add Metrics Storage

**Node Name**: `Postgres: store.metrics`

| Parameter | Value |
|-----------|-------|
| Credential | `PostgreSQL - reachy_local` |
| Operation | `Insert` |
| Table | `obs_samples` |
| Columns | `ts, src, metric, value` |

**Column Mapping**:
| Column | Value |
|--------|-------|
| ts | `={{$json.ts}}` |
| src | `={{$json.src}}` |
| metric | `={{$json.metric}}` |
| value | `={{$json.value}}` |

---

## Part 3: Querying Stored Metrics

### Sample Queries for Dashboards

**Latest value per metric**:
```sql
SELECT DISTINCT ON (src, metric)
  ts, src, metric, value
FROM obs_samples
ORDER BY src, metric, ts DESC;
```

**Last hour's data**:
```sql
SELECT ts, src, metric, value
FROM obs_samples
WHERE ts > NOW() - INTERVAL '1 hour'
ORDER BY ts;
```

**Average queue depth per minute**:
```sql
SELECT 
  date_trunc('minute', ts) AS minute,
  AVG(value) AS avg_queue_depth
FROM obs_samples
WHERE src = 'gateway' AND metric = 'queue_depth'
  AND ts > NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute DESC;
```

**Error rate over time**:
```sql
SELECT 
  date_trunc('hour', ts) AS hour,
  MAX(CASE WHEN metric = 'executions_success' THEN value END) AS success,
  MAX(CASE WHEN metric = 'executions_error' THEN value END) AS errors
FROM obs_samples
WHERE src = 'n8n'
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

---

## Part 4: Observability SLOs

From AGENTS.md, the system has these SLOs:

| Metric | Target | How to Monitor |
|--------|--------|----------------|
| Planner P50 | ≤ 2s | Track execution latency |
| Planner P95 | ≤ 5s | Track execution latency |
| Error Budget | < 1% weekly | Track error/success ratio |
| Trace Propagation | correlation_id present | Audit log checks |

### Adding SLO Alerting (Future Enhancement)

```javascript
// In parse.metrics, add SLO check
const errorRate = n8nExecErrors / (n8nExecSuccess + n8nExecErrors);
if (errorRate > 0.01) {
  // Emit alert
  items.push({
    json: {
      ts,
      src: 'slo',
      metric: 'error_budget_exceeded',
      value: errorRate,
      alert: true
    }
  });
}
```

---

## Part 5: Testing

### Test 1: Manual Trigger

Since cron runs every 30 seconds, you can test manually:

1. Execute the workflow manually
2. Check execution output for parsed metrics
3. Query the database:

```sql
SELECT * FROM obs_samples ORDER BY ts DESC LIMIT 10;
```

### Test 2: Wait for Cron

1. Activate the workflow
2. Wait 1-2 minutes
3. Check database for new records

### Test 3: Dashboard Query

```sql
-- Verify data is being collected
SELECT 
  src,
  metric,
  COUNT(*) as samples,
  MIN(ts) as first_sample,
  MAX(ts) as last_sample
FROM obs_samples
GROUP BY src, metric
ORDER BY src, metric;
```

---

## Module 9 Summary

### What You Learned

| Concept | Implementation |
|---------|---------------|
| High-frequency polling | Cron every 30 seconds |
| Prometheus parsing | Regex extraction |
| Parallel HTTP | Multiple connections from trigger |
| Multi-source merge | `$('NodeName').first()` |
| Time-series storage | INSERT with timestamp |

### Nodes Created

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Cron: every 30s | Schedule Trigger | High-frequency trigger |
| 2 | HTTP: n8n.metrics | HTTP Request | n8n metrics |
| 3 | HTTP: mediamover.metrics | HTTP Request | Media Mover metrics |
| 4 | HTTP: gateway.metrics | HTTP Request | Gateway metrics |
| 5 | Code: parse.metrics | Code | Parse Prometheus format |
| 6 | Postgres: store.metrics | Postgres | Store time-series |

---

## Next Steps

Proceed to **Module 10: ML Pipeline Orchestrator** where you'll learn:
- **Workflow-to-workflow calls** (triggering other agents)
- **End-to-end pipeline coordination**
- **Auto-deploy mode** configuration
- **Pipeline state management**

---

*Module 9 Complete — Proceed to Module 10: ML Pipeline Orchestrator*
