# Agent 9 — Observability/Telemetry Agent (Reachy 08.4.2)

> **Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/09_observability_agent.json`  
> **Version:** 08.4.2  
> **Last Updated:** 2025-11-07

## Overview

The Observability/Telemetry Agent aggregates system metrics from n8n, Media Mover, and Gateway services. It runs every 30 seconds, fetches Prometheus-format metrics via HTTP, parses them, and stores samples in PostgreSQL for dashboarding and alerting.

## Node Inventory (Alphabetical)

| Node Name | Node Type | Node ID |
|-----------|-----------|---------|
| Code: parse.metrics | n8n-nodes-base.code | parse_metrics |
| Cron: every 30s | n8n-nodes-base.cron | cron_metrics |
| HTTP: gateway.metrics | n8n-nodes-base.httpRequest | fetch_gw_metrics |
| HTTP: mediamover.metrics | n8n-nodes-base.httpRequest | fetch_mm_metrics |
| HTTP: n8n.metrics | n8n-nodes-base.httpRequest | fetch_n8n_metrics |
| Postgres: store.metrics | n8n-nodes-base.postgres | db_store_metrics |

---

## Workflow Flow (Left to Right, Top to Bottom)

```
Cron: every 30s
    │
    ├──► HTTP: n8n.metrics ─────────┐
    │                               │
    ├──► HTTP: mediamover.metrics ──┼──► Code: parse.metrics
    │                               │            │
    └──► HTTP: gateway.metrics ─────┘            ▼
                                        Postgres: store.metrics
```

---

## Node Details

### 1. Cron: every 30s

**Type:** `n8n-nodes-base.cron` (v2)  
**Position:** [-400, 300]  
**Purpose:** Triggers metrics collection every 30 seconds.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `rule.interval[0].triggerAtSecond` | `30` | Trigger at :00 and :30 |

#### Frequency

- **Interval:** 30 seconds
- **Daily executions:** 2,880
- **Purpose:** Near real-time observability

#### Test Status: ✅ OPERATIONAL

---

### 2. HTTP: n8n.metrics

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-200, 200]  
**Purpose:** Fetches n8n internal metrics.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `http://n8n:5678/metrics` | n8n metrics endpoint |
| `responseFormat` | `string` | Raw Prometheus format |

#### Expected Metrics

```prometheus
# HELP n8n_active_executions Number of active executions
# TYPE n8n_active_executions gauge
n8n_active_executions 3

# HELP n8n_workflow_executions_total Total workflow executions
# TYPE n8n_workflow_executions_total counter
n8n_workflow_executions_total{status="success"} 1234
n8n_workflow_executions_total{status="error"} 12
```

#### Test Status: ✅ OPERATIONAL

---

### 3. HTTP: mediamover.metrics

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-200, 300]  
**Purpose:** Fetches Media Mover service metrics.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `http://10.0.4.130:9101/metrics` | Media Mover metrics |
| `responseFormat` | `string` | Raw Prometheus format |

#### Expected Metrics

```prometheus
# HELP media_mover_promote_total Total promotions
# TYPE media_mover_promote_total counter
media_mover_promote_total 456

# HELP media_mover_ingest_total Total ingests
# TYPE media_mover_ingest_total counter
media_mover_ingest_total 789
```

#### Test Status: ⚠️ TBD (requires metrics endpoint)

---

### 4. HTTP: gateway.metrics

**Type:** `n8n-nodes-base.httpRequest` (v4)  
**Position:** [-200, 400]  
**Purpose:** Fetches Gateway service metrics.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `url` | `http://10.0.4.140:9100/metrics` | Gateway metrics |
| `responseFormat` | `string` | Raw Prometheus format |

#### Expected Metrics

```prometheus
# HELP gateway_queue_depth Current queue depth
# TYPE gateway_queue_depth gauge
gateway_queue_depth 5

# HELP gateway_requests_total Total requests
# TYPE gateway_requests_total counter
gateway_requests_total{endpoint="/api/events"} 1000
```

#### Test Status: ⚠️ TBD (requires metrics endpoint)

---

### 5. Code: parse.metrics

**Type:** `n8n-nodes-base.code` (v2)  
**Position:** [0, 300]  
**Purpose:** Parses Prometheus-format metrics into structured data.

#### JavaScript Code

```javascript
const parseMetric = (text, name) => {
  const m = text.match(new RegExp(`${name}\\s+(\\d+\\.?\\d*)`));
  return m ? parseFloat(m[1]) : null;
};

const ts = new Date().toISOString();
const items = [];

const n8n = $('fetch_n8n_metrics').first().json.data;
const mm = $('fetch_mm_metrics').first().json.data;
const gw = $('fetch_gw_metrics').first().json.data;

items.push({
  json: {
    ts,
    src: 'n8n',
    metric: 'active_executions',
    value: parseMetric(n8n, 'n8n_active_executions')
  }
});

items.push({
  json: {
    ts,
    src: 'media_mover',
    metric: 'promote_total',
    value: parseMetric(mm, 'media_mover_promote_total')
  }
});

items.push({
  json: {
    ts,
    src: 'gateway',
    metric: 'queue_depth',
    value: parseMetric(gw, 'gateway_queue_depth')
  }
});

return items.filter(i => i.json.value !== null);
```

#### Metrics Extracted

| Source | Metric | Description |
|--------|--------|-------------|
| n8n | `active_executions` | Current running workflows |
| media_mover | `promote_total` | Total promotions |
| gateway | `queue_depth` | Event queue depth |

#### Output Schema (per item)

```json
{
  "ts": "2025-11-07T03:00:30.000Z",
  "src": "n8n",
  "metric": "active_executions",
  "value": 3
}
```

#### Test Status: ✅ OPERATIONAL

---

### 6. Postgres: store.metrics

**Type:** `n8n-nodes-base.postgres` (v2.4)  
**Position:** [200, 300]  
**Purpose:** Stores parsed metrics in the database.

#### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `operation` | `insert` | Insert new records |
| `table` | `obs_samples` | Observability samples table |
| `columns` | `ts, src, metric, value` | Columns to insert |

#### Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `ObsSample` | 247-268 | Observability sample model |

**ObsSample Schema:**

| Column | Type | Purpose |
|--------|------|---------|
| `sample_id` | `BigInteger` | Primary key |
| `ts` | `DateTime` | Timestamp |
| `src` | `String(50)` | Source service |
| `metric` | `String(100)` | Metric name |
| `value` | `Float` | Metric value |

#### Credentials

| Credential Type | ID | Name |
|-----------------|-----|------|
| `postgres` | `2` | PostgreSQL - reachy_local |

#### Test Status: ✅ OPERATIONAL

---

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| (none) | URLs are hardcoded | N/A |

---

## Credentials Required

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 2 | PostgreSQL - reachy_local | PostgreSQL | Metrics storage |

---

## Tags

- `agent`
- `observability`

---

## Metrics Endpoints

| Service | URL | Port | Status |
|---------|-----|------|--------|
| n8n | `http://n8n:5678/metrics` | 5678 | ✅ Built-in |
| Media Mover | `http://10.0.4.130:9101/metrics` | 9101 | ⚠️ TBD |
| Gateway | `http://10.0.4.140:9100/metrics` | 9100 | ⚠️ TBD |

---

## Observability SLOs (from AGENTS.md)

| Metric | Target | Description |
|--------|--------|-------------|
| Planner Actions P50 | ≤ 2s | 50th percentile latency |
| Planner Actions P95 | ≤ 5s | 95th percentile latency |
| Error Budget | < 1% weekly | Per agent error rate |

---

## Related Code

**File:** `apps/api/app/db/models.py`

| Class | Lines | Purpose |
|-------|-------|---------|
| `ObsSample` | 247-268 | Metrics storage model |

---

## TBD Items

| Item | Priority | Required Actions |
|------|----------|------------------|
| Media Mover Metrics | HIGH | Add `/metrics` endpoint to media.py |
| Gateway Metrics | HIGH | Add `/metrics` endpoint to gateway.py |
| Grafana Dashboard | MEDIUM | Create dashboard for stored metrics |
| Alerting Rules | MEDIUM | Define alert thresholds |
| More Metrics | LOW | Add latency, error rates, queue depths |

---

## Connections Summary

```json
{
  "cron_metrics": { 
    "main": [["fetch_n8n_metrics", "fetch_mm_metrics", "fetch_gw_metrics"]] 
  },
  "fetch_n8n_metrics": { "main": [["parse_metrics"]] },
  "fetch_mm_metrics": { "main": [["parse_metrics"]] },
  "fetch_gw_metrics": { "main": [["parse_metrics"]] },
  "parse_metrics": { "main": [["db_store_metrics"]] }
}
```

---

## Sample Query for Dashboard

```sql
-- Get latest metrics by source
SELECT DISTINCT ON (src, metric)
  ts, src, metric, value
FROM obs_samples
ORDER BY src, metric, ts DESC;

-- Get metrics over last hour
SELECT ts, src, metric, value
FROM obs_samples
WHERE ts > NOW() - INTERVAL '1 hour'
ORDER BY ts;

-- Calculate average queue depth
SELECT 
  date_trunc('minute', ts) AS minute,
  AVG(value) AS avg_queue_depth
FROM obs_samples
WHERE src = 'gateway' AND metric = 'queue_depth'
GROUP BY minute
ORDER BY minute DESC
LIMIT 60;
```
