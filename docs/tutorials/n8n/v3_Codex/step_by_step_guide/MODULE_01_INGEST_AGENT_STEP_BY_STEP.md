# Agent 1 — Ingest Agent (Reachy 08.4.2 v3) - Step-by-Step Wiring Guide

**Source workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Related Scripts and Functionalities
- `apps/api/app/routers/ingest.py` -> `POST /api/v1/ingest/pull` (download/hash/ffprobe/thumbnail/DB insert).
- `apps/api/routers/gateway.py` -> `POST /api/events/ingest` (ingest event intake).

## Before You Start
1. Create a workflow named `Agent 1 — Ingest Agent (Reachy 08.4.2 v3)`.
2. Confirm service endpoints are reachable from n8n host:
- Media Mover: `http://10.0.4.130:8083`
- Gateway: `http://10.0.4.140:8000`
3. Confirm local trusted-network policy: no workflow-level auth gate is used for this module.

## Step 1: Add and Configure Nodes
### Step 1 - `Webhook: ingest.video`
- Node type: `Webhook`
- Rename to: `Webhook: ingest.video`

| UI Field | Value |
|---|---|
| `httpMethod` | `POST` |
| `path` | `video_gen_hook` |
| `responseMode` | `responseNode` |

### Step 2 - `Code: normalize.payload`
- Node type: `Code`
- Rename to: `Code: normalize.payload`

| UI Field | Value |
|---|---|
| `mode` | `runOnceForAllItems` |

**Code Script**
```text
const clean = (v) => (typeof v === 'string' ? v.trim() : '');
const body = $json.body ?? $json;
const sourceUrl = clean(body.source_url ?? body.url ?? body.asset?.url ?? body.data?.asset?.url);

if (!sourceUrl) throw new Error('Missing source_url in request body');

const allowedLabels = new Set(['happy', 'sad', 'neutral']);
let label = clean(body.label ?? body.emotion ?? '').toLowerCase();
if (!label) label = null;
if (label && !allowedLabels.has(label)) throw new Error(`Invalid label '${label}'. Allowed: happy, sad, neutral`);

const meta = body.meta ?? {};
const generator = clean(meta.generator ?? body.generator ?? body.source ?? 'unknown') || 'unknown';
const prompt = clean(meta.prompt ?? body.prompt ?? '');
const source = clean(meta.source ?? body.source ?? 'agent1.ingest_agent') || 'agent1.ingest_agent';

const incomingCorrelation = clean($json.headers?.['x-correlation-id']);
const correlationId = incomingCorrelation || `ing-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

const incomingIdempotency = clean($json.headers?.['idempotency-key']);
const stableSeed = `${sourceUrl}|${label ?? ''}|${generator}|${prompt}`;
let hash = 0;
for (let i = 0; i < stableSeed.length; i += 1) {
  hash = ((hash << 5) - hash) + stableSeed.charCodeAt(i);
  hash |= 0;
}
const stableIdempotency = `idem-${Math.abs(hash).toString(36)}`;
const idempotencyKey = incomingIdempotency || stableIdempotency;

return [{
  json: {
    source_url: sourceUrl,
    label,
    meta: { generator, prompt, source },
    correlation_id: correlationId,
    idempotency_key: idempotencyKey,
    issued_at: new Date().toISOString(),
    schema_version: 'v1'
  }
}];
```

### Step 3 - `HTTP: media.pull`
- Node type: `HTTP Request`
- Rename to: `HTTP: media.pull`

| UI Field | Value |
|---|---|
| `method` | `POST` |
| `url` | `http://10.0.4.130:8083/api/v1/ingest/pull` |
| `sendHeaders` | `True` |
| `headerParameters` | `Idempotency-Key={{$json.idempotency_key}}, X-Correlation-ID={{$json.correlation_id}}` |
| `sendBody` | `True` |
| `bodyParameters` | `source_url, correlation_id, intended_emotion, generator, prompt` |
| `options.timeout` | `120000` |
| `retryOnFail` | `True` |
| `maxTries` | `5` |
| `waitBetweenTries` | `1000` |

### Step 4 - `IF: status.done?`
- Node type: `If`
- Rename to: `IF: status.done?`

| UI Field | Value |
|---|---|
| `conditions` | `{{ ['done','duplicate'].includes($json.status) }} == true` |

### Step 5 - `HTTP: emit.completed`
- Node type: `HTTP Request`
- Rename to: `HTTP: emit.completed`

| UI Field | Value |
|---|---|
| `method` | `POST` |
| `url` | `http://10.0.4.140:8000/api/events/ingest` |
| `sendBody` | `True` |
| `bodyParameters` | `schema_version, event_type, source, issued_at, video_id, correlation_id, file_path, sha256, duplicate` |
| `options.timeout` | `60000` |
| `retryOnFail` | `True` |
| `maxTries` | `5` |
| `waitBetweenTries` | `1000` |

### Step 6 - `Respond: success`
- Node type: `Respond to Webhook`
- Rename to: `Respond: success`

| UI Field | Value |
|---|---|
| `respondWith` | `json` |
| `responseBody` | `{"status": $json.status || "accepted", "video_id": $json.video_id || null, "correlation_id": $json.correlation_id || null, "duplicate": $json.duplicate || false}` |
| `options.responseCode` | `200` |

## Step 2: Wire Connections Exactly
- `Webhook: ingest.video` -> `Code: normalize.payload`
- `Code: normalize.payload` -> `HTTP: media.pull`
- `HTTP: media.pull` -> `IF: status.done?`
- `IF: status.done?` true -> `HTTP: emit.completed`
- `IF: status.done?` false -> `Respond: success`
- `HTTP: emit.completed` -> `Respond: success`

## Step 3: Activation and Smoke Test
1. Save workflow and run webhook test call.
2. Verify node outputs include `correlation_id`, `idempotency_key`, `schema_version`.
3. Verify gateway event payload includes `schema_version`, `source`, `issued_at`.
4. Activate workflow only after successful end-to-end run.
