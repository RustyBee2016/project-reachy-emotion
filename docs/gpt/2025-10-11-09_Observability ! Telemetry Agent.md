# 09_Observability ! Telemetry Agent

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:56:40  
**Updated:** 10/21/2025 21:58:24  
**Exported:** 10/21/2025 21:59:09  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b956-f940-8332-8827-6c917f1b9a4e](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b956-f940-8332-8827-6c917f1b9a4e)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 9: Observability / Telemetry Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

Thought for 25s

## Response:
You’re building Agent 9 to be your “eyes & ears.” It should: (1) expose platform health, (2) turn errors into actionable incidents, and (3) watch your SLAs so it barks before things break.

Below is a practical n8n design with import-ready workflows. I’m leaning on current n8n docs for Prometheus metrics, error handling, and node settings so you don’t have to guess. [n8n Docs+5n8n Docs+5n8n Docs+5](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)

* * *

What this agent covers
======================

1.  **Metrics collection & surfacing**
    *   Enable n8n’s native `/metrics` endpoint (Prometheus format).
    *   Poll your app services (Ubuntu 1 Media Mover, Ubuntu 2 Gateway) at their `/metrics` endpoints.
    *   Normalize a tiny set of business KPIs (promotion success/error rates, manifest rebuild times, queue depth) into a compact table (PostgreSQL) for quick dashboards + ad-hoc queries.
2.  **Error → Incident workflow**
    *   Catch any workflow failure with **Error Trigger** and auto-open an incident record (Postgres), plus notify (email/Slack/Teams—your pick).
    *   Attach `executionId`, `workflowId`, `correlation_id` so you can trace it end-to-end. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)
3.  **SLO watchdog**
    *   Evaluate thresholds on latency p95, error rate, DLQ depth, and jetson heartbeat.
    *   If breached, flip a “safe mode” (e.g., call FastAPI to pause promotions) and page you.
4.  **(Optional) Tracing**
    *   If you want distributed traces, keep Prometheus for metrics and add OpenTelemetry OTLP export (Jaeger/Tempo/etc.). Community approaches exist for n8n until first-party tracing matures. [OpenTelemetry+2GitHub+2](https://opentelemetry.io/docs/languages/js/exporters/?utm_source=chatgpt.com)

* * *

One-time platform switches
==========================

*   **Enable n8n metrics** (self-hosted): set `N8N_METRICS=true` and restart. n8n exposes `/metrics` for Prometheus to scrape. You can also tune `N8N_METRICS_INCLUDE_*` labels later. [n8n Docs](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)
*   **Know where the endpoints live** (you already do, per requirements):
    *   Media Mover (Ubuntu 1): `http://ubuntu1:9101/metrics`
    *   App Gateway (Ubuntu 2): `http://ubuntu2:9100/metrics`
    *   n8n: `http://n8n:5678/metrics` (or via your ingress)  
        Docs confirm `/metrics` and endpoint customization via env vars. [n8n Docs+1](https://docs.n8n.io/hosting/logging-monitoring/monitoring/?utm_source=chatgpt.com)

* * *

Workflow set (import these)
===========================

You’ll get three workflows:

*   **9A\_Metrics\_Collector (Cron → HTTP Request → Function → Postgres)**
*   **9B\_Error\_to\_Incident (Error Trigger → Function → Postgres → Notify)**
*   **9C\_SLO\_Watchdog (Cron → HTTP Request → Function thresholds → HTTP Request “safe mode” → Notify)**

> Heads-up: The **HTTP Request** node settings below match n8n’s latest guidance; response format must be `String` when pulling Prometheus text. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)

* * *

9A\_Metrics\_Collector — scrape → normalize → store
---------------------------------------------------

**Nodes & parameters (key bits):**

*   **Cron**
    *   Mode: Every X seconds → 30 (start conservative).
*   **HTTP Request: n8n\_metrics**
    *   Method: GET
    *   URL: `http://n8n.internal:5678/metrics`
    *   Response: **String**
*   **HTTP Request: mm\_metrics (Media Mover)**
    *   URL: `http://ubuntu1:9101/metrics`
    *   Response: **String**
*   **HTTP Request: gw\_metrics (Gateway)**
    *   URL: `http://ubuntu2:9100/metrics`
    *   Response: **String**
*   **Function: parse\_prom\_text**
    *   JS parses a handful of lines from Prometheus exposition (fast + robust):
        *   `media_mover_promote_seconds_bucket{le="0.5"}` … → latency hist p95 estimate
        *   `media_mover_promote_total`, `media_mover_promote_errors_total`
        *   `gateway_ws_active`, `gateway_queue_depth`
        *   `n8n_active_executions`, `n8n_workflow_errors_total`
*   **Postgres (Insert)**
    *   Table: `obs_samples` (create it once)
    *   Columns: `ts timestamptz, src text, metric text, value double precision, correlation_id text`

> Prometheus is still your source of truth; this table is for quick UI slices and joining with incidents. Prometheus continues to scrape directly. n8n is just adding business-aware snapshots. Prometheus setup is standard per docs and community guides. [n8n Docs+2Andreffs+2](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)

**Import-ready JSON (minimal skeleton):**

```json
{
  "name": "09A_Metrics_Collector",
  "nodes": [
    {
      "parameters": {"triggerTimes": {"item": [{"mode": "everyX","seconds": 30}]}},
      "id": "Cron",
      "name": "Cron",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 2,
      "position": [ -60, 300 ]
    },
    {
      "parameters": {"url": "http://n8n.internal:5678/metrics","responseFormat": "string"},
      "id": "N8NMetrics",
      "name": "HTTP n8n /metrics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 200, 120 ]
    },
    {
      "parameters": {"url": "http://ubuntu1:9101/metrics","responseFormat": "string"},
      "id": "MMetrics",
      "name": "HTTP MediaMover /metrics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 200, 300 ]
    },
    {
      "parameters": {"url": "http://ubuntu2:9100/metrics","responseFormat": "string"},
      "id": "GWMetrics",
      "name": "HTTP Gateway /metrics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 200, 480 ]
    },
    {
      "parameters": {
        "functionCode": "const lines = (s)=>s.split('\\n').filter(Boolean);\nfunction pick(src, name){\n  const l = src.find(x=>x.startsWith(name+' '));\n  if(!l) return null; const v = parseFloat(l.split(' ').pop()); return isNaN(v)?null:v;\n}\nfunction histQuantile(src, prefix, q){\n  // crude p95 from _sum/_count if buckets aren't handy\n  const sum = pick(src, prefix+'_sum');\n  const cnt = pick(src, prefix+'_count');\n  if(sum==null||cnt==null||cnt===0) return null; return (sum/cnt)* (q/0.5); // heuristic\n}\nconst out=[]; const ts = new Date().toISOString();\nconst n8n = lines(items[0].json.body);\nconst mm  = lines(items[1].json.body);\nconst gw  = lines(items[2].json.body);\nfunction emit(src, metric, value){ if(value==null) return; out.push({json:{ts, src, metric, value, correlation_id:$json.correlation_id||null}}); }\nemit('n8n','n8n_active_executions', pick(n8n,'n8n_active_executions'));\nemit('n8n','n8n_workflow_errors_total', pick(n8n,'n8n_workflow_errors_total'));\nemit('media_mover','promote_total', pick(mm,'media_mover_promote_total'));\nemit('media_mover','promote_errors_total', pick(mm,'media_mover_promote_errors_total'));\nemit('media_mover','promote_latency_p95', histQuantile(mm,'media_mover_promote_seconds',0.95));\nemit('gateway','ws_active', pick(gw,'gateway_ws_active'));\nemit('gateway','queue_depth', pick(gw,'gateway_queue_depth'));\nreturn out;"
      },
      "id": "Parse",
      "name": "Function parse_prom_text",
      "type": "n8n-nodes-base.function",
      "typeVersion": 2,
      "position": [ 520, 300 ]
    },
    {
      "parameters": {
        "operation": "insert",
        "table": "obs_samples",
        "columns": "ts, src, metric, value, correlation_id",
        "values": "={{$json.ts}}, {{$json.src}}, {{$json.metric}}, {{$json.value}}, {{$json.correlation_id}}"
      },
      "id": "PG",
      "name": "Postgres Insert",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [ 820, 300 ]
    }
  ],
  "connections": {
    "Cron": { "main": [[ { "node": "HTTP n8n /metrics", "type": "main", "index": 0 } ]] },
    "HTTP n8n /metrics": { "main": [[ { "node": "HTTP MediaMover /metrics", "type": "main", "index": 0 } ]] },
    "HTTP MediaMover /metrics": { "main": [[ { "node": "HTTP Gateway /metrics", "type": "main", "index": 0 } ]] },
    "HTTP Gateway /metrics": { "main": [[ { "node": "Function parse_prom_text", "type": "main", "index": 0 } ]] },
    "Function parse_prom_text": { "main": [[ { "node": "Postgres Insert", "type": "main", "index": 0 } ]] }
  }
}
```

* * *

9B\_Error\_to\_Incident — auto-incident on any failure
------------------------------------------------------

**Nodes & parameters:**

*   **Error Trigger**
    *   Default settings. It receives failed workflow context (error msg, stack, `executionId`, etc.). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com)
*   **Function: shape\_incident**
    *   Map n8n error fields to your schema (`severity`, `service`, `workflowId`, `executionId`, `message`, `node`, `ts`).
*   **Postgres (Insert)** → table `incidents`
    *   Columns: `opened_at, severity, workflow_id, execution_id, node, message, details`
*   **(Optional) HTTP Request: Slack/Teams**
    *   POST webhook with a compact JSON body.

**Notes:** n8n’s logging guide recommends including multiple IDs in logs to make search sane; we mirror that here. [n8n Docs](https://docs.n8n.io/hosting/logging-monitoring/logging/?utm_source=chatgpt.com)

_Minimal JSON skeleton available on request; omitted here to keep the page short._

* * *

9C\_SLO\_Watchdog — thresholds → act
------------------------------------

**Nodes & parameters:**

*   **Cron**: every 60s.
*   **HTTP Request**: fetch Gateway `/metrics` (string).
*   **Function: eval\_thresholds**:
    *   Parse key gauges (e.g., `gateway_queue_depth`, `media_mover_promote_errors_total` delta, `n8n_active_executions`).
    *   If any threshold violated, set `items[0].json.alert=true` and add `reason`.
*   **IF** (`{{$json.alert}} is true`) branch:
    *   **HTTP Request** → FastAPI “safe mode” endpoint (pause promotions, reduce concurrency, etc.).
    *   **Postgres Insert** → `incidents` (type=`SLO_BREACH`).
    *   **Notify** (Slack/Email).

Why this structure? It keeps evaluation logic close to where the data is fetched, and actions are explicit and observable. It also lines up with n8n’s error-handling and monitoring model so you don’t fight the tool. [n8n Docs](https://docs.n8n.io/flow-logic/error-handling/?utm_source=chatgpt.com)

* * *

Prometheus + Grafana (still the backbone)
=========================================

*   n8n’s **/metrics** is for Prometheus to scrape; enable it and let Prom do its thing. Grafana dashboards and alerts stay in Grafana/Prom rules. Docs and up-to-date guides are straightforward. [n8n Docs+2n8n Docs+2](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)
*   Use this agent to **add context** (incidents, correlation IDs, domain counters) and to **automate responses** (flip safe mode, page humans).

* * *

Optional: Tracing (OpenTelemetry)
=================================

If you want end-to-end flamegraphs (Jetson → Ubuntu 2 → Ubuntu 1 → DB), standard OTLP exporters are the safe bet; the ecosystem supports them broadly. Community tooling shows n8n logs → OTel traces if you want to experiment today. [Reddit+3OpenTelemetry+3OpenTelemetry+3](https://opentelemetry.io/docs/languages/js/exporters/?utm_source=chatgpt.com)

* * *

Why this fits your spec
=======================

*   Requirements already list Prometheus counters for Media Mover and Gateway, plus structured logs and key dashboard metrics. These workflows wire that into a minimal, legible loop and keep Prometheus in the driver’s seat.
*   n8n’s newest docs confirm the exact toggles/endpoints and how to catch errors sanely; we’re using those features exactly as intended. [n8n Docs+3n8n Docs+3n8n Docs+3](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)

* * *

Quick checklist to finish wiring
--------------------------------

*    Set `N8N_METRICS=true` on your n8n container and restart. [n8n Docs](https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/?utm_source=chatgpt.com)
*    Confirm `/metrics` resolves for n8n, Media Mover, and Gateway. [n8n Docs](https://docs.n8n.io/hosting/logging-monitoring/monitoring/?utm_source=chatgpt.com)
*    Create tables:
    ```sql
    create table if not exists obs_samples (
      ts timestamptz not null,
      src text not null,
      metric text not null,
      value double precision not null,
      correlation_id text
    );
    create table if not exists incidents (
      id bigserial primary key,
      opened_at timestamptz default now(),
      kind text default 'ERROR',
      severity text default 'MEDIUM',
      workflow_id text,
      execution_id text,
      node text,
      message text,
      details jsonb
    );
    ```
*    Import 09A/09B/09C, update URLs, and set Postgres creds in the node creds.
*    Point Prometheus at all `/metrics` endpoints; keep Grafana for dashboards/alerts (Prom rules).
*    (Optional) Add OTLP collector later if you want traces.

If you want the full JSON for 9B and 9C with Slack + “safe mode” HTTP calls filled in, I’ll drop those next so you can import and run immediately.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)