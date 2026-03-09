# Agent 9 — Observability/Telemetry Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/09_observability_agent.json`

## Related Scripts and Functionalities
- `apps/api/app/routers/metrics.py` exposes Media Mover metrics at `/metrics`.
- `apps/api/routers/gateway.py` exposes gateway metrics at `/metrics`.
- Parsed telemetry is stored in `obs_samples` via `Postgres: store.metrics`.

## Before You Start
1. In n8n, create a new workflow and set the workflow name exactly as shown above.
2. Ensure all required credentials exist in n8n before wiring nodes.
- `Postgres: store.metrics` uses credential type `postgres` with display name `PostgreSQL - reachy_local`.
3. Set required environment variables in n8n runtime/environment:
- `GATEWAY_BASE_URL`

## Step 1: Add and Configure Nodes
### Step 1 - `Cron: every 30s`
- Add node type: `Cron`
- Rename node to: `Cron: every 30s`
- Why this node exists: Frequent telemetry scrape trigger.

| UI Field | Value |
|---|---|
| `rule` | `{"interval": [{"triggerAtSecond": 30}]}` |

**Connection checklist for this node**
- Outgoing: this node output branch `0` -> `HTTP: n8n.metrics`
- Outgoing: this node output branch `0` -> `HTTP: mediamover.metrics`
- Outgoing: this node output branch `0` -> `HTTP: gateway.metrics`

### Step 2 - `HTTP: n8n.metrics`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: n8n.metrics`
- Why this node exists: Fetch n8n Prometheus metrics.

| UI Field | Value |
|---|---|
| `url` | `http://n8n:5678/metrics` |
| `responseFormat` | `string` |
| `method` | `GET` |

**Connection checklist for this node**
- Incoming: `Cron: every 30s` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.metrics`

### Step 3 - `HTTP: mediamover.metrics`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: mediamover.metrics`
- Why this node exists: Fetch Media Mover Prometheus metrics.

| UI Field | Value |
|---|---|
| `url` | `http://10.0.4.130:9101/metrics` |
| `responseFormat` | `string` |
| `method` | `GET` |

**Connection checklist for this node**
- Incoming: `Cron: every 30s` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.metrics`

### Step 4 - `HTTP: gateway.metrics`
- Add node type: `HTTP Request`
- Rename node to: `HTTP: gateway.metrics`
- Why this node exists: Fetch Gateway Prometheus metrics.

| UI Field | Value |
|---|---|
| `url` | `={{$env.GATEWAY_BASE_URL}}/metrics` |
| `responseFormat` | `string` |
| `method` | `GET` |

**Connection checklist for this node**
- Incoming: `Cron: every 30s` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Code: parse.metrics`

### Step 5 - `Code: parse.metrics`
- Add node type: `Code`
- Rename node to: `Code: parse.metrics`
- Why this node exists: Parse selected metrics into normalized records.

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
const parseMetric = (text, name) => {
  const m = text.match(new RegExp(`${name}\s+(\d+\.?\d*)`));
  return m ? parseFloat(m[1]) : null;
};

const ts = new Date().toISOString();
const items = [];
const n8n = $('HTTP: n8n.metrics').first().json.data;
const mm = $('HTTP: mediamover.metrics').first().json.data;
const gw = $('HTTP: gateway.metrics').first().json.data;

items.push({json: {ts, src: 'n8n', metric: 'active_executions', value: parseMetric(n8n, 'n8n_active_executions')}});
items.push({json: {ts, src: 'media_mover', metric: 'promote_total', value: parseMetric(mm, 'media_mover_promote_total')}});
items.push({json: {ts, src: 'gateway', metric: 'queue_depth', value: parseMetric(gw, 'gateway_queue_depth')}});

return items.filter(i => i.json.value !== null);
```

**Connection checklist for this node**
- Incoming: `HTTP: n8n.metrics` output branch `0` -> this node
- Incoming: `HTTP: mediamover.metrics` output branch `0` -> this node
- Incoming: `HTTP: gateway.metrics` output branch `0` -> this node
- Outgoing: this node output branch `0` -> `Postgres: store.metrics`

### Step 6 - `Postgres: store.metrics`
- Add node type: `Postgres`
- Rename node to: `Postgres: store.metrics`
- Why this node exists: Persist telemetry samples to database.

| UI Field | Value |
|---|---|
| `operation` | `insert` |
| `table` | `obs_samples` |
| `columns` | `ts, src, metric, value` |

**Credential binding**
- `postgres` -> `PostgreSQL - reachy_local`

**Connection checklist for this node**
- Incoming: `Code: parse.metrics` output branch `0` -> this node

## Step 2: Wire Connections Exactly
Use this source -> target list to verify every edge in the canvas.
- `Cron: every 30s` branch `0` -> `HTTP: n8n.metrics`
- `Cron: every 30s` branch `0` -> `HTTP: mediamover.metrics`
- `Cron: every 30s` branch `0` -> `HTTP: gateway.metrics`
- `HTTP: n8n.metrics` branch `0` -> `Code: parse.metrics`
- `HTTP: mediamover.metrics` branch `0` -> `Code: parse.metrics`
- `HTTP: gateway.metrics` branch `0` -> `Code: parse.metrics`
- `Code: parse.metrics` branch `0` -> `Postgres: store.metrics`

## Step 3: Activation and Smoke Test
1. Save the workflow.
2. Click **Test workflow** in n8n and send a test request to the webhook path(s) listed above.
3. Verify each node turns green and inspect node output data for contract fields (`correlation_id`, status fields, IDs).
4. Activate the workflow only after successful webhook-test execution.

## Codebase Alignment Notes
- This guide is generated from v3 workflow JSON and should match current backend endpoint contracts.
- If runtime behavior differs, verify router implementation in `apps/api/app/routers/*` and `apps/api/routers/gateway.py` before modifying node logic.
