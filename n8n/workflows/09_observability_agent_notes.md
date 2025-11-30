# Agent 9 — Observability / Telemetry Agent (Workflow `09_observability_agent.json`)

Rusty, this note walks through the telemetry workflow so you can rebuild it in n8n without losing details. It starts with an alphabetical node inventory, then covers inputs, parameter JSON snippets you can paste, and the control flow that samples metrics every 30 seconds.

## Alphabetical inventory of nodes (workflow scope)
- Code: parse.metrics
- Cron: every 30s
- HTTP: gateway.metrics
- HTTP: mediamover.metrics
- HTTP: n8n.metrics
- Postgres: store.metrics

---

## Node-by-node flow details
The workflow fires every 30 seconds, scrapes Prometheus-style metrics from n8n, Media Mover, and Gateway, parses a few key counters, and stores them in the `obs_samples` table for dashboards and alerts.

### Cron node
**Cron: every 30s** — Time-based trigger that kicks off each scrape. It emits an empty item that fans out to the three HTTP requests.

Parameters:
```json
{ "rule": { "interval": [{ "triggerAtSecond": 30 }] } }
```

### HTTP Request nodes
Each HTTP node receives the Cron trigger item and fetches a Prometheus text payload.

**HTTP: n8n.metrics** — Pulls `/metrics` from the local n8n instance running inside Docker.

Parameters:
```json
{ "url": "http://n8n:5678/metrics", "responseFormat": "string" }
```

**HTTP: mediamover.metrics** — Scrapes the Media Mover Prometheus exporter on Ubuntu 1.

Parameters:
```json
{ "url": "http://10.0.4.130:9101/metrics", "responseFormat": "string" }
```

**HTTP: gateway.metrics** — Scrapes the Gateway service exporter on Ubuntu 2.

Parameters:
```json
{ "url": "http://10.0.4.140:9100/metrics", "responseFormat": "string" }
```

### Code node
**Code: parse.metrics** — Aggregates the three HTTP responses, extracts specific counters, and emits one item per parsed metric. It uses a helper regex to locate the numeric value after each metric name; nulls are filtered out so only found metrics proceed.

Parameters:
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "const parseMetric = (text, name) => {\n  const m = text.match(new RegExp(`${name}\\\\s+(\\\\d+\\\\.?\\\\d*)`));\n  return m ? parseFloat(m[1]) : null;\n};\n\nconst ts = new Date().toISOString();\nconst items = [];\n\nconst n8n = $('fetch_n8n_metrics').first().json.data;\nconst mm = $('fetch_mm_metrics').first().json.data;\nconst gw = $('fetch_gw_metrics').first().json.data;\n\nitems.push({ json: { ts, src: 'n8n', metric: 'active_executions', value: parseMetric(n8n, 'n8n_active_executions') } });\nitems.push({ json: { ts, src: 'media_mover', metric: 'promote_total', value: parseMetric(mm, 'media_mover_promote_total') } });\nitems.push({ json: { ts, src: 'gateway', metric: 'queue_depth', value: parseMetric(gw, 'gateway_queue_depth') } });\n\nreturn items.filter(i => i.json.value !== null);"
}
```

### Postgres node
**Postgres: store.metrics** — Inserts each emitted metric item into `obs_samples` with timestamp, source, metric name, and value. It receives the array of parsed items from the Code node.

Parameters:
```json
{ "operation": "insert", "table": "obs_samples", "columns": "ts, src, metric, value" }
```

### Flow wiring (inputs between nodes)
- **Cron every 30s** fans out to **HTTP n8n.metrics**, **HTTP mediamover.metrics**, and **HTTP gateway.metrics** (they all share the same trigger item).
- The three **HTTP** nodes converge into **Code parse.metrics**, which reads each response via the node selectors.
- **Code parse.metrics** outputs one item per metric and passes them to **Postgres store.metrics** for persistence.

This keeps a rolling series of metrics samples: the Cron trigger controls cadence, HTTP nodes fetch raw Prometheus text, the Code node normalizes and filters the values Rusty cares about, and Postgres keeps an append-only history for Grafana dashboards and alerting thresholds.
