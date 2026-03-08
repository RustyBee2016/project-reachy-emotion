# MODULE 09 -- Observability/Telemetry Agent

**Duration:** ~3 hours
**Workflow File:** `n8n/workflows/ml-agentic-ai_v.2/09_observability_agent.json`
**Nodes to Wire:** 6
**Prerequisite:** MODULE 08 complete
**Outcome:** A high-frequency metrics collector that scrapes Prometheus endpoints from all three infrastructure nodes every 30 seconds and stores time-series data in PostgreSQL

---

## 9.1 What Does the Observability Agent Do?

This is the simplest agent by node count (6 nodes) but introduces a powerful pattern: **parallel HTTP fan-out for metrics collection**.

Every 30 seconds, it:
1. Fires a cron trigger
2. Simultaneously scrapes 3 Prometheus endpoints (n8n, Media Mover, Gateway)
3. Parses all three text responses into structured metrics
4. Stores the metrics in the `obs_samples` time-series table

### Architecture

```
                    ┌──► n8n:5678/metrics ─────────┐
                    │                               │
Cron (30s) ────────┼──► 10.0.4.130:9101/metrics ──┼──► Parse ──► PostgreSQL
                    │                               │     (merge)   (obs_samples)
                    └──► 10.0.4.140:9100/metrics ──┘
```

### New Concept: Parallel Fan-Out

This is the first workflow where a trigger node has **three outputs** going to three different nodes simultaneously.

---

## 9.2 Pre-Wiring Checklist

- [ ] **n8n metrics** enabled (set `N8N_METRICS=true` in n8n's environment):
  ```bash
  curl -s http://localhost:5678/metrics | head -5
  ```
- [ ] **Media Mover metrics** available:
  ```bash
  curl -s http://10.0.4.130:9101/metrics | head -5
  ```
- [ ] **Gateway metrics** available:
  ```bash
  curl -s http://10.0.4.140:9100/metrics | head -5
  ```
- [ ] **PostgreSQL** `obs_samples` table exists:
  ```bash
  psql -h localhost -U reachy_dev -d reachy_emotion -c "\d obs_samples"
  ```

---

## 9.3 Create the Workflow

1. Name: `Agent 9 -- Observability/Telemetry Agent (Reachy 08.4.2)`
2. Tags: `agent`, `observability`

---

## 9.4 Wire Node 1: cron_metrics

This is the first time we use a **Cron** node (different from Schedule Trigger).

### Step-by-Step

1. Add a **Cron** node → rename to `cron_metrics`
2. Configure:

| Parameter | Value | Why |
|-----------|-------|-----|
| **Mode** | `Every X` | Simple interval-based trigger |
| **Value** | `30` | Fire every 30 seconds |
| **Unit** | `Seconds` | Near-real-time metrics collection |

### Cron vs Schedule Trigger

| Feature | Cron Node | Schedule Trigger |
|---------|-----------|-----------------|
| Minimum interval | Seconds | Minutes |
| Best for | High-frequency tasks | Daily/hourly schedules |
| Cron expression | Optional | Required |

We use Cron here because Schedule Trigger can't fire every 30 seconds.

---

## 9.5 Wire Node 2: fetch_n8n_metrics

### Step-by-Step

1. Add an **HTTP Request** node → rename to `fetch_n8n_metrics`
2. **Connect `cron_metrics` → `fetch_n8n_metrics`**
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `http://n8n:5678/metrics` |

### Why `http://n8n:5678`?

If n8n is running in Docker, `n8n` resolves to the container's hostname. If running natively, use `http://localhost:5678`.

---

## 9.6 Wire Node 3: fetch_mm_metrics

1. Add an **HTTP Request** node → rename to `fetch_mm_metrics`
2. **Connect `cron_metrics` → `fetch_mm_metrics`** (this is the parallel fan-out)
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `http://10.0.4.130:9101/metrics` |

---

## 9.7 Wire Node 4: fetch_gw_metrics

1. Add an **HTTP Request** node → rename to `fetch_gw_metrics`
2. **Connect `cron_metrics` → `fetch_gw_metrics`** (third parallel output)
3. Configure:

| Parameter | Value |
|-----------|-------|
| **Method** | `GET` |
| **URL** | `http://10.0.4.140:9100/metrics` |

### Parallel Fan-Out Wiring

After connecting all three, your cron node should have three outgoing connections. When the cron fires, all three HTTP requests execute **simultaneously**. This is much faster than sequential fetching.

```
           ┌──► fetch_n8n_metrics
           │
cron ──────┼──► fetch_mm_metrics
           │
           └──► fetch_gw_metrics
```

---

## 9.8 Wire Node 5: parse_metrics

This Code node receives data from all three HTTP nodes and merges them.

### Step-by-Step

1. Add a **Code** node → rename to `parse_metrics`
2. **Connect all three fetch nodes to this node:**
   - `fetch_n8n_metrics` → `parse_metrics`
   - `fetch_mm_metrics` → `parse_metrics`
   - `fetch_gw_metrics` → `parse_metrics`
3. Mode: `Run Once for All Items`
4. Code:

```javascript
// Helper: parse Prometheus text format
function parsePrometheus(text, source) {
  const metrics = [];
  const lines = (text || '').split('\n');

  for (const line of lines) {
    // Skip comments and empty lines
    if (line.startsWith('#') || line.trim() === '') continue;

    // Parse: metric_name{labels} value
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([\d.eE+-]+)/);
    if (match) {
      metrics.push({
        src: source,
        metric: match[1],
        value: parseFloat(match[2])
      });
    }
  }
  return metrics;
}

// Get data from all three sources
const n8nData = $('fetch_n8n_metrics').first()?.json?.data || '';
const mmData = $('fetch_mm_metrics').first()?.json?.data || '';
const gwData = $('fetch_gw_metrics').first()?.json?.data || '';

// Parse all sources
const allMetrics = [
  ...parsePrometheus(n8nData, 'n8n'),
  ...parsePrometheus(mmData, 'media_mover'),
  ...parsePrometheus(gwData, 'gateway')
];

// Filter to key metrics we care about
const keyMetrics = [
  'n8n_active_executions',
  'n8n_workflow_executions_total',
  'media_mover_promote_total',
  'media_mover_ingest_total',
  'gateway_queue_depth',
  'gateway_request_duration_seconds'
];

const filtered = allMetrics.filter(m =>
  keyMetrics.some(k => m.metric.startsWith(k))
);

const ts = new Date().toISOString();

// Return as individual items for batch insert
return filtered.map(m => ({
  json: {
    ts,
    src: m.src,
    metric: m.metric,
    value: m.value
  }
}));
```

### Key Parsing Logic

Prometheus metrics are plain text:
```
# HELP n8n_active_executions Number of active executions
# TYPE n8n_active_executions gauge
n8n_active_executions 3
```

The regex `^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([\d.eE+-]+)` extracts the metric name and value, ignoring comment lines.

### `$('NodeName').first()` Pattern

When a Code node has multiple inputs, use `$('NodeName').first()` to explicitly reference which source you want. This is the same pattern we used in Module 04 (Reconciler).

---

## 9.9 Wire Node 6: db_store_metrics

### Step-by-Step

1. Add a **Postgres** node → rename to `db_store_metrics`
2. Configure:

| Parameter | Value |
|-----------|-------|
| **Credential** | `PostgreSQL - reachy_local` |
| **Operation** | `Execute Query` |
| **Query** | *(see below)* |

```sql
INSERT INTO obs_samples (ts, src, metric, value)
VALUES (
  '{{ $json.ts }}'::timestamptz,
  '{{ $json.src }}',
  '{{ $json.metric }}',
  {{ $json.value }}
);
```

### Time-Series Storage

The `obs_samples` table stores timestamped metric readings. Over time, this builds a time-series dataset that can be queried for dashboards:

```sql
-- Example: Get average n8n active executions over the last hour
SELECT
  date_trunc('minute', ts) AS minute,
  AVG(value) AS avg_value
FROM obs_samples
WHERE metric = 'n8n_active_executions'
  AND ts > NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute;
```

---

## 9.10 Final Connection Map

```
cron_metrics ──┬──► fetch_n8n_metrics ──┐
               │                         │
               ├──► fetch_mm_metrics  ──┼──► parse_metrics ──► db_store_metrics
               │                         │
               └──► fetch_gw_metrics ──┘
```

---

## 9.11 Testing

### Manual Test

1. Execute the workflow manually
2. Check that all three HTTP nodes succeed
3. Verify data in PostgreSQL:
   ```sql
   SELECT * FROM obs_samples ORDER BY ts DESC LIMIT 20;
   ```

### Activate and Monitor

1. Toggle the workflow **Active: ON**
2. Wait 2 minutes
3. Check execution history -- you should see ~4 executions (30s interval)
4. Query the database to verify time-series data is accumulating

### Performance Note

This workflow runs every 30 seconds, producing many executions. Consider:
- Setting **Save Successful Executions** to `No` in workflow settings to save disk space
- Monitoring n8n's own performance (meta!)

---

## 9.12 Key Concepts Learned

- **Cron node** for sub-minute intervals
- **Parallel fan-out** -- one trigger to three simultaneous HTTP requests
- **Multiple inputs to one node** -- `parse_metrics` receives from 3 sources
- **Prometheus text format parsing** with regex
- **Time-series data storage** in PostgreSQL
- **`$('NodeName').first()`** for explicit source referencing in multi-input nodes

---

*Previous: [MODULE 08 -- Deployment Agent](MODULE_08_DEPLOYMENT_AGENT.md)*
*Next: [MODULE 10 -- ML Pipeline Orchestrator](MODULE_10_ML_PIPELINE_ORCHESTRATOR.md)*
